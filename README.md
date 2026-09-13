# ListingCreator Amazon

Aplicación para generar y editar fichas de producto a partir de imágenes y datos Excel/CSV. Incluye título, highlights, material, medidas, cinco bullets y descripción.

## Inicio local

Requiere Python 3.9 o posterior; el backend utiliza únicamente la biblioteca estándar.

```sh
python3 server.py
```

Abre http://localhost:8787/ para usar los catálogos Signes, DCasa, Minerales y Trediser. La interfaz alternativa sigue disponible en `/amazon-titulos.html`. Ambas utilizan `app.js` y la misma implementación de generación en `api/generate.py`.

El servidor escucha únicamente en el equipo local. Publica solo las páginas y `app.js`; no permite descargar `.env`, código Python ni archivos Git. Atiende solicitudes en hilos independientes para que una generación no bloquee la interfaz.

## Uso

Antes de «Procesar imágenes», el botón **Subir Excel y previsualizar** abre un listado independiente de referencias con su imagen al lado, una fila por producto. Utiliza la primera hoja de un Excel (XLSX, XLS o XLSM) o CSV: columna A = número de producto, columna B = URL HTTP(S) de imagen, con encabezado opcional «URL». Admite hasta 1000 productos y 10 MB; conserva el formato visible de las referencias, incluidos ceros iniciales. Las filas con URLs inválidas o imágenes que no cargan muestran un aviso. «Vaciar listado» limpia únicamente esta vista. No requiere clave de API, no consume IA y no modifica los datos ni los resultados de generación. La vista se pierde al recargar la página.

1. Selecciona proveedor e introduce tu clave. En local también puedes definirla en `.env`: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `QWEN_API_KEY`, `KIMI_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY` o `HF_TOKEN`.
2. Pega una URL HTTP(S) pública por línea, o importa un Excel/CSV con URL en la primera columna, nombre/contexto en la segunda y medidas en la tercera. Los catálogos comparten actualmente este formato.
3. Procesa el lote, edita las celdas y exporta Excel, CSV o copia la tabla. Los errores se excluyen de la exportación; «Reintentar errores» vuelve a solicitar únicamente las filas fallidas.

Las claves introducidas se conservan en `sessionStorage` durante la sesión de la pestaña, sin cifrado. Se eliminan las copias antiguas de `localStorage` al seleccionar el proveedor. Los resultados se mantienen en memoria: exporta antes de cerrar o recargar.

Límites: 1000 productos por lote, 10 MB por archivo importado, y 5 MB para las imágenes descargadas por el proxy (Claude/Gemini). Las imágenes deben devolver JPEG, PNG, WebP o GIF. Los proveedores que descargan la URL directamente aplican además sus propios límites.

Las medidas requieren una unidad explícita (`mm`, `cm` o `m`). `100x200 mm` produce `10x20 cm`; `100x200 cm` permanece igual. Sin unidad se devuelve `-`, evitando deducir una escala por el tamaño de los números. Se aceptan unidades mezcladas y se conservan los decimales.

## Criterios editoriales

Las fichas incluyen **Peso producto (g)**, editable, también disponible al generar productos de Signes. La IA solo debe extraer peso neto explícito del contexto o de una etiqueta legible; si no está disponible la celda queda sin dato. Se normalizan g/gr/gramos y kg a gramos. El Excel general, CSV y portapapeles incluyen el peso. En el XLSM de Amazon se escribe en los atributos técnicos `item_weight.value` y `item_weight.unit` (EC/ED en la plantilla limpia actual), con unidad `Gramos`. No se rellena el peso del paquete con el peso neto. La exportación conserva la fila de ejemplos y empieza los productos en la fila 7 indicada en los metadatos.

La generación adjunta la imagen de la URL al modelo y le pide identificar el objeto antes de escribir el título: tipo comercial, forma y detalles visibles, contrastados con el contexto del proveedor. Por ejemplo, debe distinguir un adorno de pared con forma de pez del animal representado. El nombre del archivo o un nombre genérico del catálogo no sustituyen la observación de la imagen.

