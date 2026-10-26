"""Alta inicial del administrador sin guardar su contraseña en Compose."""
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def test_bootstrap_creates_admin_once():
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env['JB360_DB'] = tmp + '/general.sqlite3'
        env.pop('JB360_ADMIN_PASSWORD', None)
        password = 'Clave-bootstrap-privada-2026'
        command = [sys.executable, 'bootstrap.py']
        first = subprocess.run(command, cwd=Path(__file__).parent, env=env,
                               input=(password + '\n' + password + '\n').encode(),
                               capture_output=True, timeout=30)
        assert first.returncode == 0, first.stderr.decode()
        assert password.encode() not in first.stdout + first.stderr
        with sqlite3.connect(env['JB360_DB']) as db:
            assert db.execute('SELECT username,role FROM users').fetchall() == [('admin', 'admin')]
        second = subprocess.run(command, cwd=Path(__file__).parent, env=env,
                                input=b'', capture_output=True, timeout=30)
        assert second.returncode != 0
        with sqlite3.connect(env['JB360_DB']) as db:
            assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 1
