# Notas técnicas

## IA, multimedia y dependencias

El servicio no requiere dependencias de Python externas. La IA utiliza `codex exec`, con la sesión existente de ChatGPT, salida estructurada y herramientas de shell, aplicaciones y agentes deshabilitadas. El proceso de generación tiene acceso de solo lectura; la escritura la realiza el servicio después de la revisión del usuario.

La ampliación multimedia utiliza Poppler, FFmpeg y `yt-dlp`. Whisper se ejecuta en un entorno separado del servicio: `media-venv/` en la carpeta de datos (`anaco-ob install-media`) o `.media-venv/` en el repositorio (`scripts/install-media.sh`), que tiene preferencia. Ambos fijan Faster Whisper 1.2.1 y PyAV 16.1.0 por compatibilidad con su API de decodificación. El audio no se envía a una API de transcripción.

La recuperación inicial busca en archivos locales y lee fragmentos relevantes. No se mantiene un índice semántico ni se envía el vault completo al proveedor. Se ha elegido una extensión pequeña propia para integrar la cola local y la revisión explícita de relaciones; las plantillas e interpretación de Obsidian Web Clipper sirvieron de referencia, sin crear un fork que hubiera que mantener.

La vista previa utiliza Marked y DOMPurify empaquetados en `extension/vendor/`, con sus licencias. No carga scripts de una CDN. Para regenerar esas copias en desarrollo: `npm ci` y `npm run vendor`. No hace falta npm para cargar la extensión entregada.

## Identidad y compatibilidad

- Proyecto y repositorio: `anaco-ob`. Nombre visible: **Anaco**.
- Paquete: `dist/anaco-ob-<versión>.zip`. Servicio: `org.samuh.anaco_ob`.
- Datos locales: `~/.local/share/anaco-ob/`. El instalador conserva un alias de la ubicación anterior para las rutas de trabajos pendientes y registra el servicio anterior como alias si ya estaba instalado.
- Identificador de la extensión: `anaco-ob@samuhlo` desde la versión publicable. Las instalaciones anteriores usaban `second-brain-capture@samuh.local`: tras actualizar hay que volver a ejecutar el instalador para que el servicio acepte el nuevo identificador. El nombre se aplica a títulos, menús y listados de extensiones.

## Instalación del servicio

El paquete `anaco-ob` (`pyproject.toml`) incluye los módulos de `native/` y el contrato editorial. La orden `anaco-ob` instala, comprueba (`doctor`), desinstala y arranca el servicio. `native/installer.py` es la única implementación del registro de Native Messaging:

| SISTEMA | DATOS DEL SERVICIO | REGISTRO |
| :--- | :--- | :--- |
| **Linux** | `$XDG_DATA_HOME/anaco-ob` o `~/.local/share/anaco-ob` | `~/.mozilla/native-messaging-hosts/` y `~/.config/zen/native-messaging-hosts/` |
| **macOS** | `~/Library/Application Support/anaco-ob` | `~/Library/Application Support/Mozilla/NativeMessagingHosts/` y `…/zen/NativeMessagingHosts/` |
| **Windows** | `%APPDATA%\anaco-ob` | `HKCU\Software\Mozilla\NativeMessagingHosts\org.samuh.anaco_ob` y lanzador `.bat` |

La CI instala el paquete con `pipx` en los tres sistemas y comprueba el servicio con un mensaje real de Native Messaging (`scripts/smoke_native_host.py`).
