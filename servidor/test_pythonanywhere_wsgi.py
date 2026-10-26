"""The free-host WSGI bridge serves the actual FastAPI app and persistent DB."""
import os
import subprocess
import sys

import pytest


def test_wsgi_bridge_login_and_persistent_database(tmp_path):
    pytest.importorskip('a2wsgi')
    env = os.environ.copy()
    env.update(JB360_DB=str(tmp_path / 'root.sqlite3'),
               JB360_ALLOWED_HOSTS='myname.pythonanywhere.com',
               JB360_ADMIN_PASSWORD='Private-test-passphrase-2026')
    program = r'''
import io, json, os
from wsgiref.util import setup_testing_defaults
from pythonanywhere_wsgi import application

def send(method, path, body=b'', auth=''):
    environ = {}
    setup_testing_defaults(environ)
    environ.update(REQUEST_METHOD=method, PATH_INFO=path,
                   SERVER_NAME='myname.pythonanywhere.com',
                   HTTP_HOST='myname.pythonanywhere.com',
                   CONTENT_TYPE='application/json',
                   CONTENT_LENGTH=str(len(body)),
                   HTTP_AUTHORIZATION=auth,
                   **{'wsgi.input': io.BytesIO(body), 'wsgi.url_scheme': 'https'})
    result = []
    def start_response(status, headers, exc_info=None):
        result.extend([status, dict(headers)])
    data = b''.join(application(environ, start_response))
    return result[0], result[1], data

status, headers, page = send('GET', '/')
assert status.startswith('200 '), status
assert b'JB360' in page
assert 'strict-transport-security' in headers
status, headers, script = send('GET', '/app.js')
assert status.startswith('200 '), status
assert len(script) > 100
status, headers, data = send('POST', '/api/login',
    json.dumps({'username': 'admin', 'password': os.environ['JB360_ADMIN_PASSWORD']}).encode())
assert status.startswith('200 '), (status, data)
token = json.loads(data)['token']
assert token.startswith('root.')
status, headers, data = send('POST', '/api/admin/backup',
    json.dumps({'password': os.environ['JB360_ADMIN_PASSWORD']}).encode(), 'Bearer ' + token)
assert status.startswith('200 '), (status, data)
assert data[:16] == b'SQLite format 3\x00'
assert os.path.isfile(os.environ['JB360_DB'])
'''
    result = subprocess.run([sys.executable, '-c', program], env=env,
                            cwd=os.path.dirname(__file__), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
    assert result.returncode == 0, result.stderr
