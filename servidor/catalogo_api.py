"""Catálogo referencial de normas contables cubanas. Sin activación automática."""
import csv, io, json, os, re
from fastapi import Header, HTTPException
from pydantic import BaseModel, Field
from server import app, admin, require, conn, now
ROOT=os.path.dirname(__file__)
CATALOG=json.load(open(os.path.join(ROOT,'catalogo_referencial.json'),encoding='utf8'))
class OwnAccount(BaseModel):
    codigo:str=Field(min_length=1,max_length=40)
    nombre:str=Field(min_length=2,max_length=160)
    naturaleza:str=Field(pattern='^(activo|pasivo|patrimonio|ingreso|gasto|costo|resultado|orden|otro)$')
    uso:str=Field(min_length=10,max_length=1000)
    fuente:str=Field(min_length=5,max_length=300)
class OwnPlan(BaseModel):
    regimen:str=Field(min_length=2,max_length=40)
    version:str=Field(min_length=1,max_length=80)
    cuentas:list[OwnAccount]=Field(min_length=1,max_length=5000)
def setup():
    with conn() as c:c.execute("CREATE TABLE IF NOT EXISTS plan_cuentas(id INTEGER PRIMARY KEY,codigo TEXT NOT NULL UNIQUE,nombre TEXT NOT NULL,naturaleza TEXT NOT NULL,uso TEXT NOT NULL,fuente TEXT NOT NULL,regimen TEXT NOT NULL,version TEXT NOT NULL,aprobado INTEGER NOT NULL DEFAULT 0,fecha TEXT NOT NULL)")
setup()
@app.get('/api/contabilidad/catalogo')
def catalogo(regimen:str='empresarial',authorization:str|None=Header(None)):
    require(authorization)
    if regimen not in ('tcp','empresarial'):raise HTTPException(422,'Régimen no disponible')
    return {**{k:v for k,v in CATALOG.items() if k!='cuentas'},'regimen':regimen,'cuentas':[a for a in CATALOG['cuentas'] if a['regimen']==regimen]}
@app.post('/api/admin/contabilidad/plan')
def cargar_plan(x:OwnPlan,authorization:str|None=Header(None)):
    u=admin(authorization)
    codigos=[a.codigo for a in x.cuentas]
    if len(set(codigos))!=len(codigos):raise HTTPException(422,'Códigos duplicados')
    if any(not re.fullmatch(r'[A-Za-z0-9._-]+',c) for c in codigos):raise HTTPException(422,'Código de cuenta inválido')
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('DELETE FROM plan_cuentas')
        for a in x.cuentas:
            c.execute('INSERT INTO plan_cuentas(codigo,nombre,naturaleza,uso,fuente,regimen,version,aprobado,fecha) VALUES(?,?,?,?,?,?,?,?,?)',(a.codigo,a.nombre,a.naturaleza,a.uso,a.fuente,x.regimen,x.version,0,now()))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'plan_importado',f'{x.version}: {len(x.cuentas)} cuentas sin aprobar'))
        c.commit()
    return {'ok':True,'cuentas':len(x.cuentas),'estado':'PENDIENTE_REVISION_CONTABLE','aviso':'La carga NO autoriza automáticamente su uso en asientos'}
@app.get('/api/admin/contabilidad/plan')
def ver_plan(authorization:str|None=Header(None)):
    admin(authorization)
    with conn() as c:rows=c.execute('SELECT codigo,nombre,naturaleza,uso,fuente,regimen,version,aprobado FROM plan_cuentas ORDER BY codigo').fetchall()
    return {'cuentas':[dict(r) for r in rows]}
