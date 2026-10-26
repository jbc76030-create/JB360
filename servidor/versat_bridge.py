"""Accounting export staging for VERSAT Sarasola; NOT a verified VERSAT importer."""
import csv, io, datetime, json, sqlite3
from fastapi import HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from server import app, conn, admin, require, now, business_today

class Mapping(BaseModel):
    cash: str=Field(min_length=1,max_length=40)
    transfer: str=Field(min_length=1,max_length=40)
    card: str=Field(min_length=1,max_length=40)
    revenue_goods: str=Field(min_length=1,max_length=40)
    revenue_services: str=Field(min_length=1,max_length=40)
    inventory: str=Field(min_length=1,max_length=40)
    cost_of_goods: str=Field(min_length=1,max_length=40)
    expenses: str=Field(min_length=1,max_length=40)
    other_income: str=Field(min_length=1,max_length=40)
    clearing: str=Field(min_length=1,max_length=40)
    unit: str=Field(min_length=1,max_length=40)
    cost_center: str=Field(min_length=1,max_length=40)

DEFAULT_KEYS=set(Mapping.model_fields)
def setup():
    with conn() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS versat_mapping(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS versat_batches(id INTEGER PRIMARY KEY,created_at TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),start TEXT NOT NULL,end TEXT NOT NULL,sha256 TEXT NOT NULL UNIQUE,row_count INTEGER NOT NULL,status TEXT NOT NULL CHECK(status IN ('prepared','confirmed')),notes TEXT NOT NULL DEFAULT '');''')
setup()

@app.post('/api/admin/versat/mapping')
def set_mapping(x:Mapping,authorization:str|None=Header(None)):
    u=admin(authorization)
    if len(set([x.cash,x.transfer,x.card,x.revenue_goods,x.revenue_services,x.inventory,x.cost_of_goods,x.expenses,x.other_income,x.clearing]))<10:
        raise HTTPException(422,'Se requieren cuentas diferentes por función para evitar clasificaciones ambiguas')
    with conn() as c:
        c.execute('INSERT INTO versat_mapping(id,data,updated_at) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at',(x.model_dump_json(),now()))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'versat_mapping',x.model_dump_json()))
    return {'ok':True,'warning':'El contador debe validar la correspondencia con el plan de cuentas de VERSAT.'}

@app.get('/api/admin/versat/mapping')
def get_mapping(authorization:str|None=Header(None)):
    admin(authorization)
    with conn() as c:r=c.execute('SELECT data FROM versat_mapping WHERE id=1').fetchone()
    return {'mapping':json.loads(r['data']) if r else None}

def make_entries(start,end,mapping):
    if start>end:raise HTTPException(422,'Período inválido')
    if end>=business_today():raise HTTPException(422,'Exportación solo de períodos finalizados')
    if (end-start).days>366:raise HTTPException(422,'Máximo 367 días')
    out=[]
    def pair(date,ref,point,concept,debit,credit,amount):
        if amount<=0:return
        out.append({'fecha':date,'referencia':ref,'punto':point,'concepto':concept,'cuenta':debit,'debe_cents':amount,'haber_cents':0,'unidad':mapping['unit'],'centro_costo':mapping['cost_center']})
        out.append({'fecha':date,'referencia':ref,'punto':point,'concepto':concept,'cuenta':credit,'debe_cents':0,'haber_cents':amount,'unidad':mapping['unit'],'centro_costo':mapping['cost_center']})
    with conn() as c:
        tickets=c.execute('SELECT * FROM tickets WHERE substr(created_at,1,10) BETWEEN ? AND ? ORDER BY id',(str(start),str(end))).fetchall()
        for t in tickets:
            d=t['created_at'][:10];ref='JB-T-'+str(t['id']);point=t['point'];concept=t['description']
            revenue=mapping['revenue_goods'] if t['kind']=='goods' else mapping['revenue_services']
            for p in c.execute('SELECT * FROM payments WHERE ticket_id=?',(t['id'],)).fetchall():
                debit=mapping[{'Efectivo':'cash','Transferencia':'transfer','Tarjeta':'card'}[p['method']]]
                pair(d,ref,point,concept,debit,revenue,p['amount_cents'])
            if t['kind']=='goods':pair(d,ref,point,'Costo de ventas',mapping['cost_of_goods'],mapping['inventory'],t['cost_cents'])
            # Service cost needs its underlying cost classification and settlement voucher.
            if t['kind']=='service' and t['cost_cents']:
                raise HTTPException(409,'Costo de servicio sin documento de contrapartida: ticket '+str(t['id']))
        reversed_tickets=c.execute('SELECT * FROM tickets WHERE substr(reversed_at,1,10) BETWEEN ? AND ? ORDER BY id',(str(start),str(end))).fetchall()
        for t in reversed_tickets:
            d=t['reversed_at'][:10];ref='JB-R-'+str(t['id']);point=t['point'];concept='Reversión: '+(t['reverse_reason'] or '')
            revenue=mapping['revenue_goods'] if t['kind']=='goods' else mapping['revenue_services']
            for p in c.execute('SELECT * FROM payments WHERE ticket_id=?',(t['id'],)).fetchall():
                credit=mapping[{'Efectivo':'cash','Transferencia':'transfer','Tarjeta':'card'}[p['method']]]
                pair(d,ref,point,concept,revenue,credit,p['amount_cents'])
            if t['kind']=='goods':pair(d,ref,point,'Reversión costo de ventas',mapping['inventory'],mapping['cost_of_goods'],t['cost_cents'])
            if t['kind']=='service' and t['cost_cents']:
                raise HTTPException(409,'Reversión de costo de servicio sin contrapartida: ticket '+str(t['id']))
        ops=c.execute('SELECT * FROM operations WHERE effective_date BETWEEN ? AND ? ORDER BY id',(str(start),str(end))).fetchall()
        for o in ops:
            # Unclassified settlement is not guessed: all manual operations require accountant review.
            raise HTTPException(409,'Operación manual sin clasificación contable y cuenta de contrapartida: '+str(o['id']))
    return out

@app.get('/api/admin/versat/preview')
def preview(start:datetime.date,end:datetime.date,authorization:str|None=Header(None)):
    admin(authorization)
    with conn() as c:r=c.execute('SELECT data FROM versat_mapping WHERE id=1').fetchone()
    if not r:raise HTTPException(409,'Configure y valide primero el plan de cuentas')
    rows=make_entries(start,end,json.loads(r['data']))
    debe=sum(x['debe_cents'] for x in rows);haber=sum(x['haber_cents'] for x in rows)
    if debe!=haber:raise HTTPException(409,'Asientos descuadrados')
    return {'rows':rows,'total_debe_cents':debe,'total_haber_cents':haber,'balanced':True,'warning':'Precontabilización interna. No es fichero oficial de importación VERSAT Sarasola.'}

@app.get('/api/admin/versat/export.csv')
def export(start:datetime.date,end:datetime.date,authorization:str|None=Header(None)):
    data=preview(start,end,authorization)
    output=io.StringIO();w=csv.writer(output);w.writerow(['Fecha','Referencia JB360','Punto','Concepto','Cuenta','Debe CUP','Haber CUP','Unidad','Centro de costo'])
    def safe(v):
        s=str(v)
        return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
    for r in data['rows']:
        w.writerow([safe(r['fecha']),safe(r['referencia']),safe(r['punto']),safe(r['concepto']),safe(r['cuenta']),f"{r['debe_cents']/100:.2f}",f"{r['haber_cents']/100:.2f}",safe(r['unidad']),safe(r['centro_costo'])])
    return StreamingResponse(iter([output.getvalue()]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="JB360_precontabilizacion_para_revision.csv"'})
