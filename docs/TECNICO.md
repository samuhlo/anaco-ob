# Notas técnicas

## IA, multimedia y dependencias

El servicio no requiere dependencias de Python externas. La IA utiliza `codex exec`, con la sesión existente de ChatGPT, salida estructurada y herramientas de shell, aplicaciones y agentes deshabilitadas. El proceso de generación tiene acceso de solo lectura; la escritura la realiza el servicio después de la revisión del usuario.

La ampliación multimedia utiliza Poppler, FFmpeg y `yt-dlp`. Whisper se ejecuta en un entorno separado del servicio: `media-venv/` en la carpeta de datos (`anaco-ob install-media`) o `.media-venv/` en el repositorio (`scripts/install-media.sh`), que tiene preferencia. Ambos fijan Faster Whisper 1.2.1 y PyAV 16.1.0 por compatibilidad con su API de decodificación. El audio no se envía a una API de transcripción.

Una transcripción de más de 60.000 caracteres (algo más de una hora de conversación) se lee por tramos (`native/conversation.py`): cortes de línea completa de hasta 40.000 caracteres, y un capítulo de YouTube abre tramo si el actual ya pasa de la mitad. Cada tramo devuelve notas con sus marcas `[mm:ss]` y citas; una cita solo pasa a la síntesis si sus palabras aparecen en ese orden en la transcripción, sin contar mayúsculas ni puntuación, porque los subtítulos parten las frases en líneas cortas y no la llevan. La misma comprobación palabra a palabra vale para la evidencia literal de las relaciones y de las notas derivadas. Los tramos leídos se guardan en `stretches/<captura>/` con una clave del texto, el modelo, la intención y el perfil, de modo que un reintento solo lee los que faltan. La transcripción se conserva hasta 400.000 caracteres (unas 4 h de habla); la vista de la extensión recibe los primeros 160.000.

Un vídeo puede convertirse en una nota de conversación (`native/conversation.py`, `shape`). La elección viaja con la captura (`conversation`: `auto`, `on` u `off`): en `auto` decide el modelo con `source_format` `podcast` o `entrevista`; el modo **Podcast · entrevista** del panel envía `on` y la revisión puede volver a preparar la captura con `on` u `off` (`redraft` en el fondo de la extensión). El esquema añade `quotes` (texto y quien habla) y `author`. Las citas no van en `body`: el modelo deja una línea `%%citas%%` (aunque la escriba como encabezado o bajo un encabezado propio, queda uno solo) y el servicio pone allí, o al final, la sección `quotes` del perfil («Citas destacadas») con las citas que superan `quote_time` y el minuto sacado de la transcripción. `author` conserva solo los nombres que aparecen en el título, el canal o la transcripción, y ocupa `fuente_autor`; si no queda ninguno, se usa el canal que da `yt-dlp`. La revisión por apartados envía a la IA los primeros 160.000 caracteres de la fuente, así que en un podcast muy largo no ve el final de la transcripción.

La recuperación inicial busca en archivos locales y lee fragmentos relevantes. No se mantiene un índice semántico ni se envía el vault completo al proveedor. Se ha elegido una extensión pequeña propia para integrar la cola local y la revisión explícita de relaciones; las plantillas e interpretación de Obsidian Web Clipper sirvieron de referencia, sin crear un fork que hubiera que mantener.

El enlace de una relación apunta al encabezado bajo el que está el fragmento literal de la nota destino (`section_anchor` en `native/core.py`), sin preguntar a la IA. Enlaza la nota entera cuando el fragmento no está bajo un encabezado de nivel 2 o inferior, aparece más de una vez, el encabezado está repetido o contiene caracteres que Obsidian reescribe en los enlaces (`[]|#^:%*` y acentos graves). No se usan referencias a bloque (`^id`): exigirían modificar la nota destino. En el frontmatter, `relacionadas` sigue enlazando la nota entera.

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

