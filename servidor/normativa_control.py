"""Registro normativo verificable y recepción de cuentas para cotejo humano."""
import base64, binascii, hashlib, json, os, re, sqlite3
from fastapi import Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from server import app, admin, require, conn, now
ROOT=os.path.dirname(__file__)
REG=json.load(open(os.path.join(ROOT,'registro_normativo.json'),encoding='utf-8'))
class Entrada(BaseModel):
    codigo:str=Field(min_length=1,max_length=40)
    nombre:str=Field(min_length=2,max_length=200)
    naturaleza:str=Field(min_length=2,max_length=40)
    uso_contenido:str=Field(min_length=10,max_length=5000)
    norma:str=Field(min_length=5,max_length=100)
    anexo:str=Field(min_length=1,max_length=50)
    pagina:str=Field(min_length=1,max_length=40)
    regimen:str=Field(min_length=2,max_length=40)
class Lote(BaseModel):
    version:str=Field(min_length=2,max_length=80)
    cuentas:list[Entrada]=Field(min_length=1,max_length=6000)
def setup():
  with conn() as c:
    c.execute("CREATE TABLE IF NOT EXISTS normativa_lotes(id INTEGER PRIMARY KEY, version TEXT NOT NULL, estado TEXT NOT NULL, fecha TEXT NOT NULL, usuario TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS normativa_cuentas(id INTEGER PRIMARY KEY, lote_id INTEGER NOT NULL, codigo TEXT NOT NULL, nombre TEXT NOT NULL, naturaleza TEXT NOT NULL, uso_contenido TEXT NOT NULL, norma TEXT NOT NULL, anexo TEXT NOT NULL, pagina TEXT NOT NULL, regimen TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'PENDIENTE_COTEJO', UNIQUE(lote_id,codigo,regimen))")
    c.execute("CREATE TABLE IF NOT EXISTS normativa_documentos(id INTEGER PRIMARY KEY, norma TEXT NOT NULL, filename TEXT NOT NULL, content BLOB NOT NULL, sha256 TEXT NOT NULL, uploaded_at TEXT NOT NULL, user_id INTEGER NOT NULL REFERENCES users(id), estado TEXT NOT NULL DEFAULT 'PENDIENTE_COTEJO')")
setup()

class NormDocument(BaseModel):
    norma:str=Field(min_length=5,max_length=40)
    filename:str=Field(min_length=1,max_length=160)
    file_b64:str

@app.post('/api/admin/contabilidad/normativa/documentos')
def subir_documento(x:NormDocument,authorization:str|None=Header(None)):
    u=admin(authorization)
    valid={v['id'] for v in REG['instrumentos'] if v['estado_verificacion']!='derogada'}
    if x.norma not in valid:raise HTTPException(422,'Norma no registrada para cotejo')
    if len(x.file_b64)>7*1024*1024:raise HTTPException(413,'Archivo superior a 5 MiB')
    try:raw=base64.b64decode(x.file_b64,validate=True)
    except (binascii.Error,ValueError):raise HTTPException(422,'Archivo codificado incorrectamente')
    if not raw.startswith(b'%PDF-') or b'%%EOF' not in raw[-1024:] or len(raw)>5*1024*1024:
        raise HTTPException(422,'Se requiere PDF válido de hasta 5 MiB')
    filename=re.sub(r'[^A-Za-z0-9 _.-]','_',x.filename.replace('\\','/').split('/')[-1]).strip(' .')[:120]
    if not filename.lower().endswith('.pdf'):filename=(filename[:110] or 'norma')+'.pdf'
    digest=hashlib.sha256(raw).hexdigest()
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        cur=c.execute('INSERT INTO normativa_documentos(norma,filename,content,sha256,uploaded_at,user_id) VALUES(?,?,?,?,?,?)',
                      (x.norma,filename,raw,digest,now(),u['id']))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',
                  (now(),u['id'],'upload_normativa_documento',json.dumps({'id':cur.lastrowid,'norma':x.norma,'sha256':digest})))
        c.commit()
    return {'id':cur.lastrowid,'estado':'PENDIENTE_COTEJO','sha256':digest}

@app.get('/api/admin/contabilidad/normativa/documentos')
def listar_documentos(authorization:str|None=Header(None)):
    admin(authorization)
    with conn() as c:
        rows=c.execute('SELECT id,norma,filename,sha256,uploaded_at,estado,length(content) size_bytes FROM normativa_documentos ORDER BY id DESC').fetchall()
    return {'documentos':[dict(r) for r in rows]}

@app.get('/api/admin/contabilidad/normativa/documentos/{doc_id}/download')
def bajar_documento(doc_id:int,authorization:str|None=Header(None)):
    admin(authorization)
    with conn() as c:row=c.execute('SELECT * FROM normativa_documentos WHERE id=?',(doc_id,)).fetchone()
    if not row:raise HTTPException(404,'Documento inexistente')
    if hashlib.sha256(row['content']).hexdigest()!=row['sha256']:
        raise HTTPException(409,'Documento alterado; revise el respaldo')
    return Response(row['content'],media_type='application/pdf',headers={
        'Content-Disposition':f'attachment; filename="norma-{doc_id}.pdf"'})
@app.get('/api/contabilidad/normativa/registro')
def registro_normativo(authorization:str|None=Header(None)):
    require(authorization)
    return REG
@app.post('/api/admin/contabilidad/normativa/lotes')
def importar_lote(x:Lote,authorization:str|None=Header(None)):
    u=admin(authorization)
    ids=[(z.codigo,z.regimen) for z in x.cuentas]
    if len(ids)!=len(set(ids)):raise HTTPException(422,'Cuentas duplicadas dentro del regimen')
    if any(not re.fullmatch(r'[0-9A-Za-z._-]+',z.codigo) for z in x.cuentas):raise HTTPException(422,'Codigo invalido')
    valid={v['id'] for v in REG['instrumentos'] if v['estado_verificacion']!='derogada'}
    if any(z.norma not in valid for z in x.cuentas):raise HTTPException(422,'Norma no registrada; revisar antes de importar')
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        cur=c.execute('INSERT INTO normativa_lotes(version,estado,fecha,usuario) VALUES(?,?,?,?)',(x.version,'PENDIENTE_COTEJO',now(),str(u['id'])))
        lid=cur.lastrowid
        for z in x.cuentas:
            c.execute('INSERT INTO normativa_cuentas(lote_id,codigo,nombre,naturaleza,uso_contenido,norma,anexo,pagina,regimen) VALUES(?,?,?,?,?,?,?,?,?)',(lid,z.codigo,z.nombre,z.naturaleza,z.uso_contenido,z.norma,z.anexo,z.pagina,z.regimen))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'normativa_lote_pendiente',f'lote {lid} version {x.version}: {len(x.cuentas)}'))
        c.commit()
    return {'lote':lid,'cuentas':len(x.cuentas),'estado':'PENDIENTE_COTEJO','utilizable_en_asientos':False}
@app.get('/api/admin/contabilidad/normativa/lotes')
def consultar_lotes(authorization:str|None=Header(None)):
    admin(authorization)
    with conn() as c:
        rows=c.execute('SELECT l.id,l.version,l.estado,l.fecha,COUNT(a.id) total FROM normativa_lotes l LEFT JOIN normativa_cuentas a ON a.lote_id=l.id GROUP BY l.id ORDER BY l.id DESC').fetchall()
    return {'lotes':[dict(r) for r in rows]}
