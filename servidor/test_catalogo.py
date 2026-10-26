import os, tempfile, importlib, sys
from fastapi.testclient import TestClient

def test_catalogo_y_plan():
    with tempfile.TemporaryDirectory() as td:
        os.environ['JB360_DB']=os.path.join(td,'test.sqlite3');os.environ['JB360_ADMIN_PASSWORD']='ClaveTemporalMuyLarga*123'
        for name in ('fiscal2026','normativa_control','catalogo_api','versat_bridge','commercial','extension','server'):
            sys.modules.pop(name,None)
        server=importlib.import_module('server')
        with TestClient(server.app) as c:
            t=c.post('/api/login',json={'username':'admin','password':'ClaveTemporalMuyLarga*123'}).json()['token'];h={'Authorization':'Bearer '+t}
            r=c.get('/api/contabilidad/catalogo?regimen=tcp',headers=h)
            assert r.status_code==200 and any(a['codigo']=='100' for a in r.json()['cuentas'])
            assert c.get('/api/contabilidad/catalogo?regimen=desconocido',headers=h).status_code==422
            plan={'regimen':'tcp','version':'local-1','cuentas':[{'codigo':'100','nombre':'Efectivo en Caja','naturaleza':'activo','uso':'Registro de cobros y pagos en caja','fuente':'Res. 346/2021 MFP'}]}
            assert c.post('/api/admin/contabilidad/plan',json=plan,headers=h).json()['estado']=='PENDIENTE_REVISION_CONTABLE'
            assert c.get('/api/admin/contabilidad/plan',headers=h).json()['cuentas'][0]['aprobado']==0
            plan['cuentas'].append(plan['cuentas'][0]);assert c.post('/api/admin/contabilidad/plan',json=plan,headers=h).status_code==422
