# Historial de versiones

Cambios visibles de cada versión de Anaco, de la más antigua a la más reciente. El detalle de las pruebas de cada una está en [VALIDACION.md](VALIDACION.md).

La versión 0.2.0 permite localizar imágenes del artículo al pasar por sus filas en el panel y revisar la nota en una pestaña amplia. Guardar o descartar cierra la revisión y devuelve al artículo de origen.

La versión 0.3.0 añade PDF, subtítulos y archivos de vídeo/audio, análisis visual y pies de imagen generados. Distingue texto y páginas procesadas, transcribe localmente con Whisper y ofrece exploración de visores incrustados para cursos. Los reproductores privados concretos requieren validación dentro de la sesión del usuario.

La versión 0.3.1 aprovecha primero los pies HTML y metadatos de cada imagen. No adjunta imágenes ya descritas y conserva el modelo ligero cuando puede; reutiliza descripciones visuales por huella del archivo y permite desactivar o forzar visión. Las páginas PDF y fotogramas mantienen el análisis de contenido en automático.

La versión 0.3.2 permite detectar vaults desde el registro de Obsidian y ubicaciones habituales, elegir entre varios resultados o introducir la ruta manualmente. La selección se aplica al guardar las opciones.

La versión 0.4.0 sigue la pestaña actual y muestra solo las acciones del contenido detectado. Lee marcos anidados con permisos por dominio, reconoce PDF sin extensión en el visor nativo y recursos de reproductores dinámicos. Si no puede capturar, muestra un motivo y un diagnóstico. La importación manual queda en Opciones.

La versión 0.4.1 añade botones pequeños para copiar errores y diagnósticos, con confirmación visual y un campo seleccionado como alternativa si el portapapeles está bloqueado.

La versión 0.4.2 añade lectores HTML con páginas dibujadas, detección de PDF descargados por el visor y corrección de permisos falsos tras redirecciones. El diagnóstico distingue marcos de autenticación, contenido y superficies gráficas.

La versión 0.5.0 separa libros y figuras: extrae todas las páginas de un lector con progreso, OCR y transferencia por fragmentos; las lee por lotes y sintetiza el libro completo. Conserva los lotes para reintentos y evita la recaptura continua que hacía parpadear el panel.

La versión 0.6.0 adapta el resultado al contenido y a la intención: fuente, apuntes de estudio, referencia técnica o modelo mental. Un curso con temas distintos puede proponer una síntesis y varios apuntes enlazados, revisables por separado. Puedes editar, renombrar y excluir notas antes del guardado; los enlaces se ajustan a la selección. Las plantillas orientan la redacción sin imponer un esquema fijo. Durante una extracción o generación, el panel mantiene el origen y el progreso aunque cambies de pestaña.

La versión 0.6.1 conserva el marco del reproductor en las descargas de vídeo, subtítulos y HLS. Intenta leer desde el contexto de la página antes de recurrir al de la extensión, para respetar la sesión y el referente del reproductor. El diagnóstico de un fallo identifica el recurso por dominio y los contextos intentados, sin incluir cookies ni enlaces firmados.

La versión 0.6.2 añade una tarjeta de trabajo visible con fase, tiempo transcurrido y avance medido del audio durante la transcripción. La galería del panel tiene scroll propio y contador: enumera todas las imágenes de artículo detectadas, conservando el límite de ocho seleccionadas. Los reproductores antiguos `youtube.googleapis.com/v/…` se identifican como YouTube y se normalizan; las direcciones de API no se tratan como vídeos. El motor local sigue usando CPU; no utiliza automáticamente una GPU AMD.

La versión 0.7.0 incorpora criterios editoriales revisados y una evaluación comparada en seis fuentes ficticias; revisión por apartados con comparación y deshacer; integración de notas; relaciones tipadas y descartables; ampliaciones revisadas de notas existentes; y cancelación con recuperación de transcripciones y preparaciones. La extracción puede abrir la propuesta automáticamente. El diseño se adapta a paneles estrechos, títulos largos, tablas y código, sin desplazar horizontalmente la página completa.

La versión 0.7.1 evita que una ventana nueva herede el panel abierto y limita la detección de cada panel a su ventana. Si terminas una tarea mientras trabajas en otra pestaña o ventana, la revisión queda en segundo plano en la ventana de origen, sin cambiarte el foco. El icono, el atajo y los menús contextuales siguen abriendo el plugin de forma explícita.

