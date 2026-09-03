from http.server import BaseHTTPRequestHandler
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request

PROMPT_TEMPLATE = (
    "ACTÚA COMO UN EXPERTO EN SEO DE AMAZON. GENERA EL TÍTULO, 5 BULLET POINTS Y LA DESCRIPCIÓN "
    "SIGUIENDO ESTRICTAMENTE LA NUEVA NORMATIVA OFICIAL DE AMAZON 2026.\n\n"
    "DATOS DEL PRODUCTO:\n"
    "- Producto / Contexto: {name}\n"
    "- Medidas: {dims}\n\n"
    "DIRECTRICES OBLIGATORIAS:\n"
    "1. TÍTULO (title): MÁXIMO 75 CARACTERES (espacios incluidos).\n"
    "   - Estructura: [Tipo de producto comercial] + [Material/Color principal] + [Variante clave o modelo].\n"
    "   - Prohibido: relleno de keywords, frases de marketing ('calidad garantizada', 'oferta'), emojis o símbolos (™, ®).\n"
    "2. HIGHLIGHTS (highlights): MÁXIMO 125 CARACTERES (espacios incluidos).\n"
    "   - Frases cortas separadas por comas, sin promesas ni símbolos especiales.\n"
    "3. BULLET POINTS (bullet_points): EXACTAMENTE 5 puntos, cada uno entre 100 y 200 caracteres.\n"
    "   - Cada punto empieza por una característica y explica su beneficio. Información única y verificable.\n"
    "   - Sin precios, envíos, contacto, garantías, opiniones, mayúsculas integrales, emojis ni afirmaciones médicas.\n"
    "4. DESCRIPCIÓN (description): 500-1000 caracteres, clara y natural, basada solo en los datos disponibles.\n"
    "   - Sin HTML, precio, promociones, contacto, garantías absolutas ni información no confirmada.\n\n"
    "RESPONDE ÚNICAMENTE CON UN OBJETO JSON VÁLIDO CON ESTE FORMATO EXACTO (sin texto adicional ni markdown):\n"
    '{{"title": "...", "highlights": "...", "bullet_points": ["...", "...", "...", "...", "..."], "description": "..."}}'
)


def parse_ai_response(raw_text):
    """Extrae y normaliza title y highlights asegurando cumplimiento de límites de Amazon 2026."""
    title = ""
    highlights = ""
    bullet_points = []
    description = ""

    if not raw_text or not isinstance(raw_text, str):
        return {"title": "", "highlights": "", "bullet_points": [], "description": ""}

    text = raw_text.strip()

    # 1. Extraer bloque JSON directo o embebido
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            title = str(data.get("title") or data.get("titulo") or "").strip()
            highlights = str(data.get("highlights") or data.get("puntos_destacados") or data.get("destacados") or "").strip()
            bullet_points = data.get("bullet_points") or data.get("bullets") or data.get("puntos") or []
            if isinstance(bullet_points, str): bullet_points = [p.strip() for p in re.split(r"\n|\|", bullet_points) if p.strip()]
            bullet_points = [str(p).strip() for p in bullet_points[:5]]
            description = str(data.get("description") or data.get("descripcion") or "").strip()
        except Exception:
            pass

    # 2. Fallback con regex si no se obtuvo JSON válido
    if not title:
        t_match = re.search(r'(?:title|título|titulo)\s*[:=]\s*["\']?([^"\n\r]+)', text, re.IGNORECASE)
        if t_match:
            title = t_match.group(1).strip().strip('"\'')
    if not highlights:
        h_match = re.search(r'(?:highlights|destacados|puntos destacados)\s*[:=]\s*["\']?([^"\n\r]+)', text, re.IGNORECASE)
        if h_match:
            highlights = h_match.group(1).strip().strip('"\'')

    # 3. Fallback por líneas si aún está vacío
    if not title and not highlights:
        lines = [line.strip().strip('"\'') for line in text.split("\n") if line.strip() and not line.startswith(("{", "}", "```"))]
        if len(lines) >= 1:
            title = lines[0]
        if len(lines) >= 2:
            highlights = lines[1]

    # Limpieza de comillas circundantes o prefijos residuales
    title = re.sub(r'^(?:t[íi]tulo|title)\s*[:\-]\s*', '', title, flags=re.IGNORECASE).strip(' "\'')
    highlights = re.sub(r'^(?:highlights|destacados)\s*[:\-]\s*', '', highlights, flags=re.IGNORECASE).strip(' "\'')

    # Aplicar límites máximos de Amazon (75 y 125 caracteres)
    if len(title) > 75:
        truncated = title[:75]
        last_space = truncated.rfind(' ')
        if last_space > 40:
            title = truncated[:last_space].rstrip(',.- ')
        else:
            title = truncated.rstrip(',.- ')

    if len(highlights) > 125:
        truncated = highlights[:125]
        last_comma = truncated.rfind(',')
        last_space = truncated.rfind(' ')
        if last_comma > 80:
            highlights = truncated[:last_comma].rstrip(',.- ')
        elif last_space > 80:
            highlights = truncated[:last_space].rstrip(',.- ')
        else:
            highlights = truncated.rstrip(',.- ')

    return {
        "title": title,
        "highlights": highlights,
        "bullet_points": bullet_points,
        "description": description
    }


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
        "max_tokens": 350,
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
            "User-Agent": "Mozilla/5.0"
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
        "max_tokens": 350,
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
                time.sleep(5)
                continue
            raise e


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
        "generationConfig": {
            "maxOutputTokens": 2048,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        }
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError as e:
            if e.code in [429, 503] and attempt < max_retries - 1:
                time.sleep(8)
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
            "User-Agent": "Mozilla/5.0"
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
        "max_tokens": 350,
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
                    "User-Agent": "Mozilla/5.0"
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(10)
                continue
            raise e