La bienvenida ofrece una sola línea: `scripts/install.sh` (Linux y macOS) o `scripts/install.ps1` (Windows). Instalan `uv` si falta, que trae su propio Python, después el paquete desde el zip del repositorio (sin git) con `uv tool install --python 3.12`, lo añaden al PATH y ejecutan `anaco-ob install`. `ANACO_OB_SOURCE` cambia el origen del paquete. La extensión no puede ejecutar programas: la página espera consultando `settings` cada 3 s, que responde aunque falte el vault.

La CI instala el paquete con `pipx` y con la línea única en los tres sistemas, y comprueba el servicio con un mensaje real de Native Messaging (`scripts/smoke_native_host.py`).

## Proveedores de IA

Todas las llamadas al modelo pasan por `App.ai_json`. Con Codex (predeterminado) se ejecuta `codex exec` como siempre. Con el proveedor compatible con OpenAI, `native/ai.py` envía `POST {api_base}/chat/completions` con `response_format: json_schema` estricto y, además, el esquema en el texto: la capa compatible de Claude ignora `response_format`. Si el servidor rechaza el esquema, reintenta con `json_object`. No envía `temperature`, porque los modelos recientes de Claude y los de razonamiento solo aceptan la suya. `extension/providers.js` guarda la dirección y un modelo sugerido de cada servicio (Claude, Gemini, OpenAI, MiniMax, Qwen, OpenRouter, Ollama, LM Studio); el servicio local solo recibe `api_base`, `api_model` y la clave. Las imágenes viajan como URL `data:` al modelo visual, o al modelo principal si no hay visual. La clave API vive en `config.json` (permisos 0600) y las respuestas a la extensión solo indican `api_key_set`.

## Idiomas de la interfaz

La extensión está en español (principal y respaldo) e inglés. Los textos viven en `extension/_locales/{es,en}/messages.json`, en el formato de `browser.i18n`, que también traduce el manifiesto (`default_locale: es`). `scripts/i18n.py build` los reúne en `extension/i18n-catalog.js`, porque `browser.i18n` solo sigue el idioma del navegador y Anaco permite elegirlo en Opciones.

- **Código:** `tx('clave', [valores])` sustituye `$1`…`$n`; en HTML, `data-i18n` para el texto y `data-i18n-<atributo>` para `placeholder`, `title`, `aria-label` y `alt`. `i18n.js` traduce cada página al cargar.
- **Elección:** `localStorage['anaco-ob:lang']` (`auto`, `es` o `en`). En automático se usa inglés si el navegador está en inglés. Al cambiarlo, las páginas abiertas se recargan y el fondo actualiza los menús contextuales.
- **Scripts de contenido:** no leen el almacenamiento de la extensión. El fondo inyecta `globalThis.AnacoObLang` con el idioma resuelto y después el catálogo, antes de `capture.js` y `resource.js`.
- **Servicio local:** la extensión envía `lang` en cada mensaje. `native/translation.py` traduce con `native/locales/en.json`, cuya clave es el texto español del código: `UserError("texto {valor}", valor=...)` y `t()` siguen el idioma de la interfaz (errores, avisos, progreso); los avisos se traducen al crearse y se guardan así.
- **Notas:** `note_language` (`es` por defecto, en Opciones) decide el idioma de las notas nuevas. `n()` traduce los textos fijos de la nota (encabezados predeterminados, fuente, recursos, aportes, tipos de relación) y `writing_rule()` sustituye al antiguo «Escribe en español» en los prompts, que siguen escritos en español. Los marcadores internos `[Página N]` no cambian.
- **Comprobación:** `python3 scripts/i18n.py check` (en CI) exige cada clave usada en ambos idiomas con los mismos marcadores, rechaza claves calculadas y avisa si el catálogo no está al día. En el servicio exige traducción para cada texto de `UserError`, `t()` y `n()` y rechaza mensajes formateados con f-strings o concatenación.
