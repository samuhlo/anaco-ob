# Second Brain Capture

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

- [Cómo instalar y probar](PRUEBA.md).
- [Idea del producto](IDEA.md).
- [Plan de desarrollo](PLAN.md).
- [Skill del vault](skills/second-brain-capture/SKILL.md).
- [Resultados y alcance de las pruebas](docs/VALIDACION.md).

## Estructura

```text
extension/     WebExtension: captura, revisión, opciones y comunicación nativa
native/        Servicio local: perfil, búsqueda, generación y guardado
skills/        Criterios de redacción y organización del Second Brain
scripts/       Instalación y comprobaciones reproducibles
tests/         Pruebas del servicio y recorridos en Zen
docs/          Evidencias y limitaciones de la entrega
```

El servicio no requiere dependencias de Python externas. La IA utiliza `codex exec`, con la sesión existente de ChatGPT, salida estructurada y herramientas de shell, aplicaciones y agentes deshabilitadas. El proceso de generación tiene acceso de solo lectura; la escritura la realiza el servicio después de la revisión del usuario.

La ampliación multimedia utiliza Poppler, FFmpeg y `yt-dlp`. Whisper se ejecuta en `.media-venv/`, separado del servicio. `scripts/install-media.sh` fija Faster Whisper 1.2.1 y PyAV 16.1.0 por compatibilidad con su API de decodificación. El audio no se envía a una API de transcripción.

La recuperación inicial busca en archivos locales y lee fragmentos relevantes. No se mantiene un índice semántico ni se envía el vault completo al proveedor. Se ha elegido una extensión pequeña propia para integrar la cola local y la revisión explícita de relaciones; las plantillas e interpretación de Obsidian Web Clipper sirvieron de referencia, sin crear un fork que hubiera que mantener.

La vista previa utiliza Marked y DOMPurify empaquetados en `extension/vendor/`, con sus licencias. No carga scripts de una CDN. Para regenerar esas copias en desarrollo: `npm ci` y `npm run vendor`. No hace falta npm para cargar la extensión entregada.
