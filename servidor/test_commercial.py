import os,sys,tempfile,importlib
from fastapi.testclient import TestClient

def test_parties_invoice_and_roles():
 with tempfile.TemporaryDirectory() as d:
  os.environ['JB360_DB']=d+'/db.sqlite3';os.environ['JB360_ADMIN_PASSWORD']='Admin-Password-2026-Strong'
  sys.path.insert(0,os.path.dirname(__file__))
  for n in ('vector_fiscal', 'fiscal2026','normativa_control','catalogo_api','versat_bridge','commercial','extension','server'):sys.modules.pop(n,None)
  s=importlib.import_module('server')
  with TestClient(s.app) as c:
   def auth(user,password):
    r=c.post('/api/login',json={'username':user,'password':password});assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}
   a=auth('admin','Admin-Password-2026-Strong')
   assert c.post('/api/admin/renew',headers=a,json={'months':6,'reference':'PAGO-PRUEBA','payment_verified':True}).status_code==200
   assert c.post('/api/users',headers=a,json={'username':'cajero','password':'Password-2026-Strong','role':'operator'}).status_code==200
   u=auth('cajero','Password-2026-Strong')
   assert c.post('/api/issuer',headers=u,json={'name':'Mi Empresa','tax_id':'123','address':'Morón','actor':'mipyme'}).status_code==403
   assert c.post('/api/issuer',headers=a,json={'name':'Mi Empresa','tax_id':'123','address':'Morón','actor':'mipyme'}).status_code==200
   p=c.post('/api/parties',headers=u,json={'kind':'customer','name':'Cliente Uno','tax_id':'456','address':'Ciego de Ávila'});assert p.status_code==200,p.text
   customer=p.json()['id']
   assert c.post('/api/parties',headers=u,json={'kind':'supplier','name':'Proveedor Uno','tax_id':'789','address':'Cuba'}).status_code==200
   assert len(c.get('/api/parties',headers=u).json()['rows'])==2
   product=c.post('/api/products',headers=a,json={'sku':'A','name':'Jabón','price':'100.00','cost':'40.00','stock':3}).json()['id']
   t=c.post('/api/tickets',headers=u,json={'kind':'goods','point':'T001','customer':'Cliente Uno','description':'Jabón','items':[{'product_id':product,'qty':1}],'payments':[{'method':'Efectivo','amount':'100.00'}]});assert t.status_code==200,t.text
   tid=t.json()['id']
   payload={'ticket_id':tid,'customer_id':customer,'series':'JB'}
   inv=c.post('/api/invoices',headers=u,json=payload);assert inv.status_code==200,inv.text
   iid=inv.json()['id'];assert inv.json()['number'].startswith('JB-')
   assert c.post('/api/invoices',headers=u,json=payload).status_code==409
   assert c.get(f'/api/invoices/{iid}',headers=u).json()['invoice']['issuer_tax_id']=='123'
   assert 'BORRADOR COMERCIAL' in c.get(f'/api/invoices/{iid}/print',headers=u).text
   t2=c.post('/api/tickets',headers=u,json={'kind':'goods','point':'T001','customer':'Cliente Uno','description':'Jabón','items':[{'product_id':product,'qty':1}],'payments':[{'method':'Efectivo','amount':'100.00'}]}).json()['id']
   assert c.post(f'/api/tickets/{t2}/reverse',headers=u,json={'reason':'Error en registro'}).status_code==200
   assert c.post('/api/invoices',headers=u,json={**payload,'ticket_id':t2}).status_code==409
