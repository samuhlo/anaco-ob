# Publicación en addons.mozilla.org

Textos y material para la ficha de Anaco en AMO. El paquete se genera con `npm run build` en `dist/anaco-ob-<versión>.zip`.

## Pasos

1. `npm ci && npm test && npm run lint && npm run build`.
2. En <https://addons.mozilla.org/developers/> → **Submit a New Add-on** → **On this site**, sube `dist/anaco-ob-<versión>.zip`.
3. Código fuente: responde **No**. El paquete no está minificado ni compilado: `vendor/purify.js` es la distribución oficial de DOMPurify sin modificar, y `i18n-catalog.js` es JSON legible generado desde `_locales`. Si el revisor lo pide, enlaza el repositorio y las notas de abajo.
4. Rellena la ficha en español (idioma predeterminado) y añade la traducción al inglés con los textos de abajo.
5. Sube las capturas de `docs/amo/` (1280×800; también las usa el README del repositorio). Se regeneran con `.venv/bin/python scripts/amo_shots.py`.
6. Pega las notas para el revisor.

## Subir una versión nueva

Una versión ya enviada no se puede reemplazar ni reutilizar su número. Para la siguiente:

1. Sube la versión en `extension/manifest.json`, `package.json`, `pyproject.toml` y `VERSION` en `native/core.py` (`tests/test_release.py` exige que coincidan) y añade su entrada en `docs/HISTORIAL.md`.
2. `npm run build` y, en la página del complemento en AMO, **Upload New Version** con el nuevo zip.
3. En **Version notes**, pega las notas de la versión de abajo.

**1.0.1 · notas de la versión**

- ES: Primer uso guiado: explica por qué hace falta la pieza local, la instala con una sola línea en la terminal y detecta sola cuándo responde. Elige la IA por su nombre: ChatGPT (Codex), Claude, Gemini, OpenAI, MiniMax, Qwen, OpenRouter, Ollama o LM Studio.
- EN: Guided first run: it explains why the local piece is needed, installs it with a single line in the terminal and notices by itself when it answers. Choose the AI by name: ChatGPT (Codex), Claude, Gemini, OpenAI, MiniMax, Qwen, OpenRouter, Ollama or LM Studio.

## Ficha · español

- **Nombre:** Anaco
- **Resumen** (máx. 250): Convierte artículos, PDF, vídeos, cursos e imágenes en notas revisadas para tu vault de Obsidian, con transcripción local, descripciones visuales y relaciones verificables con tus notas.
- **Categoría:** Productividad (Productivity)
- **Etiquetas:** obsidian, notes, markdown, productivity
- **Página de soporte:** <https://github.com/samuhlo/anaco-ob/issues>
- **Página web:** <https://github.com/samuhlo/anaco-ob>
- **Licencia:** MIT
- **Política de privacidad:** el contenido de [PRIVACY.md](../../PRIVACY.md).

**Descripción**

Anaco convierte lo que lees en el navegador en notas para Obsidian que revisas antes de guardar.

- Captura artículos, frases, imágenes, PDF, vídeos con subtítulos o transcripción local y cursos con visores incrustados.
- Conserva publicaciones de X, demos de CodePen sin conexión y clips de vídeo, colocados en su sitio dentro de la nota.
- Aprende la estructura de tu vault (destinos, tipos, nombres de archivo y metadatos) y guarda según tus reglas.
- Propone relaciones con tus notas apoyadas en fragmentos literales de ambas; tú decides cuáles aceptar.
- Prepara las notas con Codex y tu cuenta de ChatGPT, con Claude, Gemini, OpenAI, MiniMax, Qwen u OpenRouter con tu clave, con un modelo local (Ollama, LM Studio) o sin IA.
- Interfaz y notas en español o inglés.

Necesita un pequeño servicio local, de código abierto. La página de bienvenida explica por qué y lo instala con una sola línea en la terminal, que trae Python si no lo tienes.

Sin servidores propios ni telemetría. La transcripción se hace en tu ordenador.

