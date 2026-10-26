"""Dos negocios acceden concurrentemente a una sola dirección sin mezclar datos."""
import base64
import importlib
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient


def test_single_url_isolates_accounts_licenses_documents_and_sales():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['JB360_DB'] = tmp + '/central.sqlite3'
        os.environ['JB360_ADMIN_PASSWORD'] = 'General-admin-password-2026'
        sys.path.insert(0, os.path.dirname(__file__))
        for name in ('vector_fiscal', 'fiscal2026', 'versat_bridge', 'normativa_control',
                     'catalogo_api', 'commercial', 'extension', 'server'):
            sys.modules.pop(name, None)
        server = importlib.import_module('server')
        with TestClient(server.app) as client:
            def call(method, path, token=None, business=None, **kwargs):
                headers = {}
                if token: headers['Authorization'] = 'Bearer ' + token
                if business: headers['X-JB360-Cliente'] = business
                return client.request(method, path, headers=headers, **kwargs)

            def login(tenant, password):
                response = call('POST', '/api/login', json={
                    'tenant': tenant, 'username': 'vendedor' if tenant else 'admin',
                    'password': password})
                assert response.status_code == 200, response.text
                return response.json()['token']

            root = login('', 'General-admin-password-2026')
            for slug, password in (('uno', 'Clave-cliente-uno-2026'),
                                   ('dos', 'Clave-cliente-dos-2026')):
                response = call('POST', '/api/root/tenants', root, json={
                    'slug': slug, 'name': 'Negocio ' + slug,
                    'username': 'vendedor', 'password': password})
                assert response.status_code == 200, response.text
            a = login('uno', 'Clave-cliente-uno-2026')
            b = login('dos', 'Clave-cliente-dos-2026')
            assert a != b
            assert call('POST', '/api/login', json={'tenant': 'dos', 'username': 'vendedor',
                       'password': 'Clave-cliente-uno-2026'}).status_code == 401
            assert call('GET', '/api/license', a).json()['expired'] is True
            assert call('GET', '/api/license', b).json()['expired'] is True
            assert call('GET', '/api/license', a, business='dos').status_code == 403
            assert call('GET', '/api/root/tenants', a).status_code == 403
            assert call('POST', '/api/admin/renew', a, json={'months': 6,
                        'reference': 'PAGO-FALSO', 'payment_verified': True}).status_code == 403
            assert call('POST', '/api/admin/renew', root, 'uno', json={'months': 6,
                        'reference': 'PAGO-UNO', 'payment_verified': True}).status_code == 200
            assert call('GET', '/api/license', a).json()['expired'] is False
            assert call('GET', '/api/license', b).json()['expired'] is True
            assert call('GET', '/api/products', b).status_code == 402
            assert call('POST', '/api/admin/renew', root, 'dos', json={'months': 6,
                        'reference': 'PAGO-DOS', 'payment_verified': True}).status_code == 200

            def sell(slug, token, value):
                return call('POST', '/api/tickets', token, json={
                    'kind': 'service', 'point': 'P1', 'customer': slug,
                    'description': 'Informe de ' + slug, 'service_price': value,
                    'service_cost': '0', 'payments': [{'method': 'Efectivo', 'amount': value}]})

            with ThreadPoolExecutor(max_workers=2) as pool:
                ra, rb = list(pool.map(lambda args: sell(*args),
                                       [('uno', a, '100.00'), ('dos', b, '250.00')]))
            assert ra.status_code == 200 and rb.status_code == 200
            assert ra.json()['id'] == rb.json()['id'] == 1  # Different databases.
            period = '?start=2026-01-01&end=2026-12-31'
            assert call('GET', '/api/integrated-report' + period, a).json()['net_sales_cents'] == 10000
            assert call('GET', '/api/integrated-report' + period, b).json()['net_sales_cents'] == 25000
            pdf = base64.b64encode(b'%PDF-1.4\n%%EOF').decode()
            upload = call('POST', '/api/fiscal/vector', a, json={
                'actor': 'mipyme', 'nit': '12345678901', 'approved_on': '2026-01-01',
                'filename': 'vector-uno.pdf', 'file_b64': pdf})
            assert upload.status_code == 200
            assert call('GET', '/api/fiscal/vector', b).json()['vector'] is None
            assert call('GET', '/api/fiscal/vector/download', b).status_code == 404
            assert call('POST', '/api/admin/contabilidad/normativa/documentos', root, 'uno', json={
                'norma': 'MFP-272-2024', 'filename': 'norma.pdf', 'file_b64': pdf}).status_code == 200
            assert call('GET', '/api/admin/contabilidad/normativa/documentos', root, 'dos').json()['documentos'] == []
            assert call('POST', '/api/admin/backup', root, 'uno',
                        json={'password': 'General-admin-password-2026'}).status_code == 200
            assert call('POST', '/api/admin/backup', root, 'uno',
                        json={'password': 'Clave-cliente-uno-2026'}).status_code == 403
            operators = call('GET', '/api/admin/users', root, 'dos').json()['rows']
            operator_id = next(row['id'] for row in operators if row['username'] == 'vendedor')
            assert call('POST', f'/api/admin/users/{operator_id}/password', a,
                        json={'admin_password': 'Clave-cliente-uno-2026',
                              'new_password': 'Nueva-clave-dos-2026'}).status_code == 403
            assert call('POST', f'/api/admin/users/{operator_id}/password', root, 'dos',
                        json={'admin_password': 'General-admin-password-2026',
                              'new_password': 'Nueva-clave-dos-2026'}).status_code == 200
            assert call('GET', '/api/license', b).status_code == 401
            b = login('dos', 'Nueva-clave-dos-2026')
            assert call('GET', '/api/integrated-report' + period, b).json()['net_sales_cents'] == 25000
            assert call('POST', '/api/account/password', b, json={
                'old_password': 'incorrecta', 'new_password': 'Otra-clave-dos-2026'}).status_code == 403
            assert call('POST', '/api/account/password', b, json={
                'old_password': 'Nueva-clave-dos-2026', 'new_password': 'Otra-clave-dos-2026'}).status_code == 200
            assert call('GET', '/api/license', b).status_code == 401
            b = login('dos', 'Otra-clave-dos-2026')
            assert call('GET', '/api/license', b).status_code == 200
            assert call('POST', '/api/logout', root, 'uno').status_code == 200
            assert call('GET', '/api/root/tenants', root).status_code == 401
            assert call('GET', '/api/license', a).status_code == 200
