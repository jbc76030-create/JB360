import base64, os, sys, importlib, tempfile
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
            token=c.post('/api/login',json={'username':'admin','password':'TestAdmin_2026!'}).json()['token']
            headers={'Authorization':'Bearer '+token}
            entry={'codigo':'101','nombre':'Caja','naturaleza':'activo',
                   'uso_contenido':'Uso y contenido cotejados con la fuente',
                   'norma':'MFP-494-2016','anexo':'1','pagina':'12','regimen':'empresarial'}
            payload={'version':'2026-revision','cuentas':[entry]}
            upload=c.post('/api/admin/contabilidad/normativa/lotes',headers=headers,json=payload)
            assert upload.status_code==200 and upload.json()['estado']=='PENDIENTE_COTEJO'
            assert upload.json()['utilizable_en_asientos'] is False
            assert c.get('/api/admin/contabilidad/normativa/lotes',headers=headers).json()['lotes'][0]['total']==1
            assert c.post('/api/admin/contabilidad/normativa/lotes',headers=headers,
                          json={'version':'duplicado','cuentas':[entry,entry]}).status_code==422
            assert c.post('/api/admin/contabilidad/normativa/lotes',headers=headers,
                          json={'version':'norma-invalida','cuentas':[{**entry,'norma':'MFP-346-2021'}]}).status_code==422
            document={'norma':'MFP-272-2024','filename':'../../normatador.pdf',
                      'file_b64':base64.b64encode(b'%PDF-1.4\n%%EOF').decode()}
            assert c.post('/api/admin/contabilidad/normativa/documentos',json=document).status_code==401
            assert c.post('/api/admin/contabilidad/normativa/documentos',headers=headers,
                          json={**document,'norma':'MFP-346-2021'}).status_code==422
            created=c.post('/api/admin/contabilidad/normativa/documentos',headers=headers,json=document)
            assert created.status_code==200 and created.json()['estado']=='PENDIENTE_COTEJO'
            doc_id=created.json()['id']
            listed=c.get('/api/admin/contabilidad/normativa/documentos',headers=headers).json()['documentos']
            assert listed[0]['filename']=='normatador.pdf' and listed[0]['id']==doc_id
            downloaded=c.get(f'/api/admin/contabilidad/normativa/documentos/{doc_id}/download',headers=headers)
            assert downloaded.status_code==200 and downloaded.content==b'%PDF-1.4\n%%EOF'
