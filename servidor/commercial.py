
# Documentos comerciales de referencia: no sustituyen factura fiscal verificada.
from pydantic import BaseModel, Field
from fastapi import HTTPException, Header
from fastapi.responses import HTMLResponse
from html import escape
import sqlite3
from server import app,conn,require,admin,now

class Party(BaseModel):
    kind:str
    name:str=Field(min_length=2,max_length=180)
    tax_id:str=Field(default='',max_length=40)
    address:str=Field(default='',max_length=250)
    phone:str=Field(default='',max_length=60)
    email:str=Field(default='',max_length=150)
class Issuer(BaseModel):
    name:str=Field(min_length=2,max_length=180)
    tax_id:str=Field(min_length=1,max_length=40)
    address:str=Field(min_length=3,max_length=250)
    actor:str=Field(min_length=2,max_length=40)
class InvoiceNew(BaseModel):
    ticket_id:int=Field(gt=0)
    customer_id:int=Field(gt=0)
    series:str=Field(default='JB',min_length=1,max_length=12)
    notes:str=Field(default='',max_length=400)

def setup_parties():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS parties(id INTEGER PRIMARY KEY,kind TEXT NOT NULL CHECK(kind IN ('customer','supplier')),name TEXT NOT NULL,tax_id TEXT NOT NULL,address TEXT NOT NULL,phone TEXT NOT NULL,email TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS issuer(id INTEGER PRIMARY KEY CHECK(id=1),name TEXT NOT NULL,tax_id TEXT NOT NULL,address TEXT NOT NULL,actor TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY,number TEXT NOT NULL UNIQUE,ticket_id INTEGER NOT NULL UNIQUE REFERENCES tickets(id),customer_id INTEGER NOT NULL REFERENCES parties(id),issuer_name TEXT NOT NULL,issuer_tax_id TEXT NOT NULL,issuer_address TEXT NOT NULL,customer_name TEXT NOT NULL,customer_tax_id TEXT NOT NULL,customer_address TEXT NOT NULL,issued_at TEXT NOT NULL,notes TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id));
        """)
setup_parties()

@app.post('/api/issuer')
def issuer_set(x:Issuer,authorization:str|None=Header(None)):
    u=admin(authorization)
    with conn() as c:
        c.execute('INSERT INTO issuer(id,name,tax_id,address,actor) VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,tax_id=excluded.tax_id,address=excluded.address,actor=excluded.actor',(x.name,x.tax_id,x.address,x.actor))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'set_issuer',x.name))
    return {'ok':True}

@app.get('/api/issuer')
def issuer_get(authorization:str|None=Header(None)):
    require(authorization)
    with conn() as c:r=c.execute('SELECT * FROM issuer WHERE id=1').fetchone()
    return {'issuer':dict(r) if r else None}

@app.post('/api/parties')
def party_create(x:Party,authorization:str|None=Header(None)):
    u=require(authorization)
    if x.kind not in ('customer','supplier'):raise HTTPException(422,'Tipo de tercero inválido')
    with conn() as c:
        cur=c.execute('INSERT INTO parties(kind,name,tax_id,address,phone,email,created_at) VALUES(?,?,?,?,?,?,?)',(x.kind,x.name,x.tax_id,x.address,x.phone,x.email,now()))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'create_party',str(cur.lastrowid)))
    return {'id':cur.lastrowid,'ok':True}

@app.get('/api/parties')
def party_list(kind:str|None=None,authorization:str|None=Header(None)):
    require(authorization)
    if kind and kind not in ('customer','supplier'):raise HTTPException(422,'Tipo inválido')
    with conn() as c:
        rows=c.execute('SELECT * FROM parties WHERE kind=? ORDER BY name',(kind,)).fetchall() if kind else c.execute('SELECT * FROM parties ORDER BY kind,name').fetchall()
    return {'rows':[dict(r) for r in rows]}

@app.post('/api/invoices')
def invoice_create(x:InvoiceNew,authorization:str|None=Header(None)):
    u=require(authorization)
    if not x.series.isalnum():raise HTTPException(422,'Serie solo alfanumérica')
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        t=c.execute('SELECT * FROM tickets WHERE id=?',(x.ticket_id,)).fetchone()
        if not t:raise HTTPException(404,'Venta inexistente')
        if t['reversed_at']:raise HTTPException(409,'Venta anulada')
        p=c.execute('SELECT * FROM parties WHERE id=? AND kind=?',(x.customer_id,'customer')).fetchone()
        if not p:raise HTTPException(404,'Cliente inexistente')
        i=c.execute('SELECT * FROM issuer WHERE id=1').fetchone()
        if not i:raise HTTPException(409,'Configure los datos del emisor')
        # UNIQUE(ticket_id) ensures no duplicate document for one ticket.
        try:
            nextid=c.execute('SELECT COALESCE(MAX(id),0)+1 FROM invoices').fetchone()[0]
            number=f'{x.series}-{nextid:08d}'
            cur=c.execute('INSERT INTO invoices(number,ticket_id,customer_id,issuer_name,issuer_tax_id,issuer_address,customer_name,customer_tax_id,customer_address,issued_at,notes,user_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(number,x.ticket_id,x.customer_id,i['name'],i['tax_id'],i['address'],p['name'],p['tax_id'],p['address'],now(),x.notes,u['id']))
        except sqlite3.IntegrityError:raise HTTPException(409,'Ya existe documento para esta venta')
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'create_invoice',number))
        c.commit()
    return {'id':cur.lastrowid,'number':number,'ok':True,'status':'BORRADOR COMERCIAL NO VALIDADO FISCALMENTE'}

@app.get('/api/invoices/{iid}')
def invoice_get(iid:int,authorization:str|None=Header(None)):
    require(authorization)
    with conn() as c:
        r=c.execute('SELECT * FROM invoices WHERE id=?',(iid,)).fetchone()
        if not r:raise HTTPException(404,'Documento inexistente')
        t=c.execute('SELECT * FROM tickets WHERE id=?',(r['ticket_id'],)).fetchone()
        items=[dict(a) for a in c.execute('SELECT ti.qty,ti.unit_price_cents,ti.unit_cost_cents,p.sku,p.name FROM ticket_items ti JOIN products p ON p.id=ti.product_id WHERE ti.ticket_id=?',(r['ticket_id'],))]
        payments=[dict(a) for a in c.execute('SELECT method,amount_cents FROM payments WHERE ticket_id=?',(r['ticket_id'],))]
    return {'invoice':dict(r),'ticket':dict(t),'items':items,'payments':payments,'warning':'BORRADOR COMERCIAL. No se ha cotejado con los requisitos de facturación vigentes en Gaceta Oficial.'}

@app.get('/api/invoices/{iid}/print',response_class=HTMLResponse)
def invoice_print(iid:int,authorization:str|None=Header(None)):
    # Browser printing requires authentication header, use API fetch + print from panel instead.
    data=invoice_get(iid,authorization)
    r=data['invoice'];t=data['ticket']
    rows=''.join('<tr><td>'+escape(z['name'])+'</td><td>'+str(z['qty'])+'</td><td>'+f"{z['unit_price_cents']/100:.2f}"+'</td></tr>' for z in data['items'])
    return '<!doctype html><meta charset="utf-8"><title>Documento comercial</title><h1>BORRADOR COMERCIAL - NO FACTURA FISCAL VALIDADA</h1><p>Documento '+escape(r['number'])+'</p><p>Emisor: '+escape(r['issuer_name'])+' · NIT: '+escape(r['issuer_tax_id'])+' · '+escape(r['issuer_address'])+'</p><p>Cliente: '+escape(r['customer_name'])+' · NIT: '+escape(r['customer_tax_id'])+' · '+escape(r['customer_address'])+'</p><p>Fecha: '+escape(r['issued_at'])+'</p><table border="1"><tr><th>Concepto</th><th>Cantidad</th><th>Precio CUP</th></tr>'+rows+'</table><p>Descripción: '+escape(t['description'])+'</p><p>Total CUP: '+f"{t['subtotal_cents']/100:.2f}"+'</p><p>Estado de venta: '+('ANULADA' if t['reversed_at'] else 'VIGENTE')+'</p><button onclick="print()">Imprimir</button>'
