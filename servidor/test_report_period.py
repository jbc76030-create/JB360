import importlib
import os
import sys
import tempfile

from fastapi.testclient import TestClient


def test_cuban_day_boundary_and_cross_period_service_refund():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['JB360_DB'] = tmp + '/data.sqlite3'
        os.environ['JB360_ADMIN_PASSWORD'] = 'Strong-admin-password-2026'
        sys.path.insert(0, os.path.dirname(__file__))
        for name in ('vector_fiscal', 'fiscal2026', 'versat_bridge', 'normativa_control', 'catalogo_api', 'commercial', 'extension', 'server'):
            sys.modules.pop(name, None)
        server = importlib.import_module('server')
        with TestClient(server.app) as client:
            login = client.post('/api/login', json={'username': 'admin', 'password': 'Strong-admin-password-2026'})
            headers = {'Authorization': 'Bearer ' + login.json()['token']}
            sale = client.post('/api/tickets', headers=headers, json={
                'kind': 'service', 'point': 'P', 'customer': 'C', 'description': 'Informe',
                'service_price': '100.00', 'service_cost': '20.00',
                'payments': [{'method': 'Tarjeta', 'amount': '100.00'}],
            })
            assert sale.status_code == 200, sale.text
            tid = sale.json()['id']
            with server.conn() as db:
                db.execute('UPDATE tickets SET created_at=?, reversed_at=?, reverse_reason=? WHERE id=?',
                           ('2026-10-01T01:00:00+00:00', '2026-10-01T05:00:00+00:00', 'Anulado', tid))
            sep = client.get('/api/integrated-report', headers=headers, params={'start': '2026-09-30', 'end': '2026-09-30'}).json()
            octo = client.get('/api/integrated-report', headers=headers, params={'start': '2026-10-01', 'end': '2026-10-01'}).json()
            assert sep['by_kind']['servicios']['neto_cents'] == 10000
            assert sep['net_collections_by_method_cents']['Tarjeta'] == 10000
            assert octo['by_kind']['servicios']['neto_cents'] == -10000
            assert octo['net_collections_by_method_cents']['Tarjeta'] == -10000
            assert octo['by_kind']['bienes']['neto_cents'] == 0