## Listing · English

- **Summary** (max. 250): Turn articles, PDFs, videos, courses and images into reviewed notes for your Obsidian vault, with local transcription, visual descriptions and verifiable links to your notes.
- **Description**

Anaco turns what you read in the browser into Obsidian notes that you review before saving.

- Captures articles, quotes, images, PDFs, videos with subtitles or local transcription, and courses with embedded viewers.
- Keeps posts from X, CodePen demos that work offline and video clips, placed where they belong in the note.
- Learns your vault's structure (destinations, types, file names and metadata) and saves following your rules.
- Proposes links to your notes backed by literal excerpts from both; you decide which to accept.
- Prepares notes with Codex and your ChatGPT account, with Claude, Gemini, OpenAI, MiniMax, Qwen or OpenRouter using your key, with a local model (Ollama, LM Studio) or without AI.
- Interface and notes in Spanish or English.

It needs a small open-source local service. The welcome page explains why and installs it with a single line in the terminal, which brings Python if you don’t have it.

No servers of its own and no telemetry. Transcription runs on your computer.

## Capturas

| ARCHIVO | PIE · ES | CAPTION · EN |
| :--- | :--- | :--- |
| `1-resaltado.png` | Elige los recursos incrustados; al pasar por uno se resalta en el artículo. | Choose embedded resources; hovering one highlights it in the article. |
| `2-revision.png` | Revisa la nota, sus imágenes y sus relaciones antes de guardarla. | Review the note, its images and its links before saving it. |
| `3-panel-perfil.png` | El panel lateral y el perfil del vault que guía dónde y cómo guardar. | The sidebar and the vault profile that guides where and how to save. |
| `4-bienvenida.png` | La bienvenida explica por qué hace falta la pieza local y la instala con una sola línea. | The welcome page explains why the local piece is needed and installs it with a single line. |
| `5-perfil.png` | Revisa la propuesta de perfil: dónde guardar, qué tipos y metadatos usar. | Review the profile proposal: where to save, which types and metadata to use. |

## Notes for the reviewer

Paste this in **Notes to Reviewer**:

> Anaco works together with a local companion service through Native Messaging (`nativeMessaging`, host `org.samuh.anaco_ob`). The service is open source (MIT) in the same repository: https://github.com/samuhlo/anaco-ob (`native/`). The welcome page explains why it is needed and offers one line to install it (`scripts/install.sh`, `scripts/install.ps1`: uv, then the package from the repository archive, then `anaco-ob install`); the extension itself never runs or downloads programs. `pipx install git+https://github.com/samuhlo/anaco-ob` and `anaco-ob install` also work.
>
> To test without any AI account: install the service, run `anaco-ob install --vault <an empty folder>`, open the sidebar on any article, choose "Captura manual · sin IA" / "Manual capture · no AI", prepare and save. The interface language can be switched to English in Options → Language.
>
> Permissions:
> - `activeTab`, `tabs`, `webNavigation`: read the current tab and its frames to detect articles, PDFs, videos and embedded viewers when the user opens the panel.
> - `<all_urls>` (optional, requested at runtime per site): read cross-origin frames, images and media the user chooses to keep.
> - `menus`: "Save quote/image with Anaco" context menu items.
> - `storage`: panel state and pending captures.
> - `nativeMessaging`: talk to the local service that writes the notes into the user's Obsidian vault.
>
> Third-party code, unmodified, copied by `scripts/vendor.mjs` from npm (versions pinned in package.json): `vendor/marked.js` (marked 18.1.1, `lib/marked.umd.js`) and `vendor/purify.js` (DOMPurify 3.4.17, `dist/purify.min.js`). Rendered Markdown is always sanitized with DOMPurify. `i18n-catalog.js` is generated by `scripts/i18n.py build` from `_locales/*/messages.json`. Nothing else is generated, bundled or minified.
>
> Data: no remote servers of our own and no telemetry. Page content reaches an AI provider only if the user picks one in Options; see the privacy policy.
