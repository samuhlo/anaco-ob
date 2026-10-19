# Publicación en addons.mozilla.org

Textos y material para la ficha de Anaco en AMO. El paquete se genera con `npm run build` en `dist/anaco-ob-<versión>.zip`.

## Pasos

1. `npm ci && npm test && npm run lint && npm run build`.
2. En <https://addons.mozilla.org/developers/> → **Submit a New Add-on** → **On this site**, sube `dist/anaco-ob-<versión>.zip`.
3. Código fuente: responde **No**. El paquete no está minificado ni compilado: `vendor/purify.js` es la distribución oficial de DOMPurify sin modificar, y `i18n-catalog.js` es JSON legible generado desde `_locales`. Si el revisor lo pide, enlaza el repositorio y las notas de abajo.
4. Rellena la ficha en español (idioma predeterminado) y añade la traducción al inglés con los textos de abajo.
5. Sube las capturas de `docs/amo/` (1280×800). Se regeneran con `.venv/bin/python scripts/amo_shots.py`.
6. Pega las notas para el revisor.

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
- Prepara las notas con Codex y tu cuenta de ChatGPT, con cualquier servidor compatible con OpenAI (incluidos modelos locales con Ollama o LM Studio) o sin IA.
- Interfaz y notas en español o inglés.

Necesita un pequeño servicio local, de código abierto, que se instala una vez con `pipx install git+https://github.com/samuhlo/anaco-ob` y `anaco-ob install`. La página de bienvenida muestra los comandos para tu sistema.

Sin servidores propios ni telemetría. La transcripción se hace en tu ordenador.

## Listing · English

- **Summary** (max. 250): Turn articles, PDFs, videos, courses and images into reviewed notes for your Obsidian vault, with local transcription, visual descriptions and verifiable links to your notes.
- **Description**

Anaco turns what you read in the browser into Obsidian notes that you review before saving.

- Captures articles, quotes, images, PDFs, videos with subtitles or local transcription, and courses with embedded viewers.
- Keeps posts from X, CodePen demos that work offline and video clips, placed where they belong in the note.
- Learns your vault's structure (destinations, types, file names and metadata) and saves following your rules.
- Proposes links to your notes backed by literal excerpts from both; you decide which to accept.
- Prepares notes with Codex and your ChatGPT account, with any OpenAI-compatible server (including local models with Ollama or LM Studio) or without AI.
- Interface and notes in Spanish or English.

It needs a small open-source local service, installed once with `pipx install git+https://github.com/samuhlo/anaco-ob` and `anaco-ob install`. The welcome page shows the commands for your system.

No servers of its own and no telemetry. Transcription runs on your computer.

## Capturas

| ARCHIVO | PIE · ES | CAPTION · EN |
| :--- | :--- | :--- |
| `1-resaltado.png` | Elige los recursos incrustados; al pasar por uno se resalta en el artículo. | Choose embedded resources; hovering one highlights it in the article. |
| `2-revision.png` | Revisa la nota, sus imágenes y sus relaciones antes de guardarla. | Review the note, its images and its links before saving it. |
| `3-panel-perfil.png` | El panel lateral y el perfil del vault que guía dónde y cómo guardar. | The sidebar and the vault profile that guides where and how to save. |

## Notes for the reviewer

Paste this in **Notes to Reviewer**:

> Anaco works together with a local companion service through Native Messaging (`nativeMessaging`, host `org.samuh.anaco_ob`). The service is open source (MIT) in the same repository: https://github.com/samuhlo/anaco-ob (`native/`, installed with `pipx install git+https://github.com/samuhlo/anaco-ob` and `anaco-ob install`). Without it, the panel and the welcome page explain how to install it.
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
