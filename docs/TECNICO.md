# Notas técnicas

## IA, multimedia y dependencias

El servicio no requiere dependencias de Python externas. La IA utiliza `codex exec`, con la sesión existente de ChatGPT, salida estructurada y herramientas de shell, aplicaciones y agentes deshabilitadas. El proceso de generación tiene acceso de solo lectura; la escritura la realiza el servicio después de la revisión del usuario.

Los valores predeterminados de Codex son `gpt-6.1-sol` para elaborar notas y visión, `gpt-6-luna` para leer los tramos de podcasts largos y `reasoning_effort=medium` en ambas fases. El modelo de lectura se ajusta por separado en Opciones; los proveedores compatibles mantienen su propio modelo configurado. El servicio envía ese esfuerzo explícitamente como `model_reasoning_effort` a todas sus llamadas Codex, incluidas lectura por tramos, síntesis, revisión y conexiones. Se puede ajustar en Opciones. Las cachés de tramos y de lectura de libros incluyen el esfuerzo para no reutilizar un análisis de menor calidad al cambiarlo. El contrato `editorial-v5` desarrolla ideas clave con mecanismos, ejemplos y condiciones. Para conversaciones separa dos bloques de nivel 2: primero «Resumen del podcast», con subtítulos por temas y lo importante de cada uno; después «Qué puedo aprender e incorporar a mi vida», con aprendizajes, situaciones, pasos, ejemplos y un punto de partida. Las propuestas del editor se concentran en el segundo bloque y se distinguen de las recomendaciones expresadas en la fuente. Las notas derivadas conservan la misma distinción sobre su tema. Una petición expresa de otra estructura o análisis académico conserva su prioridad. Cambiar esta elaboración final no exige repetir la lectura factual de los tramos.

`native/editorial_profile.py` compila una vez las instrucciones propias del vault cuando superan 12.000 caracteres. Usa el modelo de lectura para eliminar repeticiones y procedimientos que ya resuelve el servicio, conservando criterios editoriales, condiciones, excepciones y prioridad del vault. El contrato general se envía íntegro y la síntesis conserva el mismo hash de los originales. El perfil compacto se guarda en `editorial-profiles/` por versión, hash de las guías y configuración del lector; un cambio de las guías lo invalida. Una compilación fallida, inválida o declarada incompleta utiliza los documentos originales sin recortarlos. Las guías cortas no requieren otra llamada. La primera elaboración puede incluir este paso; las siguientes reutilizan el perfil. El banco de fragmentos originales y las validaciones de citas y relaciones no cambian.

El progreso medible viaja como `{stage, message, unit, completed, total}`; `completed` cuenta unidades terminadas, nunca la que está empezando. Whisper conserva `{stage: transcribe, processed_seconds, total_seconds}` y emite la duración completa al finalizar, incluido el silencio final. `extension/progress.js` valida los valores y calcula porcentajes de la fase. Lectura, síntesis, texto del PDF, imágenes del PDF, descarga y cancelación tienen estados distintos. La síntesis no hereda el 100 % de lectura; las fases sin medición muestran el indicador de actividad sin barra. Los mensajes tardíos de un trabajo cancelado no reemplazan «Cancelando». La franja del logotipo identifica la etapa del flujo y no calcula un porcentaje global a partir de una fase.

La síntesis de podcasts recibe además `source_excerpts`: hasta 128 fragmentos literales de hasta 640 caracteres, repartidos por la transcripción original e incluyendo su final. El esquema de `source_evidence` de derivadas y relaciones se restringe a sus identificadores. La IA selecciona el fragmento que respalda cada idea; el servicio sustituye ese identificador por el texto original antes de la validación habitual. El resumen de un tramo no se acepta como cita de la transcripción. Identificadores desconocidos y paráfrasis siguen fallando; no se asigna una referencia aproximada ni se omite la validación. El banco es contexto de generación y no sustituye la captura guardada. Se reutilizan las lecturas ya completadas.

La ampliación multimedia utiliza Poppler, FFmpeg y `yt-dlp`. Whisper se ejecuta en un entorno separado del servicio: `media-venv/` en la carpeta de datos (`anaco-ob install-media`) o `.media-venv/` en el repositorio (`scripts/install-media.sh`), que tiene preferencia. Ambos fijan Faster Whisper 1.2.1 y PyAV 16.1.0 por compatibilidad con su API de decodificación. El audio no se envía a una API de transcripción.

Una transcripción de más de 60.000 caracteres (algo más de una hora de conversación) se lee por tramos (`native/conversation.py`): cortes de línea completa de hasta 40.000 caracteres, y un capítulo de YouTube abre tramo si el actual ya pasa de la mitad. Cada tramo devuelve notas con sus marcas `[mm:ss]` y citas; una cita solo pasa a la síntesis si sus palabras aparecen en ese orden en la transcripción, sin contar mayúsculas ni puntuación, porque los subtítulos parten las frases en líneas cortas y no la llevan. La misma comprobación palabra a palabra vale para la evidencia literal de las relaciones y de las notas derivadas. Se leen hasta dos tramos simultáneamente, se ensamblan siempre en orden temporal y el progreso cuenta solo resultados completos. Los trabajadores no usan SQLite ni emiten progreso. Un fallo o cancelación detiene los procesos Codex hermanos y conserva los resultados completos. Los tramos se guardan atómicamente en `stretches/shared/` y en `stretches/<captura>/`. La clave incluye la petición factual exacta (texto, tiempos, título, autor e intención), el proveedor y endpoint, el modelo de lectura, el razonamiento, el idioma y el hash de las instrucciones. Una captura nueva del mismo contenido puede reutilizarlos; cambiar solo el modelo final no repite la lectura. Los JSON incompletos o corruptos se vuelven a obtener. La transcripción se conserva hasta 400.000 caracteres (unas 4 h de habla); la vista de la extensión recibe los primeros 160.000.

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

## Interfaz

`extension/style.css` define los tokens (colores, `--r-sm`/`--r-md`/`--radius`, `--fs-meta`/`--fs-small`/`--fs-title`) y los componentes comunes; `panel.css` y `review.css` solo colocan piezas de su página y no redefinen reglas de otro archivo.

- **Botones:** cuatro niveles. `.primary` es la acción principal y hay como mucho una visible por vista; el botón sin clase es secundario; `.quiet` es una acción discreta sin borde; `.icon` es un botón cuadrado con `aria-label`. `.sm` reduce el tamaño y `.danger` solo cambia el color. `.link` se reserva para navegación dentro de un texto.
- **Acciones raras:** van en un menú `details.more` con `.menu`; las destructivas, al final y tras un `hr`.
- **Modos y vistas:** un selector `.seg` con `aria-pressed` cambia de modo (por ejemplo, **Esta página | Varios enlaces**); nunca ejecuta una acción.
- **Estados:** `.chip` con `data-tone`: `run` (amarillo, pendiente o en curso), `ok` (verde, hecho), `error` (rojo, necesita acción); sin `data-tone`, neutro. El amarillo de acento no indica «hecho».
- **Enlaces que salen:** «↗» marca siempre lo que abre otra pestaña o página.
- **Logo:** la interfaz usa `logo.svg` sin la firma «second brain», que a 26–36 px no se lee; el README y la ficha de Mozilla usan `docs/brand/logo-firma.svg`. El icono es la piedra con una «A».

## Integridad de capturas largas

La captura manual conserva íntegramente el cuerpo hasta el límite de edición de 100.000 caracteres, incluido su encabezado. Si lo supera, la preparación se rechaza con un mensaje y la captura permanece pendiente; se puede importar un rango menor o pedir un resumen con IA. La entrada de texto ordinaria conserva su límite de 160.000 caracteres y ahora avisa si se ha limitado. El límite de generación asistida continúa en 80.000 caracteres.

Las nuevas transcripciones usan `fingerprint_version: 2`: la huella representa todo el texto conservado, hasta 400.000 caracteres, no solo los primeros 150.000. La huella anterior se conserva como referencia de compatibilidad; solo permite reconocer un guardado antiguo si su captura conservada coincide íntegramente. Una coincidencia de prefijo por sí sola no se acepta. No se reescriben capturas antiguas ni intenciones de guardado interrumpido. La detección adicional por URL y las protecciones contra colisiones de archivos siguen vigentes.

## Aislamiento de vaults durante el trabajo

Cada cola guarda su vault de origen y lo comprueba al continuar, reintentar, reprocesar y antes de cada enlace. La extensión bloquea cambios de configuración y perfil mientras hay una operación o cola activa; una cola pausada puede conservarse al cambiar de vault, pero solo continúa en el original. Las solicitudes del trabajo llevan `expected_vault`, que el servicio valida antes de actuar. Cada solicitud usa una instantánea de configuración para que un cambio externo durante el procesamiento no mueva su contenido a otro vault.

Las subidas, incluidos adjuntos, guardan el vault en sus metadatos y lo comprueban antes de aceptar fragmentos o finalizar. Una subida antigua sin esa propiedad exige volver a importar y conserva los archivos: un trabajo creado al reintentar no demuestra a qué vault pertenecía la subida original. Las colas antiguas sin vault requieren conservar los enlaces y crear una nueva cola; sus capturas preparadas no se eliminan. Cambiar de vault también invalida la selección del perfil anterior.

## Procesos y progreso multiplataforma

Las consultas de trabajos usan información de creación del proceso para distinguir reutilización de PID cuando el sistema permite obtenerla. En Windows se consulta un handle con permisos de lectura y sincronización; nunca se usa una señal para comprobar si sigue vivo. Los trabajos antiguos sin identidad conservan una comprobación prudente de actividad.

Los comandos se ejecutan bajo un propietario del árbol de procesos: sesión/grupo en POSIX y Job Object con cierre terminante en Windows. En Windows el proceso se crea suspendido, se asigna al Job Object y después se reanuda, evitando que cree hijos antes de quedar vinculado. Cancelar, agotar el tiempo o cerrar el contexto elimina también los descendientes, incluso si su padre ya terminó.

La salida JSONL del transcriptor se lee mediante un hilo y una cola acotada, compatibles con tuberías de Windows. La cancelación y el plazo se comprueban en el hilo principal. Solo se publican campos de progreso permitidos; el texto de la transcripción permanece en el resultado privado. La CI ejecuta procesos reales y tuberías en Linux, macOS y Windows con Python 3.11 y 3.13, sin necesitar Whisper.

## Rutas de los lanzadores

El lanzador POSIX escapa cada argumento con `shlex.quote`, de modo que dólares, acentos graves y comillas de una ruta no se ejecutan como shell. El lanzador Windows mantiene un `.bat` ASCII con expansión retardada desactivada y usa PowerShell sin perfil para arrancar Python mediante `ProcessStartInfo`, pasando rutas Unicode como datos y heredando stdin/stdout binarios. No utiliza una tubería de PowerShell para transportar mensajes.

Windows no admite `%` ni `!` en la carpeta de datos que contiene el `.bat`: `cmd.exe` puede expandirlos antes de entrar en el script. El instalador lo rechaza antes de escribir el lanzador y permite elegir otra carpeta con `anaco-ob --state RUTA install`. Las rutas de Python y del módulo host sí se transportan literalmente, incluidos esos caracteres. La CI añade una transferencia binaria a través del lanzador real en los tres sistemas, con rutas de prueba que incluyen espacios, Unicode y metacaracteres.
