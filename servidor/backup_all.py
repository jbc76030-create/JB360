"""Copia consistente de la base general y todas las bases cliente a stdout (ZIP)."""
import datetime
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path


def main():
    root_input = Path(os.environ.get('JB360_DB', '/data/jb360.sqlite3'))
    if root_input.is_symlink():
        raise SystemExit('Ruta de base general insegura')
    root = root_input.resolve()
    directory = root.parent / (root.stem + '-tenants')
    if not root.is_file() or root.is_symlink():
        raise SystemExit('Base general no disponible')
    paths = [(root, 'central.sqlite3')]
    if directory.is_dir():
        for path in sorted(directory.glob('*.sqlite3')):
            if path.is_symlink() or not path.is_file():
                raise SystemExit('Base cliente insegura: ' + path.name)
            paths.append((path, 'clientes/' + path.name))
    manifest = {'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'databases': []}
    with tempfile.TemporaryDirectory(prefix='jb360-copia-') as temp:
        snapshots = []
        for index,(source_path, archive_name) in enumerate(paths):
            copy_path = Path(temp) / (str(index) + '.sqlite3')
            with sqlite3.connect(f'file:{source_path}?mode=ro', uri=True) as source, sqlite3.connect(copy_path) as target:
                source.backup(target)
            with sqlite3.connect(copy_path) as copy:
                copy.execute('PRAGMA journal_mode=DELETE')
                copy.execute('DELETE FROM tokens')
                copy.execute('DELETE FROM login_failures')
                if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise SystemExit('Fallo de integridad en ' + archive_name)
            with copy_path.open('rb') as file:
                digest = hashlib.file_digest(file, 'sha256').hexdigest()
            manifest['databases'].append({'name': archive_name,
                                          'sha256': digest,
                                          'bytes': copy_path.stat().st_size})
            snapshots.append((copy_path, archive_name))
        with zipfile.ZipFile(sys.stdout.buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', json.dumps(manifest,ensure_ascii=False,indent=2))
            for path,name in snapshots:
                archive.write(path,name)


if __name__ == '__main__':
    main()