La versión 0.7.2 añade **Volver a la captura** en Opciones, siempre visible al hacer scroll. Regresa a la pestaña de origen y conserva localmente los cambios pendientes hasta que decidas guardarlos.

La versión 0.7.3 distingue el vault detectado de la ruta aplicada, añade **Guardar y volver** en la barra superior y actualiza los paneles abiertos tras guardar la configuración, retirando el error anterior de vault inexistente.

La versión 0.8.0 permite elegir una nota, varias notas enlazadas o automático, con una nota como valor predeterminado. Los tutoriales técnicos seleccionan código cuando aporta comprensión o consulta y explican su función, parámetros y límites. La captura conserva el lenguaje, las líneas en blanco y los delimitadores del código. Se han probado la captura y las dos formas de organización con el artículo de Codrops sobre Ghost Trails.

La versión 0.8.1 ajusta la tarjeta de trabajo a paneles estrechos y divide los mensajes largos para evitar scroll horizontal. Los botones Lectura / Editar Markdown permanecen en su posición dentro de la nota y dejan de seguir el desplazamiento.

La versión 0.8.2 añade **Proponer división en notas** desde la revisión. Antes de reorganizar muestra el motivo, los temas y su contenido para aceptar o conservar la nota actual. Distribuye los apartados editados sin reescribir su código o anotaciones y mantiene las imágenes y sus pies. Tras aceptar se revisan las notas enlazadas antes del guardado final.

La versión 0.9.0 busca conexiones por cada tema con evidencia literal de la nota revisada y de las candidatas del vault. Añade relaciones verificables y recíprocas entre temas, permite actualizar enlaces sin regenerar el texto y conserva las decisiones de revisión. Mientras haya una revisión abierta en la ventana, el panel lateral ofrece navegación, selección de notas, edición, conexiones, división y guardado; al cerrarla vuelve a la captura.

La versión 0.9.1 concentra los controles de revisión en el panel lateral. La página conserva la nota, los campos editables y las propuestas por confirmar, sin repetir navegación, selección, lectura/edición, división, búsqueda de conexiones o guardado. **Abrir panel lateral** permite recuperar el menú si se cierra.

La versión 0.9.2 adopta el nombre **Anaco**, el proyecto `anaco-ob` y una «o» de cristal como icono. Actualiza rutas, módulos, skill, servicio local y paquetes. El instalador migra configuración, pendientes e historial a `~/.local/share/anaco-ob/`.

La versión 0.10.0 reconoce los recursos incrustados de un artículo: publicaciones de X, demos de CodePen y clips silenciosos en bucle. Se eligen en el panel como las imágenes y la nota los inserta donde aparecían. Las publicaciones usan el embed nativo de Obsidian y conservan su texto. Los clips se guardan como mp4 en el vault, con aviso si pesan más de 20 MB o no se conoce su tamaño, y ya no se ofrecen para transcribir. Cada demo guarda su código y una copia ejecutable sin conexión con sus librerías y módulos, que se ve en la nota con el plugin HTML Prototype Viewer. Los marcos de esos servicios ya no sustituyen al artículo ni piden permisos. Un selector de **Modo de captura** ofrece Automático, Artículo web y Curso; Curso conserva la detección anterior para los cursos.

La versión 0.11.0 adapta Anaco a cualquier vault mediante un **perfil del vault**. En Opciones, un escaneo lee carpetas, nombres y metadatos sin sacar del ordenador el contenido de las notas. Después la IA interpreta las instrucciones, skills, guías y plantillas que elijas y propone dónde guardar, qué tipos y nombres usar, de dónde sale cada campo del frontmatter, la carpeta de adjuntos y dónde buscar relaciones. Revisas cada regla con su evidencia y la confirmas. El perfil se guarda como `.json` dentro del vault, de modo que viaja con la sincronización. El panel avisa cuando el vault cambia de forma que afecta al perfil. Las notas existentes nunca se modifican. Un vault sin convenciones recibe un perfil mínimo: el título como nombre y frontmatter básico. También corrige **Guardar y volver** cuando se pulsaba mientras se actualizaba la vista previa: la orden se descartaba sin aviso.

La versión 1.0.0 es la primera publicable en addons.mozilla.org. Cumple sus requisitos (declaración de datos, identificador fijo, sin navegación privada y política de privacidad) y el servicio local se instala con `pipx` y `anaco-ob install` en Linux, macOS y Windows. Además de Codex, prepara notas con cualquier servidor compatible con OpenAI, incluidos modelos locales. Una página de bienvenida guía la instalación y el panel explica qué falta cuando algo no responde. La interfaz, los mensajes del servicio y las notas pueden estar en español o en inglés; el español sigue siendo el principal.

