import os,tempfile,datetime,sys,importlib,threading
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

def test_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['JB360_DB']=tmp+'/data.sqlite3';os.environ['JB360_ADMIN_PASSWORD']='A-strong-admin-password-2026'
        sys.path.insert(0,os.path.dirname(__file__))
        for name in ('vector_fiscal', 'fiscal2026','normativa_control','catalogo_api','versat_bridge','commercial','extension','server'):
            sys.modules.pop(name,None)
        server=importlib.import_module('server')
        with TestClient(server.app) as client:
            def login(user,pw):
                r=client.post('/api/login',json={'username':user,'password':pw});assert r.status_code==200,r.text
                return {'Authorization':'Bearer '+r.json()['token']}
            a=login('admin','A-strong-admin-password-2026')
            r=client.post('/api/users',headers=a,json={'username':'vendedor','password':'Operator-Password-2026','role':'operator'});assert r.status_code==200,r.text
            u=login('vendedor','Operator-Password-2026')
            state=client.get('/api/license',headers=u);assert state.status_code==200 and state.json()['expired']
            assert client.get('/api/products',headers=u).status_code==402
            assert client.post('/api/admin/renew',headers=u,json={'months':6,'reference':'PAGO-1','payment_verified':True}).status_code==403
            assert client.post('/api/admin/renew',headers=a,json={'months':12,'reference':'PAGO-1','payment_verified':True}).status_code==422
            assert client.post('/api/admin/renew',headers=a,json={'months':6,'reference':'PAGO-1','payment_verified':False}).status_code==422
            activation=client.post('/api/admin/renew',headers=a,json={'months':6,'reference':'PAGO-1','payment_verified':True});assert activation.status_code==200,activation.text
            assert client.post('/api/admin/renew',headers=a,json={'months':6,'reference':'PAGO-1','payment_verified':True}).status_code==409
            assert client.post('/api/admin/renew',headers=a,json={'months':6,'reference':'    ','payment_verified':True}).status_code==422
            assert not client.get('/api/license',headers=u).json()['expired']
            today=str(server.business_today())
            p=client.post('/api/products',headers=a,json={'sku':'SKU01','name':'Jabón','price':'100.00','cost':'40.00','stock':100});assert p.status_code==200,p.text
            pid=p.json()['id']
            def sell(i):
                r=client.post('/api/tickets',headers=u,json={'kind':'goods','point':'T001' if i%2 else 'T002','customer':'Cliente','description':'Jabón','items':[{'product_id':pid,'qty':1}],'payments':[{'method':'Efectivo','amount':'60.00'},{'method':'Transferencia','amount':'40.00'}]})
                assert r.status_code==200,r.text
                return r.json()['id']
            with ThreadPoolExecutor(max_workers=8) as pool: ids=list(pool.map(sell,range(30)))
            stock=client.get('/api/products',headers=u).json()['rows'][0]['stock'];assert stock==70
            rev=client.post(f'/api/tickets/{ids[0]}/reverse',headers=u,json={'reason':'Error de captura'});assert rev.status_code==200,rev.text
            assert client.get('/api/products',headers=u).json()['rows'][0]['stock']==71
            assert client.post(f'/api/tickets/{ids[0]}/reverse',headers=u,json={'reason':'Duplicado'}).status_code==409
            service=client.post('/api/tickets',headers=u,json={'kind':'service','point':'T002','customer':'Cliente','description':'Asesoría','service_price':'150.00','service_cost':'30.00','payments':[{'method':'Tarjeta','amount':'150.00'}]});assert service.status_code==200,service.text
            bad=client.post('/api/tickets',headers=u,json={'kind':'goods','point':'T001','customer':'Cliente','description':'Error','items':[{'product_id':pid,'qty':1}],'payments':[{'method':'Efectivo','amount':'1.00'}]});assert bad.status_code==422
            expense=client.post('/api/operations',headers=u,json={'kind':'expense','category':'Suministros','description':'Compra papel','amount':'20.00','payment':'Efectivo','point':'T001','reference':'FAC-1','actor':'mipyme','effective_date':today});assert expense.status_code==200,expense.text
            report=client.get('/api/integrated-report',headers=u,params={'start':today,'end':today});assert report.status_code==200,report.text
            data=report.json();assert data['ticket_sales_cents']==315000,data
            assert data['ticket_refunds_cents']==10000,data
            assert data['net_sales_cents']==305000,data
            assert data['other_expenses_cents']==2000,data
            assert data['gross_collections_by_method_cents']['Efectivo']==180000
            assert data['refunds_by_method_cents']=={'Efectivo':6000,'Transferencia':4000,'Tarjeta':0}
            assert data['net_collections_by_method_cents']=={'Efectivo':174000,'Transferencia':116000,'Tarjeta':15000}
            assert data['by_kind']['bienes']['neto_cents']==290000
            assert data['by_kind']['servicios']=={'tickets_vendidos':1,'tickets_revertidos':0,'ventas_cents':15000,'devoluciones_cents':0,'neto_cents':15000,'costo_cents':3000,'margen_cents':12000}
            assert client.post(f"/api/tickets/{service.json()['id']}/reverse",headers=u,json={'reason':'Servicio cancelado'}).status_code==200
            after=client.get('/api/integrated-report',headers=u,params={'start':today,'end':today}).json()
            assert after['by_kind']['servicios']['neto_cents']==0
            assert after['net_collections_by_method_cents']['Tarjeta']==0
            assert client.get('/api/products',headers=u).json()['rows'][0]['stock']==71
            ledger=client.get('/api/fiscal-ledger',headers=u,params={'start':today,'end':today});assert ledger.status_code==200;assert len(ledger.json()['rows'])==34
            assert client.post('/api/admin/renew',headers=u,json={'months':6,'reference':'PAGO-2','payment_verified':True}).status_code==403
            old=client.get('/api/license',headers=a).json()['expires_on']
            new=client.post('/api/admin/renew',headers=a,json={'months':6,'reference':'PAGO-2','payment_verified':True});assert new.status_code==200,new.text
            assert new.json()['expires_on']>old
            history=client.get('/api/admin/license-renewals',headers=a).json()['rows']
            assert len(history)==2 and history[0]['reference']=='PAGO-2'
            assert client.get('/api/admin/license-renewals',headers=u).status_code==403
            assert client.post('/api/logout',headers=u).status_code==200
            assert client.get('/api/license',headers=u).status_code==401
            print('PASS: 30 concurrent sales; stock; reversal; service; mixed payments; expenses; reports; auxiliary ledger; roles; renewal')
