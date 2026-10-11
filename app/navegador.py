"""Apertura de Chrome con la sesión habitual del usuario en cada sistema."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import webbrowser


def abrir_en_chrome(url: str) -> str:
    """Prefiere Chrome; si no está disponible, intenta el navegador por defecto."""
    if sys.platform == "darwin":
        # Launch Services reutiliza la aplicación/sesión abierta. También
        # encuentra instalaciones fuera de /Applications por su nombre.
        aplicaciones = (Path("/Applications/Google Chrome.app"),
                        Path.home() / "Applications/Google Chrome.app")
        aplicacion = next((str(p) for p in aplicaciones if p.is_dir()),
                          "Google Chrome")
        try:
            subprocess.run(["/usr/bin/open", "-a", aplicacion, url],
                           check=True, capture_output=True, timeout=15)
            return "chrome"
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        if sys.platform == "win32":
            rutas = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]
        else:
            rutas = [shutil.which(nombre) for nombre in
                     ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
        for ruta in rutas:
            if ruta and Path(ruta).is_file():
                try:
                    opciones = ({"creationflags": getattr(subprocess, "DETACHED_PROCESS", 0)}
                                if sys.platform == "win32" else {"start_new_session": True})
                    subprocess.Popen([ruta, url], **opciones)
                    return "chrome"
                except OSError:
                    continue
    try:
        if webbrowser.open(url):
            return "navegador por defecto"
    except (OSError, webbrowser.Error):
        pass
    return "no se pudo abrir"