La versión 1.0.1 guía el primer uso. La bienvenida explica con palabras sencillas por qué hace falta el servicio local, lo instala con una sola línea en la terminal (trae Python si falta) en Linux, macOS y Windows, detecta sola cuándo responde y deja elegir el vault y la IA. Los servicios se eligen por su nombre: Codex con tu cuenta de ChatGPT; Claude, Gemini, OpenAI, MiniMax, Qwen u OpenRouter con tu clave; Ollama o LM Studio en tu ordenador; o ninguno. El panel lleva de vuelta a ese recorrido cuando el servicio falta o está desactualizado.

La versión 1.1.0 añade **podcasts y entrevistas**. Una conversación de YouTube de hasta 4 h se convierte en una nota de fuente con ficha, resumen, temas con su minuto, ideas clave, consejos, citas y qué llevarte a la práctica. Las conversaciones de más de una hora se leen por tramos, empezando en los capítulos del vídeo, y después se sintetizan enteras. Cada cita se comprueba palabra a palabra contra la transcripción. Anaco reconoce si un vídeo es una conversación; el modo **Podcast · entrevista** lo fuerza y la revisión permite prepararlo de nuevo como vídeo, o al revés. Cada `[mm:ss]` de una nota de YouTube abre el vídeo en ese segundo. Las relaciones con tus notas enlazan la sección donde está su evidencia (`[[nota#Sección]]`), en cualquier tipo de captura. La duración máxima predeterminada pasa a 240 minutos.

## 1.2.0 · 2026-10-22

**velocidad y lectura con dos modelos:** los podcasts largos usan GPT-6 Luna para leer dos tramos a la vez y GPT-6.1 Sol para elaborar la nota, con razonamiento medio. El lector se configura por separado. La caché de lecturas se comparte entre capturas equivalentes y no se invalida al cambiar solo el redactor. Las instrucciones extensas del vault se compactan una vez y se reutilizan, conservando el contrato y los criterios particulares; si no se pueden compilar, se usan completas. Se mantienen las citas y evidencias originales y su comprobación literal.

**corrección de YouTube:** los canvas del reproductor dejan de detectarse como páginas de un libro y los reproductores internos se agrupan por el enlace del vídeo. Una página de YouTube requiere extraer el vídeo antes de preparar la nota: su descripción, comentarios y recomendaciones no se usan como transcripción. La extracción de plataformas pide los subtítulos completos y conserva la alternativa de transcribir el audio; no se limita a las frases que el navegador ya ha reproducido.

**progreso y calidad:** el progreso cuenta unidades terminadas de cada fase (tramos, páginas, segmentos o recursos), admite el 100 % y separa la lectura de la síntesis. Las fases sin avance intermedio muestran actividad sin una barra que parezca completa. La cancelación conserva su estado frente a mensajes tardíos. Codex pasa a GPT-6.1 Sol con razonamiento medio por defecto, ajustable en Opciones. Los podcasts distinguen dos partes: un resumen por temas de lo importante que se habló y, después, aprendizajes personales con situaciones, ejemplos y pasos para incorporarlos. La personalización usa la intención y el contexto aportados. Las lecturas guardadas distinguen el nivel de razonamiento. Se corrige además un fallo que podía impedir terminar la transcripción local al preparar fotogramas.

**notas enlazadas de podcasts:** corrige el rechazo de referencias cuando una derivada citaba una paráfrasis de la síntesis en lugar de la transcripción original. La generación recibe fragmentos originales identificados, selecciona los que respaldan cada nota y conserva la comprobación literal antes de permitir el guardado. El arreglo aprovecha los tramos ya leídos.

**barra lateral:** simplifica la captura a contenido, intención opcional, organización y una acción principal. Las páginas mixtas permiten elegir texto, PDF, vídeo o lector; los selectores con una sola opción desaparecen. Adjuntos, ajustes y pendientes se despliegan cuando hacen falta. Los ajustes especiales activos se indican incluso estando plegados. Se unifican separación y tamaño de botones, se retira el formulario durante el procesamiento y se prioriza abrir una revisión existente sobre volver a generar. La intención y organización elegidas se conservan al actualizar la detección y al terminar de extraer.

