<div align="center">
  <br />
  <img src="extension/logo.svg" alt="Logo de Anaco: «Anac» con la O sustituida por un cristal facetado amarillo" height="56" />
  <h1><code>./ANACO.sh</code></h1>

**Captura artículos, cursos, PDF y vídeos desde el navegador y los convierte en notas revisadas para tu vault de Obsidian, con su procedencia, sus recursos y relaciones que puedes comprobar.**
<br /><br />

  <img src="https://img.shields.io/badge/STATUS-ACTIVE-FFCA40?style=for-the-badge&labelColor=000000" alt="Status" />
  <img src="https://img.shields.io/badge/VERSIÓN-0.11.0-FFCA40?style=for-the-badge&labelColor=000000" alt="Versión" />
  <img src="https://img.shields.io/badge/LICENCIA-MIT-FFCA40?style=for-the-badge&labelColor=000000" alt="Licencia MIT" />
  <br/>
  <img src="https://img.shields.io/badge/Zen_·_Firefox-0C0011?style=for-the-badge&logo=firefoxbrowser&logoColor=FFCA40&labelColor=000000" alt="Zen y Firefox" />
  <img src="https://img.shields.io/badge/Obsidian-0C0011?style=for-the-badge&logo=obsidian&logoColor=FFCA40&labelColor=000000" alt="Obsidian" />
  <br/>
  <img src="https://img.shields.io/badge/JavaScript-0C0011?style=for-the-badge&logo=javascript&logoColor=FFCA40&labelColor=000000" alt="JavaScript" />
  <img src="https://img.shields.io/badge/Python-0C0011?style=for-the-badge&logo=python&logoColor=FFCA40&labelColor=000000" alt="Python" />
  <img src="https://img.shields.io/badge/Codex-0C0011?style=for-the-badge&logo=openai&logoColor=FFCA40&labelColor=000000" alt="Codex" />
  <img src="https://img.shields.io/badge/Whisper_local-0C0011?style=for-the-badge&labelColor=000000" alt="Whisper local" />
  <br/><br/>

[Guía de prueba](PRUEBA.md) ·
[Historial](docs/HISTORIAL.md) ·
[Validación](docs/VALIDACION.md) ·
[Notas técnicas](docs/TECNICO.md) ·
[Privacidad](PRIVACY.md)

  <code style="color:#737373;">// anaco: un trozo, una pieza que merece quedarse //</code>

  <br /><br />
  <img src="docs/assets/revision.png" alt="Revisión de una nota capturada de Codrops: la nota a la izquierda y sus propiedades, destino y conexiones a la derecha" width="820" />

  <br />
</div>

---

## // 00_ LA_FRICCIÓN

Guardar lo que aprendes en la web suele acabar en marcadores que no vuelves a abrir o en notas copiadas sin contexto. Un artículo con tuits, demos de CodePen y clips se convierte en un texto plano sin lo que lo hacía útil. Una lección de un curso vive dentro de un visor que no se deja copiar. Y cada vault tiene sus carpetas, sus metadatos y su forma de relacionar notas.

Anaco lee lo que estás viendo, prepara una propuesta de nota que respeta las reglas de tu vault y no escribe nada hasta que la revisas.

---

## // 01_ QUÉ_HACE

| PIEZA | QUÉ ES |
| :--- | :--- |
| **Panel lateral** | Detecta el contenido de la pestaña actual: artículo, frase, imagen, PDF, vídeo, lector de un curso o recursos incrustados. Eliges qué incluir. |
| **Recursos incrustados** | Publicaciones de X, demos de CodePen y clips silenciosos. Al pasar el ratón por cada uno, el artículo lo resalta. En la nota aparecen en su sitio. |
| **Revisión** | Una pestaña amplia con la nota, sus propiedades, destino, imágenes y conexiones. Puedes editar, ajustar apartados, dividir en varias notas o integrarlas. |
| **Perfil del vault** | Escanea tu vault y, con tus propias instrucciones, propone dónde guardar, qué tipos y nombres usar y cómo rellenar el frontmatter. Lo confirmas tú. |
| **Servicio local** | Python sin dependencias externas: busca relaciones, llama a la IA, transcribe en local y escribe en el vault solo tras tu revisión. |

<div align="center">
  <img src="docs/assets/recursos.png" alt="Panel lateral con la lista de clips de vídeo de un artículo de Codrops" width="300" />
  &nbsp;&nbsp;
  <img src="docs/assets/resaltado.png" alt="Artículo con un clip rodeado en amarillo y la etiqueta Clip 1" width="480" />
</div>

---

## // 02_ EL_FLUJO

```text
pestaña → panel: detectar contenido y recursos → elegir imágenes, clips, demos y publicaciones
        → preparar: IA (Codex) o captura manual → revisión: editar, conectar, dividir
        → guardar en el vault según su perfil → volver al artículo
```

La barra de rayitas bajo el logo sigue el avance de la nota: detectada, preparándose, en revisión y guardada.

> _note: nada se escribe en el vault sin pasar por la revisión. las notas existentes solo se amplían con un aporte que apruebas explícitamente._

---

## // 03_ PERFIL_DEL_VAULT

<div align="center">
  <img src="docs/assets/perfil.png" alt="Propuesta de perfil del vault: resumen de destinos, tipos, metadatos, adjuntos y documentos, con secciones plegables" width="620" />
</div>

En **Opciones → Perfil del vault** pulsas **Escanear el vault**. Anaco lee carpetas, nombres de archivo y metadatos, nunca el contenido de tus notas. Te enseña qué instrucciones, skills, guías y plantillas ha encontrado para que elijas cuáles puede leer la IA. La propuesta empieza por un resumen de lo que hará; cada regla se ajusta en su desplegable, con la evidencia que la justifica.

El perfil se guarda como `.json` en una carpeta normal del vault, por ejemplo `99_Recursos/anaco/perfil.json`, de modo que viaja con tu sincronización. Si mueves una guía o desaparece un destino, el panel pide **Revisar perfil**.

---

## // 04_ CARACTERÍSTICAS

- **Cursos y visores**: lee marcos anidados con permisos por dominio, lectores HTML con páginas dibujadas y PDF del visor. El modo **Curso** conserva la detección clásica.
- **Vídeo y audio**: usa subtítulos cuando existen y, si no, transcribe en tu equipo con Whisper. El audio no sale a una API.
- **Demos sin conexión**: cada pen de CodePen se guarda como un `index.html` con sus librerías y módulos ES, para verlo en la nota con el plugin HTML Prototype Viewer.
- **Imágenes con criterio**: aprovecha los pies del HTML y solo envía a análisis visual las imágenes que lo necesitan.
- **Relaciones verificables**: cada conexión con una nota existente se apoya en fragmentos literales de ambas notas, y la aceptas o la descartas tú.
- **Una o varias notas**: una nota con apartados, varias enlazadas por temas o que decida la IA, con división e integración revisables.
- **Privacidad**: sin servidores propios ni telemetría. El vault no se envía completo; la IA recibe la captura y fragmentos de las notas candidatas. Detalle en [PRIVACY.md](PRIVACY.md).

---

## // 05_ STACK

| CAPA | TECNOLOGÍA |
| :--- | :--- |
| **Extensión** | WebExtension Manifest V2 para Zen y Firefox (140+), JavaScript sin framework |
| **Vista previa** | Marked y DOMPurify empaquetados en `extension/vendor/` |
| **Servicio** | Python 3 estándar vía Native Messaging (`org.samuh.anaco_ob`) |
| **IA** | `codex exec` con tu sesión de ChatGPT, salida estructurada y sin herramientas de shell |
| **Multimedia** | Poppler, FFmpeg, `yt-dlp` y Faster Whisper en `.media-venv/` |
| **Pruebas** | `node:test`, `unittest` y Selenium sobre Zen real |

---

## // 06_ INICIO_RÁPIDO

```bash
# 1. Instala el servicio local (Linux, macOS o Windows, Python 3.11+)
pipx install git+https://github.com/samuhlo/anaco-ob

# 2. Regístralo para Firefox y Zen, y comprueba qué falta
anaco-ob install --vault ~/ruta/a/tu/vault
anaco-ob doctor

# 3. Opcional: transcripción local con Whisper (PDF y vídeo usan Poppler, FFmpeg y yt-dlp del sistema)
anaco-ob install-media

# 4. Opcional: IA con tu cuenta de ChatGPT (sin ella, usa la captura manual)
codex login
```

Después, en Zen o Firefox: `about:debugging#/runtime/this-firefox` → **Cargar complemento temporal** → `extension/manifest.json`, hasta que esté publicada en addons.mozilla.org. Abre **Opciones**, elige tu vault y confirma su **Perfil del vault**. La guía completa, paso a paso, está en [PRUEBA.md](PRUEBA.md).

| COMANDO | PARA QUÉ |
| :--- | :--- |
| `anaco-ob uninstall [--purge]` | Quitar el registro del navegador; `--purge` borra también los datos locales |
| `python3 scripts/install.py` | Desarrollo: registrar el servicio desde el repositorio y generar `dist/anaco-ob-<versión>.zip` |
| `npm test` | Pruebas unitarias de la extensión |
| `python3 -m unittest discover -s tests` | Pruebas del servicio |
| `python3 tests/e2e_zen.py --profile` | Recorrido real en Zen: perfil, captura y guardado |
| `python3 tests/e2e_zen.py --readme-shots` | Regenerar las capturas de este README (usa la red) |

---

## // 07_ BLUEPRINT

```text
extension/     # WebExtension: panel, captura, recursos incrustados, revisión y opciones
native/        # Servicio local: perfil y escaneo del vault, IA, relaciones y guardado
skills/        # Contrato editorial genérico que recibe la IA
scripts/       # Instalación y comprobaciones reproducibles
tests/         # Pruebas unitarias, fixtures y recorridos en Zen
docs/          # Historial, validación, notas técnicas y capturas
```

---

## // 08_ TESTS · DOCS · ESTADO · LICENCIA

- **Estado:** 0.11.0, en uso diario. Los cursos privados se validan en la sesión del usuario; ver [VALIDACION.md](docs/VALIDACION.md).
- **Docs:** [guía de prueba](PRUEBA.md), [historial](docs/HISTORIAL.md), [notas técnicas](docs/TECNICO.md) y [contrato editorial de la IA](skills/anaco-ob/SKILL.md).
- **Licencia:** [MIT](LICENSE).

---

<div align="center">
<br />

<code>DESIGNED & CODED BY <a href="https://github.com/samuhlo">samuhlo</a></code>

</div>