def call_kimi(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "model": "moonshot-v1-8k-vision-preview",
        "max_tokens": 350,
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
            "User-Agent": "Mozilla/5.0"
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()


def call_deepseek(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "model": "deepseek-v3-vision",
        "max_tokens": 350,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "image": image_url}
            ]
        }]
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
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
        return data["choices"][0]["message"]["content"].strip()


def call_openrouter(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    body = json.dumps({
        "model": "deepseek/deepseek-v4-flash-vision-exp",
        "max_tokens": 800,
        "reasoning": {"effort": "none"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }]
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://listingcreator.local",
            "X-Title": "ListingCreator Amazon",
            "User-Agent": "Mozilla/5.0"
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str) or not content.strip():
            reason = (message.get("refusal")
                      or data.get("error", {}).get("message")
                      or f"finalización: {data.get('choices', [{}])[0].get('finish_reason', 'desconocida')}")
            raise ValueError(reason or "OpenRouter no devolvió contenido de texto")
        return content.strip()


def call_huggingface(api_key, image_url, name="", dims=""):
    prompt = PROMPT_TEMPLATE.format(name=name, dims=dims)
    model_id = "Qwen/Qwen2-VL-7B-Instruct" 
    body = json.dumps({
        "inputs": f"{prompt} [IMAGE]: {image_url}",
        "parameters": {"max_new_tokens": 350}
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
    "openrouter": call_openrouter,
    "huggingface": call_huggingface,
}


def get_api_key(provider, client_key):
    if client_key and str(client_key).strip():
        return str(client_key).strip()
    env_map = {
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "qwen": ["QWEN_API_KEY", "DASHSCOPE_API_KEY"],
        "kimi": ["KIMI_API_KEY", "MOONSHOT_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "huggingface": ["HUGGINGFACE_API_KEY", "HF_TOKEN"],
    }
    for env_var in env_map.get(provider, []):
        val = os.environ.get(env_var, "").strip()
        if val:
            return val
    return ""


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length))
        provider = payload.get("provider", "gemini")
        client_key = payload.get("api_key", "")
        image_url = payload.get("image_url", "")

        api_key = get_api_key(provider, client_key)
        if not api_key:
            self._respond(400, {
                "error": f"Falta la clave de API para {provider}. Introduce tu clave en la interfaz o configúrala en el servidor."
            })
            return

        fn = PROVIDERS.get(provider)
        if not fn:
            self._respond(400, {"error": f"Proveedor desconocido: {provider}"})
            return

        try:
            model = payload.get("model", "")
            name = payload.get("name", "")
            dims = payload.get("dimensions", "")
            
            args = {"api_key": api_key, "image_url": image_url, "name": name, "dims": dims}
            if provider == "gemini" and model:
                args["model"] = model
            
            raw_response = fn(**args)
            parsed = parse_ai_response(raw_response)
            self._respond(200, parsed)
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
