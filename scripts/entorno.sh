#!/bin/bash
# Compartido por los lanzadores .command; compatible con Bash 3.2 de macOS.
CHAMBA_RAIZ="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$CHAMBA_RAIZ" || exit 1

python_compatible() {
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1
}

seleccionar_python() {
    local candidato prefijo nombre
    if [ -d "$CHAMBA_RAIZ/.venv" ]; then
        CHAMBA_PYTHON="$CHAMBA_RAIZ/.venv/bin/python"
        if ! python_compatible "$CHAMBA_PYTHON"; then
            echo 'El .venv no funciona en este Mac o usa Python anterior a 3.12.' >&2
            echo 'Renombra .venv y vuelve a ejecutar ./instalar-macos.command.' >&2
            return 1
        fi
        return 0
    fi
    # PYTHON permite elegir una instalación concreta sin cambiar el PATH.
    if [ -n "${PYTHON:-}" ]; then
        if ! python_compatible "$PYTHON"; then
            echo 'PYTHON debe apuntar a un ejecutable de Python 3.12 o posterior.' >&2
            return 1
        fi
        CHAMBA_PYTHON="$PYTHON"
        return 0
    fi
    # Finder no siempre hereda el PATH de Terminal/Homebrew.
    for prefijo in '' /opt/homebrew/bin/ /usr/local/bin/ \
        /Library/Frameworks/Python.framework/Versions/Current/bin/; do
        for nombre in python3 python3.14 python3.13 python3.12; do
            candidato="$prefijo$nombre"
            if python_compatible "$candidato"; then
                CHAMBA_PYTHON="$candidato"
                return 0
            fi
        done
    done
    echo 'Necesitas Python 3.12 o posterior. Instálalo desde https://www.python.org/downloads/macos/.' >&2
    return 1
}

comprobar_dependencias() {
    if ! "$CHAMBA_PYTHON" -c 'import requests, urllib3, httpx, bs4, lxml.etree' >/dev/null 2>&1; then
        echo 'Faltan dependencias. Ejecuta primero ./instalar-macos.command.' >&2
        return 1
    fi
}
