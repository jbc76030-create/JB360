import os, sys, importlib, tempfile
from fastapi.testclient import TestClient

def test_registro_y_lotes():
    with tempfile.TemporaryDirectory() as td:
        os.environ['JB360_DB']=td+'/test.sqlite3';os.environ['JB360_ADMIN_PASSWORD']='TestAdmin_2026!'
        for name in ('vector_fiscal', 'fiscal2026','normativa_control','catalogo_api','versat_bridge','commercial','extension','server'):
            sys.modules.pop(name,None)
        server=importlib.import_module('server')
        from normativa_control import REG
        assert len(REG['instrumentos'])==4
        assert all(x['url'].startswith('https://') for x in REG['instrumentos'])
        assert all('gacetaoficial.gob.cu' in x['url'] for x in REG['instrumentos'])
        assert 'MFP-272-2024' in {x['id'] for x in REG['instrumentos']}
        assert 'MFP-346-2021' not in {x['id'] for x in REG['instrumentos']}
        assert all(x['estado_verificacion'] for x in REG['instrumentos'])
        with TestClient(server.app) as c:
            r=c.get('/api/contabilidad/normativa/registro')
            assert r.status_code in (401,403)
            r=c.post('/api/admin/contabilidad/normativa/lotes',json={'version':'2026-revision','cuentas':[{'codigo':'101','nombre':'Caja','naturaleza':'activo','uso_contenido':'Uso de caja conforme a la fuente','norma':'MFP-494-2016','anexo':'1','pagina':'1','regimen':'empresarial'}]})
            assert r.status_code in (401,403)
