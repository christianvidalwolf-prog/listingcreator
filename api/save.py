from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # En entornos serverless como Vercel, no hay acceso al sistema de archivos local del cliente.
        # Las descargas se gestionan de forma nativa en el navegador mediante los botones 'Descargar Excel' y 'Descargar CSV'.
        self._respond(200, {
            "message": "En la versión web de Vercel, utiliza los botones 'Descargar Excel (.xlsx)' o 'Descargar CSV' para guardar el archivo directamente en tu equipo."
        })

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _respond(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass
