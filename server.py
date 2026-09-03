#!/usr/bin/env python3
"""Servidor local con proxy multi-proveedor para evitar CORS."""

import base64
import http.server
import json
import urllib.request
import urllib.error
import os

PORT = 8787
DIR = os.path.dirname(os.path.abspath(__file__))

PROMPT_TEMPLATE = (
    "ACTÚA COMO UN EXPERTO EN SEO DE AMAZON. GENERA UN TÍTULO DE 200 CARACTERES (MÁXIMA LONGITUD).\n\n"
    "DATOS:\n"
    "- Producto: {name}\n"
    "- Medidas: {dims}\n\n"
    "ESTRUCTURA OBLIGATORIA (EXPANDE CADA BLOQUE):\n"
    "1. [PRODUCTO]: Nombre comercial completo y descriptivo.\n"
    "2. [MATERIAL]: Describe material (madera, metal, resina) y acabado (brillante, mate, rugoso).\n"
    "3. [COLOR]: Define el tono exacto (beige seda, gris antracita, dorado envejecido).\n"
    "4. [ESTILO]: Añade conceptos como 'Estilo Nórdico', 'Decoración Industrial' o 'Vintage Art'.\n"
    "5. [UBICACIÓN]: 'Ideal para decorar el salón, oficina, dormitorio o recibidor'.\n"
    "6. [CARACTERÍSTICA]: 'Resistente, elegante y de diseño exclusivo'.\n"
    "7. [MEDIDAS]: 'Dimensiones: {dims}'.\n"
    "8. [UNIDAD]: Solo si hay varios diseños en la foto: ' | 1 Unidad Surtida'.\n\n"
    "INSTRUCCIÓN FINAL: NO SEAS ESCUETO. RELLENA CON ADJETIVOS Y PALABRAS CLAVE HASTA ROZAR LAS 200 LETRAS. "
    "SI EL TÍTULO ES CORTO, ESTÁ MAL HECHO. RESPONDE SOLO CON EL TÍTULO EXTENSO."
)


def fetch_image_b64(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        data = resp.read()
        return mime, base64.b64encode(data).decode()


def call_anthropic(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "model": "claude-3-opus-20240229",
        "max_tokens": 200,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": image_url}},
                {"type": "text", "text": prompt}
            ]
        }]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["content"][0]["text"].strip()


def call_openai(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "model": "gpt-4o",
        "max_tokens": 200,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt}
            ]
        }]
    }).encode()
    url = "https://api.openai.com/v1/chat/completions"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(5) # Esperar 5 segundos antes de reintentar OpenAI
                continue
            raise e


import time

def call_gemini(api_key, image_url, name="", dims="", model="gemini-2.5-flash"):
    mime, b64 = fetch_image_b64(image_url)
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime, "data": b64}},
                {"text": prompt}
            ]
        }],
        "generationConfig": {"maxOutputTokens": 500}
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=body,
                                          headers={
                                              "Content-Type": "application/json",
                                              "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                                          },
                                          method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError as e:
            if e.code in [429, 503] and attempt < max_retries - 1:
                print(f"⚠️ Cuota excedida. Esperando 62s para reintentar (intento {attempt+1})...")
                time.sleep(62) # Esperar 62 segundos antes de reintentar
                continue
            raise e
        except Exception as e:
            raise e


def call_qwen(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "model": "qwen-3-vl-max",
        "input": {
            "messages": [{
                "role": "user",
                "content": [
                    {"image": image_url},
                    {"text": prompt}
                ]
            }]
        }
    }).encode()
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["output"]["choices"][0]["message"]["content"][0]["text"].strip()


def call_groq(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "max_tokens": 200,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }]
    }).encode()
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                print(f"⚠️ Cuota de Groq excedida. Esperando 62s (intento {attempt+1})...")
                time.sleep(62) # Esperar 62 segundos antes de reintentar Groq
                continue
            raise e


def call_kimi(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "model": "moonshot-v1-8k-vision-preview",
        "max_tokens": 300,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }]
    }).encode()
    req = urllib.request.Request(
        "https://api.moonshot.cn/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()


def call_deepseek(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    # DeepSeek a veces requiere que la imagen sea procesada de forma distinta o bajo otro campo
    body = json.dumps({
        "model": "deepseek-v3-vision",
        "max_tokens": 300,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "image": image_url} # Formato DeepSeek VL
            ]
        }]
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()


def call_huggingface(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    # Usamos Qwen2-VL, que es el estándar actual más compatible en HF
    model_id = "Qwen/Qwen2-VL-7B-Instruct" 
    body = json.dumps({
        "inputs": f"{prompt} [IMAGE]: {image_url}",
        "parameters": {"max_new_tokens": 200}
    }).encode()
    req = urllib.request.Request(
        f"https://router.huggingface.co/models/{model_id}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0"
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        # HF responde a veces con el texto crudo o con una lista de diccionarios
        if isinstance(data, list):
            res = data[0].get("generated_text", "")
        else:
            res = data.get("generated_text", "")
        return res.replace(prompt, "").strip()


PROVIDERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "gemini": call_gemini,
    "qwen": call_qwen,
    "groq": call_groq,
    "kimi": call_kimi,
    "deepseek": call_deepseek,
    "huggingface": call_huggingface,
}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_POST(self):
        if self.path == "/api/generate":
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            provider = payload.get("provider", "anthropic")
            api_key = payload.get("api_key", "")
            image_url = payload.get("image_url", "")

            fn = PROVIDERS.get(provider)
            if not fn:
                self._respond(400, {"error": f"Proveedor desconocido: {provider}"})
                return

            try:
                model = payload.get("model", "")
                name = payload.get("name", "")
                dims = payload.get("dimensions", "")
                
                # Preparamos los argumentos según el proveedor
                args = {"api_key": api_key, "image_url": image_url, "name": name, "dims": dims}
                if provider == "gemini" and model:
                    args["model"] = model
                
                title = fn(**args)
                self._respond(200, {"title": title})
            except urllib.error.HTTPError as e:
                err_body = e.read().decode(errors="replace")
                try:
                    msg = json.loads(err_body)
                    msg = (msg.get("error", {}) or {}).get("message") or err_body
                except Exception:
                    msg = err_body
                self._respond(e.code, {"error": msg})
            except Exception as e:
                self._respond(500, {"error": str(e)})
        elif self.path == "/api/save":
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            csv_content = payload.get("content", "")
            filename = payload.get("filename", "titulos_amazon.csv")
            
            try:
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                if not os.path.exists(downloads_path):
                    os.makedirs(downloads_path)
                
                full_path = os.path.join(downloads_path, filename)
                with open(full_path, "w", encoding="utf-8-sig") as f:
                    f.write(csv_content)
                
                self._respond(200, {"message": f"Archivo guardado en: {full_path}"})
            except Exception as e:
                self._respond(500, {"error": f"Error al guardar: {str(e)}"})
        else:
            self.send_response(404)
            self.end_headers()

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    with http.server.HTTPServer(("", PORT), Handler) as httpd:
        print(f"✓ Servidor en http://localhost:{PORT}/amazon-titulos.html")
        httpd.serve_forever()
