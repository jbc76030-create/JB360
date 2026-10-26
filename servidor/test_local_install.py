"""Primer arranque y reinicio de una instalación local independiente."""
import os
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def available_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def run_until_ready(env, url):
    process = subprocess.Popen([sys.executable, 'iniciar.py'],
                               cwd=Path(__file__).parent, env=env,
                               stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(70):
        if process.poll() is not None:
            raise AssertionError('No arrancó la instalación local')
        try:
            with urllib.request.urlopen(url, timeout=.5) as response:
                if response.status == 200:
                    return process
        except (OSError, urllib.error.URLError):
            time.sleep(.1)
    process.terminate()
    raise AssertionError('El servidor local no respondió')


def test_first_install_and_restart_without_admin_secret_in_file():
    with tempfile.TemporaryDirectory() as tmp:
        port = available_port()
        url = f'http://127.0.0.1:{port}/'
        env = os.environ.copy()
        env.update(JB360_DB=tmp + '/cliente.sqlite3', JB360_PORT=str(port),
                   JB360_ADMIN_PASSWORD='Clave-admin-instalacion-2026')
        backup_file = tmp + '/copia_restaurada.sqlite3'
        for restart in range(2):
            if restart:
                env.pop('JB360_ADMIN_PASSWORD')
                env['JB360_DB'] = backup_file
            process = run_until_ready(env, url)
            try:
                assert Path(env['JB360_DB']).is_file()
                def post(path, data, token=None):
                    headers = {'Content-Type': 'application/json'}
                    if token: headers['Authorization'] = 'Bearer ' + token
                    request = urllib.request.Request(url + path, data=json.dumps(data).encode(),
                                                     headers=headers)
                    with urllib.request.urlopen(request, timeout=5) as response:
                        return response.read()
                admin = json.loads(post('api/login', {'username': 'admin',
                              'password': 'Clave-admin-instalacion-2026'}))['token']
                if not restart:
                    assert json.loads(post('api/users', {'username': 'operador',
                        'password': 'Clave-operador-2026', 'role': 'operator'}, admin))['ok']
                    assert json.loads(post('api/admin/renew', {'months': 6,
                        'reference': 'PAGO-INSTALACION', 'payment_verified': True}, admin))['ok']
                    Path(backup_file).write_bytes(post('api/admin/backup',
                        {'password': 'Clave-admin-instalacion-2026'}, admin))
                else:
                    operator = json.loads(post('api/login', {'username': 'operador',
                                  'password': 'Clave-operador-2026'}))['token']
                    request = urllib.request.Request(url + 'api/license',
                                headers={'Authorization': 'Bearer ' + operator})
                    with urllib.request.urlopen(request, timeout=5) as response:
                        assert json.loads(response.read())['expired'] is False
            finally:
                process.terminate()
                process.wait(timeout=5)
