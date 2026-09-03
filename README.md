# ListingCreator (Generador de Títulos SEO para Amazon)

Herramienta web local que analiza imágenes de productos (vía scraping o URLs) y genera títulos optimizados para Amazon (hasta 200 caracteres) aplicando algoritmos de posicionamiento SEO y visión artificial multi-proveedor.

## 🚀 Características

- **Servidor Proxy Local (`server.py`)**: Descarga imágenes directamente para saltarse restricciones de CORS de los proveedores y reenviarlas codificadas en base64 a las APIs de visión.
- **Frontend Interactivo (`amazon-titulos.html`)**:
  - Carga masiva de productos vía Excel / CSV (`.xlsx`, `.xls`, `.csv`).
  - Extracción visual por URL de imagen.
  - Edición y previsualización en tiempo real con contador de caracteres.
  - Exportación directa a CSV y Excel listo para subir a Amazon Seller Central.
- **Soporte Multi-Proveedor de IA**:
  - **Anthropic** (Claude 3 Opus / Sonnet)
  - **OpenAI** (GPT-4o)
  - **Google AI Studio** (Gemini 2.5 Flash / Pro)
  - **Groq** (Llama Vision)
  - **DeepSeek**
  - **Qwen** (Alibaba Cloud DashScope)
  - **Kimi / Moonshot AI**
  - **Hugging Face**

## 📋 Requisitos

- Python 3.8 o superior
- Navegador web moderno

## ⚙️ Puesta en marcha

1. **Clonar o descargar el repositorio**:
   ```bash
   git clone https://github.com/christianvidalwolf-prog/listingcreator.git
   cd listingcreator
   ```

2. **Iniciar el servidor local**:
   ```bash
   python3 server.py
   ```

3. **Abrir en el navegador**:
   Visita `http://localhost:8787/amazon-titulos.html`.

4. **Configuración de API Key**:
   Introduce tu API Key en la interfaz según el proveedor que vayas a utilizar. Se almacenará localmente en tu navegador (`localStorage`).
