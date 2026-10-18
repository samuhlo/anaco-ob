# Validación de la primera entrega

Fecha: 2026-10-16. Versión actual: 0.3.1. Se conserva el historial de validación de las versiones anteriores.

## Resultado

Primera versión preparada para validación personal. El servicio, la extensión y los recorridos de revisión y guardado han sido comprobados en un Zen aislado con datos ficticios. No se han creado notas de prueba en `Second_Brain`.

| Comprobación | Resultado |
| --- | --- |
| Pruebas automáticas del servicio | 39 superadas |
| Pruebas JavaScript de permisos y entradas multimedia | 7 superadas |
| Sintaxis JavaScript de la extensión | Correcta |
| Compilación de los módulos Python | Correcta |
| Skill específica del vault | Validador de skills superado |
| Navegador real | Zen 1.22.3b, perfil temporal y modo headless |
| Comunicación con servicio local | Native Messaging comprobado desde la extensión instalada |
| Artículo → revisión → Markdown | Superado |
| Frase literal → nota | Superado |
| Imagen → archivo local e incrustación | Superado |
| Resumen con sesión real de ChatGPT | Superado con `gpt-6-luna`, mediante Codex CLI |
| Relación correcta frente a coincidencia de vocabulario | Propone recuperación activa y descarta recuperación de paquetes de red |
| Selección manual de relaciones | Inicialmente desmarcadas; selección conservada al reabrir |
| Ediciones y cierre inmediato del panel | Se conserva hasta el último carácter probado |
| Guardado tras reapertura | Incluye la edición, el enlace aceptado y la imagen |

## Evidencias locales

- [Resultado de la prueba directa de IA](../.test-artifacts/ai/result.json).
- [Resultado de artículo, frase e imagen en Zen](../.test-artifacts/zen/report.json).
- [Resultado del recorrido completo con IA en Zen](../.test-artifacts/zen-ai/report.json).
- [Captura de la interfaz de revisión](../.test-artifacts/zen-ai/review.png).

Los informes contienen la ruta del vault ficticio y las notas resultantes, que se han conservado para inspección. `.test-artifacts/` está excluido del control de versiones y puede reconstruirse con las pruebas.

## Qué se ha comprobado en el servicio

- Atribución de asistencia IA según el modo realmente utilizado.
- Conservación literal de frases y de su contexto, sin autor inventado.
- Adjuntos con contenido idéntico al capturado y rutas locales de Obsidian.
- Duplicados exactos frente a otra selección de la misma página.
- Rechazo de colisiones sin modificar notas existentes.
- Rechazo de rutas externas, carpetas no admitidas y enlaces simbólicos que salen del vault.
- Frontmatter de clases y naming coherente con el destino.
- Filtrado de relaciones sin evidencia literal o con destino inexistente.
- Revalidación de una nota relacionada renombrada antes del guardado.
- Recuperación de una captura pendiente tras un error de IA.
- Aislamiento de capturas entre vaults distintos.
- Fallos de adjuntos y publicación sin producir una nota a medias.
- Enmarcado binario de mensajes nativos y lecturas parciales.

## Alcance de las pruebas de navegador

La copia de prueba añade únicamente el permiso de host `http://127.0.0.1/*` para que WebDriver pueda iniciar la extracción en la página de prueba sin accionar la barra del navegador. Ese permiso adicional **no forma parte de la extensión entregada**.

Se ejercitan el capturador y el background de producción, las pantallas reales de revisión, el proveedor de IA, Native Messaging y la escritura en disco. La activación desde el icono, el atajo y el menú contextual del Zen habitual queda incluida en la validación manual del usuario. No se ha automatizado su perfil personal ni se han utilizado sus pestañas.

Las pruebas con páginas ficticias no garantizan extracción correcta de todos los sitios. Para páginas reales se muestra el texto extraído y se indica si no se detectó un artículo principal o si hay vídeo/marcos sin transcribir.

## Correcciones realizadas durante la integración

- El script inyectado termina con un valor serializable para que Firefox no rechace la inyección.
- Los permisos opcionales de imágenes utilizan patrones de host válidos y no solicitan de nuevo permisos ya concedidos.
- Las ediciones del panel se conservan de forma síncrona para evitar perder las últimas teclas al cerrar.
- Las capturas quedan vinculadas al vault de origen.
- Una nueva captura no sustituye a otra que siga procesándose.
- Los archivos se publican completos con una operación exclusiva, sin sobrescribir contenido previo.

## Reproducir

