#!/bin/bash
set -e
source "$(dirname -- "$0")/scripts/entorno.sh"
seleccionar_python
comprobar_dependencias
exec "$CHAMBA_PYTHON" -X utf8 -u "$CHAMBA_RAIZ/app/servidor.py" --host 0.0.0.0 --agente-local "$@"
