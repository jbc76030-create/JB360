import base64
import importlib
import os
import sys
import tempfile
import sqlite3

from fastapi.testclient import TestClient


def test_vector_access_integrity_and_login_limit():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['JB360_DB'] = tmp + '/data.sqlite3'
        os.environ['JB360_ADMIN_PASSWORD'] = 'Secure-admin-password-2026'
        sys.path.insert(0, os.path.dirname(__file__))
        for name in ('vector_fiscal', 'fiscal2026', 'versat_bridge', 'normativa_control',
                     'catalogo_api', 'commercial', 'extension', 'server'):
            sys.modules.pop(name, None)
        server = importlib.import_module('server')
        with TestClient(server.app) as client:
            for _ in range(5):
                assert client.post('/api/login', json={'username': 'admin', 'password': 'wrong'}).status_code == 401
            assert client.post('/api/login', json={'username': 'admin', 'password': 'Secure-admin-password-2026'}).status_code == 429
            with server.conn() as db:
                db.execute('DELETE FROM login_failures')
            r = client.post('/api/login', json={'username': 'admin', 'password': 'Secure-admin-password-2026'})
            admin = {'Authorization': 'Bearer ' + r.json()['token']}
            assert client.get('/api/fiscal/vector', headers=admin).headers['x-content-type-options'] == 'nosniff'
            assert client.get('/api/fiscal/vector', headers=admin).headers['x-frame-options'] == 'DENY'
            page = client.get('/')
            assert page.status_code == 200 and '<script src="/app.js" defer></script>' in page.text
            assert "script-src 'self';" in page.headers['content-security-policy']
            assert 'onclick=' not in page.text
            assert client.get('/app.js').status_code == 200
            assert client.post('/api/users', headers=admin, json={
                'username': 'operador', 'password': 'Secure-client-password-2026', 'role': 'operator',
            }).status_code == 200
            r = client.post('/api/login', json={'username': 'operador', 'password': 'Secure-client-password-2026'})
            user = {'Authorization': 'Bearer ' + r.json()['token']}
            good = base64.b64encode(b'%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF').decode()
            payload = dict(actor='mipyme', nit='12345678901', approved_on='2026-01-01',
                           filename='../../vector.pdf', file_b64=good)
            assert client.post('/api/fiscal/vector', headers=user, json=payload).status_code == 402
            assert client.post('/api/admin/renew', headers=admin, json={
                'months': 6, 'reference': 'VECTOR-001', 'payment_verified': True,
            }).status_code == 200
            assert client.post('/api/fiscal/vector', headers=user, json={**payload, 'file_b64': base64.b64encode(b'<script>').decode()}).status_code == 422
            r = client.post('/api/fiscal/vector', headers=user, json=payload)
            assert r.status_code == 200, r.text
            vid = r.json()['id']
            info = client.get('/api/fiscal/vector', headers=user).json()['vector']
            assert info['filename'] == 'vector.pdf' and info['status'] == 'pending'
            download = client.get('/api/fiscal/vector/download', headers=user)
            assert download.status_code == 200 and download.content.startswith(b'%PDF-')
            assert download.headers['content-disposition'].startswith('attachment;')
            review = dict(vector_id=vid, situation='standard', obligations=['sales_services', 'profit'],
                          valid_from='2026-01-01', valid_to='2026-12-31',
                          review_note='Cotejo manual de prueba con vector aprobado')
            assert client.post('/api/admin/fiscal/vector/review', headers=user, json=review).status_code == 403
            assert client.post('/api/admin/fiscal/vector/review', headers=admin,
                               json={**review, 'obligations': ['invented_tax']}).status_code == 422
            assert client.post('/api/admin/fiscal/vector/review', headers=admin, json=review).status_code == 200
            assert client.post('/api/admin/fiscal/vector/review', headers=admin, json=review).status_code == 409
            second = client.post('/api/fiscal/vector', headers=user, json=payload)
            assert second.status_code == 200
            vector_state = client.get('/api/fiscal/vector', headers=user).json()
            assert vector_state['vector']['status'] == 'pending'
            assert vector_state['active_vector']['id'] == vid
            previous_rule = client.post('/api/fiscal/simulate', headers=user, json={
                'actor': 'mipyme', 'month': '2026-10', 'situation': 'standard',
                'goods_base': '100.00', 'services_base': '0',
                'bases_reviewed': True, 'exceptions_reviewed': True,
            })
            assert previous_rule.status_code == 200
            assert previous_rule.json()['lineas'][0]['estimado_cents'] == 1000
            with server.conn() as db:
                db.execute('UPDATE fiscal_vectors SET content=? WHERE id=?', (b'tampered', second.json()['id']))
            assert client.get('/api/fiscal/vector/download', headers=user).status_code == 409
            assert client.post('/api/admin/backup', headers=user,
                               json={'password': 'Secure-admin-password-2026'}).status_code == 403
            assert client.post('/api/admin/backup', headers=admin,
                               json={'password': 'wrong'}).status_code == 403
            backup = client.post('/api/admin/backup', headers=admin,
                                 json={'password': 'Secure-admin-password-2026'})
            assert backup.status_code == 200 and backup.content.startswith(b'SQLite format 3')
            backup_path = tmp + '/restored.sqlite3'
            with open(backup_path, 'wb') as saved:
                saved.write(backup.content)
            with sqlite3.connect(backup_path) as db:
                assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                assert db.execute('SELECT COUNT(*) FROM fiscal_vectors').fetchone()[0] == 2
                assert db.execute('SELECT COUNT(*) FROM tokens').fetchone()[0] == 0