El servicio solo necesita Python estándar. Las pruebas de navegador utilizan Selenium 4.51.0 y geckodriver oficial 0.37.1.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/smoke_ai.py
.venv/bin/python tests/e2e_zen.py
.venv/bin/python tests/e2e_zen.py --ai
```

Las dos órdenes con IA consumen solicitudes con información ficticia. Las pruebas de navegador registran temporalmente el host de pruebas y restauran los manifiestos anteriores al terminar; no deben ejecutarse en paralelo ni mientras se usa la extensión para capturas personales.

`tests/e2e_zen.py` espera encontrar geckodriver en `.test-artifacts/bin/geckodriver`. Para preparar otro entorno de desarrollo, crea un venv, instala Selenium y descarga el binario desde las [publicaciones oficiales de Mozilla](https://github.com/mozilla/geckodriver/releases/tag/v0.37.1). La aplicación normal no utiliza esos componentes de automatización.

## Límites y validación pendiente

- Calidad y utilidad de los resúmenes sobre material elegido por el usuario.
- Relevancia de relaciones dentro de su vault real; la evidencia literal filtra invenciones, pero la utilidad semántica exige revisión.
- Captura en los sitios concretos del usuario y recursos autenticados.
- Comodidad del panel lateral en su configuración habitual de Zen.
- Resolución final de incrustaciones y apertura por URI en su Obsidian habitual.
- La latencia de Codex CLI es variable: algunas pruebas tardaron varios minutos. Hay un límite de 180 segundos por generación y la captura permanece pendiente si se supera.
- Esta entrega no incluye transcripción, análisis visual/OCR, aprendizaje de organización, enlaces automáticos, actualización de notas existentes ni distribución firmada permanente.

La guía de aceptación personal está en [PRUEBA.md](../PRUEBA.md).

## Corrección 0.1.1 — Permisos de imágenes

El usuario encontró `permissions.request may only be called from a user input handler` al capturar un artículo de Codrops con imágenes. La causa era un `await permissions.contains()` previo a `permissions.request()`: Firefox pierde la activación del usuario al esperar esa promesa. La versión 0.1.1 llama a `request()` directamente dentro del clic, sin preconsultas asíncronas. Los permisos ya concedidos se resuelven silenciosamente.

Las pruebas previas tenían concedido el host de imágenes y no cubrían el primer permiso. Se ha añadido una variante de integración que mantiene el artículo en `127.0.0.1` y sirve su imagen desde `localhost`, inicialmente sin autorizar. Comprueba que aparece la notificación real de permisos de Zen, la acepta dentro del perfil de prueba y completa la descarga, preparación y guardado de las tres notas.

- [Resultado con un host de imágenes sin autorizar](../.test-artifacts/zen-permissions/report.json).
- [Notificación real mostrada por Zen](../.test-artifacts/zen-permissions/permission-prompt.json).
- Cuatro pruebas de regresión JavaScript: permiso dentro del clic original, rechazo, captura sin imágenes/ya preparada y solicitud limitada a los hosts seleccionados.
- Las 17 pruebas del servicio siguen pasando.
- Se ha abierto el artículo real de Codrops en un Zen temporal y ejecutado el capturador: se recuperan 27.808 caracteres y se detectan tres imágenes. El aviso identifica que el vídeo incrustado no se ha transcrito. Esta comprobación valida la extracción de la página; la prueba del permiso y guardado completo usa los recursos ficticios anteriores. [Resultado de extracción](../.test-artifacts/noho-probe.json).

```bash
node --test tests/permissions.test.cjs
.venv/bin/python tests/e2e_zen.py --fresh-permissions
```

Referencia del comportamiento de Firefox: [acciones del usuario](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/User_actions) y [permissions.request](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/permissions/request).

## Versión 0.2.0 — Imágenes localizables y revisión en pestaña

El panel lateral se dedica a capturar y elegir imágenes. Sus filas tienen número, dimensiones y miniatura cuando el navegador permite obtenerla de la imagen ya cargada. Al pasar por una fila o enfocar su casilla, el artículo se desplaza a la imagen y muestra un marco amarillo. Al salir se elimina el marco sin cambiar los bordes o estilos originales de la página.

La propuesta se abre en `review.html?capture=<id>`, en una pestaña nueva vinculada a esa captura. La lectura utiliza Markdown renderizado y muestra los adjuntos locales, que se pueden ampliar. Las propiedades y las relaciones se revisan en una columna lateral dentro de esa página. El modo de edición conserva las últimas teclas incluso al recargar la revisión.

Operaciones verificadas en el perfil temporal de Zen:

- Guardar publica la nota y vuelve exactamente a la pestaña original, cerrando únicamente la revisión.
- Descartar retira la captura de pendientes sin crear una nota ni borrar notas ya guardadas, y vuelve a su origen.
- Volver al artículo conserva el borrador y permite reabrirlo desde el panel.
- Si se cierra la pestaña de origen, al terminar se abre de nuevo la URL de la captura.
- La identificación funciona con ratón y con foco de teclado; el estilo previo del artículo se conserva.
- La vista previa muestra imágenes mediante blobs locales; no vuelve a descargar sus URLs remotas.
- El renderizador muestra encabezados, énfasis, código y tablas. Se ha comprobado que elimina scripts, imágenes remotas insertadas en el Markdown y enlaces JavaScript.
- Se mantiene la prueba del diálogo real de permisos para un host todavía sin autorizar.

Las imágenes se transmiten desde el servicio al visor en fragmentos acotados para respetar el límite de Native Messaging. Las miniaturas tampoco se incluyen en el contexto de IA.

Pruebas locales actuales: **20 de Python y 4 de JavaScript superadas**, más el recorrido en Zen con permisos nuevos. La repetición completa con IA real también pasa: resumen, relación aceptada, edición, reapertura, imagen local y guardado con retorno al artículo. [Informe del recorrido con permisos](../.test-artifacts/zen-permissions/report.json), [informe con IA](../.test-artifacts/zen-ai/report.json) y [captura de la nueva revisión](../.test-artifacts/zen-ai/review.png).

El renderizado usa copias locales de [Marked](https://marked.js.org/) y [DOMPurify](https://github.com/cure53/DOMPurify), con versiones fijadas y licencias incluidas en el paquete.

## Versión 0.3.0 — PDF, vídeo y descripciones visuales

### Pruebas realizadas

**30 pruebas de Python y 7 de JavaScript superadas.** La ampliación cubre transferencia de archivos por fragmentos, rangos PDF, rechazo de una página de login presentada como PDF, extracción de texto con páginas, renderizado de documentos, parsing de SRT/VTT, deduplicación de subtítulos progresivos y conservación de las descripciones en Markdown. Las entradas de PDF, exploración de iframe y subtítulos comprueban además que los permisos se solicitan dentro del clic original, sin esperas previas.

La prueba real con `gpt-6.1-sol` recibe las dos páginas de un PDF sintético como imágenes adjuntas a Codex CLI. Resume el contenido y describe el diagrama: identifica los bloques Identidad azul → Política morada → Bucket S3 naranja. Las descripciones se guardan como pies, con el modelo real en la nota. También se ha comprobado que las imágenes se adjuntan mediante `--image`, sin incluir base64 como texto del prompt, y que la ausencia de descripciones no se presenta silenciosamente como éxito.

La transcripción real se ha ejecutado con Whisper base, en CPU, sobre la muestra de voz `jfk.flac` del repositorio oficial de OpenAI Whisper. Produce texto en inglés con marcas temporales. Se ha corregido una incompatibilidad de PyAV 19 con Faster Whisper fijando PyAV 16.1.0 en el entorno multimedia.

La prueba de integración en Zen 1.22.3b comprueba:

- PDF en el visor nativo, donde no se pueden inyectar scripts de contenido.
- Descarga con cookie de sesión de un PDF y de subtítulos desde un curso simulado.
- Extracción de dos páginas, revisión de sus imágenes y edición del pie antes del guardado.
- Exploración de una lección dentro de un iframe, de tipo Canvas/Moodle.
- Lectura de pistas de subtítulos de un vídeo HTML e importación de un archivo VTT usando el elemento de selección de archivos real.
- Importación de un MP4, transcripción local y extracción de fotogramas.
- Conservación del flujo anterior de artículos, frases, imágenes, resaltado y retorno desde la revisión.

Evidencias:

- [Resumen visual PDF y transcripción real](../.test-artifacts/media/result.json).
- [Recorrido multimedia en Zen](../.test-artifacts/zen-media/report.json).
- [Descarga de vídeo por URL, ASR y fotogramas](../.test-artifacts/media/url-result.json).

### Límites de esta evidencia

Los enlaces privados de AWS Academy/Canvas y Xunta facilitados por el usuario no son accesibles desde las herramientas del asistente, y no hay una superficie de navegador conectada que permita inspeccionar su sesión. Por tanto, la detección de sus visores y reproductores concretos está **pendiente de validación por el usuario**. El curso de prueba exige cookie, pero no reproduce todos los mecanismos de autenticación, cookies entre dominios, DRM o visores de esas plataformas.

Drive se detecta por su visor de archivo y se ofrece descarga con la sesión del navegador. No se ha validado un vídeo privado real de su cuenta. Si hay una confirmación de descarga, el recurso está protegido o no se expone el audio/subtítulo, la alternativa es importar el archivo descargado legítimamente desde la plataforma.

El análisis visual de PDF utiliza capturas de páginas completas como candidatas; todavía no segmenta automáticamente figuras vectoriales independientes. Si se limita el rango o queda contenido sin leer, la nota lo indica. Los vídeos con subtítulos se procesan como texto; los fotogramas se extraen de los archivos de vídeo accesibles, no del audio descargado sin pista de vídeo.

No se han creado notas de prueba en el vault personal. Los modelos visual y de texto siguen usando la sesión de Codex; el audio se procesa localmente. Referencias técnicas: [imágenes en Codex CLI](https://learn.chatgpt.com/docs/cli/reference), [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) y [yt-dlp](https://github.com/yt-dlp/yt-dlp).

Para reproducir las pruebas:

```bash
python3 -m unittest discover -s tests -v
npm test
.venv/bin/python tests/e2e_zen.py --media
python3 scripts/smoke_media.py --vision --audio .test-artifacts/jfk.flac
```

La prueba del PDF requiere Ghostscript para generar el documento sintético; la extracción de documentos reales utiliza Poppler. La última orden consume una solicitud de IA con contenido de prueba. El audio de ejemplo y el modelo ASR se prepararon durante el desarrollo; la aplicación descarga el modelo local si no existe.

## Versión 0.3.1 — Aprovechar HTML antes de usar visión

La captura recoge por separado `figcaption`, `aria-describedby`, `alt`, `aria-label` y `title`. El servicio prioriza un pie explícito y las descripciones suficientemente informativas, descarta etiquetas genéricas y trata los nombres de archivo descriptivos como pistas etiquetadas. Nunca convierte un hash o `image-01.png` en una descripción inventada.

En automático, los metadatos útiles evitan adjuntar esa imagen. Una captura mixta envía solo los índices que necesitan visión; si ninguno la necesita, utiliza `gpt-6-luna` en lugar del modelo visual. Las descripciones visuales de imágenes de artículos se reutilizan por SHA-256. No se usa esa caché para sustituir la lectura del contenido de otras páginas PDF o fotogramas.

**39 pruebas de Python y 7 de JavaScript superadas.** Las nueve nuevas verifican la prioridad del HTML, los fallbacks accesibles, rechazo de etiquetas genéricas, nombres claros frente a hashes, ausencia de adjuntos y uso del modelo ligero, envío de una sola imagen en una captura mixta, reutilización de caché y modos automático/sin visión/forzado. Se inspeccionan los argumentos reales que recibiría Codex sin consumir nuevas solicitudes de IA.

El recorrido en Zen confirma que la captura distingue el `alt` y el `figcaption`, conserva el pie visible en el Markdown y muestra «Pie original del HTML» en la revisión. [Informe](../.test-artifacts/zen-permissions/report.json).

La opción automática es el nuevo valor predeterminado. Los PDF y fotogramas conservan la lectura visual de contenido en ese modo; el usuario puede desactivarla. Los textos genéricos como «Página 2 del PDF» no se confunden con una lectura del documento.

En esta configuración, Codex está autenticado con ChatGPT y utiliza su cuota. No se ha añadido una API de pago independiente. Los precios por token de la API no equivalen a un precio por captura dentro de una suscripción: [documentación de planes](https://learn.chatgpt.com/docs/pricing). Los inputs visuales consumen tokens: [imágenes y visión](https://developers.openai.com/api/docs/guides/images-vision).

## Versión 0.3.2 — Detección del vault y ruta manual

Opciones permite elegir detección automática o ruta manual. La búsqueda consulta el registro de Obsidian, incluidos XDG y Flatpak, y comprueba marcadores en ubicaciones habituales con límites de profundidad y número de entradas. No lee el contenido de las notas ni utiliza IA. Los resultados incluyen ruta y origen; si hay varios, se puede elegir cuál utilizar. El destino solo se aplica al guardar las opciones y no cambia por encontrar otro vault.

Las configuraciones anteriores conservan su ruta y se interpretan como manuales. La pantalla carga mediante una consulta independiente del estado de captura, de modo que una carpeta movida no impide corregir la ruta. Una ruta inexistente muestra un error y conserva el último archivo de configuración válido.

**50 pruebas de Python y 7 de JavaScript superadas.** Las once nuevas de Python cubren registros válidos, corruptos y obsoletos, XDG/Flatpak, varias ubicaciones, marcadores, límites de profundidad, deduplicación de enlaces simbólicos, rutas con `~`, compatibilidad con configuraciones anteriores, consulta de opciones sin vault y conservación del destino tras una búsqueda.

La prueba con Zen 1.22.3b instala la extensión y el servicio reales en un perfil temporal. Comprueba selección automática persistida, edición manual, rechazo de una ruta inexistente y recuperación cuando la ruta guardada ya no existe. Después completa el recorrido habitual de artículo, frase e imagen hasta revisión y guardado. Todos los guardados utilizan un vault ficticio. La búsqueda detectó además `/home/samuh/Second_Brain` mediante el registro real de Obsidian.

- [Resultado de Opciones](../.test-artifacts/zen-options/options-report.json).
- [Captura de Opciones](../.test-artifacts/zen-options/options.png).
- [Recorrido de captura y guardado](../.test-artifacts/zen-options/report.json).

```bash
python3 -m unittest discover -s tests -q
npm test
.venv/bin/python tests/e2e_zen.py --options
```

## Versión 0.7.3 — Vault seleccionado y vault aplicado

El servicio conservaba una ruta antigua inexistente, mientras que la detección mostraba el vault nuevo sin haber aplicado todavía la selección. Además, guardar podía no actualizar el panel si los campos de captura que se limpiaban ya estaban vacíos.

- Se añade **Guardar y volver** a la barra superior, con validación del formulario antes de salir.
- La selección de un vault diferente indica que aún no está en uso y cómo aplicarlo.
- Cada guardado emite una revisión de configuración independiente del estado de captura. Los paneles abiertos consultan de nuevo el servicio y retiran el error de conexión anterior cuando se recupera, conservando otros errores que sigan siendo pertinentes.
- Se ha actualizado la configuración local al vault nuevo registrado en Obsidian. La consulta de estado real responde correctamente y encuentra nueve carpetas de destino; no se han escrito notas en ese vault para probarlo.

**39 pruebas JavaScript y recorrido real en Zen 1.22.3b superados.** La nueva regresión deja un panel abierto con una ruta inexistente, detecta un vault ficticio mediante un registro XDG aislado, comprueba que la selección aún no modifica el servicio y pulsa Guardar y volver. Se verifica la ruta aplicada, la reconexión del panel y la retirada del error, sin recargarlo. También pasan los recorridos anteriores de Opciones, artículo, frase e imagen.

Evidencias: [Opciones y cambio de vault](../.test-artifacts/zen-options/options-report.json) y [captura y guardado](../.test-artifacts/zen-options/report.json).

## Versión 0.8.0 — Organización elegible y código de consulta

El usuario informa de una división poco predecible y de la omisión de snippets en un tutorial de Codrops. Aclara que el código debe seleccionarse por su utilidad didáctica y de consulta, sin obligación ni cuota.

### Cambios

- **Una nota con apartados** es el valor predeterminado. El panel permite elegir **Varias notas enlazadas por temas** o **Automático** antes de preparar. Opciones guarda el valor predeterminado. La elección se transmite también desde la extracción automática de PDF, libros, subtítulos y archivos; se conserva en el trabajo para los reintentos.
- El servicio valida las elecciones. En una nota, si el modelo devuelve derivadas pese a la instrucción, verifica primero sus referencias y reúne sus apartados, código, páginas, tags y relaciones en la nota principal. No descarta el contenido de esas derivadas.
- El contrato editorial `editorial-v3` pide síntesis técnica, selección de fragmentos literales que enseñen mecanismos y explicación de contexto, parámetros y límites. Evita copiar cada ejemplo o inventar código donde no lo hay. La división y la presencia de snippets son criterios independientes.
- El conversor HTML conserva el lenguaje del bloque y sus líneas en blanco, usa delimitadores suficientemente largos cuando el código contiene backticks y conserva el texto literal del código en línea.

Se usan instrucciones explícitas, ejemplos representativos y pruebas sobre las salidas siguiendo la [documentación oficial de OpenAI sobre prompts](https://developers.openai.com/api/docs/guides/prompt-engineering). Se conserva el modelo de texto configurado, sin migración de modelo.

### Pruebas

**91 pruebas Python y 39 JavaScript superadas.** Las cinco regresiones nuevas cubren el valor predeterminado, la reunión sin pérdida cuando el modelo divide indebidamente, la prioridad de la elección por captura, su recuperación tras una interrupción, el modo automático y el rechazo de valores o páginas no válidos. Las pruebas anteriores de colecciones solicitan ahora división expresamente.

Se descargó con un perfil aislado de Zen el [artículo público indicado por el usuario](https://tympanus.net/codrops/2026/10/13/scroll-driven-ghost-trails/). La prueba de captura sirve ese HTML desde localhost sin los medios externos. Comprueba que sus **17 bloques** llegan literalmente a la captura y al borrador manual, además de un caso sintético con backticks anidados, saltos de línea múltiples, lenguaje y código en línea. La selección del panel llega al servicio y el predeterminado es una nota.

La prueba con **IA real (`gpt-6-luna`)** sobre esa captura obtuvo:

| Elección / fuente | Notas | Fragmentos seleccionados | Resultado |
| --- | --- | --- | --- |
| Una nota / tutorial real | 1 | 4 | Todos literales de la fuente |
| Varias notas / tutorial real | 5: síntesis y 4 temas | 8 | Todos literales de la fuente |
| Una nota / fuente ficticia sin código | 1 | 0 | No añade código inventado |

Una primera prueba conservó los 17 ejemplos en una sola nota. Se acotó el criterio para priorizar mecanismos centrales y describir el cableado auxiliar en prosa; la repetición pasó la selección y la fidelidad. Los recuentos son resultados de estas pruebas, **no cuotas impuestas**. Los ejemplos se han inspeccionado: incluyen explicaciones antes y después de los fragmentos. La valoración didáctica final corresponde al usuario; las comprobaciones automáticas validan estructura y literalidad.

También pasan en Zen los recorridos de Opciones y cambio de vault; artículo, frase e imagen; revisión por apartados; integración; ampliaciones aprobadas; cancelación y recuperación; y revisión automática tras extracción. Todas las notas de prueba permanecen en vaults ficticios. Se ha restaurado la instalación personal con el vault nuevo.

Evidencias: [captura de código](../.test-artifacts/zen-code/report.json), [evaluación de código y organización](../.test-artifacts/code-notes-eval/report.json), [ejemplo de una nota](../.test-artifacts/code-notes-eval/single/source.md), [síntesis enlazada](../.test-artifacts/code-notes-eval/linked/source.md) y [regresión del flujo](../.test-artifacts/zen-workflow/report.json).

```bash
npm test
python3 -m unittest discover -s tests -q
.venv/bin/python scripts/cache_codrops_fixture.py
.venv/bin/python tests/e2e_zen.py --code
python3 scripts/smoke_code_notes.py --ai
.venv/bin/python tests/e2e_zen.py --options
.venv/bin/python tests/e2e_zen.py --workflow
python3 scripts/install.py
```

Los recorridos de navegador se ejecutan secuencialmente; la prueba `--ai` consume solicitudes de la sesión existente y usa el artículo público y una fuente ficticia.

## Versión 0.8.1 — Progreso sin desbordamiento y selector de vista en el documento

Se reproduce un desbordamiento horizontal durante el trabajo al mostrar nombres largos de recursos o motores: en una ventana con 289 px útiles, el documento llegaba a 4037 px de ancho. La tarjeta de progreso ahora limita su ancho, ajusta el texto de fase, operación y motor, y reparte cabecera y tiempo mediante columnas que pueden contraerse. El panel impide además el desplazamiento horizontal de su página.

El selector **Lectura / Editar Markdown** deja de ser sticky. Conserva su posición dentro del documento encima de la nota y sale de la vista al bajar. Se ajusta el margen de navegación de los controles al espacio de la cabecera general, sin reservar la altura de la antigua barra flotante.

### Comprobaciones en Zen 1.22.3b

- **32 estados de progreso**: ocho fases o tipos de mensaje en viewports exactos de **200, 240, 300 y 360 px**, con anchos útiles medidos de 188, 228, 288 y 348 px. Se incluyen un título sin espacios, un contador de más de cien horas y nombres de recurso y motor extensos. En todos los casos, el ancho desplazable del documento coincide con su ancho útil.
- Los rectángulos de las líneas de texto de fase, operación, motor y ayuda permanecen dentro de sus cajas: se comprueba el ajuste del texto además de la ausencia de barra horizontal.
- Se usa el panel real en un iframe de la propia extensión para fijar el viewport, porque Zen puede limitar el tamaño mínimo de su ventana nativa. No se sustituye el DOM del panel ni se inyectan estilos de corrección en las pruebas.
- El recorrido de revisión comprueba que el selector tenga posición estática, conserve su coordenada dentro del documento y salga de la pantalla tras hacer scroll. También pasan edición, deshacer, integración, ampliación aprobada de notas, cancelación, recuperación y revisión automática.
- La regresión de galería conserva 24 imágenes enumeradas, scroll vertical propio, límite de ocho seleccionadas y disponibilidad de imágenes posteriores. Se inspeccionan las capturas del progreso y de la revisión desplazada.

Evidencias: [resultado del panel](../.test-artifacts/zen-quality/report.json), [mediciones de progreso](../.test-artifacts/zen-quality/busy-layout.json), [progreso](../.test-artifacts/zen-quality/progress.png), [revisión desplazada](../.test-artifacts/zen-workflow/toolbar-scrolled.png) y [resultado de revisión](../.test-artifacts/zen-workflow/report.json).

```bash
.venv/bin/python tests/e2e_zen.py --quality
.venv/bin/python tests/e2e_zen.py --workflow
python3 scripts/install.py
```

Los recorridos se ejecutan secuencialmente con perfiles y vaults ficticios. No se requieren nuevas solicitudes de IA para estas correcciones de presentación. Se restaura la configuración personal al instalar la entrega.

## Versión 0.8.2 — Sugerencia de división desde la revisión

Se añade **Proponer división en notas** junto al selector de lectura y edición. La acción trabaja sobre la nota activa y sus ediciones, tanto en una propuesta de una nota como sobre un tema de una colección. Muestra el motivo, la síntesis para la nota actual y los títulos, propósitos y cuerpos de las notas propuestas. Cada cuerpo se puede desplegar antes de aceptar.

### Comportamiento

- Solicitar una sugerencia conserva la captura nativa y el borrador actual. **Conservar la nota actual** elimina la sugerencia y no modifica el contenido. También se puede recomendar no dividir si falta una separación útil.
- La IA propone agrupaciones de bloques, no reescribe los cuerpos derivados. El servicio verifica que cada bloque aparezca exactamente una vez. La segmentación reconoce encabezados fuera de los bloques de código y conserva todos los caracteres de los apartados, incluidas anotaciones personales y delimitadores.
- Solo **Aplicar división al borrador** cambia la propuesta nativa. Conserva las ediciones de título, destino y resto de notas; asigna las imágenes sugeridas y transporta sus pies editados. Después vuelve a la revisión, con enlaces entre la síntesis y los temas. El guardado en el vault sigue siendo una acción posterior.
- La aceptación compara la propuesta con el borrador y las ediciones sobre los que se calculó. Si han cambiado, rechaza aplicar la sugerencia para conservar el trabajo más reciente. Las sugerencias tienen identidad por captura y vault, y caducan para su aceptación tras 24 horas.
- Los cuerpos, índices de imágenes, tipos y rutas se validan antes de aplicar. La preparación usa el modelo de texto y admite cancelación mediante el mecanismo existente de trabajos.

### Evidencia

**101 pruebas Python y 39 JavaScript superadas.** Diez casos nuevos comprueban la segmentación con backticks y encabezados dentro del código; propuesta y descarte sin cambios; aceptación explícita; código, anotaciones y enlaces; bloques omitidos, repetidos o desconocidos; borradores y ediciones desactualizados; recomendación de no dividir; identidad de captura; imágenes y pies editados; y división de una nota temática conservando las otras notas y sus ediciones.

El nuevo recorrido en **Zen 1.22.3b** crea una nota, añade un comentario personal y solicita una sugerencia. Comprueba que aún no cambia el borrador; la descarta y verifica sus ediciones; solicita otra, la acepta, recarga la revisión y guarda tres notas enlazadas. Comprueba que el código y el comentario se conservan y que no se escriben notas antes del guardado final. También vuelve a pasar el recorrido anterior de edición parcial, deshacer, integración, ampliaciones aprobadas, cancelación, recuperación y revisión automática, incluido el selector de vista que no sigue el scroll.

La prueba con **IA real (`gpt-6-luna`)** sobre la nota del tutorial de Codrops propone **dos temas**: estelas tipográficas con Canvas y GSAP, y revelaciones de imágenes con Three.js. Se verifican el borrador intacto antes de aceptar y la presencia de todos los bloques editados exactamente una vez, incluidos los cuatro snippets originales de esa nota y una anotación ficticia. Tras la aceptación de prueba se guardan tres notas en un vault ficticio. La utilidad concreta de esa agrupación queda disponible para revisión personal.

Evidencias: [recorrido en Zen](../.test-artifacts/zen-split-review/report.json), [sugerencia visible](../.test-artifacts/zen-split-review/suggestion.png), [prueba con IA real](../.test-artifacts/split-review-ai/report.json), [propuesta completa](../.test-artifacts/split-review-ai/suggestion.json), [síntesis resultante](../.test-artifacts/split-review-ai/source.md) y [regresión del flujo anterior](../.test-artifacts/zen-workflow/report.json).

```bash
npm test
python3 -m unittest discover -s tests -q
.venv/bin/python tests/e2e_zen.py --split-review
python3 scripts/smoke_split_review.py --ai
.venv/bin/python tests/e2e_zen.py --workflow
python3 scripts/install.py
```

Los recorridos de navegador se ejecutan secuencialmente. La prueba con IA usa la nota pública generada en la validación de 0.8.0 y una anotación ficticia. Todos los archivos de prueba permanecen fuera del vault personal; la instalación final conserva el vault y la configuración del usuario.

## Versión 0.9.0 — Conexiones por tema y asistente lateral

### Problema y corrección

La búsqueda encontraba las notas de GSAP del usuario, pero la división creaba derivadas con `relations=[]` y solo un enlace al padre. Además, validar las conexiones contra citas libres de la captura original rechazaba extractos que el modelo había parafraseado o tomado de un resumen en español.

- La búsqueda adicional usa cada nota temática y sus ediciones para recuperar candidatas. La IA propone conexiones mediante identificadores de extractos; el servicio incorpora después las citas literales de ambos textos. Se distinguen evidencias de la nota revisada y de la captura original.
- Las propuestas enlazan con notas existentes y con otros temas de la misma colección. Los vínculos temáticos se representan en ambas direcciones y se pueden descartar; las notas excluidas no producen enlaces colgantes. La búsqueda prioriza conexiones concretas y acota la cantidad de sugerencias nuevas.
- Al dividir se heredan las conexiones cuya evidencia sigue presente y las selecciones aceptadas que corresponden. Tras aceptar una división se vuelve a buscar por los nuevos temas. **Buscar conexiones** permite repetir la operación sin regenerar cuerpos, código, títulos o anotaciones.
- Los destinos y su evidencia se comprueban al guardar. Una edición que invalida un extracto obliga a revisar la conexión; las relaciones desactualizadas pueden retirarse en la siguiente búsqueda. Se conservan decisiones de selección y descarte que siguen siendo válidas. Una captura manual no se marca como asistida solo por recibir propuestas no utilizadas; sí se atribuye el uso efectivo de conexiones generadas.
- La respuesta de revisión evita duplicar la captura completa y los borradores, reduciendo el tamaño transportado cuando hay varias notas y muchas evidencias.

### Asistente de revisión

El panel lateral cambia de funciones mientras exista una revisión abierta en su ventana. Muestra las notas y sus contadores de conexiones, permite recorrerlas, incluirlas o excluirlas, alternar lectura y edición, acceder a propiedades y conexiones, repetir la búsqueda, proponer una división y guardar la selección. La lista tiene scroll propio para propuestas largas.

Las acciones se dirigen a la instancia concreta de revisión y a su ventana. Si hay varias, el selector sigue la revisión enfocada y permite volver a otra. El modo permanece al visitar otro artículo y termina al cerrar la revisión, incluso manualmente. Las ediciones se conservan al reabrir. El icono y el atajo evitan intentar capturar la página interna de revisión cuando se abre el panel de ayuda.

### Pruebas

**106 pruebas Python y 41 JavaScript superadas.** Las nuevas regresiones comprueban relaciones basadas en la nota traducida frente a una captura en inglés, evidencia literal de ambos lados, identidad de candidatas, enlaces temáticos recíprocos, descarte, exclusión de notas, invalidación tras editar y recuperación mediante nueva búsqueda. Los casos del coordinador verifican el aislamiento por ventana, el destino de los comandos por instancia y la limpieza al cerrar la pestaña.

El nuevo recorrido en **Zen 1.22.3b** comprueba:

- Sustitución de las opciones de captura por el asistente de revisión.
- Navegación y edición desde el menú, selección sincronizada y conservación de comentarios.
- Propuestas externas por tema y enlaces entre temas en ambos sentidos.
- Panel real en un iframe de **240 px**, sin desbordamiento horizontal.
- Dos revisiones simultáneas: seguimiento del foco y selección de la revisión que se controla.
- Persistencia del modo al cambiar de artículo, salida al cerrar manualmente, reapertura con las ediciones y guardado de tres notas desde el propio menú.

También pasan los recorridos de división sugerida, revisión y ampliaciones, cancelación y recuperación, importación local, 32 estados de progreso en paneles estrechos y ventanas que no heredan el panel ni pierden el foco.

### IA real y vault del usuario

La comprobación con `gpt-6-luna` sobre un vault ficticio con notas de GSAP, estado/renderizado y una mención de noticias produjo cinco propuestas externas y cuatro pares temáticos. No enlazó la mención de noticias sin contenido técnico útil.

En una comprobación de **solo lectura** sobre la propuesta actual de Codrops y las candidatas reales del usuario, se obtuvieron ocho propuestas externas, **cuatro de ellas con tres notas de GSAP**, y **tres pares entre los temas nuevos**. Se verificó que el borrador real permanecía idéntico; no se escribieron notas en el vault personal. Los recuentos describen estas ejecuciones y no son cuotas ni garantías para otras fuentes. Las razones y los extractos siguen disponibles para la validación del usuario.

Evidencias: [asistente de revisión](../.test-artifacts/zen-review-menu/report.json), [menú](../.test-artifacts/zen-review-menu/menu.png), [IA con datos ficticios](../.test-artifacts/connections-ai/report.json), [IA en modo lectura con candidatas reales](../.test-artifacts/real-connections/report.json), [progreso estrecho](../.test-artifacts/zen-quality/report.json) y [ventanas y foco](../.test-artifacts/zen-windows/report.json).

```bash
npm test
python3 -m unittest discover -s tests -q
.venv/bin/python tests/e2e_zen.py --review-menu
.venv/bin/python tests/e2e_zen.py --split-review
.venv/bin/python tests/e2e_zen.py --workflow
.venv/bin/python tests/e2e_zen.py --quality
.venv/bin/python tests/e2e_zen.py --windows
.venv/bin/python tests/e2e_zen.py --manual-import
python3 scripts/smoke_connections.py --ai
python3 scripts/smoke_connections.py --ai --real-vault
python3 scripts/install.py
```

Los recorridos de navegador se ejecutan secuencialmente. Las solicitudes con `--ai` usan la sesión existente; `--real-vault` está reservado para una comprobación autorizada de la propuesta del usuario y sus candidatas, sin guardar cambios. La instalación final restaura el servicio y la configuración personales.

La búsqueda limitada puede omitir vaults fuera del registro y de las ubicaciones habituales; se ofrece la ruta manual para esos casos. No se ha vuelto a consumir IA en estas pruebas porque el cambio afecta únicamente a la configuración del destino.

## Versión 0.4.0 — Pestaña actual y detección de cursos

### Cambios y comprobaciones

El panel escucha activación y navegación de pestañas, actualiza su contexto y agrupa detecciones concurrentes de la misma página. Una respuesta que llega tarde no sustituye a una pestaña más reciente. Los borradores y los resultados de trabajos en curso se conservan por origen; la detección puede cambiar mientras se procesa otro recurso. Las acciones de preparación y extracción comprueban que siguen correspondiendo a la captura seleccionada.

Se retiran el botón permanente «Capturar PDF de esta pestaña» y el importador general del panel habitual. Se muestran los controles correspondientes a documentos o medios detectados. Una página vacía, un login, un reproductor sin fuente accesible y un visor autorizado pero ilegible tienen mensajes distintos. La importación deliberada de archivos sigue disponible desde Opciones, en una pestaña propia; los PDF locales detectados también muestran su selector.

La lectura de marcos utiliza `webNavigation.getAllFrames` e inyecciones por `frameId`. El fallo de un dominio se trata individualmente. Los marcos pendientes de permiso presentan una única acción para autorizar y volver a detectar; no se pide repetidamente el mismo permiso para un visor ya autorizado pero inaccesible. Las imágenes conservan el marco donde pueden localizarse y los subtítulos se intentan leer primero desde el contexto del reproductor, respetando su referencia y partición de sesión. Si los subtítulos fallan y existe una fuente de audio compatible ya autorizada, se intenta la transcripción.

Los visores PDF sin extensión se comprueban mediante MIME, tanto en la pestaña como en marcos. Se evita interpretar cualquier botón de descarga como PDF. Para reproductores `blob:` se consultan los recursos multimedia que ya cargó el marco y se vuelve a detectar ante cambios en vídeo, pistas o visores. HLS terminado y sin cifrar se descarga en el navegador con su sesión, con límite de tamaño y duración, y se transcribe mediante Whisper. No se exportan cookies ni se entrega la sesión del curso a `yt-dlp`. Los subtítulos y el contenido se siguen revisando antes de generar una nota.

**50 pruebas de Python y 20 de JavaScript superadas.** Las pruebas de JavaScript cubren marcos anidados, conservación de imágenes por marco, fallos de acceso, detecciones sin contenido, respuestas fuera de orden, trabajos en segundo plano, rechazo de acciones pertenecientes a otra pestaña, fallbacks desde subtítulos rechazados y parsing/descarga de HLS con límites. Se mantienen las regresiones de permisos dentro del clic original.

### Integración en Zen

El recorrido utiliza Zen 1.22.3b, una extensión instalada en un perfil temporal y el servicio nativo real con un vault ficticio. Se comprueban:

- Cambios PDF → artículo → página vacía → vídeo sin fuente, con controles correspondientes a cada página.
- PDF servido con sesión y MIME `application/pdf` desde una URL de descarga sin extensión.
- Dos niveles de marcos de un curso, incluido otro dominio que necesita una notificación real de permiso.
- Lectura de pistas VTT con la sesión iniciada en el proveedor incrustado.
- Detección de un reproductor dinámico, recuperación de HLS con cookie y transcripción real con Whisper.
- Importación manual separada, lectura de VTT local y preparación/revisión/descarte con retorno a su origen.
- Conservación del recorrido de artículos, frases e imágenes, resaltado, Markdown revisable y guardado en el vault ficticio.

Evidencias:

- [Detección, cursos anidados y HLS](../.test-artifacts/zen-detection/report.json).
- [Importación manual y revisión](../.test-artifacts/zen-import/report.json).
- [Página sin contenido: error y controles ocultos](../.test-artifacts/zen-detection/empty.png).
- [Reproductor de un curso anidado](../.test-artifacts/zen-detection/nested-video.png).

```bash
python3 -m unittest discover -s tests -q
npm test
.venv/bin/python tests/e2e_zen.py --detection
.venv/bin/python tests/e2e_zen.py --manual-import
.venv/bin/python tests/e2e_zen.py --media
```

Los perfiles de prueba registran el servicio temporalmente y restauran los manifiestos al terminar; estos recorridos no deben ejecutarse a la vez. Las pruebas de vídeo requieren las herramientas multimedia, la muestra de voz y Whisper preparados en este entorno. No consumen solicitudes nuevas de IA generativa.

### Límites de la validación

**No se ha podido abrir la sesión privada de AWS Academy o Xunta del usuario.** La herramienta de navegador conectada no expone pestañas y los enlaces no ofrecen aquí el contenido autenticado. Las pruebas anteriores reproducen mecanismos de esas plataformas, pero no confirman su visor concreto. El panel ofrece un diagnóstico con dominios y recuentos para identificar el punto de fallo; no incluye cookies, texto de notas ni parámetros de URLs firmadas.

HLS no admite directos, cifrado, rangos de segmentos ni todos los esquemas con pistas separadas. DASH tampoco tiene descarga privada mediante la sesión del navegador. Un dominio adicional de segmentos o un servidor que exija autenticación distinta puede rechazar la descarga; se informa del fallo. La búsqueda de recursos de `blob:` reconoce URLs de medios comunes ya cargados, no descifra un reproductor protegido.

Se añaden los permisos `tabs` para identificar la pestaña seleccionada y `webNavigation` para enumerar marcos. El acceso al contenido continúa limitado a `activeTab` y a los dominios opcionales concedidos. Referencia: [enumeración de marcos de Firefox](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webNavigation/getAllFrames).

## Versión 0.4.1 — Copiar errores y diagnóstico

Se añade un botón pequeño junto al error y otro dentro del diagnóstico. Copian el error visible, el diagnóstico disponible y la versión, con confirmación «Copiado ✓». El error original se conserva. Si falla el portapapeles, aparece un campo de texto con el contenido ya seleccionado para pulsar Ctrl+C.

La prueba en Zen 1.22.3b pulsa los botones reales, lee el portapapeles y comprueba el mensaje y diagnóstico copiados. Simula también un portapapeles rechazado y verifica la selección del campo alternativo y la conservación del error. El botón del error desaparece cuando se oculta el aviso. Las 20 regresiones JavaScript siguen pasando.

La copia entregada no necesita permisos adicionales. Solo el paquete de pruebas recibe `clipboardRead` para verificar el contenido que acaba de escribir; ese permiso no forma parte de la extensión distribuida.

- [Resultado de copia](../.test-artifacts/zen-copy-error/report.json).
- [Botón de copia en un panel estrecho](../.test-artifacts/zen-copy-error/copy-error.png).

```bash
.venv/bin/python tests/e2e_zen.py --copy-error
```

## Versión 0.4.2 — Lectores de libros y redirecciones de marcos

El diagnóstico real de AWS Academy mostró ocho marcos leídos, texto marcado como legible, ningún PDF ni vídeo detectado y acceso pendiente a `emergingtalent.contentcontroller.com`, pese a que ese dominio también aparecía entre los leídos. El usuario aclaró que se trata de un libro con scroll dentro de un visor. Este dato no prueba el formato del documento, pero exige distinguir una lección HTML de un PDF renderizado y del texto del contenedor.

La lectura de marcos pasa a usar el árbol de navegación vivo como autoridad de acceso. Una dirección `src` antigua después de redirigir no genera por sí sola un permiso pendiente. Se excluyen marcos identificados de autenticación y contenedores, y se evita repetir texto de ancestros cuando hay contenido en sus hijos. El diagnóstico añade rol, número de caracteres, imágenes, tipo de documento y superficies por marco, sin copiar el texto ni parámetros de direcciones.

La captura añade páginas de `canvas`, SVG y fondos CSS, con el marco y elemento de origen para su localización. Solo se rasterizan superficies que el navegador permite leer. Para SVG se crea la imagen dentro del documento y se solicita lectura anónima: la prueba detectó y corrigió un `SecurityError` que se producía al dibujar una imagen creada desde el contexto aislado de la extensión. Se mantienen límites de tamaño y número de candidatas, que se anuncian en el panel y en la nota. El texto de páginas cargadas debajo de la pantalla se incluye; las páginas ocultas por CSS se excluyen.

Los recursos de red con URL PDF y el parámetro de archivo de un visor PDF.js permiten recuperar el documento original aunque no haya enlace visible. Cuando se reconoce esa fuente en PDF.js se ofrece la extracción del PDF en lugar de preparar imágenes parciales como si fueran todo el documento.

**51 pruebas de Python y 23 de JavaScript superadas.** Las nuevas regresiones cubren autenticación/contendores de AWS, selección de texto útil frente a SSO, relación padre/hijo y el análisis visual de páginas dibujadas aunque tengan una etiqueta HTML. Los modos sin visión siguen respetándose.

El recorrido real en Zen 1.22.3b utiliza un libro ficticio en otro dominio, con una redirección de lanzamiento y dos niveles de iframe. Comprueba:

- Permiso inicial para el proveedor, sin volver a solicitarlo por la dirección previa a la redirección.
- Captura y guardado de canvas, SVG y fondo PNG como adjuntos locales.
- Texto de otra página cargada a más de 1.400 píxeles bajo la pantalla y exclusión de una página oculta.
- Aviso explícito de límite en un lector de diez superficies gráficas.
- Detección de un PDF descargado por un visor HTML sin enlace y extracción de sus dos páginas desde el documento original.
- Revisión y guardado manual en un vault ficticio. No se han creado notas de prueba en el vault personal ni se han consumido nuevas solicitudes de IA generativa.

Se repite además el recorrido de artículo, frase e imagen para comprobar la extracción y el retorno desde revisión.

- [Informe del lector](../.test-artifacts/zen-reader/report.json).
- [Pantalla del lector](../.test-artifacts/zen-reader/reader.png).
- [Recorrido de captura anterior](../.test-artifacts/zen/report.json).

```bash
python3 -m unittest discover -s tests -q
npm test
.venv/bin/python tests/e2e_zen.py --reader
.venv/bin/python tests/e2e_zen.py
```

No se ha inspeccionado aún el libro privado real de AWS: el diagnóstico nuevo y la prueba del usuario siguen siendo necesarios para confirmar su estructura. Tampoco se afirma cobertura completa de un libro virtualizado; solo se recupera lo que está cargado o el PDF original cuando puede identificarse. No se navega ni se cambia el progreso del curso automáticamente. La documentación de [Content Controller](https://docs.contentcontroller.com/integration/features/launcher-links/) describe un reproductor de contenido en paquetes de lanzamiento; por eso no se presupone que una página de ese proveedor sea un PDF o un vídeo.

## Versión 0.5.0 — Libros completos, separados de sus figuras

El usuario detectó parpadeo y recaptura del lector, además de un resultado incompleto al tratar un libro de 55 páginas como ocho imágenes sueltas. El nuevo flujo separa enumeración, extracción, lectura y selección de figuras.

### Comportamiento

- La detección del lector enumera sus páginas sin rasterizar y almacenar repetidamente imágenes grandes en el panel. Los cambios de estilo ya no recapturan un libro existente ni vacían su tarjeta. La nueva extracción utiliza una instantánea del lector.
- **Extraer libro completo** recorre las páginas localizables y las transmite una a una en fragmentos de hasta 393.216 bytes. El servicio guarda cada página antes de pasar a la siguiente y muestra progreso. Restaura las posiciones de scroll al terminar.
- Cada página conserva su texto HTML; se aplica Tesseract local cuando el texto es insuficiente. Los dibujos de canvas esperan a estar pintados o indican el fallo en vez de aceptar una captura vacía. Si falta una página, el servicio rechaza el cierre del libro como completo.
- Los datos y avances se guardan en un trabajo vinculado al vault. Un reintento de la misma instantánea reutiliza páginas recibidas. Una instantánea cambiada o un trabajo de otro vault se rechazan.
- Al preparar con IA se leen **todas** las páginas en lotes, de seis por defecto, y después se sintetiza el conjunto. Los resultados de lotes completos se conservan con una clave que incluye páginas, modelos, política de visión, intención y perfil. La síntesis final no recibe solamente las primeras páginas.
- Las figuras candidatas para la nota se gestionan aparte. La selección o desmarcado de esas figuras no reduce las páginas leídas. Los modelos realmente utilizados constan en el método de la nota.
- El protocolo nativo admite progreso durante la lectura larga sin resolver prematuramente la solicitud. Las imágenes originales permanecen en el trabajo local; no se envían 55 imágenes juntas en un mensaje al panel.

### Pruebas

**56 pruebas Python y 24 JavaScript superadas.** Las nuevas cubren ingestión de 55 páginas, conservación de la 55, diez lotes completos antes de la síntesis, reutilización de lotes, reanudación tras faltar una página, persistencia tras fallo del tercer lote, aislamiento entre vaults, rechazo de fragmentos corruptos y estabilidad de una captura ante cambios automáticos de estilos.

Los recorridos con Zen 1.22.3b y un vault ficticio comprueban:

- Libro de 55 páginas con texto y dibujos: 55 detectadas, 55 transferidas, última página presente en la nota, panel estable durante veinte cambios de estilo y scroll restaurado.
- Libro de 55 páginas **solo gráficas**, con OCR real: recuperación del texto hasta «UNIQUE PAGE 55», revisión y guardado.
- Ese mismo recorrido con un CLI determinista de pruebas: diez solicitudes de lectura que contienen las páginas 1–55, **55 imágenes adjuntadas entre los lotes**, una síntesis final y mensajes de progreso nativos hasta el último lote. Este CLI no se instala en el servicio personal ni consume solicitudes de IA.
- Lector entre dominios con redirección, SVG, canvas, fondo PNG, texto bajo la pantalla y extracción del PDF original oculto: se mantiene el recorrido con el nuevo botón de extracción.
- Artículo, frase e imagen: se mantiene la preparación, revisión, adjuntos, resaltado y retorno al origen.

Una prueba aparte utiliza **los modelos reales `gpt-6.1-sol` y `gpt-6-luna`** con tres páginas gráficas ficticias. Completa la lectura visual y sus pies, y después la síntesis textual. El resultado describe correctamente los rótulos de las imágenes y evita inventar definiciones que no aparecen en el material. Esta prueba consume dos solicitudes mediante la sesión existente de Codex; no utiliza una API de pago independiente.

Evidencias:

- [Libro de 55 páginas](../.test-artifacts/zen-book/report.json).
- [55 páginas solo gráficas, OCR e integración por lotes](../.test-artifacts/zen-book-images/report.json).
- [Panel al detectar el libro](../.test-artifacts/zen-book-images/book-detected.png).
- [55/55 páginas extraídas y figuras separadas](../.test-artifacts/zen-book-images/book-extracted.png).
- [Lectura y síntesis con modelos reales](../.test-artifacts/reader-ai/result.json).
- [Regresión de lector y PDF incrustados](../.test-artifacts/zen-reader/report.json).
- [Regresión de artículo, frase e imagen](../.test-artifacts/zen/report.json).

```bash
python3 -m unittest discover -s tests -q
npm test
.venv/bin/python tests/e2e_zen.py --book
.venv/bin/python tests/e2e_zen.py --book-images --book-ai
.venv/bin/python tests/e2e_zen.py --reader
.venv/bin/python tests/e2e_zen.py
python3 scripts/smoke_reader.py --ai --source-state RUTA_DEL_STATE_FICTICIO_DE_BOOK_IMAGES
```

Las pruebas de navegador registran temporalmente el servicio y deben ejecutarse secuencialmente. La última orden está reservada para datos ficticios y requiere un trabajo previo con sus páginas; `--ai` hace explícito el consumo de solicitudes.

### Alcance

La integración confirma los mecanismos con documentos ficticios; el libro privado de AWS requiere la comprobación del usuario. Se admiten hasta 500 páginas localizables. No se afirma que un visor virtualizado que exponga solo unas pocas páginas permita enumerar todo el libro: se muestra el número localizado antes de empezar. El reintento de transferencia requiere la misma captura; tras cambiar o recargar el libro se detecta una instantánea nueva. Un error de lectura, de imagen o de modelo se presenta con su página/lote, conservando el trabajo; no se omite en silencio.

## Versión 0.6.0 — Redacción adaptativa y colecciones enlazadas

El usuario confirma que el lector de AWS ya produce un resumen, pero detecta que el panel mezcla el origen al cambiar de pestaña y que el texto conserva una estructura pensada para artículos de diseño. También indica que las plantillas del vault son orientativas y están anticuadas.

### Comportamiento

- Cada trabajo reclama una instantánea del origen. La detección automática de otras pestañas, incluida una respuesta ya en vuelo, no sustituye su contenido, título ni progreso. La importación manual utiliza la misma propiedad del trabajo.
- El modelo decide estructura, tipo, destino y número de notas según contenido e intención. Un curso con varios temas puede proponer un índice o síntesis y apuntes independientes; una fuente breve puede quedarse en una sola nota. Se admiten notas de conocimiento, referencias técnicas y modelos mentales con tipos y nombres compatibles con sus destinos.
- Las plantillas se incorporan como contexto, sin obligar a utilizar sus secciones. Los apuntes conservan páginas y procedencia en un pie de fuente, junto con cobertura y método. Los lotes sirven para leer, no para determinar la división de notas.
- La revisión permite recorrer, editar y excluir las notas de una colección. Los enlaces internos resuelven las rutas finales, conservan vuelta al índice y omiten destinos excluidos. Las conexiones con notas existentes siguen requiriendo evidencia y aceptación. Las sugerencias opcionales de enlaces a identificadores inexistentes se omiten; no invalidan todo el contenido ni crean enlaces rotos.
- El guardado comprueba todas las rutas y colisiones antes de escribir, rechaza sobrescrituras y registra hashes para recuperar una publicación interrumpida. Un fallo revierte únicamente los archivos creados en ese intento. Una colección derivada no se confunde con la captura de su fuente guardada previamente.
- Se reutilizan las lecturas completadas cuando cambia únicamente el perfil editorial. Se vuelve a generar la síntesis. La asignación de una figura a un apunte la retira del índice y conserva su pie.
- Se corrige además un clic perdido en Guardar: repetir la actualización en el evento de pérdida de foco de un campo de texto deshabilitaba el botón entre pulsación y clic.

### Pruebas

**70 pruebas Python y 26 JavaScript superadas.** Incluyen tipos y metadatos, enlaces recíprocos, renombrados, exclusiones, figuras por apunte, cobertura y método, rechazo de páginas no leídas, colisiones, reversión de escrituras, recuperación de archivos coincidentes, deduplicación de colecciones y reutilización de lecturas. La skill editorial supera su validador.

Los recorridos reales en **Zen 1.22.3b**, con vaults ficticios, comprueban:

- Colección de cuatro notas: recorrer un wikilink en la revisión, editar un apunte, renombrarlo, excluir otro, recargar sin perder los cambios y guardar tres notas con enlaces actualizados y vuelta al origen. Utiliza un CLI determinista para aislar el editor y el transporte.
- Libro de 55 páginas solo gráficas: OCR real, cambio a otro artículo mientras se transfieren páginas, origen y título estables, recuperación de la página 55, restauración del scroll y guardado. El CLI de prueba recibe las 55 imágenes en diez lotes y realiza la síntesis final; no consume IA generativa.
- Regresión de artículo, frase e imagen: resaltado, lectura, edición, guardado, descarte y retorno. El guardado tras editar un nombre funciona al primer clic.
- Importación local de subtítulos con origen propio, preparación y descarte desde su revisión.

Una prueba editorial separada usa **`gpt-6-luna` real** con fuentes ficticias:

| Entrada | Resultado comprobado |
| --- | --- |
| Tres apartados sobre identidades, EC2 y S3 | Índice y tres apuntes en la carpeta de clases, páginas de procedencia y enlaces recíprocos y entre temas |
| Caso breve de diseño editorial | Una fuente externa con decisiones y aprendizajes; sin colección artificial |
| Mecanismo de inversión del razonamiento | `modelo_mental` en `02_Cerebro/Modelos_Mentales`, mecanismo, aplicación y límites |

Se revisó el Markdown resultante: los apuntes explican los conceptos y distinguen lo que la captura no detalla; el caso de diseño no inventa resultados medidos y el modelo mental conserva sus límites. Se mantiene el modelo ligero para texto y el modelo visual configurado. No se usaron las notas personales como material de estas pruebas ni se reorganizó el vault del usuario.

Evidencias:

- [Revisión y guardado de colección](../.test-artifacts/zen-editorial/report.json) y [pantalla](../.test-artifacts/zen-editorial/collection-review.png).
- [55 páginas y cambio de pestaña](../.test-artifacts/zen-book-images/report.json).
- [Resultados del modelo real](../.test-artifacts/editorial-ai/result.json) y [síntesis de estudio](../.test-artifacts/editorial-ai/book-indice_2026-10-17_fundamentos-de-cloud-identidades-computo-y-almacenamiento.md).
- [Caso de diseño](../.test-artifacts/editorial-ai/design-case.md) y [modelo mental](../.test-artifacts/editorial-ai/mental-model.md).
- [Artículos, frases e imágenes](../.test-artifacts/zen/report.json) e [importador manual](../.test-artifacts/zen-import/report.json).

```bash
python3 -m unittest discover -s tests -q
npm test
.venv/bin/python tests/e2e_zen.py --editorial
.venv/bin/python tests/e2e_zen.py --book-images --book-ai
.venv/bin/python tests/e2e_zen.py
.venv/bin/python tests/e2e_zen.py --manual-import
python3 scripts/smoke_editorial.py --ai
```

Las pruebas de Zen deben ejecutarse secuencialmente. La última consume solicitudes del modelo con datos ficticios. La pertinencia y profundidad de las notas del curso real siguen requiriendo la validación del usuario: estas pruebas comprueban el mecanismo y casos representativos. La limpieza del vault, la organización aprendida, las actualizaciones de notas anteriores y el guardado automático quedan fuera de esta entrega.

## Versión 0.6.1 — Descarga desde el contexto del reproductor

El usuario informa de un 403 al extraer vídeos de AWS. El diagnóstico anterior confirma acceso a los marcos, pero no identifica el recurso rechazado ni su transporte. La revisión del código encuentra que las solicitudes de audio/vídeo directo pierden el identificador del marco; la descarga se realiza únicamente en segundo plano. Los subtítulos sí intentaban leer desde un script del marco, pero usaban el `fetch` de la extensión.

En Firefox con Manifest V2, `fetch` desde un content script utiliza el contexto de la extensión; `content.fetch` permite una solicitud con el contexto de página. Está documentado por [Mozilla](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Content_scripts#cross-origin_requests). Ese cambio permite conservar el referente y el contexto de sesión del reproductor; no demuestra por sí solo qué condición exige el vídeo privado concreto de AWS.

### Implementación

- La detección y el botón de extracción conservan el marco y la dirección de la página del reproductor para vídeo directo, subtítulos y HLS. El paso de subtítulos a audio conserva ese marco.
- El lector de recursos se inyecta en el marco seleccionado y utiliza `content.fetch` con credenciales. Devuelve fragmentos de hasta 393.216 bytes y cancela trabajos que superan sus límites o quedan inactivos. No copia cookies al servicio local.
- Si el marco no permite leer la respuesta —por ejemplo, por CORS del CDN— se intenta la lectura con los permisos ya concedidos a la extensión. HTML de acceso no se acepta como contenido multimedia.
- Manifiestos y segmentos HLS utilizan el mismo transporte; se conservan los límites de tamaño y duración y el rechazo de contenido cifrado o en directo.
- Los errores incluyen un bloque `extraction` con tipo, marco, dominios, contexto, fase y estado HTTP de los intentos. No incluye cookies, cabeceras ni parámetros de enlaces firmados. Un 403 persistente se muestra como fallo; no se confunde con una transcripción vacía.

### Validación

**70 pruebas Python y 33 JavaScript superadas.** Las nuevas regresiones comprueban la conservación del marco en el botón, lectura con `content.fetch`, límites de fragmentos, cancelación, rechazo de HTML de acceso, alternativa tras CORS, diagnóstico sin URLs firmadas y transporte HLS compartido.

El recorrido nuevo se ejecuta en **Zen 1.22.3b** con un curso y reproductor ficticios. El servidor exige que las peticiones incluyan la sesión y el referente del marco:

- La petición de control desde la extensión devuelve **403**; la descarga desde el marco devuelve **200**.
- MP4 protegido: descarga, transcripción real con Whisper local, preparación manual, guardado y vuelta al origen.
- Subtítulos protegidos: recuperación y captura del texto conocido con marcas temporales.
- HLS protegido: lectura del manifiesto maestro, variante y segmento desde el marco; transcripción local completada.
- Recurso que mantiene el 403: se registran los rechazos de ambos contextos, se libera el trabajo y el diagnóstico copiable omite el parámetro firmado de prueba.

No se consumen solicitudes de IA generativa. Los archivos y notas de prueba quedan en un vault temporal. Se mantiene la regresión de detección de pestañas y recursos anidados, incluido PDF sin extensión, subtítulos con sesión y vídeo dinámico HLS.

Evidencias: [vídeo y sesión](../.test-artifacts/zen-session-video/report.json), [diagnóstico de fallo persistente](../.test-artifacts/zen-session-video/blocked-diagnostic.png) y [regresión de detección](../.test-artifacts/zen-detection/report.json).

```bash
npm test
python3 -m unittest discover -s tests -q
.venv/bin/python tests/e2e_zen.py --session-video
.venv/bin/python tests/e2e_zen.py --detection
```

Las pruebas de navegador deben ejecutarse secuencialmente. La comprobación del recurso privado real sigue correspondiendo a la sesión del usuario; si el 403 continúa, el bloque nuevo permite identificar el contexto y el dominio que lo rechazan.

## Versión 0.6.2 — Progreso, galería y nombres de reproductores

El usuario confirma que AWS funciona y que una transcripción acabó rápidamente en el portátil. La ausencia de un trabajador activo al comprobar los procesos correspondía a una tarea ya terminada. Solicita que los trabajos sean visibles y que las imágenes no ocupen una lista interminable ni se recorten antes de elegirlas. Identifica `youtube.googleapis` como un nombre mostrado en el selector de vídeos.

### Cambios

- Tarjeta de trabajo con origen, fase, tiempo transcurrido, indicador animado y barra. Solo la transcripción muestra porcentaje y audio procesado/duración, a partir de los segmentos realmente obtenidos. Las demás fases mantienen una barra indeterminada.
- El trabajador local ofrece un protocolo JSONL de progreso y resultado. El servicio reenvía únicamente metadatos de avance, conserva el resultado por separado y termina el subproceso al alcanzar su límite. Los fallos no publican una transcripción como completa.
- La descarga de plataforma se identifica como búsqueda de subtítulos o descarga de audio antes de empezar Whisper. Sus conexiones tienen tiempo y reintentos limitados.
- Galería con scroll independiente, contador y selección de hasta ocho figuras. Se retiran los dos cortes de dieciséis imágenes que afectaban a artículos; se conservan todas las imágenes HTML detectadas y se deduplican sus URLs. Al alcanzar el límite se pueden seguir revisando las filas y sustituir una elección por otra posterior.
- Los adjuntos de la revisión también tienen scroll propio. El panel compacta las direcciones, separa grupos y deshabilita controles incompatibles con el trabajo en curso.
- Los reproductores antiguos con un identificador válido en `youtube.googleapis.com/v/…` se normalizan a un enlace de vídeo de YouTube. El selector muestra un nombre legible. El dominio histórico de estos reproductores está documentado en un [anuncio del equipo de YouTube](https://groups.google.com/g/youtube-api/c/8kof0d8a2H0). Se distinguen direcciones de API y URLs que solo contienen la palabra YouTube; no se ofrecen como páginas de vídeo de plataforma.
- Opciones identifica el motor actual como CPU/int8. No se instala ni activa aceleración AMD. La documentación de [Faster Whisper](https://github.com/SYSTRAN/faster-whisper#gpu) describe su aceleración GPU con NVIDIA/CUDA; la 9070 XT requiere otra integración compatible para utilizar su GPU.

### Validación

**73 pruebas Python y 35 JavaScript superadas.** Las nuevas pruebas comprueban el protocolo de progreso, separación del texto privado, resultado final, fallos, terminación por tiempo máximo, normalización de enlaces antiguos y rechazo de APIs como vídeos.

En **Zen 1.22.3b**, con vaults ficticios:

- Artículo con 24 imágenes: las 24 llegan al selector; la galería desborda internamente y permite elegir la última después de desmarcar otra, manteniendo ocho seleccionadas.
- Panel estrecho: tarjeta visible, tiempo que avanza, porcentaje conocido del audio y controles deshabilitados durante el trabajo. Se revisan las capturas para confirmar el diseño. Esta parte usa datos de progreso de prueba para mantener un estado estable durante la comprobación visual.
- Vídeo protegido y HLS: descarga y Whisper real en CPU, con fases de carga, transcripción, segundos procesados y extracción de fotogramas transmitidas por Native Messaging. No se consumen solicitudes de IA generativa.
- Se mantiene la regresión de artículos, frases, imágenes, detección por pestaña, recursos anidados, subtítulos con sesión y HLS dinámico.

Evidencias: [galería y estados](../.test-artifacts/zen-quality/report.json), [galería estrecha](../.test-artifacts/zen-quality/gallery.png), [tarjeta de progreso](../.test-artifacts/zen-quality/progress.png), [trabajador real y sesión](../.test-artifacts/zen-session-video/report.json), [regresión de detección](../.test-artifacts/zen-detection/report.json).

```bash
python3 -m unittest discover -s tests -q
npm test
.venv/bin/python tests/e2e_zen.py --quality
.venv/bin/python tests/e2e_zen.py --session-video
.venv/bin/python tests/e2e_zen.py --detection
```

La ampliación no enumera imágenes todavía no cargadas por una página ni convierte la selección de figuras del libro en todas sus páginas: la lectura íntegra del lector sigue por su recorrido propio. Los límites de rasterizado de superficies especiales y de tamaño de adjuntos se mantienen. La aceleración AMD y el rendimiento del equipo principal no se han probado.

## Versión 0.7.0 — Los cinco puntos de mejora

El usuario autoriza implementar calidad editorial, diseño adaptable y flujo simple, conexiones, revisión por apartados y recuperación de tareas. La entrega mantiene el guardado explícito y no utiliza el vault personal para pruebas de escritura.

### Calidad editorial

El contrato se separa en instrucciones editoriales propias, con criterios para estudiar, conservar casos de diseño, destilar conceptos, interpretar citas y describir imágenes. Se retira la cuota orientativa de dos a ocho notas: la división debe aportar temas independientes, sin repetir la síntesis. Se incluyen ejemplos breves de buenos y malos resultados, límites de la fuente y relaciones concretas. La lectura por lotes mantiene instrucciones distintas de la síntesis final.

La evaluación compara la guía anterior y la nueva sobre seis fuentes ficticias: fundamentos de AWS, diseño editorial, inversión como modelo mental, una cita, un diagrama descrito por HTML y subtítulos parciales. Ambas versiones usan el modelo de texto configurado, `gpt-6-luna`, y la misma infraestructura. El orden A/B se alterna para el juez. Se conservan las notas y sus razones de comparación.

El juez automático prefiere la candidata en **6/6 casos**. Esto es evidencia provisional, no una valoración humana ni una garantía para el curso real. En el curso breve, por ejemplo, valora una nota coherente frente a fragmentar tres párrafos en cuatro archivos. La evaluación necesita ampliarse con ejemplos revisados por el usuario. El enfoque sigue ejemplos y criterios específicos de [OpenAI Docs sobre prompts](https://developers.openai.com/api/docs/guides/prompt-engineering) y [evaluación](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

Una primera propuesta de la prueba de curso repitió un identificador reservado; se corrigió el contrato de identificadores derivados en la salida estructurada. Se conservan validadores de tipos, páginas, rutas y conexiones. No se cambian las plantillas personales.

### Diseño y flujo

- La revisión puede abrirse al terminar una extracción, sin pedir otra pulsación para preparar. Una opción visible permite conservar el recorrido de extracción independiente. La intención permanece visible antes de empezar y los parámetros secundarios se pliegan.
- Las ventanas estrechas alternan contenido y propiedades. Se eliminan anchos mínimos que desbordaban el documento; títulos y URLs pueden partirse. Tablas y código conservan su desplazamiento dentro del bloque.
- La barra de lectura tiene en cuenta la altura real de la cabecera para que los controles no queden tapados al editar propiedades.
- Frases e imágenes de un mismo artículo obtienen nombres de fuente distintos por tipo y huella, evitando una colisión inmediata con la nota del artículo.

### Conexiones y ampliaciones

Las conexiones con notas existentes muestran tipo, motivo y evidencia; el usuario puede corregir el tipo o descartar el enlace. Las conexiones entre notas nuevas se revisan aparte y pueden desmarcarse en ambas direcciones. Integraciones y exclusiones resuelven las rutas finales.

El usuario puede elegir **Ampliar una nota existente** entre las candidatas. El servicio registra la huella de esa versión y devuelve contenido actual y aporte. Solo se permite guardar después de revisar el aporte exacto. Una edición posterior o un cambio externo invalida la aceptación. El contenido anterior se conserva como prefijo exacto; su frontmatter no se reescribe y el aporte registra su propia procedencia y asistencia. Se conserva una copia local anterior y un diario de publicación. Se comprueban todas las notas de la selección antes de escribir; una publicación interrumpida puede retomarse sin duplicar el aporte.

### Revisiones parciales

Explicar, reducir o desarrollar devuelve una propuesta, sin sustituir el borrador directamente. El servidor limita el cambio al apartado seleccionado; usa páginas pertinentes de la fuente cuando constan. La interfaz compara actual/propuesta, requiere aplicar o descartar y conserva hasta cinco estados para deshacer. Se rechaza una aceptación si el cuerpo cambió mientras se generaba la propuesta. La integración de dos derivadas conserva páginas, imágenes, comentarios y conexiones, y excluye la nota integrada del guardado.

Una comprobación con **`gpt-6-luna` real** completa una revisión por apartado y una integración. El comentario personal que queda fuera se mantiene literalmente; también se conserva durante la integración. La nota publicada registra la asistencia de IA.

### Cancelación y recuperación

El control de cancelación utiliza otra conexión Native Messaging para no esperar al proceso ocupado. Se cancelan las lecturas del navegador y los subprocesos; cada tarea conserva su estado y vault. Las preparaciones se retoman desde su solicitud guardada. Los archivos completamente recibidos no se vuelven a transferir.

Whisper guarda segmentos completos de forma atómica. Al reanudar vuelve a cargar el audio y modelo y continúa la inferencia desde el último segmento guardado; no se promete recuperación de trabajo interno de un segmento incompleto. Un resultado completo se reutiliza por huella del archivo, modelo y versión del motor.

La prueba con **75 segundos de voz y Whisper real** solicita cancelar tras el primer progreso. El control independiente detiene el trabajador, quedan segmentos en disco y la siguiente solicitud comienza en el avance guardado —22 segundos en esta ejecución—. Se completa la transcripción con tiempos monotónicos, y una tercera solicitud reutiliza el resultado sin volver a transcribir. Los lectores siguen reanudando páginas recibidas desde la misma captura. Una descarga incompleta antes de recibir el archivo se repite desde el origen.

### Pruebas y evidencias

**86 pruebas Python y 35 JavaScript superadas.** Se añaden comprobaciones de revisión parcial, rechazo de wikilinks no verificados, integración y referencias, descarte de conexiones, aceptación del aporte exacto, cambios externos, rutas no candidatas, reversión de publicaciones mixtas, recuperación sin duplicación, repetición de una fuente sobre el mismo destino, cancelación real y aislamiento entre vaults.

Los recorridos con **Zen 1.22.3b** comprueban:

- Ajustar un apartado, comparar, aplicar y deshacer conservando comentarios; integrar otra nota y ajustar la selección.
- Descartar y restaurar una conexión interna; ampliar una nota con aceptación expresa y conservar su contenido previo.
- Cancelar un CLI real que estaba esperando y reanudar su solicitud hasta abrir la revisión.
- Extraer subtítulos de un marco protegido y abrir automáticamente la propuesta.
- Ventanas estrechas con títulos sin espacios, URL larga, tablas y código, sin desbordamiento horizontal global.
- Libro gráfico de 55 páginas: OCR, transferencia, restauración de scroll, cambio de pestaña, diez lotes y conservación de la página 55.
- Artículo con IA real: imágenes locales, edición, relación respaldada por fragmentos, guardado y vuelta al origen.
- Regresión de artículo, frase, imagen, permisos anidados, PDF sin extensión, subtítulos con sesión y HLS dinámico.

Artefactos:

- [Flujo nuevo de revisión, ampliación y recuperación](../.test-artifacts/zen-workflow/report.json), [comparación](../.test-artifacts/zen-workflow/revision.png), [aporte](../.test-artifacts/zen-workflow/amendment.png) y [prueba de anchos difíciles](../.test-artifacts/zen-workflow/narrow-stress.png).
- [Evaluación de prompts](../.test-artifacts/editorial-eval/report.json).
- [Revisión e integración con IA real](../.test-artifacts/revisions-ai/report.json) y [nota](../.test-artifacts/revisions-ai/merged.md).
- [Cancelación y recuperación de Whisper real](../.test-artifacts/recovery/report.json).
- [Libro completo](../.test-artifacts/zen-book-images/report.json), [Zen con IA real](../.test-artifacts/zen-ai/report.json) y [detección](../.test-artifacts/zen-detection/report.json).

```bash
python3 -m unittest discover -s tests -q
npm test
.venv/bin/python tests/e2e_zen.py --workflow
.venv/bin/python tests/e2e_zen.py --book-images --book-ai
.venv/bin/python tests/e2e_zen.py --ai
.venv/bin/python tests/e2e_zen.py --detection
python3 scripts/eval_editorial.py --ai
python3 scripts/smoke_revisions.py --ai
python3 scripts/smoke_recovery.py --real
```

Los recorridos de Zen se ejecutan secuencialmente porque registran temporalmente su servicio. Las órdenes con `--ai` consumen solicitudes con datos ficticios; `--real` ejecuta Whisper local. Se ha restaurado la configuración personal al instalar la entrega. La limpieza del vault, el aprendizaje de organización y la aceleración AMD permanecen fuera de esta ampliación.

## Versión 0.7.1 — Paneles heredados y foco entre ventanas

El usuario informa de que abrir ventanas de Zen en otros escritorios muestra automáticamente el plugin. El código solo llama a abrir el panel desde icono, atajo o menú contextual, pero el navegador hereda su estado al crear ventanas. Mozilla documenta las [instancias laterales por ventana](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/user_interface/Sidebars). Además, la revisión de un trabajo finalizado se creaba activa sin fijar ventana.

### Corrección

- El servicio distingue una ventana nueva de una apertura explícita. La primera instancia heredada consulta esa política antes de inicializar detección o servicio nativo y cierra su propio documento cuando no procede mantenerla abierta. El panel original continúa abierto. El icono, atajo y menú contextual conservan su llamada dentro del gesto de usuario.
- Se utiliza el cierre del documento lateral, corregido en [Firefox 133](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox/Releases/133#changes_for_add-on_developers). Se declara 133 como mínimo y se verifica en el Zen instalado, basado en Gecko 156.
- Cada panel atiende eventos de pestañas de su propia ventana y vuelve a detectar al recuperar su foco. La detección inicial también recibe la ventana correspondiente.
- Una revisión automática se crea en la ventana de la fuente. Solo se activa si esa ventana tiene el foco y el usuario sigue en la fuente o su panel de captura. Si se ha cambiado a otra pestaña, ventana o aplicación, queda en segundo plano. La apertura explícita de una revisión sigue disponible.

### Pruebas

**86 pruebas Python y 39 JavaScript superadas.** Las cuatro nuevas regresiones cubren la instancia heredada, la carrera entre carga del panel y creación de ventana, la apertura explícita y la política de foco de la revisión.

La prueba nueva abre **dos ventanas reales de Zen 1.22.3b** en un perfil temporal:

- Abre el panel en la original y crea otra ventana: se observa la denegación de la instancia heredada y su cierre, conservando el panel original.
- Abre expresamente el panel en la ventana nueva y comprueba que se permite y se muestra.
- Cierra el panel original y abre otra pestaña: el panel permanece cerrado.
- Finaliza una propuesta ficticia mientras la segunda ventana está enfocada: la revisión pertenece a la ventana original y queda inactiva. La ventana enfocada permanece igual antes y después.

La regresión de 0.7.0 vuelve a comprobar edición parcial, integración, aceptación de ampliaciones, cancelación, recuperación y revisión automática. Se utilizan solo vaults temporales y no se consumen nuevas solicitudes de IA.

Evidencias: [ventanas y foco](../.test-artifacts/zen-windows/report.json) y [flujo de revisión](../.test-artifacts/zen-workflow/report.json).

```bash
npm test
python3 -m unittest discover -s tests -q
.venv/bin/python tests/e2e_zen.py --windows
.venv/bin/python tests/e2e_zen.py --workflow
```

Los recorridos de navegador se ejecutan secuencialmente. La comprobación usa ventanas reales de Zen; la colocación de esas ventanas en escritorios de Omarchy se valida en el uso del usuario.

## Versión 0.7.2 — Salir de Opciones

Se añade **← Volver a la captura** en una barra que permanece visible al hacer scroll. Las opciones abiertas desde el panel recuerdan su pestaña de origen durante la sesión; volver activa esa pestaña y cierra solo Opciones. Si no hay un origen disponible, la misma pestaña muestra la herramienta de captura. Los cambios pendientes se guardan como borrador local y solo se aplican al servicio al pulsar **Guardar opciones**.

**39 pruebas JavaScript superadas** y recorrido real en **Zen 1.22.3b**, con vault temporal:

- Regreso desde Opciones abiertas directamente y desde el panel, antes y después de guardar.
- Recuperación de cambios pendientes al reabrir, configuración del servicio intacta mientras no se guardan y eliminación del borrador tras el guardado.
- Botón visible al final de la página en ventana de 420 px, sin desplazamiento horizontal.
- Regresión de detección automática y ruta manual del vault, rechazo de rutas inexistentes y recuperación de vault movido.
- Regresión de artículo, frase e imagen, con revisión, guardado y descarte.

El navegador de prueba se inicia con una pestaña que Zen identifica como `-1` ante la extensión; el recorrido de regreso usa una pestaña creada mediante la API del navegador para disponer de una referencia válida. Los destinos se conservan solo durante la sesión para evitar reutilizar identificadores después de reiniciar.

Evidencias: [Opciones](../.test-artifacts/zen-options/options-report.json), [vista estrecha](../.test-artifacts/zen-options/options.png) y [captura y guardado](../.test-artifacts/zen-options/report.json).

```bash
npm test
.venv/bin/python tests/e2e_zen.py --options
```


## Versión 0.9.1 — Un solo menú de revisión

La página de revisión deja de repetir los controles del asistente lateral: navegación y selección de notas, Lectura / Editar Markdown, división, búsqueda de conexiones y guardado. Conserva el contenido, las propiedades editables, la revisión de evidencias e imágenes y las confirmaciones de propuestas. El motivo de la organización se mantiene en las propiedades. Volver y descartar siguen disponibles en la cabecera.

**Abrir panel lateral** recupera el asistente mediante un clic real, conservando el gesto de usuario que exige Firefox y la política de apertura por ventana. La vista de lectura o edición activa se indica en el lateral. El estado de guardado se mantiene en el controlador de revisión y ya no depende de un botón duplicado en la página.

Validación: **106 pruebas Python y 41 JavaScript superadas**. En Zen 1.22.3b se comprueban la ausencia de controles duplicados, recuperación del lateral, navegación, edición, selección y guardado; también el descarte y aceptación de divisiones conservando código y anotaciones, recuperación tras recargar y revisión previa al guardado. El panel de 240 px mantiene su ajuste sin scroll horizontal.

Evidencias: [asistente lateral](../.test-artifacts/zen-review-menu/report.json), [página simplificada](../.test-artifacts/zen-review-menu/review-with-sidebar.png) y [división desde el menú](../.test-artifacts/zen-split-review/report.json). Las pruebas usan vaults temporales y no escriben notas personales.

También supera el recorrido de ajustes por apartado, aceptación y deshacer, integración de notas, ampliación con aprobación explícita, cancelación y reanudación; comprueba anchos de 480, 640 y 950 px. [Informe del recorrido](../.test-artifacts/zen-workflow/report.json).


## Versión 0.9.2 — Anaco (`anaco-ob`)

El proyecto y el checkout adoptan `anaco-ob`; el nombre visible de la extensión es **Anaco**. El icono es una «o» facetada en violeta, integrada en el panel, opciones, revisión y barra del navegador. Se actualizan el paquete npm, ZIP, módulos de captura y renderizado, atributos de página, documentación, skill y servicio Native Messaging (`org.samuh.anaco_ob`).

El instalador migra los datos a `~/.local/share/anaco-ob/` y deja un alias de la ubicación anterior para las rutas absolutas de trabajos pendientes. Conserva el identificador de instalación de Firefox y registra el host anterior como alias cuando existe. Los entornos locales se reparan para la nueva ruta del checkout.

La migración real conserva todos los valores de configuración, el historial SQLite y las **11 capturas conservadas**, de las que 3 figuran como pendientes para el vault activo. Las pruebas de migración comprueban archivos, rutas absolutas de trabajos, escritura con SQLite ya abierto, repetición de la instalación, destino existente y restauración si falla el alias. **110 pruebas Python y 41 JavaScript superadas**, además de validación de la skill y sintaxis JavaScript.

El recorrido de revisión en Zen 1.22.3b supera navegación, edición, selección y guardado desde el asistente, relaciones entre temas, recuperación de ediciones, varias revisiones y panel de 240 px sin scroll horizontal. Una comprobación del test leía los enlaces antes de terminar la vista asíncrona; se corrige esperando a que la relación esté disponible.

Evidencias: [asistente de Anaco](../.test-artifacts/zen-review-menu/report.json), [interfaz con el icono](../.test-artifacts/zen-review-menu/menu.png) y [icono ampliado](../.test-artifacts/brand/anaco-icon.png). Las pruebas escriben en vaults temporales.

También supera el recorrido de artículo, frase e imagen: captura, resaltado con ratón y teclado, renderizado saneado, imágenes locales, guardado, descarte y regreso al origen. [Informe de captura](../.test-artifacts/zen/report.json).

El lector completo también supera la regresión de 55 páginas: se conserva la página final, el panel permanece estable durante las mutaciones del lector, mantiene el origen al cambiar de pestaña y restaura el scroll. [Informe del lector](../.test-artifacts/zen-book/report.json). Se comprueba además la importación de Faster Whisper desde el entorno multimedia trasladado.

## Versión 0.10.0 — Recursos incrustados y modo de captura

**48 pruebas de JavaScript y 117 de Python superadas.** Cubren hosts de incrustados frente a reproductores de cursos, URLs de publicaciones y pens, criterios de clip, avisos de peso, la opción de priorizar la página y la copia sin conexión de demos: import map, prefijos, importaciones relativas, ciclos y archivos que no se pueden copiar. En el servicio cubren la colocación en su sitio, recursos no elegidos o no colocados, validación de rutas y nombres, subida de recursos y que una captura sin recursos se presenta igual que antes.

Recorrido real en Zen:

- `--embeds`, fixture local. En **Curso** no hay recursos y el clip sigue siendo un vídeo que transcribir. Un iframe con texto sigue sustituyendo al artículo en Curso y en Automático (regla de los cursos) y no en **Artículo web**. En Automático, clip, publicación y pen quedan en su posición; se guardan el mp4, el embed y la copia de la demo. [Informe](../.test-artifacts/zen-embeds/report.json).
- `--embeds-live`, con red, en <https://tympanus.net/codrops/2026/10/16/ksenia-kondrashova/>: 8 clips, 6 pens y 6 publicaciones; el texto es el del artículo (9.295 caracteres) y no se piden permisos de marcos. Se guardan 2 clips, 6 demos sin conexión con three.js, sus módulos, lil-gui y GSAP copiados. La demo «Three.js Blobby Apple» descarga un modelo `.glb` al ejecutarse y lo avisa como parte que necesita conexión. [Informe](../.test-artifacts/zen-embeds-live/report.json) y [nota](../.test-artifacts/zen-embeds-live/note.md).
- Con la red bloqueada, Chromium ejecuta las copias: la demo de GSAP dibuja su canvas y la de three.js marca su renderizador.

CodePen solo entrega la demo sin envoltorio con un referer de `codepen.io`. Sin él, la incluye escapada en un `srcdoc`, del que se extrae el documento original. Las CDN públicas responden con CORS `*`, que rechaza las cookies, así que las librerías se piden sin credenciales. El código procede de las pestañas del pen cuando su iframe ya está cargado; si no, del documento compilado, sin las protecciones de bucle de CodePen.

Comparación de las pruebas de cursos y vídeo entre `main` y esta rama:

| Escenario | main | rama |
|---|---|---|
| `--media`, `--reader`, `--book`, `--manual-import` | supera | supera |
| `--code` | sin fixture en el worktree | supera |
| `--fresh-permissions` | elemento obsoleto (intermitente) | supera |
| recorrido por defecto, `--detection` | se agota la espera al reabrir la revisión | igual, en la misma instrucción |
| `--session-video` | se agota la espera de la revisión tras transcribir | igual, en la misma instrucción |

Los tres fallos comunes son anteriores a esta versión y no dependen de los recursos incrustados.

El visor del plugin HTML Prototype Viewer 1.0.1 compila sin cambios. Su analizador acepta el bloque `[[ruta]]` con `height:` que genera la nota, y carga el archivo con la ruta de recursos del vault, de modo que las librerías relativas se resuelven junto al `index.html`. No se ha comprobado dentro de Obsidian ni en las sesiones privadas de AWS y Xunta.

## Versión 0.11.0 — Perfil del vault

**132 pruebas de Python y 48 de JavaScript superadas.** Cubren:
- **Perfil:** el perfil clásico reproduce las reglas anteriores. Se comprueban el perfil genérico, la validación y el descubrimiento del archivo, el rechazo de rutas peligrosas, los cambios del vault y que un perfil roto muestra su error.
- **Escaneo:** sobre un fixture con la forma del second_brain reorganizado y sobre vaults sin convenciones o vacíos. Se comprueba que el cuerpo de las notas no entra en los hechos.
- **Propuesta con IA:** solo los documentos elegidos, nada inventado y sin IA en modo manual.
- **Acciones del servicio** para Opciones.

Recorrido real en Zen (`e2e_zen.py --profile`):
1. Un vault con la forma del second_brain y sin perfil muestra el aviso en el panel.
2. El escaneo en Opciones lista `AGENTS.md`, el skill y las guías, y no las notas de `00_Sistema`.
3. La propuesta automática se revisa y se guarda en `99_Recursos/anaco/perfil.json`.
4. La nota guardada lleva `tipo`, `zona`, `area` y `relacionadas: []`, y no los campos antiguos.
5. Al mover `MANUAL_VAULT.md`, el panel pide revisar el perfil.

[Informe](../.test-artifacts/zen-profile/report.json) y [nota](../.test-artifacts/zen-profile/note.md).

Codex real sobre el fixture acepta el esquema estricto, deduce `curso` y `asignatura` de la ruta y toma los encabezados de la plantilla. El escaneo determinista del vault real del usuario (423 notas, solo lectura) detecta plantillas, diario, adjuntos, archivo y sistema, y propone sus destinos y su frontmatter. No se ha enviado a la IA ningún documento del vault real: esa elección corresponde al usuario en Opciones.

Al validar se corrigió un fallo previo a esta versión. Al editar la nota, la revisión publicaba que se podía guardar antes de desactivar el guardado. Una orden **Guardar y volver** enviada mientras se actualizaba la vista previa se descartaba sin aviso. Ahora el estado se publica después y la orden espera a la vista previa. Ese era el fallo intermitente que hacía fallar varios recorridos e2e.

| Escenario | 0.10.0 (`main`) | 0.11.0 |
|---|---|---|
| `--profile`, `--embeds` | — / supera | supera |
| recorrido por defecto, `--detection`, `--options`, `--fresh-permissions` | fallan al reabrir o guardar la revisión | superan |
| `--media`, `--reader`, `--book`, `--code`, `--manual-import` | superan | superan |
| `--session-video` | falla al guardar | falla al guardar: dos vídeos con el mismo título el mismo día chocan con una nota existente, un límite de la prueba |

No se ha comprobado dentro de Obsidian ni con las sesiones privadas de AWS y Xunta.
