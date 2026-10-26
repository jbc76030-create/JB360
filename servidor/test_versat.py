import os,sys,datetime,tempfile,importlib
from fastapi.testclient import TestClient

def test_accounting_bridge():
    with tempfile.TemporaryDirectory() as td:
        os.environ['JB360_DB']=td+'/test.sqlite3'
        os.environ['JB360_ADMIN_PASSWORD']='secure-test-password'
        sys.path.insert(0,os.path.dirname(__file__))
        for name in ('vector_fiscal', 'fiscal2026','normativa_control','catalogo_api','versat_bridge','commercial','extension','server'):
            sys.modules.pop(name,None)
        import server
        server.init()
        with server.conn() as c:
            salt='ab'*16
            c.execute('INSERT INTO users(username,salt,password_hash,role) VALUES(?,?,?,?)',('admin',salt,server.hashpw('secure-test-password',salt),'admin'))
        import extension
        with TestClient(server.app) as client:
            tok=client.post('/api/login',json={'username':'admin','password':'secure-test-password'}).json()['token']
            h={'Authorization':'Bearer '+tok}
            m={k:str(i+100) for i,k in enumerate(['cash','transfer','card','revenue_goods','revenue_services','inventory','cost_of_goods','expenses','other_income','clearing'])}
            m.update(unit='U01',cost_center='C01')
            assert client.post('/api/admin/versat/mapping',headers=h,json=m).status_code==200
            p=client.post('/api/products',headers=h,json={'sku':'A1','name':'Producto','price':'20','cost':'8','stock':10})
            assert p.status_code==200,p.text
            t=client.post('/api/tickets',headers=h,json={'kind':'goods','point':'T001','customer':'Consumidor','description':'venta','items':[{'product_id':p.json()['id'],'qty':2}],'payments':[{'method':'Efectivo','amount':'10'},{'method':'Tarjeta','amount':'30'}]})
            assert t.status_code==200,t.text
            # Dates are real today; test the pure builder with controlled date updates.
            yesterday=(datetime.date.today()-datetime.timedelta(days=1)).isoformat()
            with server.conn() as c:c.execute('UPDATE tickets SET created_at=? WHERE id=?',(yesterday+'T10:00:00+00:00',t.json()['id']))
            res=client.get('/api/admin/versat/preview',params={'start':yesterday,'end':yesterday},headers=h)
            assert res.status_code==200,res.text
            data=res.json();assert data['balanced'] and data['total_debe_cents']==data['total_haber_cents']==5600
            assert len(data['rows'])==6
            csv=client.get('/api/admin/versat/export.csv',params={'start':yesterday,'end':yesterday},headers=h)
            assert csv.status_code==200 and 'JB-T-' in csv.text
            # An unclassified manual expense must stop export, never invent accounts.
            with server.conn() as c:
                uid=c.execute('SELECT id FROM users WHERE username=?',('admin',)).fetchone()[0]
                c.execute('INSERT INTO operations(kind,category,description,amount_cents,payment,point,reference,actor,recorded_at,effective_date,user_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)',('expense','General','sin clasificar',500,'Efectivo','T001','X','mipyme',yesterday,yesterday,uid))
            bad=client.get('/api/admin/versat/preview',params={'start':yesterday,'end':yesterday},headers=h)
            assert bad.status_code==409