El servidor exige una identificación visual estructurada en la respuesta. Si el modelo declara que no puede ver la imagen, no reconoce el producto o encuentra una contradicción clara entre foto y contexto, la fila muestra un error para corregirla y reintentar; no se acepta un título basado solo en texto. Esto comprueba lo declarado por el modelo, no certifica que su identificación sea correcta. Los materiales exactos requieren datos aportados o una etiqueta legible; no se deducen por apariencia. Se hace una solicitud de generación por producto y, si la respuesta está vacía, contiene JSON inválido o le faltan campos de la ficha, un único reintento automático con la misma imagen y datos. Este reintento puede consumir una solicitud adicional del proveedor. Los errores de identificación visual requieren revisar la fila. La clasificación de nodo sigue siendo independiente.

El perfil de generación usa 75 caracteres para título y 125 para Item Highlights. El [anuncio oficial actualizado de Amazon de junio de 2026](https://sellercentral.amazon.com/seller-forums/discussions/t/145b6d0f-999c-4555-896c-c694bda2e470) anuncia este formato desde el 27 de julio de 2026, salvo categorías de medios. Verifica la disponibilidad y reglas concretas en la plantilla de cada marketplace; la información histórica de 200 caracteres ya no debe presentarse como única referencia.

El prompt prioriza una keyword principal del tipo comercial y keywords secundarias pertinentes a su categoría. Incluye una medida principal confirmada en el título (o el conjunto de dimensiones si los ejes son ambiguos) y el material confirmado en título o highlights. No estima medidas por la foto ni composición por apariencia. Los highlights aportan información complementaria sin repetir el título. No hay consulta de volúmenes de búsqueda: la optimización es semántica, no una garantía de ranking. Las nuevas generaciones que exceden 75/125 se rechazan para reintentar, evitando recortar la medida o el material.

El sistema exige JSON con título, highlights, cinco bullets y descripción para aceptar una respuesta. Valida los límites de título/highlights; las longitudes solicitadas para bullets y descripción son instrucciones al modelo. No certifica hechos ni cumplimiento de Amazon: revisa materiales, medidas y afirmaciones antes de publicar. La falta de datos nunca debe suplirse inventando características.

## Proveedores y despliegue

Integraciones: Anthropic, OpenAI, Gemini, Qwen, Groq, Kimi, DeepSeek, OpenRouter y Hugging Face. Su disponibilidad depende de cuenta, región, cuota y modelos habilitados. No se han efectuado llamadas de pago durante la auditoría.

Puedes sobrescribir los modelos del servidor con `ANTHROPIC_MODEL`, `QWEN_MODEL`, `DEEPSEEK_MODEL` y `HUGGINGFACE_MODEL`. Hugging Face requiere un modelo visual servido por Inference Providers y un token con ese permiso. Gemini permite elegir modelo en la interfaz.

En Vercel, cada usuario debe aportar su clave por defecto. `ALLOW_SERVER_API_KEYS=1` habilita expresamente el uso de claves del servidor: solo debe utilizarse detrás de controles de acceso propios. No incluye autenticación de usuarios ni cuotas por usuario. `/api/save` no puede guardar archivos en el equipo del visitante y devuelve un error explicativo; utiliza las descargas del navegador.

El guardado local en `~/Downloads` admite solo nombres CSV y no sobrescribe archivos existentes. El navegador puede descargar archivos sin pasar por este endpoint.

La interfaz requiere conexión para cargar Tailwind y SheetJS desde sus CDN. No es una aplicación offline.

## Asignación automática de nodos Amazon.es

El catálogo incluido se ha importado de `NODOS FAMILIAS AMAZON.xls`, hoja `MAPPINGS`: **columna B = ID del nodo**, columna C = ruta. Contiene 16.777 nodos únicos (16.782 filas originales, cinco duplicadas). Los IDs se mantienen como texto, sin decimales. No se utilizan las columnas de otros países ni las notas de la hoja Instrucciones como órdenes para la IA.

Después de generar la ficha, la aplicación identifica el tipo de producto y busca candidatos en el catálogo completo mediante términos del producto, sinónimos y rutas de categorías. La búsqueda pondera más los nombres específicos de las categorías. La IA compara hasta 60 candidatos usando la imagen, los datos originales y la ficha. Si ninguno encaja, puede proponer sinónimos para una segunda búsqueda; no se envían las 16.777 categorías en cada solicitud.

El servidor verifica que el ID elegido exista entre los candidatos y recupera la ruta del catálogo, sin aceptar rutas inventadas por el modelo. El prompt completo está en `CLASSIFICATION_PROMPT`, en `api/_node_mapping.py`. Distingue tipo y finalidad de material, accesorios y forma; evita asignar Handmade o usos terapéuticos por apariencia.

La columna **Nodo Amazon.es** muestra ID, ruta, confianza y motivo:

- `asignado`: propuesta de IA con confianza alta.
- `revisar`: propuesta con confianza media, o sin ID si la evidencia es insuficiente. La confianza no es una probabilidad calibrada.
- `manual`: nodo elegido por el usuario entre resultados del catálogo.
- `pendiente` / `error`: falta recalcular o la consulta falló.

«Recalcular nodo» conserva la ficha y consulta solo la clasificación. En «Revisar o elegir otra categoría» puedes buscar por palabras o por ID exacto en todo el catálogo, sin consumir IA. Editar el contenido de la ficha vacía el nodo anterior hasta recalcularlo o elegir otro manualmente.

Excel, CSV, guardado local y portapapeles incluyen `nodo_amazon_es`, ruta, estado, confianza y motivo. Las fichas cuyo nodo esté pendiente se exportan con el ID vacío; las propuestas de confianza media se exportan con su ID y estado `revisar`.

Esta función añade normalmente una solicitud de IA por producto, y hasta dos si amplía la búsqueda, además de generar la ficha. Utiliza el proveedor y la clave seleccionados. Si falla la clasificación se conserva el texto generado. La validez de un ID respecto al Excel se comprueba; su encaje comercial sigue requiriendo revisión, y la aplicación no comprueba si Amazon ha actualizado el catálogo desde la fecha del archivo.

Para actualizar el catálogo, instala `xlrd` en un entorno de herramientas y ejecuta:

```sh
python3 scripts/import_nodes.py '/ruta/NODOS FAMILIAS AMAZON.xls'
```

Esto regenera `api/data/amazon_nodes.json` con el origen y su SHA-256. Reinicia el servidor para recargar el índice. No necesita Dropbox ni `xlrd` en ejecución normal; el archivo original no se modifica. `vercel.json` incluye el catálogo en la función Python; el módulo auxiliar usa prefijo `_` para no crear otro endpoint ([convención de Vercel](https://github.com/vercel/vercel/discussions/4983)). No se ha desplegado este cambio.

## Comprobaciones

```sh
python3 -m unittest discover -s tests -v
node --check app.js
```

Pruebas de navegador con Playwright (dependencia de desarrollo, no del backend): instala Playwright y Chromium en un entorno de pruebas, sirve este directorio en `127.0.0.1:8799` y ejecuta `node tests/browser.cjs`. La prueba simula las respuestas de IA y no consume créditos.

Detalles de la auditoría: [AUDIT.md](AUDIT.md).

### DeepSeek-V4.1-Flash (API directa)

En ambas pantallas, selecciona **DeepSeek-V4.1-Flash** y pega tu clave de DeepSeek en el campo API key. La integración envía texto e imagen a `https://api.deepseek.com/chat/completions` con el modelo `deepseek-flash`, identificador oficial de V4.1-Flash. También se utiliza al asignar nodos con este proveedor. En el servidor puedes usar `DEEPSEEK_API_KEY`; si has configurado `DEEPSEEK_MODEL`, elimina esa sobrescritura o establece `deepseek-flash` para utilizar este modelo. La clave introducida se conserva únicamente durante la sesión de la pestaña.

Referencia: https://www.deepseek.com/en/news/deepseek-v4-1-flash/
