#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Ejecute primero INSTALAR_MAC_LINUX.sh."
  exit 1
fi
.venv/bin/python iniciar.py
