"""Inicia una instalación local sin guardar la clave de administración en archivos."""
import getpass
import os
import sqlite3
from pathlib import Path

import uvicorn


def database_has_users(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with sqlite3.connect(path) as db:
            return db.execute('SELECT EXISTS(SELECT 1 FROM users)').fetchone()[0] == 1
    except sqlite3.OperationalError as error:
        if 'no such table: users' in str(error):
            return False
        raise SystemExit('La base existente no se puede leer. Conserve el archivo y restaure una copia.') from error
    except sqlite3.Error as error:
        raise SystemExit('La base existente no se puede leer. Conserve el archivo y restaure una copia.') from error


def main():
    root = Path(__file__).resolve().parent
    data_dir = root / 'datos'
    data_dir.mkdir(mode=0o700, exist_ok=True)
    if os.name != 'nt':
        os.umask(0o077)
    db_path = Path(os.environ.setdefault('JB360_DB', str(data_dir / 'jb360.sqlite3')))
    if not database_has_users(db_path) and not os.environ.get('JB360_ADMIN_PASSWORD'):
        password = getpass.getpass('Crea tu clave de administrador (mínimo 14 caracteres): ')
        if len(password) < 14:
            raise SystemExit('Se requieren al menos 14 caracteres.')
        confirmation = getpass.getpass('Repite la clave: ')
        if password != confirmation:
            raise SystemExit('Las claves no coinciden.')
        os.environ['JB360_ADMIN_PASSWORD'] = password
    port = int(os.environ.get('JB360_PORT', '8000'))
    if not 1 <= port <= 65535:
        raise SystemExit('Puerto inválido.')
    host = os.environ.get('JB360_BIND', '127.0.0.1')
    if host != '127.0.0.1' and not os.environ.get('JB360_ALLOW_LAN'):
        raise SystemExit('Para escucha en red configure JB360_ALLOW_LAN=1 y una red privada o HTTPS.')
    if host != '127.0.0.1' and not os.environ.get('JB360_ALLOWED_HOSTS'):
        raise SystemExit('Configure JB360_ALLOWED_HOSTS con la IP o el dominio del servidor.')
    if host == '127.0.0.1':
        print(f'Abra http://127.0.0.1:{port}/ en este equipo. Pulse Ctrl+C para cerrar.')
    else:
        print(f'Servidor en {host}:{port}. Use HTTPS con certificado confiable para claves y datos reales.')
    cert = os.environ.get('JB360_TLS_CERT')
    key = os.environ.get('JB360_TLS_KEY')
    if bool(cert) != bool(key):
        raise SystemExit('Indique juntos JB360_TLS_CERT y JB360_TLS_KEY.')
    uvicorn.run('server:app', host=host, port=port, ssl_certfile=cert, ssl_keyfile=key)


if __name__ == '__main__':
    main()
