# Política de privacidad · Privacy policy

_Última actualización · Last updated: 2026-10-18_

## Español

Anaco no tiene servidores propios y no recoge estadísticas, telemetría ni identificadores de uso. Funciona con dos piezas que se ejecutan en tu ordenador: la extensión del navegador y un servicio local que instalas aparte.

**Qué datos maneja**

- **Contenido de las páginas que capturas.** Cuando abres el panel, la extensión lee la pestaña activa para detectar su contenido: texto, imágenes, PDF, vídeos y recursos incrustados. Solo se envía al servicio local cuando eliges preparar una nota. Incluye el título y la dirección de la página capturada.
- **Tu vault de Obsidian.** El servicio local lee tu vault para buscar notas relacionadas, escanear su estructura (carpetas, nombres de archivo y metadatos) y guardar las notas que confirmas. El contenido de tus notas no sale de tu ordenador salvo lo que se describe abajo.
- **Audio y vídeo.** La transcripción se hace en tu ordenador con Whisper. El audio no se envía a ningún servicio de transcripción.

**Cuándo salen datos de tu ordenador**

Solo si eliges un proveedor de IA:

- **Codex (ChatGPT).** Se envían a OpenAI, con tu sesión de Codex, la captura que preparas, fragmentos de las notas candidatas para relacionarlas y los documentos de instrucciones que el perfil del vault selecciona. Al pedir una propuesta de perfil con IA se envían estadísticas agregadas del vault y los documentos que marques.
- **Captura manual.** No se envía nada a ningún proveedor.

Cada proveedor trata esos datos según sus propias condiciones. Las descargas que pides (imágenes, clips, PDF, demos de CodePen y sus librerías) se hacen directamente desde tu navegador a su origen.

**Dónde se guardan**

En tu vault (las notas y sus adjuntos), en la carpeta del servicio local (`~/.local/share/anaco-ob/` en Linux, o su equivalente en tu sistema: configuración, capturas pendientes e historial) y en el almacenamiento local de la extensión. La extensión no funciona en ventanas de navegación privada.

**Cómo borrarlos**

Desinstala la extensión y borra la carpeta del servicio local y su registro de Native Messaging (`org.samuh.anaco_ob.json`). Las notas guardadas en tu vault son tuyas y no se modifican.

**Contacto**

Abre un issue en <https://github.com/samuhlo/anaco-ob/issues>.

## English

Anaco has no servers of its own and collects no analytics, telemetry or usage identifiers. It runs as two parts on your computer: the browser extension and a local service you install separately.

**What data it handles**

- **Content of the pages you capture.** When you open the panel, the extension reads the active tab to detect its content: text, images, PDF, video and embedded resources. It is sent to the local service only when you choose to prepare a note, including the title and address of the captured page.
- **Your Obsidian vault.** The local service reads your vault to find related notes, scan its structure (folders, file names and metadata) and save the notes you confirm. The content of your notes stays on your computer except as described below.
- **Audio and video.** Transcription runs on your computer with Whisper. Audio is not sent to any transcription service.

**When data leaves your computer**

Only if you choose an AI provider:

- **Codex (ChatGPT).** The capture you prepare, excerpts of candidate notes to relate them and the instruction documents selected by the vault profile are sent to OpenAI through your Codex session. Asking the AI for a vault profile sends aggregated vault statistics and the documents you select.
- **Manual capture.** Nothing is sent to any provider.

Each provider handles that data under its own terms. The downloads you request (images, clips, PDF, CodePen demos and their libraries) go directly from your browser to their source.

**Where it is stored**

In your vault (notes and attachments), in the local service folder (`~/.local/share/anaco-ob/` on Linux, or its equivalent on your system: settings, pending captures and history) and in the extension's local storage. The extension does not run in private browsing windows.

**How to delete it**

Uninstall the extension and delete the local service folder and its Native Messaging registration (`org.samuh.anaco_ob.json`). Notes saved in your vault are yours and are left untouched.

**Contact**

Open an issue at <https://github.com/samuhlo/anaco-ob/issues>.
