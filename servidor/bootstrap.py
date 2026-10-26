"""Crea la cuenta general una sola vez, sin guardar su clave en Compose."""
import getpass
import os
import sqlite3
from pathlib import Path


def main():
    path = Path(os.environ.get('JB360_DB', '/data/jb360.sqlite3'))
    if path.exists():
        with sqlite3.connect(path) as db:
            try:
                if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                    raise SystemExit('Ya existe un administrador. No se reemplazó ninguna cuenta.')
            except sqlite3.OperationalError as error:
                if 'no such table: users' not in str(error):
                    raise
    first = getpass.getpass('Crea la clave del administrador general (mínimo 14 caracteres): ')
    second = getpass.getpass('Repítela: ')
    if len(first) < 14 or first != second:
        raise SystemExit('Las claves deben coincidir y tener al menos 14 caracteres.')
    os.environ['JB360_ADMIN_PASSWORD'] = first
    import server
    server.ADMIN_PASSWORD = first
    server.start()
    os.environ.pop('JB360_ADMIN_PASSWORD', None)
    print('Administrador creado. Arranque los servicios y use el usuario admin sin código de cliente.')


if __name__ == '__main__':
    main()
