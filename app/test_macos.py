"""Regresiones de portabilidad. No recolectan, abren navegadores ni envían correo.

    python app/test_macos.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

import navegador

RAIZ = Path(__file__).resolve().parent.parent


class NavegadorTests(unittest.TestCase):
    def test_macos_reutiliza_chrome_y_conserva_url(self):
        url = "https://example.com/empleo?q=seguridad&ciudad=San%20Pedro"
        with patch.object(navegador.sys, "platform", "darwin"), \
                patch.object(Path, "is_dir", return_value=True), \
                patch.object(navegador.subprocess, "run") as abrir, \
                patch.object(navegador.webbrowser, "open") as otro:
            self.assertEqual(navegador.abrir_en_chrome(url), "chrome")
            self.assertEqual(abrir.call_args.args[0],
                             ["/usr/bin/open", "-a", "/Applications/Google Chrome.app", url])
            otro.assert_not_called()

    def test_macos_busca_chrome_en_aplicaciones_del_usuario(self):
        with patch.object(navegador.sys, "platform", "darwin"), \
                patch.object(Path, "is_dir", side_effect=[False, True]), \
                patch.object(navegador.subprocess, "run") as abrir:
            self.assertEqual(navegador.abrir_en_chrome("https://example.com"), "chrome")
            self.assertEqual(abrir.call_args.args[0][2],
                             str(Path.home() / "Applications/Google Chrome.app"))

    def test_macos_launch_services_encuentra_ubicaciones_no_estandar(self):
        with patch.object(navegador.sys, "platform", "darwin"), \
                patch.object(Path, "is_dir", return_value=False), \
                patch.object(navegador.subprocess, "run") as abrir:
            self.assertEqual(navegador.abrir_en_chrome("https://example.com"), "chrome")
            self.assertEqual(abrir.call_args.args[0][2], "Google Chrome")

    def test_macos_sin_chrome_usa_navegador_predeterminado(self):
        with patch.object(navegador.sys, "platform", "darwin"), \
                patch.object(navegador.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "open")), \
                patch.object(navegador.webbrowser, "open", return_value=True):
            self.assertEqual(navegador.abrir_en_chrome("https://example.com"), "navegador por defecto")

    def test_fallo_de_ambos_navegadores_no_se_marca_como_exito(self):
        with patch.object(navegador.sys, "platform", "darwin"), \
                patch.object(navegador.subprocess, "run", side_effect=subprocess.TimeoutExpired("open", 15)), \
                patch.object(navegador.webbrowser, "open", return_value=False):
            self.assertEqual(navegador.abrir_en_chrome("https://example.com"), "no se pudo abrir")

    def test_windows_conserva_apertura_directa(self):
        with patch.object(navegador.sys, "platform", "win32"), \
                patch.object(Path, "is_file", return_value=True), \
                patch.object(navegador.subprocess, "Popen") as abrir:
            self.assertEqual(navegador.abrir_en_chrome("https://example.com"), "chrome")
            self.assertIn("chrome.exe", abrir.call_args.args[0][0])
            self.assertIn("creationflags", abrir.call_args.kwargs)


@unittest.skipIf(os.name == "nt", "Lanzadores POSIX y señales de macOS/Linux")
class LanzadoresTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="chamba macOS con espacios ")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        shutil.copytree(RAIZ / "app", self.raiz / "app",
                        ignore=shutil.ignore_patterns("datos", "__pycache__"))
        shutil.copytree(RAIZ / "scripts", self.raiz / "scripts")
        for nombre in ("panel.html", "movil.html", "panel.command", "ciclo-diario.command",
                       "agente-en-casa.command", "instalar-macos.command"):
            shutil.copy2(RAIZ / nombre, self.raiz / nombre)
        # Intérprete del entorno de pruebas: no se instala nada ni se usa la BD real.
        self.env = dict(os.environ, PYTHON=sys.executable)
        self.http = build_opener(ProxyHandler({}))

    def ejecutar(self, nombre, *args):
        return subprocess.run([str(self.raiz / nombre), *args], cwd="/",
                              env=self.env, capture_output=True, text=True, timeout=15)

    def test_lanzadores_desde_otra_carpeta_y_con_espacios(self):
        for nombre in ("panel.command", "ciclo-diario.command", "agente-en-casa.command",
                       "instalar-macos.command"):
            with self.subTest(nombre=nombre):
                r = self.ejecutar(nombre, "--help")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertTrue(r.stdout)

    def test_venv_del_proyecto_tiene_prioridad(self):
        binario = self.raiz / ".venv/bin/python"
        binario.parent.mkdir(parents=True)
        binario.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n')
        binario.chmod(0o755)
        self.env["PYTHON"] = "/python-que-no-existe"
        r = self.ejecutar("panel.command", "--help")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_venv_de_windows_no_se_usa_en_macos(self):
        (self.raiz / ".venv/Scripts").mkdir(parents=True)
        r = self.ejecutar("panel.command", "--help")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Renombra .venv", r.stderr)

    def iniciar(self, nombre, *args):
        log = (self.raiz / "servidor.log").open("w+")
        self.addCleanup(log.close)
        proceso = subprocess.Popen([str(self.raiz / nombre), *args], cwd="/",
                                   env=self.env, stdout=log, stderr=log,
                                   start_new_session=True)

        def limpiar():
            if proceso.poll() is None:
                proceso.terminate()
                try:
                    proceso.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(proceso.pid, signal.SIGKILL)
                    proceso.wait()
        self.addCleanup(limpiar)
        limite = time.monotonic() + 10
        while time.monotonic() < limite:
            texto = (self.raiz / "servidor.log").read_text()
            if "Ctrl+C para detener" in texto:
                return proceso, texto
            if proceso.poll() is not None:
                self.fail(texto)
            time.sleep(0.05)
        self.fail("El servidor no arrancó en 10 segundos")

    def test_panel_y_api_con_base_nueva(self):
        proceso, texto = self.iniciar("panel.command", "--sin-abrir", "--puerto", "0")
        base = re.search(r"Panel en (http://\S+)", texto).group(1).rstrip("/")
        for ruta in ("/", "/movil", "/vendor/react.production.min.js", "/api/vacantes",
                     "/api/facetas", "/api/cursos", "/api/cola", "/api/movil"):
            with self.subTest(ruta=ruta), self.http.open(base + ruta, timeout=5) as respuesta:
                self.assertEqual(respuesta.status, 200)
                datos = respuesta.read()
                if ruta.startswith("/api/"):
                    json.loads(datos)
        proceso.send_signal(signal.SIGINT)
        self.assertEqual(proceso.wait(timeout=8), 0)

    def agente_inerte(self, codigo="import time; time.sleep(60)\n"):
        # Sustituye al agente SOLO en la copia temporal: ninguna aprobación se ejecuta.
        (self.raiz / "app/agente_local.py").write_text(codigo)

    def test_red_exige_token_y_sighup_detiene_ambos_procesos(self):
        self.agente_inerte()
        proceso, texto = self.iniciar("agente-en-casa.command", "--puerto", "0")
        enlace = re.search(r"Vista móvil: (http://\S+)", texto).group(1)
        base, token = enlace.split("/movil?t=")
        self.assertTrue(token)
        with self.assertRaises(HTTPError) as error:
            self.http.open(base + "/api/vacantes", timeout=5)
        self.assertEqual(error.exception.code, 403)
        error.exception.close()
        with self.http.open(base + "/api/vacantes?t=" + token, timeout=5) as respuesta:
            self.assertEqual(respuesta.status, 200)
        pid_agente = int(re.search(r"Agente local iniciado \(PID (\d+)\)", texto).group(1))
        proceso.send_signal(signal.SIGHUP)
        self.assertEqual(proceso.wait(timeout=8), 0)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid_agente, 0)

    def test_puerto_ocupado_no_inicia_agente(self):
        self.agente_inerte("from pathlib import Path; Path('agente-arranco').touch()\n")
        with socket.socket() as ocupado:
            ocupado.bind(("127.0.0.1", 0))
            ocupado.listen()
            r = self.ejecutar("agente-en-casa.command", "--host", "127.0.0.1",
                              "--puerto", str(ocupado.getsockname()[1]))
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.raiz / "agente-arranco").exists())

    def test_salida_del_agente_detiene_el_panel(self):
        self.agente_inerte("raise SystemExit(7)\n")
        r = self.ejecutar("agente-en-casa.command", "--host", "127.0.0.1", "--puerto", "0")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("código 7", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