**descartar pendientes:** cada captura y trabajo interrumpido ofrece una × al pasar el cursor o recibir el foco; en pantallas táctiles está siempre visible. El descarte persiste, limpia la revisión y el editor de esa captura y retira sus intentos de generación fallidos. Las notas guardadas y los trabajos activos quedan protegidos.

## 1.2.1 · 2026-10-27 · pruebas locales

El panel mantiene la pestaña donde se abrió al navegar por otras páginas. El icono de Anaco o **Usar la pestaña actual** permiten cambiar de origen explícitamente. Cada ventana conserva su captura; el lateral puede seguir visible al cambiar de pestaña.

**Preparar varios enlaces** procesa hasta 100 enlaces de uno en uno en segundo plano, con la sesión y el contenedor del navegador. Permite pausar, continuar tras reiniciar y reintentar fallos sin repetir una extracción ya completada. Los enlaces que necesitan acceso o autorización quedan señalados y no bloquean los siguientes. Los borradores se abren para revisión de forma explícita y no se guardan automáticamente en el vault. El permiso opcional de cookies permite mantener el contenedor, sin leer ni exportar cookies.

Paquete local: `dist/anaco-ob-1.2.1.zip`. Esta versión todavía no está publicada en AMO.

## 1.2.2 · 2026-10-27 · pruebas locales

Corrige la selección automática de la cola que podía resumir la guía PDF general de un campus en vez del vídeo de la clase. Distingue documentos del contenido y de navegación, espera detecciones estables del recurso solicitado y prioriza vídeos sobre PDF auxiliares. Las actividades URL de Moodle pueden seguir su enlace de contenido autorizado; los marcos con carga diferida se solicitan sin activar la pestaña.

Añade **Reprocesar como vídeos** para recuperar los enlaces no guardados de un lote anterior sin reutilizar sus extracciones equivocadas. Conserva los borradores anteriores y las notas guardadas. Al reabrir el navegador, una cola que estaba terminando de pausar se recupera correctamente en pausa.

## 1.2.3 · 2026-10-27 · pruebas locales

Corrige el bloqueo de clases de Google Drive por un marco auxiliar de Google Feedback. Los permisos incluyen los dominios usados por las descargas de Drive y los mensajes identifican qué dominios faltan. **Autorizar y reintentar fallidos** recupera juntos los enlaces fallidos, conservando los preparados.

El panel se centra en la cola durante la preparación y mantiene los resultados al finalizar, con regreso explícito a la captura individual. Oculta el formulario durante el trabajo y ofrece otra lista al terminar. Los botones de la bienvenida tienen una separación uniforme respecto a los campos y se adaptan a pantallas estrechas.

### Corrección adicional de Drive en la misma 1.2.3

La cola deja de exigir acceso a todos los marcos secundarios cuando la página ya identifica un vídeo que puede extraer. Los marcos de cuentas o API ajenos a la descarga no bloquean ese recurso; se siguen comprobando los permisos de la página y de la descarga seleccionada. Las variantes `/view` y `/preview` de un mismo archivo de Drive se agrupan por su identificador, conservando los parámetros de acceso compartido. Se actualiza el paquete 1.2.3, sin incrementar la versión.

### Edición de la cola y vídeos grandes · misma 1.2.3

Añade controles individuales para quitar enlaces, quitar todos los fallidos y vaciar la cola. Conserva las capturas y notas existentes. Quitar un enlace pendiente durante otra preparación evita que el recorrido de la cola lo procese después.

Distingue la confirmación de descarga de archivos grandes de Google Drive de una página de acceso. Solo sigue el formulario GET alojado en Drive y dirigido al mismo archivo. Amplía la descarga de vídeo a 1 GB, manteniendo 100 MB para PDF. Se actualiza el paquete 1.2.3 sin cambiar la versión.

### Etiqueta obligatoria de vídeo · misma 1.2.3

Toda nota nueva procedente de una captura de vídeo incluye `video` en sus tags, con independencia de la propuesta de IA, la edición manual o las reglas de frontmatter del perfil. Se aplica a la nota principal, las notas derivadas y las divisiones posteriores. Los borradores de vídeo anteriores reciben la etiqueta al previsualizarse y guardarse, sin regeneración. Las demás etiquetas del perfil se conservan.

### Confirmación de Drive con sesión · misma 1.2.3

