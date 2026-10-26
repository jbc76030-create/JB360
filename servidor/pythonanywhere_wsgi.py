"""WSGI entry point for a PythonAnywhere web app.

Set JB360_DB and JB360_ALLOWED_HOSTS in PythonAnywhere's WSGI config before
importing this module. Run bootstrap.py once in a private Bash console first.
"""
import os
from pathlib import Path

from a2wsgi import ASGIMiddleware


db = os.environ.get('JB360_DB', '')
hosts = os.environ.get('JB360_ALLOWED_HOSTS', '')
if not db or not Path(db).is_absolute() or not hosts:
    raise RuntimeError('Configure JB360_DB (ruta absoluta) y JB360_ALLOWED_HOSTS antes de cargar la web')

from server import app, start  # noqa: E402

# a2wsgi converts requests, but does not run ASGI lifespan events. Initialize
# the DB at process startup, as Uvicorn does in the existing deployment.
start()
application = ASGIMiddleware(app)
