"""Dos procesos con bases separadas: licencia, vector y ventas independientes."""
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def call(url, path, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url + path,
                                     data=json.dumps(data).encode() if data is not None else None,
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_two_businesses_have_independent_access_license_and_vector():
    processes = []
    with tempfile.TemporaryDirectory() as tmp:
        try:
            urls = []
            for slug in ('a', 'b'):
                port = free_port()
                env = os.environ.copy()
                env['JB360_DB'] = str(Path(tmp) / f'{slug}.sqlite3')
                env['JB360_ADMIN_PASSWORD'] = 'Admin-password-' + slug + '-2026'
                process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server:app',
                                            '--host', '127.0.0.1', '--port', str(port)],
                                           cwd=Path(__file__).parent, env=env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                processes.append(process)
                url = f'http://127.0.0.1:{port}'
                for _ in range(60):
                    try:
                        with urllib.request.urlopen(url + '/', timeout=1) as response:
                            if response.status == 200:
                                break
                    except (OSError, urllib.error.URLError):
                        if process.poll() is not None:
                            raise AssertionError('No arrancó la instalación ' + slug)
                        time.sleep(.1)
                else:
                    raise AssertionError('Instalación sin respuesta ' + slug)
                urls.append(url)
            a, b = urls
            admin_a = call(a, '/api/login', {'username': 'admin', 'password': 'Admin-password-a-2026'})[1]['token']
            admin_b = call(b, '/api/login', {'username': 'admin', 'password': 'Admin-password-b-2026'})[1]['token']
            for url, admin in ((a, admin_a), (b, admin_b)):
                assert call(url, '/api/users', {'username': 'cliente', 'password': 'Client-password-2026',
                                               'role': 'operator'}, admin)[0] == 200
            user_a = call(a, '/api/login', {'username': 'cliente', 'password': 'Client-password-2026'})[1]['token']
            user_b = call(b, '/api/login', {'username': 'cliente', 'password': 'Client-password-2026'})[1]['token']
            assert call(a, '/api/admin/renew', {'months': 6, 'reference': 'COBRO-A',
                                                'payment_verified': True}, admin_a)[0] == 200
            assert call(a, '/api/license', token=user_a)[1]['expired'] is False
            assert call(b, '/api/license', token=user_b)[1]['expired'] is True
            assert call(b, '/api/products', token=user_b)[0] == 402
            assert call(b, '/api/products', token=user_a)[0] == 401
            pdf = base64.b64encode(b'%PDF-1.4\n%%EOF').decode()
            upload = call(a, '/api/fiscal/vector', {'actor': 'mipyme', 'nit': '12345678901',
                          'approved_on': '2026-01-01', 'filename': 'vector.pdf', 'file_b64': pdf}, user_a)
            assert upload[0] == 200
            assert call(a, '/api/admin/fiscal/vector/review', {
                'vector_id': upload[1]['id'], 'situation': 'standard',
                'obligations': ['sales_services'], 'valid_from': '2026-01-01',
                'valid_to': '2026-12-31', 'review_note': 'Cotejado para negocio A de prueba',
            }, admin_a)[0] == 200
            assert call(a, '/api/fiscal/vector', token=user_a)[1]['active_vector']['nit'] == '12345678901'
            assert call(b, '/api/fiscal/vector', token=admin_b)[1]['active_vector'] is None
            assert call(a, '/api/tickets', {'kind': 'service', 'point': 'P', 'customer': 'A',
                        'description': 'Servicio A', 'service_price': '100.00', 'service_cost': '10.00',
                        'payments': [{'method': 'Efectivo', 'amount': '100.00'}]}, user_a)[0] == 200
            assert call(b, '/api/integrated-report?start=2026-01-01&end=2026-12-31', token=admin_b)[1]['ticket_sales_cents'] == 0
            assert call(a, '/api/integrated-report?start=2026-01-01&end=2026-12-31', token=admin_a)[1]['ticket_sales_cents'] == 10000
        finally:
            for process in processes:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
