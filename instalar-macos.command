#!/bin/bash
set -e
source "$(dirname -- "$0")/scripts/entorno.sh"

CON_GOOGLE=0
case "${1:-}" in
    --con-google) CON_GOOGLE=1 ;;
    -h|--help)
        echo 'Uso: ./instalar-macos.command [--con-google]'
        echo 'Crea .venv e instala dependencias; --con-google añade Gmail y Drive.'
        exit 0 ;;
    '') ;;
    *) echo "Opción desconocida: $1" >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
    echo 'Uso: ./instalar-macos.command [--con-google]' >&2
    exit 2
fi

seleccionar_python
if [ ! -d "$CHAMBA_RAIZ/.venv" ]; then
    "$CHAMBA_PYTHON" -m venv "$CHAMBA_RAIZ/.venv"
fi
CHAMBA_PYTHON="$CHAMBA_RAIZ/.venv/bin/python"
"$CHAMBA_PYTHON" -m pip install -r "$CHAMBA_RAIZ/requirements.txt"
if [ "$CON_GOOGLE" -eq 1 ]; then
    "$CHAMBA_PYTHON" -m pip install -r "$CHAMBA_RAIZ/requirements-opcional.txt"
fi
"$CHAMBA_PYTHON" -m pip check
comprobar_dependencias
echo
echo 'Instalación lista. Personaliza app/perfil.py y abre ./panel.command.'
