"""El respaldo central incluye todos los negocios y omite sesiones activas."""
import hashlib
import importlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


def test_consistent_multi_business_archive():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['JB360_DB'] = tmp + '/central.sqlite3'
        os.environ['JB360_ADMIN_PASSWORD'] = 'Clave-central-respaldo-2026'
        sys.path.insert(0, os.path.dirname(__file__))
        for name in ('vector_fiscal', 'fiscal2026', 'versat_bridge', 'normativa_control',
                     'catalogo_api', 'commercial', 'extension', 'server'):
            sys.modules.pop(name, None)
        server = importlib.import_module('server')
        with TestClient(server.app) as client:
            root = client.post('/api/login', json={'username': 'admin',
                                'password': 'Clave-central-respaldo-2026'}).json()['token']
            admin = {'Authorization': 'Bearer ' + root}
            for slug in ('uno', 'dos'):
                response = client.post('/api/root/tenants', headers=admin, json={
                    'slug': slug, 'name': 'Cliente ' + slug,
                    'username': 'operador', 'password': 'Clave-operador-2026'})
                assert response.status_code == 200, response.text
            scope_a = {**admin, 'X-JB360-Cliente': 'uno'}
            assert client.post('/api/admin/renew', headers=scope_a, json={
                'months': 6, 'reference': 'PAGO-UNO', 'payment_verified': True}).status_code == 200
            copy_file = Path(tmp) / 'respaldo.zip'
            with copy_file.open('wb') as out:
                result = subprocess.run([sys.executable, 'backup_all.py'],
                    cwd=Path(__file__).parent, env=os.environ.copy(), stdout=out,
                    stderr=subprocess.PIPE, timeout=30)
            assert result.returncode == 0, result.stderr.decode()
        with zipfile.ZipFile(copy_file) as archive:
            assert archive.testzip() is None
            manifest = json.loads(archive.read('manifest.json'))
            assert {row['name'] for row in manifest['databases']} == {
                'central.sqlite3', 'clientes/uno.sqlite3', 'clientes/dos.sqlite3'}
            for row in manifest['databases']:
                contents = archive.read(row['name'])
                assert hashlib.sha256(contents).hexdigest() == row['sha256']
                db_path = Path(tmp) / ('check-' + Path(row['name']).name)
                db_path.write_bytes(contents)
                with sqlite3.connect(db_path) as db:
                    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                    assert db.execute('SELECT COUNT(*) FROM tokens').fetchone()[0] == 0
                if row['name'] == 'clientes/uno.sqlite3':
                    with sqlite3.connect(db_path) as db:
                        assert db.execute('SELECT renewal_count FROM license_state').fetchone()[0] == 1
                if row['name'] == 'clientes/dos.sqlite3':
                    with sqlite3.connect(db_path) as db:
                        assert db.execute('SELECT renewal_count FROM license_state').fetchone()[0] == 0
