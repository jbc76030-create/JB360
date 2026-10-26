import datetime
import importlib
import os
import sys
import tempfile

from fastapi.testclient import TestClient


def test_actor_examples_and_license():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['JB360_DB'] = tmp + '/test.sqlite3'
        os.environ['JB360_ADMIN_PASSWORD'] = 'Strong-admin-password-2026'
        sys.path.insert(0, os.path.dirname(__file__))
        for name in ('fiscal2026', 'versat_bridge', 'normativa_control', 'catalogo_api', 'commercial', 'extension', 'server'):
            sys.modules.pop(name, None)
        server = importlib.import_module('server')
        with TestClient(server.app) as c:
            def login(username, password):
                r = c.post('/api/login', json={'username': username, 'password': password})
                assert r.status_code == 200, r.text
                return {'Authorization': 'Bearer ' + r.json()['token']}

            admin = login('admin', 'Strong-admin-password-2026')
            assert c.post('/api/users', headers=admin, json={'username': 'owner2', 'password': 'Strong-password-2026', 'role': 'admin'}).status_code == 422
            assert c.post('/api/users', headers=admin, json={'username': 'cliente', 'password': 'Strong-password-2026', 'role': 'operator'}).status_code == 200
            user = login('cliente', 'Strong-password-2026')
            month = server.business_today().strftime('%Y-%m')
            if not month.startswith('2026-'):
                month = '2026-10'
            base = dict(actor='mipyme', month=month, goods_base='1000.00', services_base='500.00',
                        taxable_profit='200.00', payroll_base='100.00', total_activity_income_base='1500.00',
                        exceptions_reviewed=True, bases_reviewed=True)
            assert c.post('/api/fiscal/simulate', headers=user, json=base).status_code == 402
            assert c.post('/api/admin/renew', headers=admin, json={'months': 6, 'reference': 'COBRO-001', 'payment_verified': True}).status_code == 200
            assert c.post('/api/fiscal/simulate', headers=user, json={**base, 'exceptions_reviewed': False}).status_code == 422
            assert c.post('/api/fiscal/simulate', headers=user, json={**base, 'actor': 'autonomo'}).status_code == 422
            assert c.post('/api/fiscal/simulate', headers=user, json={**base, 'services_base': '-1'}).status_code == 422
            result = c.post('/api/fiscal/simulate', headers=user, json=base)
            assert result.status_code == 200, result.text
            lines = {x['concepto']: x['estimado_cents'] for x in result.json()['lineas']}
            assert lines['Ventas y servicios gravados'] == 15000
            assert lines['Impuesto sobre utilidades (base imponible revisada)'] == 7000
            assert lines['Contribución territorial MIPYME'] == 1500
            assert lines['Impuesto por utilización de fuerza de trabajo'] == 500
            assert lines['Contribución a seguridad social: 12,5 % al fisco y 1,5 % provisionado'] == 1400
            tcp = {**base, 'actor': 'tcp', 'personal_income_base': '5000.00', 'taxable_profit': None,
                   'payroll_base': None, 'total_activity_income_base': None}
            rows = c.post('/api/fiscal/simulate', headers=user, json=tcp).json()['lineas']
            assert [x['estimado_cents'] for x in rows] == [15000, 8700]
            pdl = {**base, 'actor': 'pdl', 'month': '2026-11', 'situation': 'pdl_minindustry_food', 'total_activity_income_base': None}
            assert c.post('/api/fiscal/simulate', headers=user, json={**pdl, 'month': '2026-10'}).status_code == 422
            rows = c.post('/api/fiscal/simulate', headers=user, json=pdl).json()['lineas']
            assert [x['estimado_cents'] for x in rows] == [5000, 5000, 7000, 500, 1400]
            cna = {**base, 'actor': 'cna', 'payroll_base': None, 'total_activity_income_base': None}
            assert [x['estimado_cents'] for x in c.post('/api/fiscal/simulate', headers=user, json=cna).json()['lineas']] == [15000, 7000]
            estatal = {**cna, 'actor': 'estatal', 'situation': 'state_retail_to_population'}
            assert [x['estimado_cents'] for x in c.post('/api/fiscal/simulate', headers=user, json=estatal).json()['lineas']] == [15000, 7000]
            assert c.post('/api/fiscal/simulate', headers=user, json={**estatal, 'situation': 'standard'}).status_code == 422
            # The proposed base distinguishes a service from a good and follows a reversal.
            if server.business_today().year == 2026:
                goods = c.post('/api/products', headers=user, json={'sku': 'X', 'name': 'Bien', 'price': '100.00', 'cost': '20.00', 'stock': 2}).json()['id']
                first = c.post('/api/tickets', headers=user, json={'kind': 'goods', 'point': 'P', 'customer': 'C', 'description': 'Bien', 'items': [{'product_id': goods, 'qty': 1}], 'payments': [{'method': 'Efectivo', 'amount': '100.00'}]})
                assert first.status_code == 200, first.text
                second = c.post('/api/tickets', headers=user, json={'kind': 'service', 'point': 'P', 'customer': 'C', 'description': 'Servicio', 'service_price': '50.00', 'service_cost': '10.00', 'payments': [{'method': 'Tarjeta', 'amount': '50.00'}]})
                assert second.status_code == 200, second.text
                proposed = c.get('/api/fiscal/proposed', headers=user, params={'month': month}).json()
                assert (proposed['ventas_bienes_cents'], proposed['servicios_cents']) == (10000, 5000)
                assert c.post(f"/api/tickets/{second.json()['id']}/reverse", headers=user, json={'reason': 'Anulación de prueba'}).status_code == 200
                proposed = c.get('/api/fiscal/proposed', headers=user, params={'month': month}).json()
                assert (proposed['ventas_bienes_cents'], proposed['servicios_cents']) == (10000, 0)
