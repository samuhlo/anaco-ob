# Historial de versiones

Cambios visibles de cada versión de Anaco, de la más antigua a la más reciente. El detalle de las pruebas de cada una está en [VALIDACION.md](VALIDACION.md).

Extensión personal para Zen/Firefox con servicio local en Python. Captura artículos, frases e imágenes, propone notas y relaciones revisables y guarda Markdown en Obsidian.

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

Sin publicar todavía: **podcasts y entrevistas**. Una conversación de YouTube de hasta 4 h se convierte en una nota de fuente con ficha, resumen, temas con su minuto, ideas clave, consejos, citas y qué llevarte a la práctica. Las conversaciones de más de una hora se leen por tramos, empezando en los capítulos del vídeo, y después se sintetizan enteras. Cada cita se comprueba palabra a palabra contra la transcripción. Anaco reconoce si un vídeo es una conversación; el modo **Podcast · entrevista** lo fuerza y la revisión permite prepararlo de nuevo como vídeo, o al revés. Cada `[mm:ss]` de una nota de YouTube abre el vídeo en ese segundo. Las relaciones con tus notas enlazan la sección donde está su evidencia (`[[nota#Sección]]`), en cualquier tipo de captura. La duración máxima predeterminada pasa a 240 minutos.
