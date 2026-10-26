"""JB360 shared operations pilot. NOT a certified fiscal accounting engine."""
import os, sqlite3, hmac, hashlib, secrets, datetime, json, csv, io, time, tempfile
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from starlette.background import BackgroundTask
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

DB=os.environ.get('JB360_DB','jb360_shared.sqlite3')
ADMIN_PASSWORD=os.environ.get('JB360_ADMIN_PASSWORD')
app=FastAPI(title='JB360 operaciones compartidas - piloto')
allowed_hosts=[x.strip() for x in os.environ.get('JB360_ALLOWED_HOSTS','127.0.0.1,localhost,testserver').split(',') if x.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

@app.middleware('http')
async def security_headers(request:Request,call_next):
    length=request.headers.get('content-length','')
    if length.isdigit() and int(length)>8*1024*1024:
        response=JSONResponse({'detail':'Solicitud demasiado grande'},status_code=413)
    else:
        response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    response.headers['Cross-Origin-Opener-Policy']='same-origin'
    response.headers['Cross-Origin-Resource-Policy']='same-origin'
    response.headers['Content-Security-Policy']="default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; form-action 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'"
    response.headers['Cache-Control']='no-store'
    if request.url.scheme=='https':
        response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    return response

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def business_today(): return datetime.datetime.now(ZoneInfo('America/Havana')).date()
def cents(v):
    try:
        d=Decimal(str(v)); n=d.quantize(Decimal('0.01'))
        if not d.is_finite() or d!=n or d<=0: raise ValueError()
        return int(n*100)
    except (InvalidOperation,ValueError,TypeError): raise HTTPException(422,'Importe positivo con dos decimales como máximo')

def conn():
    c=sqlite3.connect(os.environ.get('JB360_DB',DB),timeout=30,isolation_level=None)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA busy_timeout=30000');c.execute('PRAGMA foreign_keys=ON')
    return c

def init():
    with conn() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','operator')));
        CREATE TABLE IF NOT EXISTS tokens(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS operations(id INTEGER PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('income','expense')),category TEXT NOT NULL, description TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0),payment TEXT NOT NULL, point TEXT NOT NULL, reference TEXT NOT NULL, actor TEXT NOT NULL, recorded_at TEXT NOT NULL, effective_date TEXT NOT NULL, user_id INTEGER NOT NULL REFERENCES users(id), reversal_of INTEGER REFERENCES operations(id), UNIQUE(reversal_of));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT NOT NULL,user_id INTEGER NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS login_failures(id INTEGER PRIMARY KEY,username TEXT NOT NULL,ip TEXT NOT NULL,at_epoch INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS ix_login_failures ON login_failures(username,ip,at_epoch);
        CREATE INDEX IF NOT EXISTS ix_operations_period ON operations(effective_date,point,kind);
        ''')

def hashpw(p,s): return hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(s),250000).hex()
def require(auth, allow_expired=False):
    if not auth or not auth.startswith('Bearer '): raise HTTPException(401,'Se requiere sesión')
    with conn() as c:
        row=c.execute('SELECT users.*,tokens.created_at AS token_created_at FROM tokens JOIN users ON users.id=tokens.user_id WHERE tokens.token_hash=?',(hashlib.sha256(auth[7:].encode()).hexdigest(),)).fetchone()
    if row is None: raise HTTPException(401,'Sesión inválida')
    created=datetime.datetime.fromisoformat(row['token_created_at'])
    if datetime.datetime.now(datetime.timezone.utc)-created>datetime.timedelta(hours=12):
        raise HTTPException(401,'Sesión caducada; inicie sesión de nuevo')
    if row['role']!='admin' and not allow_expired:
        with conn() as c:
            try: license_row=c.execute('SELECT expires_on FROM license_state WHERE id=1').fetchone()
            except sqlite3.OperationalError: license_row=None
        if license_row and business_today()>=datetime.date.fromisoformat(license_row['expires_on']):
            raise HTTPException(402,'Licencia vencida. Solicite renovación al administrador.')
    return row

def admin(auth):
    u=require(auth,allow_expired=True)
    if u['role']!='admin':raise HTTPException(403,'Solo administrador')
    return u

class Login(BaseModel): username:str=Field(min_length=1,max_length=60); password:str=Field(min_length=1,max_length=128)
class UserNew(BaseModel):username:str=Field(min_length=3,max_length=60);password:str=Field(min_length=12,max_length=128);role:str='operator'
class Operation(BaseModel):kind:str;category:str=Field(min_length=1,max_length=80);description:str=Field(min_length=1,max_length=300);amount:str;payment:str=Field(min_length=1,max_length=40);point:str=Field(min_length=1,max_length=80);reference:str=Field(min_length=1,max_length=100);actor:str=Field(min_length=1,max_length=30);effective_date:datetime.date
class Reverse(BaseModel):reason:str=Field(min_length=5,max_length=500)
class BackupRequest(BaseModel):password:str

@app.on_event('startup')
def start():
    init()
    with conn() as c:
        if not c.execute('SELECT 1 FROM users').fetchone():
            if not ADMIN_PASSWORD or len(ADMIN_PASSWORD)<14:
                raise RuntimeError('Configure JB360_ADMIN_PASSWORD con al menos 14 caracteres antes del primer arranque')
            s=secrets.token_hex(16);c.execute('INSERT INTO users(username,salt,password_hash,role) VALUES(?,?,?,?)',('admin',s,hashpw(ADMIN_PASSWORD,s),'admin'))

@app.post('/api/login')
def login(x:Login,request:Request):
    ip=request.client.host if request.client else 'unknown'
    epoch=int(time.time())
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('DELETE FROM login_failures WHERE at_epoch<?',(epoch-900,))
        failed=c.execute('SELECT COUNT(*) FROM login_failures WHERE username=? AND ip=?',(x.username,ip)).fetchone()[0]
        if failed>=5:raise HTTPException(429,'Demasiados intentos; espere quince minutos')
        u=c.execute('SELECT * FROM users WHERE username=?',(x.username,)).fetchone()
        candidate=hashpw(x.password,u['salt'] if u else '00'*16)
        if not u or not hmac.compare_digest(u['password_hash'],candidate):
            c.execute('INSERT INTO login_failures(username,ip,at_epoch) VALUES(?,?,?)',(x.username,ip,epoch))
            c.commit()
            raise HTTPException(401,'Credenciales incorrectas')
        c.execute('DELETE FROM login_failures WHERE username=? AND ip=?',(x.username,ip))
        t=secrets.token_urlsafe(40);c.execute('INSERT INTO tokens VALUES(?,?,?)',(hashlib.sha256(t.encode()).hexdigest(),u['id'],now()))
        c.commit()
        return {'token':t,'role':u['role']}

@app.post('/api/logout')
def logout(authorization:str|None=Header(None)):
    require(authorization,allow_expired=True)
    with conn() as c:c.execute('DELETE FROM tokens WHERE token_hash=?',(hashlib.sha256(authorization[7:].encode()).hexdigest(),))
    return {'ok':True}

@app.post('/api/users')
def create_user(x:UserNew,authorization:str|None=Header(None)):
    u=admin(authorization)
    if x.role!='operator':raise HTTPException(422,'Solo se pueden crear operadores desde la aplicación')
    s=secrets.token_hex(16)
    with conn() as c:
        try:c.execute('INSERT INTO users(username,salt,password_hash,role) VALUES(?,?,?,?)',(x.username,s,hashpw(x.password,s),x.role))
        except sqlite3.IntegrityError:raise HTTPException(409,'Usuario existente')
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'create_user',x.username))
    return {'ok':True}

@app.post('/api/operations')
def operation(x:Operation,authorization:str|None=Header(None)):
    u=require(authorization)
    if x.kind not in ('income','expense'):raise HTTPException(422,'Tipo inválido')
    if x.actor not in ('tcp','mipyme','cna','pdl','estatal','otro'):raise HTTPException(422,'Actor económico no reconocido')
    if x.payment not in ('Efectivo','Transferencia','Tarjeta','Otro'):raise HTTPException(422,'Medio de pago no reconocido')
    if x.effective_date>business_today():raise HTTPException(422,'Fecha futura no permitida')
    a=cents(x.amount)
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        cur=c.execute('INSERT INTO operations(kind,category,description,amount_cents,payment,point,reference,actor,recorded_at,effective_date,user_id,reversal_of) VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)',(x.kind,x.category,x.description,a,x.payment,x.point,x.reference,x.actor,now(),str(x.effective_date),u['id']))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'create_operation',str(cur.lastrowid)))
        c.commit()
    return {'id':cur.lastrowid,'ok':True}

@app.post('/api/operations/{op_id}/reverse')
def reverse(op_id:int,x:Reverse,authorization:str|None=Header(None)):
    u=require(authorization)
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        o=c.execute('SELECT * FROM operations WHERE id=?',(op_id,)).fetchone()
        if not o:raise HTTPException(404,'Operación inexistente')
        if u['role']!='admin' and o['user_id']!=u['id']:raise HTTPException(403,'Solo autor o administrador puede anular')
        if o['reversal_of'] is not None or c.execute('SELECT 1 FROM operations WHERE reversal_of=?',(op_id,)).fetchone():raise HTTPException(409,'Ya anulada o asiento de reversión')
        kind='expense' if o['kind']=='income' else 'income'
        cur=c.execute('INSERT INTO operations(kind,category,description,amount_cents,payment,point,reference,actor,recorded_at,effective_date,user_id,reversal_of) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(kind,o['category'],'REVERSIÓN: '+x.reason,o['amount_cents'],o['payment'],o['point'],o['reference'],o['actor'],now(),str(business_today()),u['id'],op_id))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'reverse',json.dumps({'original':op_id,'reversal':cur.lastrowid,'reason':x.reason})))
        c.commit()
    return {'reversal_id':cur.lastrowid,'ok':True}

def period_rows(start,end,point=None):
    if start>end:raise HTTPException(422,'Rango inválido')
    q='SELECT o.*,u.username FROM operations o JOIN users u ON u.id=o.user_id WHERE effective_date BETWEEN ? AND ?';args=[str(start),str(end)]
    if point:q+=' AND point=?';args.append(point)
    q+=' ORDER BY effective_date,id'
    with conn() as c:return [dict(r) for r in c.execute(q,args).fetchall()]

@app.get('/api/report')
def report(start:datetime.date,end:datetime.date,point:str|None=None,authorization:str|None=Header(None)):
    require(authorization);rows=period_rows(start,end,point)
    inc=sum((-1 if r['reversal_of'] else 1)*r['amount_cents'] for r in rows if (r['kind']=='income') != (r['reversal_of'] is not None));exp=sum((-1 if r['reversal_of'] else 1)*r['amount_cents'] for r in rows if (r['kind']=='expense') != (r['reversal_of'] is not None))
    bypoint={}
    for r in rows:
        p=bypoint.setdefault(r['point'],{'income_cents':0,'expense_cents':0,'operations':0})
        origin_kind=('expense' if r['kind']=='income' else 'income') if r['reversal_of'] else r['kind']
        p[origin_kind+'_cents']+=(-1 if r['reversal_of'] else 1)*r['amount_cents'];p['operations']+=1
    return {'from':str(start),'to':str(end),'income_cents':inc,'expense_cents':exp,'balance_cents':inc-exp,'by_point':bypoint,'rows':rows,'warning':'Registro operativo. No es DJ oficial ni libro fiscal homologado; deducibilidad y tratamiento tributario pendientes.'}

@app.get('/api/export.csv')
def export(start:datetime.date,end:datetime.date,authorization:str|None=Header(None)):
    require(authorization);rows=period_rows(start,end);out=io.StringIO();w=csv.writer(out);w.writerow(['ID','Fecha efectiva','Fecha registro UTC','Punto','Actor','Tipo','Categoría','Concepto','Importe CUP','Medio','Referencia','Usuario','Reversión de'])
    def safe(v):
        v=str(v)
        return "'"+v if v.lstrip().startswith(('=','+','-','@')) else v
    for r in rows:w.writerow([r['id'],r['effective_date'],r['recorded_at'],safe(r['point']),safe(r['actor']),r['kind'],safe(r['category']),safe(r['description']),f"{Decimal(r['amount_cents'])/100:.2f}",safe(r['payment']),safe(r['reference']),safe(r['username']),r['reversal_of'] or ''])
    out.seek(0);return StreamingResponse(iter([out.getvalue()]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="jb360_registro_operativo.csv"'})

@app.get('/',response_class=HTMLResponse)
def home():return open(os.path.join(os.path.dirname(__file__),'panel.html'),encoding='utf8').read()

@app.get('/app.js')
def panel_script():
    return FileResponse(os.path.join(os.path.dirname(__file__),'panel.js'),media_type='text/javascript')

@app.get('/api/audit')
def audit(start:datetime.date,end:datetime.date,authorization:str|None=Header(None)):
    admin(authorization)
    if start>end:raise HTTPException(422,'Rango inválido')
    with conn() as c:
        rows=c.execute('SELECT a.id,a.at,u.username,a.action,a.detail FROM audit a JOIN users u ON u.id=a.user_id WHERE substr(a.at,1,10) BETWEEN ? AND ? ORDER BY a.id',(str(start),str(end))).fetchall()
    return {'rows':[dict(r) for r in rows]}

@app.post('/api/admin/backup')
def backup_download(x:BackupRequest,authorization:str|None=Header(None)):
    u=admin(authorization)
    if not hmac.compare_digest(u['password_hash'],hashpw(x.password,u['salt'])):
        raise HTTPException(403,'Contraseña administrativa incorrecta')
    fd,path=tempfile.mkstemp(prefix='jb360-backup-',suffix='.sqlite3')
    os.close(fd)
    try:
        with conn() as source, sqlite3.connect(path) as target:
            source.backup(target)
        with sqlite3.connect(path) as copy:
            copy.execute('PRAGMA journal_mode=DELETE')
            copy.execute('DELETE FROM tokens')
            copy.execute('DELETE FROM login_failures')
            if copy.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('Copia con error de integridad')
        with conn() as c:
            c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',
                      (now(),u['id'],'download_backup','Copia SQLite sin sesiones activas'))
        return FileResponse(path,media_type='application/octet-stream',
                            filename='JB360_respaldo_'+str(business_today())+'.sqlite3',
                            background=BackgroundTask(os.unlink,path))
    except Exception:
        if os.path.exists(path):os.unlink(path)
        raise

# Integrated endpoints are registered after base endpoints.
import extension

# Catálogo contable referencial y plan propio
import catalogo_api

import normativa_control  # noqa: E402

import vector_fiscal  # custodia y revision del vector antes de simular
import fiscal2026  # reglas acotadas de 2026 con fuentes oficiales
