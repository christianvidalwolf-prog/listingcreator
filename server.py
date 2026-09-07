#!/usr/bin/env python3
"""Servidor local con proxy multi-proveedor para evitar CORS y generar Títulos y Highlights de Amazon."""

import http.server
import json
import os
import re

PORT = int(os.environ.get("PORT", 8787))
DIR = os.path.dirname(os.path.abspath(__file__))

def load_env():
    env_file = os.path.join(DIR, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"\'')
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

load_env()

from api.generate import handler as GenerateHandler, read_payload
from urllib.parse import urlsplit


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path not in ("/", "/index.html", "/amazon-titulos.html", "/app.js"):
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path not in ("/", "/index.html", "/amazon-titulos.html", "/app.js"):
            self.send_error(404)
            return
        super().do_HEAD()

    def do_POST(self):
        if urlsplit("http://" + self.headers.get("Host", "")).hostname not in ("localhost", "127.0.0.1", "::1"):
            self._respond(403, {"error": "Host no permitido"})
            return
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host", ""):
            self._respond(403, {"error": "Origen no permitido"})
            return
        if self.path == "/api/generate":
            GenerateHandler.do_POST(self)
        elif self.path == "/api/save":
            try:
                payload = read_payload(self, 10 * 1024 * 1024)
            except ValueError as e:
                self._respond(400, {"error": str(e)})
                return
            csv_content = payload.get("content", "")
            filename = payload.get("filename", "titulos_amazon.csv")
            
            if not isinstance(csv_content, str) or not isinstance(filename, str) or not re.fullmatch(r"[\w .-]+\.csv", filename) or filename.startswith("."):
                self._respond(400, {"error": "Contenido o nombre CSV inválido"})
                return
            try:
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                if not os.path.exists(downloads_path):
                    os.makedirs(downloads_path)
                
                full_path = os.path.join(downloads_path, filename)
                with open(full_path, "x", encoding="utf-8-sig") as f:
                    f.write(csv_content)
                
                self._respond(200, {"message": f"Archivo guardado en: {full_path}"})
            except FileExistsError:
                self._respond(409, {"error": "Ya existe un archivo con ese nombre. Descarga el CSV desde el navegador."})
            except OSError:
                self._respond(500, {"error": "No se pudo guardar el archivo en Descargas"})
        else:
            self.send_response(404)
            self.end_headers()

    def _respond(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"✓ Servidor en http://localhost:{PORT}/amazon-titulos.html")
        httpd.serve_forever()
