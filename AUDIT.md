# Auditoría del 5 de septiembre de 2026

Se revisaron todas las fuentes de la aplicación: ambas páginas, backend local, endpoints serverless, configuración de despliegue y documentación. Los cambios previos sin confirmar se incorporaron como punto de partida, preservando catálogos, campos ampliados y OpenRouter.

## Correcciones

- Eliminada la duplicación de JavaScript y generación Python. Las dos interfaces comparten campos, importación, edición y exportación; el servidor local reutiliza el endpoint de generación.
- Corregida la restauración de filas al cambiar de catálogo. URLs, importaciones pendientes y resultados se conservan por catálogo durante la sesión.
- Bloqueado el cambio de proveedor, modelo, archivo y catálogo durante el procesamiento. Liberación de controles con `finally` y tiempo máximo de espera en navegador.
- Reintento selectivo de errores, sin repetir solicitudes de filas correctas. Los errores no se exportan como títulos y el progreso diferencia éxitos y fallos.
- Corregida la conversión de medidas en Python y JavaScript: unidades al final, unidades mezcladas, decimales y dimensiones grandes. Sin unidad no se presupone una escala.
- Corregida la prioridad de cuero sintético frente a cuero y la extracción de referencias de URLs con parámetros.
- Corregida la miniatura de sustitución: las comillas del SVG rompían el antiguo manejador inline. Carga diferida de imágenes y manejador de error de un solo uso.
- Exportaciones con cinco columnas de bullets siempre, material y medidas en ambas páginas. Neutralización de fórmulas en CSV/TSV y eliminación de saltos/tabulaciones que desplazarían las celdas TSV.
- Validación de importaciones, límite de archivo/lote y eliminación de importaciones antiguas al introducir URLs nuevas. Mensajes si falla el lector Excel o el portapapeles.
- Validación de JSON, tipos, proveedor, modelo y tamaño de solicitud. Respuestas inválidas o incompletas de IA se rechazan en lugar de exportar fragmentos como fichas correctas.
- Aumentado presupuesto de salida de 350/800 a 2048 tokens para permitir fichas completas. Gemini Pro recibe presupuesto de pensamiento positivo; se concatenan partes de texto omitiendo pensamientos y la clave se envía en cabecera.
- Actualizados Claude retirado, identificador Qwen, modelo/formato visual DeepSeek y endpoint multimodal Hugging Face.
- Servidor limitado a loopback, comprobación de Host/Origin en escrituras y lista explícita de archivos públicos. Descargas de imágenes con validación DNS, conexión fijada a IP pública, validación de redirecciones y límite de tamaño/tipo.
- Guardado local con nombre CSV validado, sin traversal ni sobrescritura. El endpoint serverless ya no anuncia éxito sin guardar.
- Eliminado CORS abierto y uso automático de claves del servidor en Vercel; claves del navegador limitadas a sesión. `.vercelignore` excluye archivos locales y secretos del despliegue.
- Corregida la presentación de 75/125 como política universal de Amazon: son criterios editoriales de la aplicación.

## Validación y límites

La suite Python prueba HTTP real en loopback con proveedores simulados: JSON inválido, generación, privacidad de archivos, guardado, URLs privadas, conversión de medidas y solicitudes Gemini. Playwright comprueba ambas páginas con IA simulada: generación, errores, reintento selectivo, edición, restauración de catálogos, importación y exportación Excel.

No se desplegó ni se consumieron créditos de proveedores. Quedan pendientes las pruebas con cada cuenta real y datos representativos para medir calidad, coste y latencia. La aplicación no garantiza que la IA identifique correctamente materiales ni que una ficha cumpla las reglas de una categoría concreta. Los resultados no persisten tras recargar. Tailwind/SheetJS siguen dependiendo de CDN; no se añadió autenticación de usuarios ni cuotas para un servicio público.

## Documentación contrastada

- [Amazon: requisitos de títulos](https://sellercentral.amazon.com/seller-forums/discussions/t/533f9cf7-3b5e-4974-b523-02e4a1a42c5f).
- [Anthropic: retirada de modelos](https://platform.claude.com/docs/en/about-claude/model-deprecations).
- [Gemini: presupuesto de pensamiento](https://ai.google.dev/gemini-api/docs/generate-content/thinking).
- [DeepSeek: entrada visual](https://api-docs.deepseek.com/guides/vision/).
- [Hugging Face: Chat Completion multimodal](https://huggingface.co/docs/inference-providers/tasks/chat-completion).
- [Alibaba: Qwen3-VL Plus](https://docs.modelstudio.console.alibabacloud.com/en/model-studio/qwen3-vl-plus).
