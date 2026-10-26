"""Custodia local del vector fiscal y revisión explícita de sus conceptos.

El archivo de ONAT se conserva como evidencia. No se interpreta automáticamente.
"""
import base64
import binascii
import datetime
import hashlib
import json
import re

from fastapi import Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from server import app, admin, business_today, conn, now
from extension import licensed

MAX_VECTOR_BYTES = 5 * 1024 * 1024
ACTORS = {'tcp', 'mipyme', 'cna', 'pdl', 'estatal'}
ALLOWED = {
    'tcp': {'sales_services', 'tcp_personal_advance'},
    'mipyme': {'sales_services', 'profit', 'workforce', 'employer_social', 'territorial'},
    'cna': {'sales_services', 'profit'},
    'pdl': {'sales_services', 'profit', 'workforce', 'employer_social'},
    'estatal': {'sales_services', 'profit'},
}

with conn() as c:
    c.execute('''CREATE TABLE IF NOT EXISTS fiscal_vectors(
        id INTEGER PRIMARY KEY, actor TEXT NOT NULL, nit TEXT NOT NULL, filename TEXT NOT NULL,
        mime TEXT NOT NULL, content BLOB NOT NULL, sha256 TEXT NOT NULL, approved_on TEXT NOT NULL,
        uploaded_at TEXT NOT NULL, uploaded_by INTEGER NOT NULL REFERENCES users(id),
        status TEXT NOT NULL CHECK(status IN ('pending','reviewed')),
        situation TEXT, obligations_json TEXT, valid_from TEXT, valid_to TEXT,
        review_note TEXT, reviewed_at TEXT, reviewed_by INTEGER REFERENCES users(id))''')


class VectorUpload(BaseModel):
    actor: str
    nit: str = Field(min_length=5, max_length=40)
    approved_on: datetime.date
    filename: str = Field(min_length=1, max_length=160)
    file_b64: str


class VectorReview(BaseModel):
    vector_id: int = Field(gt=0)
    situation: str
    obligations: list[str] = Field(min_length=1)
    valid_from: datetime.date
    valid_to: datetime.date
    review_note: str = Field(min_length=10, max_length=1000)


def public_row(row):
    if not row:
        return None
    keys = ('id', 'actor', 'nit', 'filename', 'mime', 'sha256', 'approved_on',
            'uploaded_at', 'status', 'situation', 'valid_from', 'valid_to',
            'review_note', 'reviewed_at')
    result = {key: row[key] for key in keys}
    result['obligations'] = json.loads(row['obligations_json']) if row['obligations_json'] else []
    result['size_bytes'] = len(row['content'])
    return result


def latest_vector():
    with conn() as c:
        return c.execute('SELECT * FROM fiscal_vectors ORDER BY id DESC LIMIT 1').fetchone()


@app.get('/api/fiscal/vector')
def vector_info(authorization: str | None = Header(None)):
    licensed(authorization)
    return {'vector': public_row(latest_vector()),
            'notice': 'El archivo se conserva en esta instalación. Un administrador revisa la clasificación; el sistema no lee ni certifica automáticamente su contenido.'}


@app.post('/api/fiscal/vector')
def vector_upload(x: VectorUpload, authorization: str | None = Header(None)):
    user = licensed(authorization)
    if x.actor not in ACTORS:
        raise HTTPException(422, 'Actor sin reglas fiscales automatizadas')
    nit = x.nit.strip().upper()
    if not re.fullmatch(r'[A-Z0-9-]{5,40}', nit):
        raise HTTPException(422, 'Identificador tributario inválido')
    if x.approved_on > business_today():
        raise HTTPException(422, 'La fecha de aprobación no puede ser futura')
    if len(x.file_b64) > ((MAX_VECTOR_BYTES + 2) // 3) * 4 + 8:
        raise HTTPException(413, 'Vector fiscal superior a 5 MiB')
    try:
        raw = base64.b64decode(x.file_b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, 'Archivo codificado incorrectamente')
    if not raw or len(raw) > MAX_VECTOR_BYTES:
        raise HTTPException(413, 'Vector fiscal vacío o superior a 5 MiB')
    if raw.startswith(b'%PDF-'):
        mime, ext = 'application/pdf', '.pdf'
    elif raw.startswith(b'\x89PNG\r\n\x1a\n'):
        mime, ext = 'image/png', '.png'
    elif raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'):
        mime, ext = 'image/jpeg', '.jpg'
    else:
        raise HTTPException(422, 'Solo se admiten PDF, PNG o JPEG reconocibles')
    filename = re.sub(r'[^A-Za-z0-9 _.-]', '_', x.filename.replace('\\', '/').split('/')[-1]).strip(' .')[:120]
    if not filename.lower().endswith(ext):
        filename = (filename[:110] or 'vector-fiscal') + ext
    digest = hashlib.sha256(raw).hexdigest()
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        issuer = c.execute('SELECT actor,tax_id FROM issuer WHERE id=1').fetchone()
        if issuer and (issuer['actor'] != x.actor or issuer['tax_id'].strip().upper() != nit):
            raise HTTPException(422, 'Actor y NIT del vector deben coincidir con el emisor configurado')
        cur = c.execute('''INSERT INTO fiscal_vectors(
            actor,nit,filename,mime,content,sha256,approved_on,uploaded_at,uploaded_by,status)
            VALUES(?,?,?,?,?,?,?,?,?,?)''',
            (x.actor, nit, filename, mime, raw, digest, str(x.approved_on), now(), user['id'], 'pending'))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',
                  (now(), user['id'], 'upload_fiscal_vector', json.dumps({'id': cur.lastrowid, 'sha256': digest})))
        c.commit()
    return {'id': cur.lastrowid, 'status': 'pending', 'sha256': digest}


