# Notas técnicas

## IA, multimedia y dependencias

El servicio no requiere dependencias de Python externas. La IA utiliza `codex exec`, con la sesión existente de ChatGPT, salida estructurada y herramientas de shell, aplicaciones y agentes deshabilitadas. El proceso de generación tiene acceso de solo lectura; la escritura la realiza el servicio después de la revisión del usuario.

La ampliación multimedia utiliza Poppler, FFmpeg y `yt-dlp`. Whisper se ejecuta en `.media-venv/`, separado del servicio. `scripts/install-media.sh` fija Faster Whisper 1.2.1 y PyAV 16.1.0 por compatibilidad con su API de decodificación. El audio no se envía a una API de transcripción.

La recuperación inicial busca en archivos locales y lee fragmentos relevantes. No se mantiene un índice semántico ni se envía el vault completo al proveedor. Se ha elegido una extensión pequeña propia para integrar la cola local y la revisión explícita de relaciones; las plantillas e interpretación de Obsidian Web Clipper sirvieron de referencia, sin crear un fork que hubiera que mantener.

La vista previa utiliza Marked y DOMPurify empaquetados en `extension/vendor/`, con sus licencias. No carga scripts de una CDN. Para regenerar esas copias en desarrollo: `npm ci` y `npm run vendor`. No hace falta npm para cargar la extensión entregada.

## Identidad y compatibilidad

- Proyecto y repositorio: `anaco-ob`. Nombre visible: **Anaco**.
- Paquete: `dist/anaco-ob-<versión>.zip`. Servicio: `org.samuh.anaco_ob`.
- Datos locales: `~/.local/share/anaco-ob/`. El instalador conserva un alias de la ubicación anterior para las rutas de trabajos pendientes y registra el servicio anterior como alias si ya estaba instalado.
- El identificador interno de Firefox se mantiene estable para conservar las preferencias y ediciones de las instalaciones existentes. El nuevo nombre se aplica a títulos, menús y listados de extensiones.