La descarga reconoce formularios de confirmación GET y POST, con parámetros en la acción o en campos ocultos, incluidos los tokens emitidos por Drive. Mantiene la comprobación del archivo solicitado y del dominio de destino. Si el intento con cookies termina devolviendo HTML, prueba la descarga pública del mismo recurso sin cookies; una respuesta HTML final sigue rechazándose. Las peticiones de Drive no reutilizan respuestas cacheadas.

Los errores conservan un diagnóstico por enlace con fases, métodos, dominios y nombres de campos del formulario. No se guardan cookies, valores de tokens ni HTML de las páginas. El error final de Drive se diferencia ahora de una página de acceso genérica.

### Revisión continua y comprobación del vault · misma 1.2.3

Guardar desde una revisión de la cola avanza a la siguiente propuesta pendiente en la misma pestaña y, al terminar, vuelve a la cola. No abre de nuevo el vídeo. La cabecera incluye la acción de guardar y el progreso de revisión; las filas revisadas y guardadas se destacan en amarillo con una etiqueta explícita. Las propuestas preparadas siguen diferenciadas de las revisadas.

La detección de duplicados comprueba la existencia del archivo registrado. Un registro de una nota borrada no bloquea una captura regenerada; al guardar se actualiza el registro dentro de la transacción. Se conservan las protecciones frente a sobrescrituras y a colecciones parcialmente eliminadas. Una revisión bloqueada vuelve a comprobar el vault al recuperar el foco.

### Relaciones en bloque y exploración de cursos · misma 1.2.3

Añade selección y desmarcado masivos de las conexiones disponibles de la nota activa, sin reactivar evidencias desactualizadas.

Añade un explorador de cursos con catálogo Canvas/AWS Academy, paginación, jerarquía de módulos y secciones, lectura de páginas internas y selección por ramas o enlaces. Mantiene la sesión y el contenedor, conserva el progreso al cerrar el panel y permite detener o reanudar. El contenido bloqueado no se selecciona; los límites o errores se muestran sin ocultar los resultados encontrados. La selección rellena la cola para revisión antes de procesarla. También se evita confundir el `about:blank` transitorio de una pestaña recién creada con un dominio sin permiso.

### Interfaz unificada · misma 1.2.3

El panel cambia entre **Esta página** y **Varios enlaces** con un selector. La cola deja de ocupar un desplegable sobre la captura y tiene su propia intención y organización: antes heredaba sin mostrarla la intención escrita para la página actual. Los ajustes de captura siguen visibles en los dos modos.

La cola muestra estado, progreso y recuento con una sola acción principal según el momento: continuar, revisar los pendientes, reintentar los fallidos o preparar otros enlaces. Las acciones poco frecuentes pasan al menú **Más**. Cada fila lleva un punto de estado (amarillo por revisar, verde guardada, rojo con acción pendiente), el dominio en lugar de la dirección completa y los iconos ↗ y × para abrir el origen o quitarla.

La búsqueda de enlaces de un curso pasa a ser **Varios enlaces → Desde un curso**, con selección en una sola barra, filas compactas que indican el tipo de cada enlace y **Añadir N a la cola**. La revisión en cola muestra **Nota N de M** con una barra de progreso en la cabecera. Panel, revisión, opciones y bienvenida comparten cuatro niveles de botón, chips de estado y la marca ↗ para lo que abre otra pestaña. Se describen en `docs/TECNICO.md`.

### Correcciones del panel vinculado · misma 1.2.3

Pulsar una captura de **Capturas pendientes** vuelve a mostrarla en el panel: desde la 1.2.1 el panel seguía mostrando la captura de su pestaña fijada. Ahora la reanudación vincula el panel a la captura, aunque su pestaña ya esté cerrada.

Capturar una selección ya no se pierde cuando la página tarda en leerla: la detección automática que lanza el panel al vincularse la sustituía por el artículo completo. Un trabajo cancelado o interrumpido con el panel abierto despliega **Capturas pendientes**, donde remite el aviso. El estado tardío de una revisión que ya se cerró no vuelve a mostrar el asistente.

La IA elegida en **Ajustes de captura** ya no vuelve sola a la predeterminada cuando el panel se actualiza: antes, una nueva detección entre la elección y **Preparar** hacía que la nota se preparase con la IA de Opciones sin avisar. La elección se mantiene hasta que cambian las opciones.

El asistente de revisión acompaña a la pestaña de revisión activa (comportamiento de la 1.2.3, ahora documentado y cubierto por `--review-menu`): con otra pestaña activa, el panel muestra su captura.
