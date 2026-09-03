# ListingCreator (Generador de Títulos y Highlights SEO para Amazon)

Herramienta web local que analiza imágenes de productos (mediante URLs o archivos Excel/CSV masivos) y genera títulos optimizados y puntos destacados (*Item Highlights*) siguiendo estrictamente la **Nueva Normativa Oficial de Amazon 2026**.

---

## 📌 Normativa Amazon 2026 Soportada

Amazon ha reestructurado la creación de fichas para optimizar la indexación móvil y los motores de búsqueda IA (*Amazon Rufus / A10 / COSMO*):

1. **Título del Producto (`title`)**:
   - **Límite estricto:** Máximo **75 caracteres** (espacios incluidos).
   - **Estructura oficial:** `[Tipo de producto comercial] + [Material/Color principal] + [Variante clave o modelo]`.
   - **Prohibiciones:** Sin relleno de palabras clave (*keyword stuffing*), sin frases promocionales (*"100% garantizado"*, *"mejor calidad"*), sin emojis ni caracteres de marca registrada (`™`, `®`).

2. **Item Highlights (`highlights`)**:
   - **Límite:** Máximo **125 caracteres** (espacios incluidos).
   - **Ubicación:** Aparece inmediatamente debajo del título en app móvil y escritorio con alto peso SEO.
   - **Formato:** Frases breves **separadas por comas** destacando materiales, especificaciones técnicas, medidas y uso principal.

> **Sinergia:** **75 car.** (Título) + **125 car.** (Highlights) = **200 caracteres** perfectamente distribuidos.

---

## 🚀 Características del Sistema

- **Backend Proxy Inteligente (`server.py`)**:
  - Evita bloqueos de CORS descargando las imágenes y sirviéndolas en base64 a los proveedores de visión artificial.
  - Parser robusto con tolerancia a fallos: extrae tanto JSON nativo como texto libre y recorta de forma inteligente respetando palabras completas si el modelo excede los límites (75 y 125 caracteres).
  - Endpoint `/api/generate` para generación en tiempo real.
  - Endpoint `/api/save` para guardar directamente en la carpeta `~/Downloads`.
- **Frontend Interactivo (`amazon-titulos.html`)**:
  - Ingesta masiva por Excel / CSV (`.xlsx`, `.xls`, `.csv`) o pegado de URLs.
  - Previsualización visual de miniaturas con enlace a la imagen original.
  - Columnas independientes para **Título (75 car.)** e **Item Highlights (125 car.)**.
  - **Edición in-situ (*contenteditable*)**: Modifica cualquier texto directamente en la tabla antes de exportar.
  - **Contadores dinámicos de caracteres** con código de color (verde óptimo, naranja aviso, rojo excedido).
  - **Múltiples opciones de exportación**:
    - 📊 **Excel (.xlsx)** con formato y anchos de columna preconfigurados.
    - 📄 **CSV (.csv)** con codificación UTF-8 con BOM (compatible con Excel en español).
    - 💾 **Guardar en ~/Downloads** directamente a través del backend local.
    - 📋 **Copiar tabla al portapapeles (TSV)** para pegar con un solo clic en Google Sheets o Excel.
- **Soporte Multi-Proveedor de IA**:
  - **Anthropic** (Claude 3 Opus / Sonnet)
  - **OpenAI** (GPT-4o)
  - **Google AI Studio** (Gemini 2.5 Flash / Pro)
  - **Groq** (Llama 3.2 Vision / Scout)
  - **Alibaba Cloud** (Qwen-3-VL)
  - **Moonshot AI** (Kimi Vision)
  - **DeepSeek** (DeepSeek Vision)
  - **Hugging Face** (Modelos Open Source)

---

## ⚙️ Puesta en marcha

1. **Iniciar el servidor local**:
   ```bash
   python3 server.py
   ```

2. **Abrir la interfaz**:
   Accede en tu navegador a:
   [http://localhost:8787/amazon-titulos.html](http://localhost:8787/amazon-titulos.html)

3. **Configurar tu API Key**:
   Introduce tu clave del proveedor preferido en la barra superior. Se guarda localmente y de forma segura en `localStorage` de tu navegador.
