"""Inicio local del servidor de evaluación, restringido al propio equipo."""
import getpass
import os
from pathlib import Path

import uvicorn


root = Path(__file__).resolve().parent
data_dir = root / 'datos'
data_dir.mkdir(exist_ok=True)
os.environ.setdefault('JB360_DB', str(data_dir / 'jb360.sqlite3'))
if not os.environ.get('JB360_ADMIN_PASSWORD'):
    password = getpass.getpass('Contraseña del administrador (mínimo 14 caracteres): ')
    if len(password) < 14:
        raise SystemExit('Se requieren al menos 14 caracteres.')
    os.environ['JB360_ADMIN_PASSWORD'] = password
print('Abra http://127.0.0.1:8000/ en este equipo. Pulse Ctrl+C para cerrar.')
uvicorn.run('server:app', host='127.0.0.1', port=8000)
