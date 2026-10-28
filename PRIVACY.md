# Política de privacidad · Privacy policy

_Última actualización · Last updated: 2026-10-28_

## Español

Anaco no tiene servidores propios y no recoge estadísticas, telemetría ni identificadores de uso. Funciona con dos piezas que se ejecutan en tu ordenador: la extensión del navegador y un servicio local que instalas aparte.

**Qué datos maneja**

- **Contenido de las páginas que capturas.** Cuando abres el panel, la extensión lee la pestaña activa para detectar su contenido: texto, imágenes, PDF, vídeos y recursos incrustados. Solo se envía al servicio local cuando eliges preparar una nota. Incluye el título y la dirección originales, la descripción, los encabezados, las migas de navegación y el contexto del catálogo o página contenedora disponibles. Estos datos acompañan a la captura si eliges prepararla con IA.
- **Cola de enlaces y sesión.** Si solicitas preparar varios enlaces, se guardan localmente los enlaces y sus estados, y se abren en segundo plano para leerlos. El permiso opcional `cookies` se usa para abrir las pestañas en el mismo contenedor; Anaco no lee ni exporta las cookies. Los recursos se intentan leer desde la página para conservar la sesión.
- **Tu vault de Obsidian.** El servicio local lee tu vault para buscar notas relacionadas, escanear su estructura (carpetas, nombres de archivo y metadatos) y guardar las notas que confirmas. El contenido de tus notas no sale de tu ordenador salvo lo que se describe abajo.
- **Audio y vídeo.** La transcripción se hace en tu ordenador con Whisper. El audio no se envía a ningún servicio de transcripción.

**Cuándo salen datos de tu ordenador**

Solo si eliges un proveedor de IA:

- **Codex (ChatGPT).** Se envían a OpenAI, con tu sesión de Codex, la captura que preparas, fragmentos de las notas candidatas para relacionarlas y los documentos de instrucciones que el perfil del vault selecciona. Al pedir una propuesta de perfil con IA se envían estadísticas agregadas del vault y los documentos que marques.
- **Proveedor compatible con OpenAI.** Lo mismo, al servicio que configures (Claude, Gemini, OpenAI, MiniMax, Qwen, OpenRouter u otro). Si es un modelo local, como Ollama o LM Studio, nada sale de tu ordenador. La clave API se guarda solo en la configuración del servicio local y la extensión no la recibe.
- **Captura manual.** No se envía nada a ningún proveedor.

Cada proveedor trata esos datos según sus propias condiciones. Las descargas que pides (imágenes, clips, PDF, demos de CodePen y sus librerías) se hacen directamente desde tu navegador a su origen.

**Exploración de cursos.** Al solicitarla, Anaco lee el catálogo de módulos y las páginas internas enlazadas con la sesión del navegador. Guarda localmente títulos, enlaces, jerarquía y selección. Esa exploración no envía contenido a la IA; la preparación empieza solo cuando eliges los enlaces y la solicitas.

**Dónde se guardan**

En tu vault (las notas y sus adjuntos), en la carpeta del servicio local (`~/.local/share/anaco-ob/` en Linux, `~/Library/Application Support/anaco-ob/` en macOS y `%APPDATA%\anaco-ob\` en Windows: configuración, capturas pendientes, historial y copias recuperables de índices actualizados) y en el almacenamiento local de la extensión. La extensión no funciona en ventanas de navegación privada.

**Cómo borrarlos**

Desinstala la extensión y ejecuta `anaco-ob uninstall --purge`, que quita el registro del servicio y borra su carpeta de datos. Las notas guardadas en tu vault son tuyas y no se modifican.

**Contacto**

Abre un issue en <https://github.com/samuhlo/anaco-ob/issues>.

## English

Anaco has no servers of its own and collects no analytics, telemetry or usage identifiers. It runs as two parts on your computer: the browser extension and a local service you install separately.

**What data it handles**

- **Content of the pages you capture.** When you open the panel, the extension reads the active tab to detect its content: text, images, PDF, video and embedded resources. It is sent to the local service only when you choose to prepare a note, including its original title and address, description, headings, breadcrumbs and available catalog or containing-page context. This context accompanies the capture if you choose AI preparation.
- **Link queue and session.** When you request multiple links, their URLs and progress are stored locally and they open in the background for capture. The optional `cookies` permission is used to open tabs in the same container; Anaco does not read or export cookies. Resources are first requested from the page to preserve its session.
- **Your Obsidian vault.** The local service reads your vault to find related notes, scan its structure (folders, file names and metadata) and save the notes you confirm. The content of your notes stays on your computer except as described below.
- **Audio and video.** Transcription runs on your computer with Whisper. Audio is not sent to any transcription service.

**When data leaves your computer**

Only if you choose an AI provider:

- **Codex (ChatGPT).** The capture you prepare, excerpts of candidate notes to relate them and the instruction documents selected by the vault profile are sent to OpenAI through your Codex session. Asking the AI for a vault profile sends aggregated vault statistics and the documents you select.
- **OpenAI-compatible provider.** The same, to the service you configure (Claude, Gemini, OpenAI, MiniMax, Qwen, OpenRouter or another). With a local model such as Ollama or LM Studio, nothing leaves your computer. The API key is stored only in the local service settings and never reaches the extension.
- **Manual capture.** Nothing is sent to any provider.

Each provider handles that data under its own terms. The downloads you request (images, clips, PDF, CodePen demos and their libraries) go directly from your browser to their source.

**Course exploration.** When requested, Anaco reads the module catalog and linked internal pages using the browser session. Titles, links, hierarchy and selections are stored locally. Exploration does not send content to AI; preparation starts only when you select the links and request it.

**Where it is stored**

In your vault (notes and attachments), in the local service folder (`~/.local/share/anaco-ob/` on Linux, `~/Library/Application Support/anaco-ob/` on macOS and `%APPDATA%\anaco-ob\` on Windows: settings, pending captures, history and recoverable backups of updated indexes) and in the extension's local storage. The extension does not run in private browsing windows.

**How to delete it**

Uninstall the extension and run `anaco-ob uninstall --purge`, which removes the service registration and deletes its data folder. Notes saved in your vault are yours and are left untouched.

**Contact**

Open an issue at <https://github.com/samuhlo/anaco-ob/issues>.
