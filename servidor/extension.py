"""JB360 integrated operational extensions; fiscal export is NOT an ONAT-certified model."""
import sqlite3, datetime, json, calendar
from zoneinfo import ZoneInfo
from decimal import Decimal
from fastapi import HTTPException, Header
from pydantic import BaseModel, Field
from server import app,conn,require,admin,now,cents,business_today

def setup():
    with conn() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE NOT NULL,name TEXT NOT NULL,price_cents INTEGER NOT NULL CHECK(price_cents>=0),cost_cents INTEGER NOT NULL CHECK(cost_cents>=0),stock INTEGER NOT NULL CHECK(stock>=0));
        CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,kind TEXT NOT NULL CHECK(kind IN ('goods','service')),point TEXT NOT NULL,customer TEXT NOT NULL,description TEXT NOT NULL,subtotal_cents INTEGER NOT NULL CHECK(subtotal_cents>0),cost_cents INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),reversed_at TEXT,reverse_reason TEXT);
        CREATE TABLE IF NOT EXISTS ticket_items(ticket_id INTEGER REFERENCES tickets(id),product_id INTEGER REFERENCES products(id),qty INTEGER NOT NULL CHECK(qty>0),unit_price_cents INTEGER NOT NULL,unit_cost_cents INTEGER NOT NULL,PRIMARY KEY(ticket_id,product_id));
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,ticket_id INTEGER REFERENCES tickets(id),method TEXT NOT NULL CHECK(method IN ('Efectivo','Transferencia','Tarjeta')),amount_cents INTEGER NOT NULL CHECK(amount_cents>0));
        CREATE TABLE IF NOT EXISTS inventory_moves(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL REFERENCES products(id),delta INTEGER NOT NULL,reason TEXT NOT NULL,ticket_id INTEGER REFERENCES tickets(id),at TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS license_state(id INTEGER PRIMARY KEY CHECK(id=1),started_on TEXT NOT NULL,expires_on TEXT NOT NULL,renewal_count INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS license_renewals(id INTEGER PRIMARY KEY,verified_on TEXT NOT NULL,reference TEXT NOT NULL,previous_expiry TEXT NOT NULL,new_expiry TEXT NOT NULL,admin_user_id INTEGER NOT NULL REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS period_closes(id INTEGER PRIMARY KEY,period_start TEXT NOT NULL,period_end TEXT NOT NULL,closed_at TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),snapshot TEXT NOT NULL,UNIQUE(period_start,period_end));
        ''')
        if not c.execute('SELECT 1 FROM license_state WHERE id=1').fetchone():
            today=business_today();c.execute('INSERT INTO license_state VALUES(1,?,?,0)',(str(today),str(today)))

def add_months(d,n):
    month=d.month-1+n;year=d.year+month//12;month=month%12+1
    return datetime.date(year,month,min(d.day,calendar.monthrange(year,month)[1]))

def licensed(auth):
    u=require(auth)
    with conn() as c:s=c.execute('SELECT * FROM license_state WHERE id=1').fetchone()
    if u['role']!='admin' and business_today()>=datetime.date.fromisoformat(s['expires_on']):raise HTTPException(402,'Licencia vencida. Contacte al administrador para renovar.')
    return u

def money(v,allow_zero=False):
    if allow_zero and str(v) in ('0','0.00','0.0'):return 0
    return cents(v)

class Product(BaseModel):sku:str=Field(min_length=1,max_length=50);name:str=Field(min_length=1,max_length=150);price:str;cost:str;stock:int=Field(ge=0)
class Restock(BaseModel):qty:int=Field(gt=0);reason:str=Field(min_length=5,max_length=250)
class Item(BaseModel):product_id:int;qty:int=Field(gt=0)
class Pay(BaseModel):method:str;amount:str
class Ticket(BaseModel):kind:str;point:str=Field(min_length=1,max_length=80);customer:str='Consumidor';description:str=Field(min_length=1,max_length=300);items:list[Item]=[];service_price:str='0';service_cost:str='0';payments:list[Pay]
class Undo(BaseModel):reason:str=Field(min_length=5,max_length=250)
class Renew(BaseModel):months:int=Field(ge=6,le=6);reference:str=Field(min_length=4,max_length=120);payment_verified:bool
class Close(BaseModel):start:datetime.date;end:datetime.date

@app.get('/api/license')
def license_info(authorization:str|None=Header(None)):
    u=require(authorization,allow_expired=True)
    with conn() as c:s=dict(c.execute('SELECT * FROM license_state WHERE id=1').fetchone())
    return {**s,'expired':str(business_today())>=s['expires_on'],'role':u['role']}

@app.post('/api/admin/renew')
def renew(x:Renew,authorization:str|None=Header(None)):
    u=admin(authorization)
    if not x.payment_verified:raise HTTPException(422,'El administrador debe confirmar el pago antes de renovar')
    reference=x.reference.strip()
    if len(reference)<4:raise HTTPException(422,'Referencia de pago válida obligatoria')
    with conn() as c:
        # The lock prevents two concurrent clicks from spending one payment twice.
        c.execute('BEGIN IMMEDIATE');s=c.execute('SELECT expires_on FROM license_state WHERE id=1').fetchone()
        if c.execute('SELECT 1 FROM license_renewals WHERE reference=?',(reference,)).fetchone():
            raise HTTPException(409,'Esta referencia de pago ya se utilizó para una renovación')
        base=max(business_today(),datetime.date.fromisoformat(s['expires_on']))
        expiry=add_months(base,6)
        c.execute('UPDATE license_state SET expires_on=?,renewal_count=renewal_count+1 WHERE id=1',(str(expiry),))
        c.execute('INSERT INTO license_renewals(verified_on,reference,previous_expiry,new_expiry,admin_user_id) VALUES(?,?,?,?,?)',(now(),reference,s['expires_on'],str(expiry),u['id']))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'renew_license',json.dumps({'expires_on':str(expiry),'reference':reference})))
        c.commit()
    return {'expires_on':str(expiry),'ok':True}

@app.get('/api/admin/license-renewals')
def license_renewals(authorization:str|None=Header(None)):
    admin(authorization)
    with conn() as c:return {'rows':[dict(r) for r in c.execute('SELECT id,verified_on,reference,previous_expiry,new_expiry,admin_user_id FROM license_renewals ORDER BY id DESC')]}

@app.get('/api/products')
def products(authorization:str|None=Header(None)):
    licensed(authorization)
    with conn() as c:return {'rows':[dict(r) for r in c.execute('SELECT * FROM products ORDER BY name')]}

@app.post('/api/products')
def product(x:Product,authorization:str|None=Header(None)):
    u=licensed(authorization);p=money(x.price,True);cost=money(x.cost,True)
    with conn() as c:
        try:
            c.execute('BEGIN IMMEDIATE');cur=c.execute('INSERT INTO products(sku,name,price_cents,cost_cents,stock) VALUES(?,?,?,?,?)',(x.sku,x.name,p,cost,x.stock))
            if x.stock:c.execute('INSERT INTO inventory_moves(product_id,delta,reason,ticket_id,at,user_id) VALUES(?,?,?,NULL,?,?)',(cur.lastrowid,x.stock,'Inventario inicial',now(),u['id']))
            c.commit()
        except sqlite3.IntegrityError:raise HTTPException(409,'SKU duplicado')
    return {'ok':True,'id':cur.lastrowid}

@app.post('/api/products/{pid}/restock')
def restock(pid:int,x:Restock,authorization:str|None=Header(None)):
    u=licensed(authorization)
    with conn() as c:
        c.execute('BEGIN IMMEDIATE');r=c.execute('UPDATE products SET stock=stock+? WHERE id=?',(x.qty,pid))
        if not r.rowcount:raise HTTPException(404,'Producto inexistente')
        c.execute('INSERT INTO inventory_moves(product_id,delta,reason,ticket_id,at,user_id) VALUES(?,?,?,NULL,?,?)',(pid,x.qty,x.reason,now(),u['id']))
        c.commit()
    return {'ok':True}

@app.post('/api/tickets')
def ticket(x:Ticket,authorization:str|None=Header(None)):
    u=licensed(authorization)
    if x.kind not in ('goods','service'):raise HTTPException(422,'Tipo inválido')
    if not x.payments:raise HTTPException(422,'Pago obligatorio')
    pays=[]
    for p in x.payments:
        if p.method not in ('Efectivo','Transferencia','Tarjeta'):raise HTTPException(422,'Medio inválido')
        pays.append((p.method,money(p.amount)))
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        total=cost=0;lines=[]
        if x.kind=='goods':
            if not x.items or len({i.product_id for i in x.items})!=len(x.items):raise HTTPException(422,'Artículos vacíos o repetidos')
            for i in x.items:
                p=c.execute('SELECT * FROM products WHERE id=?',(i.product_id,)).fetchone()
                if not p:raise HTTPException(404,'Producto inexistente')
                if p['stock']<i.qty:raise HTTPException(409,'Existencia insuficiente: '+p['name'])
                total+=p['price_cents']*i.qty;cost+=p['cost_cents']*i.qty
                lines.append((i.product_id,i.qty,p['price_cents'],p['cost_cents']))
        else:
            if x.items:raise HTTPException(422,'Servicios sin artículos de inventario')
            total=money(x.service_price);cost=money(x.service_cost,True)
        if sum(a for _,a in pays)!=total:raise HTTPException(422,'La suma de pagos no coincide con el importe de venta')
        cur=c.execute('INSERT INTO tickets(kind,point,customer,description,subtotal_cents,cost_cents,created_at,user_id) VALUES(?,?,?,?,?,?,?,?)',(x.kind,x.point,x.customer,x.description,total,cost,now(),u['id']))
        tid=cur.lastrowid
        for pid,qty,price,unitcost in lines:
            r=c.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',(qty,pid,qty))
            if not r.rowcount:raise HTTPException(409,'Existencia insuficiente')
            c.execute('INSERT INTO ticket_items VALUES(?,?,?,?,?)',(tid,pid,qty,price,unitcost))
            c.execute('INSERT INTO inventory_moves(product_id,delta,reason,ticket_id,at,user_id) VALUES(?,?,?,?,?,?)',(pid,-qty,'Venta',tid,now(),u['id']))
        for method,amount in pays:c.execute('INSERT INTO payments(ticket_id,method,amount_cents) VALUES(?,?,?)',(tid,method,amount))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'create_ticket',str(tid)))
        c.commit()
    return {'ok':True,'id':tid,'total_cents':total,'cost_cents':cost}

@app.post('/api/tickets/{tid}/reverse')
def ticket_reverse(tid:int,x:Undo,authorization:str|None=Header(None)):
    u=licensed(authorization)
    with conn() as c:
        c.execute('BEGIN IMMEDIATE');t=c.execute('SELECT * FROM tickets WHERE id=?',(tid,)).fetchone()
        if not t:raise HTTPException(404,'Ticket inexistente')
        if t['reversed_at']:raise HTTPException(409,'Ticket ya revertido')
        if u['role']!='admin' and t['user_id']!=u['id']:raise HTTPException(403,'Sin permiso')
        c.execute('UPDATE tickets SET reversed_at=?,reverse_reason=? WHERE id=?',(now(),x.reason,tid))
        for item in c.execute('SELECT * FROM ticket_items WHERE ticket_id=?',(tid,)).fetchall():
            c.execute('UPDATE products SET stock=stock+? WHERE id=?',(item['qty'],item['product_id']))
            c.execute('INSERT INTO inventory_moves(product_id,delta,reason,ticket_id,at,user_id) VALUES(?,?,?,?,?,?)',(item['product_id'],item['qty'],'Reversión de venta',tid,now(),u['id']))
        c.execute('INSERT INTO audit(at,user_id,action,detail) VALUES(?,?,?,?)',(now(),u['id'],'reverse_ticket',json.dumps({'id':tid,'reason':x.reason})))
        c.commit()
    return {'ok':True}

@app.get('/api/integrated-report')
def integrated_report(start:datetime.date,end:datetime.date,point:str|None=None,authorization:str|None=Header(None)):
    licensed(authorization)
    if start>end:raise HTTPException(422,'Rango inválido')
    cuba=ZoneInfo('America/Havana')
    def local_date(stamp):return datetime.datetime.fromisoformat(stamp).astimezone(cuba).date()
    with conn() as c:
        q='SELECT * FROM tickets';args=[]
        if point:q+=' WHERE point=?';args.append(point)
        all_tickets=[dict(r) for r in c.execute(q,args)]
        tickets=[t for t in all_tickets if start<=local_date(t['created_at'])<=end]
        reversed_tickets=[t for t in all_tickets if t['reversed_at'] and start<=local_date(t['reversed_at'])<=end]
        ids={t['id'] for t in tickets+reversed_tickets}
        pays=[dict(r) for r in c.execute('SELECT ticket_id,method,amount_cents FROM payments') if r['ticket_id'] in ids]
        q2='SELECT * FROM operations WHERE effective_date BETWEEN ? AND ?';oa=[str(start),str(end)]
        if point:q2+=' AND point=?';oa.append(point)
        ops=[dict(r) for r in c.execute(q2,oa)]
    # A reversal belongs to its own period even if the original sale was earlier.
    sold=sum(t['subtotal_cents'] for t in tickets);cost=sum(t['cost_cents'] for t in tickets)
    refunds=sum(t['subtotal_cents'] for t in reversed_tickets)
    returned_cost=sum(t['cost_cents'] for t in reversed_tickets)
    sale_ids={t['id'] for t in tickets};refund_ids={t['id'] for t in reversed_tickets}
    gross_by_method={m:sum(p['amount_cents'] for p in pays if p['method']==m and p['ticket_id'] in sale_ids) for m in ('Efectivo','Transferencia','Tarjeta')}
    refunds_by_method={m:sum(p['amount_cents'] for p in pays if p['method']==m and p['ticket_id'] in refund_ids) for m in gross_by_method}
    net_by_method={m:gross_by_method[m]-refunds_by_method[m] for m in gross_by_method}
    by_kind={}
    for kind,label in (('goods','bienes'),('service','servicios')):
        group=[t for t in tickets if t['kind']==kind];returned=[t for t in reversed_tickets if t['kind']==kind]
        sales=sum(t['subtotal_cents'] for t in group);reversed_amount=sum(t['subtotal_cents'] for t in returned)
        gross_cost=sum(t['cost_cents'] for t in group);returned_group_cost=sum(t['cost_cents'] for t in returned)
        by_kind[label]={'tickets_vendidos':len(group),'tickets_revertidos':len(returned),'ventas_cents':sales,'devoluciones_cents':reversed_amount,'neto_cents':sales-reversed_amount,'costo_cents':gross_cost-returned_group_cost,'margen_cents':sales-reversed_amount-gross_cost+returned_group_cost}
    orig_income=sum(((-1 if o['reversal_of'] else 1)*o['amount_cents']) for o in ops if (o['kind']=='income') != bool(o['reversal_of']))
    orig_expense=sum(((-1 if o['reversal_of'] else 1)*o['amount_cents']) for o in ops if (o['kind']=='expense') != bool(o['reversal_of']))
    return {'start':str(start),'end':str(end),'point':point,'timezone':'America/Havana','ticket_sales_cents':sold,'ticket_refunds_cents':refunds,'ticket_cost_cents':cost,'returned_cost_cents':returned_cost,'net_sales_cents':sold-refunds,'gross_margin_cents':sold-refunds-cost+returned_cost,'by_kind':by_kind,'other_income_cents':orig_income,'other_expenses_cents':orig_expense,'net_operational_cents':sold-refunds-cost+returned_cost+orig_income-orig_expense,'gross_collections_by_method_cents':gross_by_method,'refunds_by_method_cents':refunds_by_method,'net_collections_by_method_cents':net_by_method,'tickets':tickets,'reversed_tickets':reversed_tickets,'operations':ops,'warning':'Informe operativo. Los cobros por método suponen reversión íntegra al mismo medio; confirme el reintegro y la conciliación bancaria. No equivale a cierre contable ni declaración jurada ONAT.'}

@app.post('/api/admin/close')
def close_period(x:Close,authorization:str|None=Header(None)):
    u=admin(authorization)
    if x.start>x.end or x.end>=business_today():raise HTTPException(422,'Solo períodos finalizados')
    report=integrated_report(x.start,x.end,authorization=authorization)
    with conn() as c:
        try:
            c.execute('BEGIN IMMEDIATE');c.execute('INSERT INTO period_closes(period_start,period_end,closed_at,user_id,snapshot) VALUES(?,?,?,?,?)',(str(x.start),str(x.end),now(),u['id'],json.dumps(report)))
            c.commit()
        except sqlite3.IntegrityError:raise HTTPException(409,'Período ya cerrado')
    return {'ok':True,'report':report,'note':'Cierre operativo de referencia, NO cierre contable certificado. Ajustes posteriores requieren conciliación.'}

@app.get('/api/fiscal-ledger')
def fiscal_ledger(start:datetime.date,end:datetime.date,authorization:str|None=Header(None)):
    licensed(authorization)
    report=integrated_report(start,end,authorization=authorization)
    rows=[]
    for t in report['tickets']:
        rows.append({'fecha':t['created_at'][:10],'documento':'T-'+str(t['id']),'tipo':'ingreso','concepto':t['description'],'importe_cents':t['subtotal_cents'],'tratamiento_fiscal':'PENDIENTE DE CLASIFICAR'})
    for t in report['reversed_tickets']:
        rows.append({'fecha':t['reversed_at'][:10],'documento':'R-'+str(t['id']),'tipo':'devolucion','concepto':t['reverse_reason'],'importe_cents':-t['subtotal_cents'],'tratamiento_fiscal':'PENDIENTE DE CLASIFICAR'})
    for o in report['operations']:
        rows.append({'fecha':o['effective_date'],'documento':o['reference'],'tipo':o['kind'],'concepto':o['description'],'importe_cents':(-1 if o['reversal_of'] else 1)*o['amount_cents'],'tratamiento_fiscal':'PENDIENTE DE CLASIFICAR'})
    return {'rows':sorted(rows,key=lambda r:r['fecha']),'warning':'Libro auxiliar de ingresos y gastos, NO modelo oficial ONAT. Sin clasificación de deducibilidad, retenciones, exenciones ni fórmulas DJ.'}

setup()

import commercial  # endpoints for third parties and commercial draft documents

import versat_bridge  # puente de precontabilizacion revisable
