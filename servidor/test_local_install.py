"""Primer arranque y reinicio de una instalación local independiente."""
import os
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
        for restart in range(2):
            if restart:
                env.pop('JB360_ADMIN_PASSWORD')
            process = run_until_ready(env, url)
            try:
                assert Path(env['JB360_DB']).is_file()
                if restart:
                    data = b'{"username":"admin","password":"Clave-admin-instalacion-2026"}'
                    request = urllib.request.Request(url + 'api/login', data=data,
                                                     headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(request, timeout=5) as response:
                        assert response.status == 200
            finally:
                process.terminate()
                process.wait(timeout=5)