@app.get('/api/fiscal/vector/download')
def vector_download(authorization: str | None = Header(None)):
    licensed(authorization)
    row = latest_vector()
    if not row:
        raise HTTPException(404, 'No hay vector fiscal')
    if hashlib.sha256(row['content']).hexdigest() != row['sha256']:
        raise HTTPException(409, 'El archivo no coincide con su huella; revise la copia de seguridad')
    extension = {'application/pdf': '.pdf', 'image/png': '.png', 'image/jpeg': '.jpg'}[row['mime']]
    return Response(row['content'], media_type=row['mime'], headers={
        'Content-Disposition': 'attachment; filename="vector-fiscal-' + str(row['id']) + extension + '"',
    })


@app.post('/api/admin/fiscal/vector/review')
def vector_review(x: VectorReview, authorization: str | None = Header(None)):
    user = admin(authorization)
    if x.valid_from > x.valid_to:
        raise HTTPException(422, 'Vigencia inválida')
    if len(x.review_note.strip()) < 10:
        raise HTTPException(422, 'Documente el cotejo de los conceptos con el vector')
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT * FROM fiscal_vectors ORDER BY id DESC LIMIT 1').fetchone()
        if not row or row['id'] != x.vector_id:
            raise HTTPException(409, 'Solo puede revisarse el vector más reciente')
        if row['status'] != 'pending':
            raise HTTPException(409, 'Este vector ya fue revisado')
        if x.situation not in {'standard', 'pdl_minindustry_food', 'state_retail_to_population'}:
            raise HTTPException(422, 'Situación no reconocida')
        if x.situation == 'pdl_minindustry_food' and row['actor'] != 'pdl':
            raise HTTPException(422, 'Situación incompatible con actor')
        if row['actor'] == 'estatal' and x.situation != 'state_retail_to_population':
            raise HTTPException(422, 'Entidad estatal solo en venta minorista o servicio a población')
        if row['actor'] != 'estatal' and x.situation == 'state_retail_to_population':
            raise HTTPException(422, 'Situación estatal incompatible')
        obligations = set(x.obligations)
        if len(obligations) != len(x.obligations) or not obligations <= ALLOWED[row['actor']]:
            raise HTTPException(422, 'Conceptos duplicados o incompatibles con el actor')
        c.execute('''UPDATE fiscal_vectors SET status='reviewed',situation=?,obligations_json=?,
            valid_from=?,valid_to=?,review_note=?,reviewed_at=?,reviewed_by=? WHERE id=?''',
            (x.situation, json.dumps(sorted(obligations)), str(x.valid_from), str(x.valid_to),
             x.review_note.strip(), now(), user['id'], x.vector_id))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',
                  (now(), user['id'], 'review_fiscal_vector', json.dumps({'id': x.vector_id, 'obligations': sorted(obligations)})))
        c.commit()
    return {'id': x.vector_id, 'status': 'reviewed', 'obligations': sorted(obligations),
            'notice': 'Clasificación administrativa para simulación, no aprobación oficial de ONAT'}


def current_vector(actor, month, situation):
    row = latest_vector()
    if not row or row['status'] != 'reviewed':
        raise HTTPException(409, 'Suba el vector fiscal aprobado y espere su revisión administrativa')
    if row['actor'] != actor or row['situation'] != situation:
        raise HTTPException(422, 'El actor o la situación no coinciden con el vector revisado')
    first = month + '-01'
    import calendar
    year, number = map(int, month.split('-'))
    last = f'{month}-{calendar.monthrange(year, number)[1]:02d}'
    if row['valid_from'] > first or row['valid_to'] < last:
        raise HTTPException(422, 'El vector no cubre el mes completo; revise vigencia y transición')
    return set(json.loads(row['obligations_json']))
