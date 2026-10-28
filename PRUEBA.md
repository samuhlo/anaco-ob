# Probar Anaco 1.2.3

Esta versión captura artículos, frases, imágenes, PDF y contenido de vídeo/audio. Prepara una propuesta editable y guarda Markdown y adjuntos en tu vault. Las relaciones, las imágenes recomendadas y sus descripciones se revisan antes de guardar.

## Barra lateral actualizada

La captura muestra el contenido detectado, un objetivo opcional, su organización y **Crear nota** o **Crear notas**. Cuando hay texto, PDF y vídeo en la misma página, el selector **¿Qué contenido quieres guardar?** permite elegir uno antes de continuar. **Imágenes y recursos** se despliega para seleccionar adjuntos; **Actualizar** vuelve a detectar la página.

En **Ajustes de captura** están el tipo de contenido (Automático, Artículo, Curso o Podcast), el proveedor y **Crear la nota al terminar la extracción**. Al desmarcarlo se extrae primero y se prepara después. La cabecera de los ajustes indica los modos especiales activos. Durante el trabajo se ve el progreso; al terminar se recuperan la intención y organización elegidas. Una propuesta ya creada ofrece **Abrir revisión** y, por separado, **Volver a generar**. Los ejemplos históricos que siguen pueden usar los nombres anteriores de estos controles.

En **Pendientes**, pasa por una captura o un trabajo interrumpido para mostrar su **×** y descartarlo. También aparece al navegar con Tab y permanece visible en dispositivos táctiles. El descarte se conserva al actualizar o reiniciar; no elimina notas guardadas en el vault. Descartar una captura retira también su intento de generación fallido. Durante un trabajo en curso los controles de pendientes quedan desactivados.

## Bienvenida y diagnóstico

Al instalar la extensión se abre un recorrido de seis pasos (también desde **Opciones → Abrir la guía de instalación**):

1. **Bienvenida** y **Por qué**: qué hace Anaco y por qué necesita una pieza en tu ordenador.
2. **Instalar**: tras aceptar, muestra cómo abrir la terminal en tu sistema y una sola línea con botón de copiar. Mientras se instala, la página dice «Esperando a la pieza local…» y avanza sola cuando responde. **Prefiero instalarlo a mano** muestra los pasos con `pipx`.
3. **Tu vault**: los vaults encontrados, u **Otra carpeta** con su ruta.
4. **IA**: tu cuenta de ChatGPT (Codex), otro servicio con tu clave, un modelo en tu ordenador o sin IA.
5. **Todo listo**: comprueba el servicio, la versión, el perfil y la IA, y lleva a Opciones si falta confirmar el perfil.

Si algo falta más adelante, el panel muestra un aviso con el motivo y un enlace a la solución:

- **Falta el servicio local** o **versiones distintas**: vuelve al paso de instalación; la misma línea actualiza el servicio.
- **No encuentro tu vault**, con enlace a Opciones.
- **La IA no está lista**: Codex no encontrado o proveedor sin modelo.

## Idiomas: comprobar 1.0.0

En **Opciones → Idioma** elige **English**: la página, el panel y los avisos pasan a inglés, también los mensajes del servicio local. **Automático** sigue el idioma del navegador. Aparte, **Opciones → Preparación de notas → Idioma de las notas** decide en qué idioma se escriben las notas nuevas y sus encabezados predeterminados; las notas que ya están en el vault no cambian.

## Otro servicio de IA

En **Opciones → Preparación de notas**, elige **Otro servicio de IA** y después el **Servicio**: Claude, Gemini, OpenAI, MiniMax, Qwen, OpenRouter, Ollama o LM Studio. Anaco rellena la URL base y un modelo sugerido, que puedes cambiar, y enlaza a la página donde se consigue la clave. Pega la clave API; Ollama y LM Studio funcionan en tu ordenador y no la necesitan. **Otro servidor compatible** deja escribir la URL a mano.

Pulsa **Guardar opciones**. La clave se guarda en el servicio local y no se vuelve a mostrar. El panel ofrece el mismo proveedor en **Ajustes de esta captura**, y Codex sigue disponible. Para describir imágenes hace falta un modelo con visión; puedes indicarlo en **Modelo visual**. Si el servidor no admite salidas por esquema, Anaco reintenta pidiendo JSON simple.

## Perfil del vault: comprobar 0.11.0

Recarga la extensión y abre el panel. Mientras el vault no tenga perfil verás **Este vault aún no tiene perfil** con **Revisar perfil**.

La barra de rayitas bajo el logo se llena y se vacía al abrir el panel y después sigue a la nota: un cuarto al detectar contenido, avance durante la preparación (con el porcentaje de la transcripción cuando lo hay), tres cuartos con la revisión abierta y llena al guardar. Con movimiento reducido en el sistema se coloca sin animación.

1. En **Opciones → Perfil del vault**, pulsa **Escanear el vault**. Se leen carpetas, nombres y metadatos; el contenido de tus notas no sale del ordenador.
2. Revisa **Documentos que puede leer la IA**, agrupados en instrucciones y skills, guías y plantillas, con los sugeridos ya marcados. En tu vault deberían estar marcados `AGENTS.md`, el skill `second-brain-vault`, tus guías de `99_Recursos/guias/` y las plantillas de los tipos que Anaco puede crear. Tus notas de `00_Sistema` no aparecen.
3. Pulsa **Proponer con IA**: la IA lee esos documentos y las estadísticas y propone el perfil. Con **Usar la propuesta automática** no se usa IA.
4. Lee **Lo que hará Anaco**: en pocas líneas, las zonas donde guardará (una regla por zona, por ejemplo `02_Cerebro`), el tipo por defecto, los metadatos, los adjuntos y cuántos documentos leerá la IA. Si quieres cambiar algo, abre el desplegable **Ajustar…** de esa parte: cada regla muestra su evidencia. El JSON completo sigue disponible.
5. Pulsa **Confirmar perfil**. Se guarda en la ruta indicada (propuesta: `99_Recursos/anaco/perfil.json`), que LiveSync sincroniza.
6. Captura una página y guárdala: la nota sigue las reglas del perfil y la estructura de tus plantillas. Tus notas existentes no se modifican.
7. Mueve o edita una guía del perfil: el panel avisará con **Revisar perfil**. Si un destino deja de existir, guardar en él muestra un error claro.

## Podcasts y entrevistas: comprobar 1.2.0

1. En Opciones, comprueba que **Duración máxima de vídeo/audio** permite la duración del podcast (hasta 240 minutos).
2. Abre un podcast o una entrevista de YouTube y deja el **Modo de captura** en Automático. Extrae los subtítulos y prepara la nota con IA. Una conversación de más de una hora tarda más: el progreso muestra «Leyendo el tramo… (n/total)» y después la síntesis.
3. En la revisión, **Propiedades y destino** dice «Preparada como podcast o entrevista». La nota trae ficha rápida, resumen, temas con su minuto, ideas clave, consejos, **Citas destacadas** y qué llevarte a la práctica. Cada `[mm:ss]` abre el vídeo en ese segundo, también el de cada cita. `formato` es `podcast` (o `entrevista`) y `fuente_autor` nombra solo a invitados y programa que constan en el título, el canal o la transcripción.
4. Si una cita no aparecía palabra por palabra en la transcripción, la explicación lo dice («Se ha descartado una cita…») y no está en la nota.
5. Pulsa **Preparar como vídeo** y confírmalo: la propuesta se rehace sin la forma de conversación y se pierden los cambios de esa revisión. **Preparar como podcast o entrevista** hace lo contrario; el modo **Podcast · entrevista** del panel lo fuerza desde el principio.
6. Para notas derivadas con «Una sola nota», usa **Sugerir una división** en la revisión.

## Recursos incrustados y modo de captura: comprobar 0.10.0

Recarga la extensión. Bajo el estado del servicio aparece **Modo de captura**:

- **Automático**: artículos y cursos. Reconoce publicaciones de X, demos de CodePen y clips silenciosos en la página principal. Los marcos de esos servicios no sustituyen al artículo ni piden permiso. El resto de marcos sigue la regla de siempre, para no alterar los cursos.
- **Artículo web**: además, el texto de la página principal tiene prioridad sobre cualquier marco con texto.
- **Curso · detección clásica**: el comportamiento anterior a esta versión, sin ninguna novedad. Úsalo si una lección de AWS o de la Xunta se detecta peor que antes y avísame.
- **Podcast · entrevista**: detecta como Automático, pero prepara cualquier vídeo como una conversación (ver «Podcasts y entrevistas»).

1. Abre <https://tympanus.net/codrops/2026/10/16/ksenia-kondrashova/> en Automático. El texto extraído es el del artículo. En **Recursos incrustados** aparecen los clips de vídeo (duración y peso), las demos de CodePen y las publicaciones de X, todos marcados salvo los clips de más de 20 MB. Los clips con peso desconocido o excesivo muestran un aviso. Los clips ya no aparecen como vídeos que transcribir. Al pasar el ratón por un recurso, o al enfocarlo con el teclado, el artículo se desplaza hasta él y lo rodea de amarillo con su etiqueta («Clip 1», «Demo 2», «Publicación 3»), igual que las imágenes. Un clip pausado empieza a reproducirse, sin sonido, al marcarlo. Si recargas la página y Anaco solo tenía el permiso de la pestaña activa, el panel dirá que no tiene permiso para leer esa página: pulsa **Permitir lectura** o **Detectar contenido** para concederlo; no es un visor de otro dominio.
2. Desmarca lo que no quieras y pulsa **Preparar**. La extensión pedirá acceso a `codepen.io`, `cdpn.io` y al dominio de los clips si aún no lo tiene.
3. En la nota guardada cada recurso aparece donde estaba en el artículo. Los que la IA no haya colocado van a **Recursos de la fuente**, al final:
   - Publicación: `![](https://twitter.com/…/status/…)`, que Obsidian muestra de forma nativa, y una cita con el texto.
   - Clip: el mp4 en `clips/` dentro de la carpeta de adjuntos del perfil y `![[…mp4]]`.
   - Demo: enlace al pen, código HTML/CSS/JS plegado y una copia ejecutable en `codepen/<usuario>-<pen>/index.html` dentro de la carpeta de adjuntos, con sus librerías al lado.
4. Para ver la demo dentro de la nota sin conexión instala el plugin **HTML Prototype Viewer** ([Gloumi/obsidian-html-prototype-viewer](https://github.com/Gloumi/obsidian-html-prototype-viewer)). No está en la lista oficial ni publica `main.js`: clónalo, ejecuta `npm install && npm run build` y copia `main.js`, `manifest.json` y `styles.css` en `<vault>/.obsidian/plugins/html-prototype-viewer/`; después actívalo en Plugins de la comunidad. La versión 1.0.1 compila sin cambios. Por defecto el plugin ejecuta la demo con el mismo origen que Obsidian: el código del pen puede acceder a la API de Obsidian y a su almacenamiento local. Activa **Strict isolation** en sus ajustes si no confías en el autor. Con esa opción, las demos con módulos ES pueden no cargar sus archivos locales; ábrelas entonces con **Abrir la demo sin conexión**. Interpreta los bloques `html-preview` que apuntan a un archivo del vault. No lo combines con el plugin oficial «HTML-Preview»: usa el mismo nombre de bloque y espera el HTML dentro de la nota. Sin plugin, **Abrir la demo sin conexión** abre el archivo en el navegador.
5. Comprueba un curso de AWS y otro de la Xunta en Automático: la detección, los vídeos y la transcripción deben comportarse como en 0.9.2. Si no es así, cambia a **Curso** y avísame.

Una demo que carga texturas u otros recursos al ejecutarse puede seguir necesitando conexión para esa parte; la nota lo indica cuando una librería no se pudo copiar.

## Nombre y nueva ubicación: comprobar 0.9.2

El proyecto está en la carpeta `anaco-ob/`. Carga `extension/manifest.json` desde esta nueva carpeta en `about:debugging#/runtime/this-firefox`; debe aparecer **Anaco** con un cristal facetado amarillo sobre fondo oscuro. La ruta de carga del complemento temporal debe apuntar a la nueva ubicación.

El servicio ya utiliza `~/.local/share/anaco-ob/`. El instalador migra la configuración, capturas e historial existentes y mantiene los alias necesarios para los trabajos pendientes. Comprueba tus opciones y la lista de pendientes; abre una captura para revisar y guardar como de costumbre.

## Revisión sin menús duplicados: comprobar 0.9.1

Recarga la extensión y abre una revisión. La selección de notas, Lectura / Editar Markdown, conexiones, división y guardado están en el panel lateral. La página muestra el contenido y los campos que necesitas revisar, junto con los ajustes y confirmaciones de propuestas. Conserva **Volver al artículo** y **Descartar**.

Cierra el lateral y pulsa **Abrir panel lateral** desde la revisión: debe recuperar el asistente sin iniciar otra captura ni perder las ediciones. Los botones de Lectura / Editar Markdown del lateral indican la vista activa.

## Conexiones y asistente de revisión: comprobar 0.9.0

Recarga la extensión y vuelve a abrir tu revisión actual desde los pendientes. Puedes recuperar las conexiones sin regenerar el texto: **Buscar conexiones** revisa cada tema, tus notas candidatas y los vínculos entre las notas nuevas. En propuestas con IA que todavía no tienen esta búsqueda, se ejecuta al abrir la revisión; también se repite tras aceptar una división.

1. Abre el tema de scroll o ciclo de renderizado del artículo de Codrops. Revisa sus conexiones propuestas con tus notas de GSAP y **Ver evidencia**. Marca las conexiones existentes que quieras guardar. La evidencia indica si procede de la nota revisada o de la captura original.
2. En **Entre las notas nuevas**, comprueba los enlaces con otros temas, además del índice. Puedes ver los dos extractos que justifican la relación y desmarcarla. Si excluyes una nota, sus enlaces dejan de aparecer en las notas que guardarás.
3. Mientras la revisión esté abierta, el panel lateral será un **Asistente de revisión**: permite recorrer notas, incluirlas o excluirlas, alternar lectura y edición, ir al destino o las conexiones, buscar enlaces, proponer una división y guardar. Los contadores indican dónde hay propuestas de conexión.
4. Prueba cerrar la pestaña de revisión manualmente: el panel debe volver a capturar la pestaña actual. Al reabrir una revisión pendiente se conservan tus ediciones. El asistente controla la revisión de la pestaña activa: si abres varias en la misma ventana, cambiar de pestaña cambia de revisión, y al pasar a otro artículo el panel muestra su captura hasta que vuelvas a la revisión. Las revisiones de otras ventanas tienen su propio contexto.

Las conexiones propuestas siguen pasando por tu revisión. Buscar conexiones actualiza los enlaces y no reescribe el contenido de las notas.

## Sugerir una división desde la revisión: comprobar 0.8.2

Recarga la extensión. En una nota abierta para revisar, pulsa **Proponer división** en el panel lateral. Funciona sobre el contenido que estás revisando, incluidas tus ediciones, y también sobre una nota temática de una propuesta existente.

1. Revisa el motivo, la síntesis que quedaría en la nota actual y los títulos y propósitos de los temas. **Ver contenido propuesto** permite leer cada parte antes de decidir.
2. **Conservar la nota actual** descarta la sugerencia. La nota y tus ediciones permanecen como estaban. Si no hay temas independientes útiles, se explica por qué no se recomienda dividir.
3. **Aplicar división al borrador** reorganiza los apartados y abre la propuesta para revisarla. Se conservan el código, las anotaciones y los pies de imagen editados. Puedes ajustar títulos, destinos, imágenes y enlaces antes de **Guardar y volver**.

Solicitar o aceptar una sugerencia no escribe notas en el vault: el guardado final sigue siendo explícito. Si la nota cambia mientras se prepara la sugerencia, pide una nueva; la aplicación rechaza aplicar una propuesta desactualizada.

## Ajustes visuales: comprobar 0.8.1

Recarga la extensión y vuelve a abrir el panel. Durante un trabajo, estrecha el panel: la fase, el mensaje y el motor deben ajustarse al ancho disponible sin scroll horizontal, incluso con nombres largos de recursos. El título del trabajo conserva el recorte con puntos suspensivos.

En la revisión, **Lectura / Editar Markdown** permanece en su lugar encima de la nota. Al desplazarte hacia abajo, esa barra sale de la vista con el contenido y no te acompaña ni se superpone a la lectura.

## Organización y código: comprobar 0.8.0

Recarga la extensión desde `about:debugging#/runtime/this-firefox` y vuelve a preparar el artículo. Antes de preparar, **Organización de la propuesta** permite elegir **Una nota con apartados** (predeterminado), **Varias notas enlazadas por temas** o **Automático**. En Opciones puedes cambiar el valor predeterminado para las capturas nuevas. La elección también llega a la preparación automática de PDF, libros y vídeo.

En un tutorial con código, revisa que el resumen enseñe el mecanismo y seleccione ejemplos que aporten comprensión o consulta, con una explicación de sus parámetros y límites. No tiene que incluir código por obligación ni copiar todos los ejemplos. En el artículo [Scroll-Driven Ghost Trails](https://tympanus.net/codrops/2026/10/13/scroll-driven-ghost-trails/) se ha comprobado la captura literal de los 17 bloques y la selección de una muestra con IA real.

Ejemplos de prueba: [una nota](.test-artifacts/code-notes-eval/single/source.md) y [síntesis con notas temáticas](.test-artifacts/code-notes-eval/linked/source.md). Se guardan fuera de tu vault.

## Aplicar un vault detectado: comprobar 0.7.3

Si has movido el vault, entra en Opciones, selecciona la detección automática y elige el nuevo. El aviso distingue el vault seleccionado de la ruta que está en uso. Pulsa **Guardar y volver**, disponible en la barra superior: aplica la ruta y regresa a la captura. El panel debe reconectar y quitar el error de la ruta antigua sin cerrarlo y abrirlo de nuevo.

**Volver a la captura** conserva los cambios pendientes sin aplicarlos. **Guardar y volver** los aplica antes de salir.

## Salir de Opciones: comprobar 0.7.2

Recarga la extensión desde `about:debugging#/runtime/this-firefox`. Entra en **Opciones** desde el panel y pulsa **← Volver a la captura**: se cierra la pestaña de Opciones y vuelves a la que tenías abierta. El botón permanece visible al bajar por la página. Si abres Opciones directamente desde el gestor de extensiones, permite volver a la herramienta de captura en esa misma pestaña.

Los cambios sin guardar se conservan localmente al salir y se recuperan al volver a entrar. Solo **Guardar opciones** los aplica al servicio. Comprueba también el regreso después de guardar.

## Ventanas y foco: comprobar 0.7.1

Recarga la extensión, cierra y abre el panel donde quieras utilizarlo. Abre después otra ventana de Zen, también si la colocas en otro escritorio: no debe quedarse abierto un panel heredado en esa ventana. La original conserva el suyo. Puedes abrirlo expresamente con el icono, el atajo o el menú contextual.

Con el panel cerrado, abrir una pestaña no lo vuelve a abrir. Si una preparación termina cuando ya estás en otra pestaña o ventana, su revisión queda en segundo plano en la ventana de origen; puedes acceder a ella al volver o desde los pendientes. La detección de un panel sigue las pestañas de su propia ventana.

Esta corrección utiliza el cierre del documento lateral disponible desde Firefox 133; el mínimo declarado pasó entonces a 133 (hoy es 140) y se verificó con Zen 1.22.3b.

## Primera revisión de 0.7.0

Recarga la extensión desde `about:debugging#/runtime/this-firefox` y cierra y abre su panel. El servicio local ya está actualizado. Conserva la configuración y el vault actuales.

1. **Captura y revisión en un recorrido.** En un vídeo, PDF o libro, deja marcada **Abrir la revisión al terminar de extraer**. El botón crea la propuesta y abre su revisión al acabar. Para extraer primero y elegir figuras antes de resumir, desmarca esa opción. **Ajustes de esta captura** contiene el proveedor; la intención sigue visible antes de empezar. Guardar continúa siendo una decisión explícita.
2. **Calidad de notas.** Prepara de nuevo un material representativo. El criterio nuevo prioriza mecanismos, diferencias, matices, ejemplos y límites; usa una o varias notas según lo que aporte cada tema. Los borradores antiguos conservan su texto hasta que pidas una nueva propuesta.
3. **Ajustes por apartado.** En la revisión, abre la nota y ve a **Ajustar esta nota**. Selecciona la nota completa o un encabezado y pulsa **Explicar mejor**, **Reducir** o **Desarrollar**. Puedes añadir una indicación. Compara **Actual** y **Propuesta** y aplica o descarta el cambio. **Deshacer ajuste** recupera el estado anterior; se conservan hasta cinco estados en este navegador.
4. **Integrar temas.** Selecciona otra nota derivada de la misma propuesta y pulsa **Proponer integración**. Solo al aceptar se integra su texto y se excluye la otra nota del guardado. Las páginas, imágenes y conexiones se ajustan. Puedes deshacerlo antes de guardar.
5. **Conexiones.** Las notas existentes muestran tipo de relación, motivo y evidencia. Puedes cambiar el tipo o descartar el enlace. Las conexiones entre notas nuevas se muestran aparte; desmarcar una conexión la elimina en ambas direcciones. Cambiar nombres, integrar o excluir notas vuelve a resolver las rutas.
6. **Ampliar una nota existente.** En **Guardar como**, elige **Ampliar una nota existente** y selecciona una candidata. Revisa su contenido actual y el aporte que se añadirá al final; después marca **He revisado el aporte y quiero añadirlo**. Cada ampliación necesita aceptación. Si cambias el aporte o la nota original cambia en Obsidian, hay que revisarlo de nuevo. El contenido y frontmatter anteriores se conservan; el aporte incluye procedencia y asistencia de IA. Una copia anterior se guarda en el estado local de la captura.
7. **Cancelar y continuar.** Mientras extrae o prepara, pulsa **Cancelar y conservar avance**. Detiene el proceso, no solo oculta el indicador. Los trabajos de transcripción o preparación aparecen en **Trabajos recuperables**, y **Capturas pendientes** se despliega solo para mostrarlos. **Reanudar** utiliza el archivo recibido y los segmentos completos de Whisper guardados; una transcripción ya terminada se reutiliza. Una descarga interrumpida antes de recibir el archivo debe repetirse desde el origen. Los libros conservan las páginas recibidas y se retoman con su botón de extracción en la misma captura.
8. **Pantallas estrechas.** La revisión ofrece **Destino y enlaces** para alternar entre propiedades y contenido cuando no caben dos columnas. Prueba títulos largos, tablas y código: solo los bloques de datos deben tener desplazamiento horizontal, no la página completa.

Las pruebas nuevas usaron vaults temporales. No se han ampliado, movido ni reorganizado notas personales durante el desarrollo. El aprendizaje de carpetas y la aceleración AMD siguen siendo ampliaciones posteriores.

## Progreso y galería: qué cambia en 0.6.2

Recarga la extensión, cierra y abre su panel. Mientras procesa un vídeo verás una tarjeta destacada con la fase y el tiempo transcurrido. Distingue búsqueda de subtítulos, descarga, carga del modelo, transcripción y extracción de fotogramas. La transcripción muestra el audio procesado frente a su duración y el porcentaje medido; las fases sin avance cuantificable usan una barra indeterminada. No es una estimación de tiempo restante.

La galería tiene scroll propio, conserva todas las imágenes de artículo detectadas y muestra cuántas están elegidas. Al llegar a ocho se deshabilitan las casillas restantes; puedes seguir viendo sus filas, localizar las imágenes y desmarcar alguna para elegir otra, incluso al final de la lista. Se mantienen los límites de tamaño de los adjuntos. La selección de figuras de un libro continúa separada de la lectura de todas sus páginas.

Un reproductor antiguo cuyo nombre técnico era `youtube.googleapis` aparece como **YouTube**, con su enlace de vídeo normalizado cuando contiene un identificador válido. Una dirección de API no se ofrece como archivo de vídeo.

La transcripción actual usa **Whisper en CPU, con int8**, incluso si el ordenador tiene una 9070 XT. La aceleración AMD requiere integrar y validar otro motor; no está activada en esta entrega. La CPU, duración y modelo elegido influyen en la velocidad. En Opciones, `tiny` prioriza rapidez y `small` necesita más recursos. Se siguen aprovechando subtítulos antes de transcribir.

## Vídeos de AWS: corrección del 403

Recarga la extensión desde `about:debugging#/runtime/this-firefox`, cierra y abre el panel y comprueba que la versión es **0.7.1**. En AWS, inicia el vídeo, pulsa **Detectar de nuevo** y después **Crear nota del vídeo** (o **Extraer subtítulos o transcribir** si has desmarcado la revisión automática). La descarga conserva el marco del reproductor y prueba primero su contexto de sesión; se aplica también a los manifiestos y segmentos HLS. El usuario ha confirmado que la corrección funciona en AWS.

Si sigue fallando, utiliza el botón de copiar error. El diagnóstico añade `extraction` con el tipo de recurso, dominio del reproductor, dominio del recurso y resultado de cada contexto intentado. No incluye parámetros del enlace firmado ni cookies. Un 403 persistente no demuestra por sí solo si el enlace ha caducado o si la plataforma exige otro mecanismo: ese diagnóstico permite distinguir el siguiente paso.

## Generación adaptativa: qué probar primero

Recarga la extensión desde `about:debugging#/runtime/this-firefox`, cierra y abre su panel. Se conserva tu configuración. Para probar el nuevo criterio hay que volver a **Preparar y abrir revisión**: abrir un borrador antiguo conserva su propuesta anterior.

1. Extrae el libro de AWS y escribe una intención como «Preparar apuntes por temas para estudiar este módulo». Durante la extracción o la preparación, cambia a otro artículo: el panel debe seguir mostrando el libro y su progreso.
2. Prepara con IA. Si hay varios temas sustantivos, la revisión mostrará **Propuesta de notas**, con una síntesis y apuntes por temas. Una fuente corta o repetitiva puede producir una sola nota.
3. Pulsa cada título o sus enlaces en la lectura para recorrer la propuesta. Revisa el texto, **Tipo de nota**, carpeta y nombre por separado. Las plantillas orientan la redacción; no deberían aparecer secciones de un artículo de diseño en unos apuntes de AWS.
4. Renombra un archivo y desmarca una nota. Los enlaces deben apuntar a los nombres finales y excluir las notas no seleccionadas. Puedes cerrar o recargar la revisión sin perder esas ediciones.
5. Revisa también las conexiones propuestas con notas existentes y las imágenes de cada apunte. Pulsa **Guardar N notas y volver** para guardar la selección y regresar al origen.
6. En Obsidian, comprueba el índice, los enlaces de vuelta desde los apuntes y las conexiones entre temas. Después prueba un artículo de Codrops y un texto sobre un modelo mental: su estructura y clasificación deberían adaptarse.

El modelo de texto sigue siendo `gpt-6-luna`: en la prueba real ha distinguido curso, caso de diseño y modelo mental. El análisis visual conserva el modelo configurado. No se reorganizan ni limpian notas anteriores.

## 1. Instalar el componente local

Desde una terminal:

```bash
pipx install git+https://github.com/samuhlo/anaco-ob
anaco-ob install --vault ~/ruta/a/tu/vault
anaco-ob doctor
```

`anaco-ob install` registra el servicio de usuario para Firefox y Zen en Linux, macOS (carpetas de Mozilla y de Zen) y Windows (registro de usuario de Mozilla). En Windows, Zen no documenta dónde busca el servicio: si no conecta, avísanos. `anaco-ob doctor` indica qué falta y cómo resolverlo. Desde el repositorio, `python3 scripts/install.py` hace lo mismo para desarrollo y prepara el ZIP de la extensión. No modifica tus notas ni tus pestañas. La aplicación utiliza Python estándar; Selenium solo se usa en las pruebas de desarrollo.

Elige tu vault mediante detección automática o ruta manual en Opciones. Después confirma su **Perfil del vault** en Opciones: define los destinos, tipos, nombres, metadatos, carpeta de adjuntos y carpetas de relaciones. Sin perfil, el panel lo avisa y no se pueden preparar notas.

## 2. Cargar la extensión en Zen

1. Abre `about:debugging#/runtime/this-firefox` en Zen.
2. Pulsa **Cargar complemento temporal**.
3. Selecciona `extension/manifest.json` dentro de la carpeta del proyecto.
4. Abre una página web y pulsa el icono de **Anaco** en el menú de extensiones. Se abrirá el panel lateral con la captura.

También puedes capturar una página con `Alt+Mayús+S` o usar los menús contextuales sobre una frase seleccionada o una imagen. Si otro atajo del sistema usa esa combinación, puedes cambiarla desde la gestión de atajos de extensiones de Zen.

La instalación temporal dura hasta que cierres Zen. Después puedes volver a cargar el mismo `manifest.json`. La firma y distribución permanente no están incluidas en esta entrega.

Para aplicar una corrección mientras está cargada, vuelve a `about:debugging#/runtime/this-firefox`, busca **Anaco** y pulsa **Recargar**. Cierra y abre su panel y repite la captura. No hace falta reiniciar Zen ni reinstalar el servicio.

## 3. Comprobar las opciones

En el panel, abre **Opciones** y revisa:

- Cómo localizar el vault: **Detectar automáticamente** busca en el registro de Obsidian y en carpetas habituales; **Introducir la ruta manualmente** permite escribir una ruta absoluta o usar `~`. En automático, pulsa **Buscar vaults** para repetir la búsqueda y elige el resultado si aparecen varios. Revisa la ruta y pulsa **Guardar opciones**.
- Carpetas que se consultarán para sugerir relaciones.
- Modo de preparación: IA con Codex o captura manual.
- Modelo: `gpt-6-luna`, probado con la sesión de ChatGPT disponible en este equipo.
- Modelo visual: `gpt-6.1-sol`, utilizado cuando se analizan imágenes o páginas de un PDF. Puedes cambiarlo por otro disponible en tu cuenta.
- Política de imágenes: **Automático** consulta primero el pie HTML, descripciones accesibles, `alt` y `title`; reutiliza análisis previos de la misma imagen y considera nombres de archivo claros como pistas. Solo envía a visión lo que sigue necesitando análisis. **Sin visión** no envía imágenes; **Forzar visión** analiza todas las seleccionadas.
- Límites de páginas PDF, páginas visuales, duración de vídeo y motor de transcripción local.
- Carpeta de adjuntos.

El estado debe indicar que el servicio está conectado y que el vault está disponible. Si has movido el vault, Opciones sigue cargando y permite localizarlo de nuevo. Solo se ofrecen carpetas existentes que encajen con tu estructura. Para clases, debe existir el destino curso/asignatura.

Para utilizar la IA, Codex debe estar instalado y autenticado. Puedes comprobarlo en la terminal:

```bash
codex login status
```

Al preparar con IA se envían al proveedor el contenido capturado y hasta ocho fragmentos de notas candidatas. En automático se adjuntan únicamente las imágenes que necesitan análisis. Si ninguna lo necesita, se mantiene el modelo ligero de texto. El audio se transcribe localmente; después se envía el texto al modelo para resumirlo.

Las páginas de PDF y los fotogramas se analizan visualmente en automático porque el objetivo incluye comprender su contenido completo. Un pie existente no sustituye esa lectura. Puedes impedirlo seleccionando **Sin visión**, teniendo en cuenta que entonces solo se usa el texto extraído y las descripciones disponibles.

La revisión muestra el origen de cada pie —HTML, nombre de archivo, visión o descripción reutilizada— y cuántas imágenes se enviaron a visión. Un nombre de archivo se etiqueta como tal; nunca se presenta como una observación visual verificada. Las descripciones generadas para imágenes de artículos se guardan en caché local por huella del archivo para no volver a analizarlas.

## 4. Primera prueba: un artículo

1. Abre un artículo que tenga relación con algo que ya guardas en el vault.
2. Pulsa el icono de la extensión.
3. Despliega **Revisar contenido capturado** y comprueba que aparece el artículo correcto.
4. Selecciona solo las imágenes que aportan valor. Cada fila tiene número y, cuando se puede obtener sin permisos adicionales, una miniatura. Al pasar el cursor o enfocar su casilla con el teclado, se centra la imagen en el artículo y aparece un marco amarillo temporal. La extensión puede pedir permiso para descargar las imágenes de los dominios elegidos.
5. Escribe opcionalmente por qué quieres guardarlo.
6. Pulsa **Preparar y abrir revisión**. La primera solicitud puede tardar. Se abrirá una pestaña nueva con la nota renderizada.
7. Lee el resumen en la vista amplia. Usa **Editar Markdown** para modificarlo; las propiedades, el destino y las conexiones están al lado.
8. Lee la justificación y evidencia de cada conexión; marca las que tengan sentido.
9. La lectura se actualiza automáticamente al editar. Puedes ampliar las imágenes haciendo clic sobre ellas y consultar el Markdown completo y frontmatter en el desplegable inferior.
10. Pulsa **Guardar y volver**. Se guarda la nota, se cierra únicamente la pestaña de revisión y vuelves a la pestaña original del artículo. El panel ofrece **Abrir en Obsidian**.

Comprueba en Obsidian que la nota se lee bien, las imágenes aparecen y los wikilinks abren las notas correctas. Un enlace con `#Sección` debe llevar a ese apartado de la nota relacionada. Puedes guardar sin relaciones si no hay ninguna adecuada.

**Descartar** cierra la revisión, retira la captura de pendientes y vuelve al artículo, sin crear una nota. **Volver al artículo** cierra la revisión conservando el borrador y tus ediciones; puedes retomarlo desde **Volver a la revisión** o **Capturas pendientes**. Si la pestaña original ya no existe, se abre de nuevo la URL capturada.

## 5. Segunda prueba: una frase

Selecciona una frase y abre el menú contextual → **Guardar frase en Second Brain**. Comprueba que la sección de cita conserva el texto exacto y que tu interpretación aparece separada. El autor solo se incluye cuando se ha obtenido de la página.

Puedes escoger **Captura manual · sin IA** para escribir tú la interpretación. En ese caso, el frontmatter utiliza `llm_asistido: false`.

## 6. Tercera prueba: una imagen

Sobre una imagen, menú contextual → **Guardar imagen en Second Brain**. Prepara con IA y comprueba su descripción en la revisión. Puedes corregir el pie y desmarcar la imagen antes de guardar. Comprueba que el archivo aparece dentro de la carpeta de adjuntos y sigue visible en Obsidian sin depender de la URL original.

Se admiten PNG, JPEG, GIF y WebP, hasta 3 MB por imagen, ocho imágenes y 5 MB en conjunto. Si la imagen no puede descargarse, se mostrará el error; no se presentará como conservada. SVG, canvas y recursos protegidos pueden necesitar una captura o conversión manual en esta versión.

## PDF: visor de Zen, páginas de cursos y archivos locales

1. Abre el documento y el panel de la extensión. Se detectan URLs `.pdf`, documentos incrustados y visores nativos con tipo `application/pdf` aunque la URL no tenga extensión. Si Zen pide acceso al sitio, pulsa **Permitir detectar el contenido del visor**.
2. En una página de curso, busca **Contenido de esta página → PDF detectado**. Los enlaces habituales de archivos de Canvas se incluyen entre los candidatos.
3. Pulsa **Extraer PDF y páginas**. Puedes indicar `1-5,8` para procesar un rango concreto.
4. Revisa el texto y selecciona las capturas de página que quieras que vea el modelo.
5. Pulsa **Preparar y abrir revisión** con IA. El modelo resume, describe las páginas y recomienda conservar las que aportan valor.
6. En **Imágenes conservadas**, cambia la selección y corrige los pies si hace falta.

Un PDF local detectado muestra el selector de archivo. Para importar deliberadamente otro archivo descargado, abre **Opciones → Importar un archivo local**. El importador general no aparece en las páginas web.

La configuración inicial procesa hasta 60 páginas y genera hasta seis capturas visuales candidatas. Los límites son editables. Si se procesa una parte del documento, el alcance aparece en la nota. Los diagramas vectoriales se conservan dentro de una captura de su página; no se recortan automáticamente como figuras independientes. Si el PDF no tiene texto, se intenta OCR local en las páginas renderizadas y el modelo visual puede leer esas páginas. Las páginas que queden sin leer se indican explícitamente.

## Vídeos: subtítulos, archivo y transcripción

En una página con un vídeo detectado, usa **Vídeo o audio detectado → Extraer subtítulos o transcribir**. El orden es:

1. Subtítulos accesibles en el reproductor o en sus pistas.
2. Subtítulos ofrecidos por una plataforma compatible con `yt-dlp`.
3. Descarga de audio accesible y transcripción local con Whisper. Si una pista de subtítulos falla, se intenta el audio cuando ya hay un recurso compatible autorizado.

La detección busca también recursos multimedia ya cargados por el reproductor cuando su URL visible es `blob:`. Para HLS sin cifrar se recuperan manifiesto y segmentos desde el navegador con su sesión; no se exportan cookies. Hay límites de tamaño y duración. Los directos, segmentos cifrados, DASH y formatos de segmentos no admitidos muestran un error específico. Si no aparece una fuente accesible, inicia el vídeo y pulsa **Detectar de nuevo**.

Desde **Opciones → Importar un archivo local** puedes importar MP4, WebM, M4A, MP3, WAV, OGG, FLAC o MOV, o una transcripción SRT/VTT. Los archivos locales de vídeo generan hasta tres fotogramas candidatos, además de su transcripción. Con subtítulos solos no se descargan automáticamente todos los fotogramas del vídeo.

Los subtítulos y la voz quedan con referencias `[mm:ss]`. En un vídeo de YouTube, cada referencia de la nota enlaza al vídeo en ese segundo, y un rango `[49:00–55:41]` a su inicio; una marca posterior al final del vídeo queda como texto. Si el vídeo tiene capítulos, la transcripción los marca como `[Capítulo mm:ss] Título` antes de su primera frase. La nota indica si proceden de la plataforma, de un archivo aportado o de Whisper. Los subtítulos importados no se presentan como comprobados contra el vídeo completo.

Límites: PDF/subtítulos hasta 100 MB; archivos locales de audio/vídeo hasta 1 GB. Las descargas directas desde el navegador se limitan a 100 MB. Por defecto se admiten hasta 240 minutos (el máximo); una configuración guardada antes conserva su valor, que se cambia en Opciones. Una transcripción de más de una hora se lee por tramos de unos 35 minutos, empezando por un capítulo cuando lo hay, y después se sintetiza entera; los tramos leídos se conservan si hay que reintentar. El audio se procesa en CPU; un curso largo puede tardar varios minutos. Puedes cerrar el panel y seguir navegando mientras el proceso continúe en segundo plano.

### AWS Academy/Canvas y Xunta/Moodle

La detección recorre los marcos anidados por separado, incluidos los reproductores que estén dentro de otro visor. Si falta acceso, aparece **Permitir detectar el contenido del visor**. Autoriza los dominios indicados y se repite la búsqueda automáticamente; no hay que elegir manualmente cada marco.

La extensión utiliza la sesión del navegador para descargar los recursos seleccionados. Si el visor o el reproductor no expone el archivo/subtítulos, abre el recurso en su pestaña original o descárgalo desde la plataforma e impórtalo mediante Opciones. No se ha validado todavía el contenido privado de los enlaces concretos facilitados por el usuario: el asistente no tiene acceso a sus pestañas autenticadas.

### Google Drive

En el visor de un archivo de vídeo de Drive se detecta su enlace y se intenta descargar con la sesión del navegador. Puede requerir permiso para los dominios de descarga de Google. Los permisos del archivo, las confirmaciones de descarga y algunos visores pueden impedir la extracción directa; importar el archivo descargado es la alternativa comprobable para vídeos privados. No hay conexión OAuth independiente con Drive en esta entrega.

### Instalar la transcripción en otro equipo

En este equipo ya está instalada y probada. Para reproducirla en otro entorno con `uv`, Poppler, FFmpeg y `yt-dlp` disponibles:

```bash
anaco-ob install-media
```

El modelo Whisper se descarga la primera vez. `base` es la opción inicial; `small` mejora la precisión a costa de tiempo y una descarga mayor. Las dependencias están aisladas en `media-venv/`, dentro de la carpeta de datos del servicio. Desde el repositorio, `sh scripts/install-media.sh` las instala en `.media-venv/`, que tiene preferencia.

## 7. Qué validar y anotar

- ¿La captura contiene lo importante y excluye navegación o publicidad?
- ¿El resumen conserva matices y explica qué puedes aprender?
- ¿Se distingue la fuente de tus comentarios y de las sugerencias generadas?
- ¿El destino, nombre y frontmatter encajan con tu sistema?
- ¿Cada relación te ayuda a comprender, recuperar o aplicar algo concreto?
- ¿Hay relaciones evidentes que faltan o conexiones forzadas que sobran?
- ¿Las citas e imágenes se conservan correctamente?
- ¿El resaltado identifica la imagen que esperabas y desaparece al salir de su fila?
- ¿La nueva pestaña permite leer y editar cómodamente? ¿Guardar y Descartar vuelven al artículo correcto?

Si encuentras un fallo, apunta URL, tipo de captura, pasos, mensaje mostrado y resultado esperado. Para un problema de relaciones, indica también qué nota debía proponerse o por qué una propuesta no tiene sentido.

## 8. Recuperación y límites de la versión

- Una captura preparada se conserva en la cola local. Puedes recuperarla en **Capturas pendientes** si falla la IA o cierras el panel.
- Los cambios del editor se conservan en el almacenamiento local de la extensión al escribir, incluso si cierras la pestaña de revisión enseguida. Regenerar sustituye esa propuesta; recuperar una captura conserva las ediciones locales disponibles.
- Cambiar el vault no mueve capturas: los pendientes se muestran al volver a su vault de origen.
- Los duplicados exactos y nombres existentes se rechazan al crear notas. Las ampliaciones solo se añaden tras revisar un aporte y comprobar la versión de la nota existente.
- Las relaciones con notas existentes requieren aceptación y se revalidan antes de guardar. Enlazan la sección que contiene la evidencia cuando se puede señalar sin ambigüedad; si no, la nota entera. Los enlaces entre notas nuevas se revisan en su propuesta y se ajustan a las notas seleccionadas y sus rutas finales.
- La vista de lectura de la pestaña admite Markdown estándar, tablas, listas, código, enlaces y las imágenes locales conservadas. Las funciones de plugins de Obsidian se comprueban en Obsidian.
- Para localizar imágenes, el artículo debe seguir abierto y sin navegar a otro sitio. Tras recargar la extensión, realiza una captura nueva para volver a vincularla con su pestaña.
- Las páginas con contenido dinámico pueden requerir seleccionar el fragmento relevante. De los marcos incrustados se reconocen publicaciones de X, CodePen y clips silenciosos; otros widgets con texto pueden requerir el modo **Artículo web**. El texto extraído se puede revisar antes de preparar.
- Aún no hay guardado automático ni aprendizaje de organización. La actualización de notas existentes se limita a añadir un aporte revisado; no reescribe su contenido previo. Las notas derivadas se proponen para revisión. Tampoco se garantiza acceso a todos los reproductores privados o protegidos.

## 9. Archivos locales

- Código y documentación: la carpeta del proyecto, `anaco-ob/`.
- Configuración, cola e historial: `~/.local/share/anaco-ob/`.
- Contrato editorial de la aplicación: `skills/anaco-ob/SKILL.md`, dentro del proyecto. Se incorpora al contexto de generación junto con los documentos del vault que selecciona su perfil, que mandan sobre él.
- Perfil del vault: el `.json` que eliges al confirmarlo, por ejemplo `99_Recursos/anaco/perfil.json`. La ruta se recuerda en la configuración local y, en otro ordenador, se encuentra buscando `anaco/perfil.json`.
- Manifiestos del servicio: `~/.mozilla/native-messaging-hosts/org.samuh.anaco_ob.json` y `~/.config/zen/native-messaging-hosts/org.samuh.anaco_ob.json`.

La aplicación no guarda claves de API. Utiliza la autenticación gestionada por tu instalación de Codex.

## 10. Pruebas de desarrollo

```bash
python3 -m unittest discover -s tests -v
npm test
python3 scripts/smoke_ai.py
python3 scripts/smoke_media.py --vision --audio .test-artifacts/jfk.flac
```

Las órdenes de smoke con IA consumen solicitudes con contenido de prueba. La última requiere la muestra de audio preparada durante el desarrollo. Las pruebas de navegador requieren Selenium y el controlador oficial de Mozilla; los resultados se documentan en `docs/VALIDACION.md`.

## Comprobar la localización del vault (0.3.2)

1. Recarga la extensión y abre Opciones. Se conserva la ruta que ya tenías; las configuraciones anteriores aparecen como manuales.
2. Cambia a **Detectar automáticamente**. Debe aparecer tu vault registrado en Obsidian. Si hay varios resultados, selecciona el correcto.
3. Pulsa **Guardar opciones** y vuelve a abrir Opciones: deben conservarse el modo y la ruta.
4. Para una ubicación fuera de la búsqueda, elige **Introducir la ruta manualmente**, escribe la carpeta concreta del vault y guarda. Una carpeta inexistente muestra un error sin sustituir la configuración válida.

La búsqueda automática consulta el registro de Obsidian (también XDG y Flatpak), comprueba `.obsidian` o la estructura del Second Brain y explora ubicaciones como Documentos, Notas y carpetas de sincronización hasta una profundidad limitada. No lee las notas ni utiliza IA. No cambia el vault guardado al encontrar otro; si mueves una carpeta, vuelve a buscar y guarda la ruta nueva. Las capturas pendientes continúan vinculadas a su vault de origen.

## Detección de la pestaña actual (0.4.0)

- Al cambiar de pestaña o navegar, el panel actualiza la detección cuando no hay un trabajo en curso. Durante una extracción o generación conserva el origen y progreso del trabajo. Una respuesta lenta de otra pestaña no puede sustituirlos.
- El botón de extraer PDF aparece solo si hay evidencia de un PDF. El de vídeo aparece cuando hay un recurso o subtítulos que se pueden intentar extraer.
- Una página vacía, un inicio de sesión o un reproductor sin fuente accesible muestran el motivo; no se ofrecen todos los métodos de importación como alternativa genérica.
- Una nota que se está generando continúa en segundo plano. Su resultado queda asociado a su origen y también puede recuperarse en Pendientes.
- Las detecciones con problemas ofrecen **Diagnóstico de detección**, con dominios, recuentos y estado de acceso. No incluye cookies, texto de notas ni parámetros de URLs firmadas. Si AWS Academy o Xunta siguen fallando, copia ese diagnóstico junto al error mostrado para poder identificar su visor concreto.

Para aplicar la versión: recarga Anaco desde `about:debugging#/runtime/this-firefox` y cierra y vuelve a abrir su panel. Abre una de las lecciones, autoriza su visor si se solicita y comprueba la detección con el vídeo iniciado. El contenido privado real de esas dos plataformas sigue pendiente de validación en tu sesión.

## Copiar errores (0.4.1)

El botón pequeño **Copiar** junto al error copia su mensaje, la versión de la extensión y el diagnóstico disponible. Cambia a **Copiado ✓** al terminar. También puedes copiar desde el apartado de diagnóstico. Si el portapapeles está bloqueado, se muestra un campo con todo el texto ya seleccionado para pulsar Ctrl+C. El error original se conserva.

## Libros y lectores incrustados (0.4.2)

El panel puede mostrar **LECTOR HTML** cuando encuentra páginas con texto, `canvas`, SVG o imágenes de fondo. La captura considera el contenido cargado en el documento, incluido el que queda por debajo de la pantalla; no se limita a una captura del área visible. Excluye páginas ocultas mediante CSS y no pulsa anterior/siguiente ni cambia el progreso del curso.

Si el lector ha descargado un archivo `.pdf` o expone el parámetro de archivo de un visor PDF.js, aparece **Extraer PDF y páginas**. En ese caso se prioriza el documento original sobre las imágenes del visor, conservando los límites y el rango de PDF configurados.

Para un libro HTML, el texto se limita a 120.000 caracteres y se ofrecen candidatas visuales con límites de número y tamaño. Se preseleccionan hasta ocho imágenes para que una página dibujada también llegue al modelo visual. El aviso de alcance distingue el contenido cargado de una lectura verificada del libro entero. Si hay más superficies que candidatas, se muestra antes de preparar y se conserva en la nota. Los SVG y canvas ilegibles por restricciones del navegador también se indican; no se inventa su contenido.

La autorización de marcos se decide con las direcciones realmente cargadas en Zen. La dirección antigua de un iframe tras una redirección ya no genera por sí sola un permiso pendiente. El texto de `sso.canvaslms.com` y los contenedores identificados no se utiliza como si fuera la lección. El diagnóstico añade recuentos y tipos de superficies por marco, sin incluir el texto de la página ni parámetros de sus direcciones.

Para comprobar AWS, carga la 0.4.2, abre el libro y pulsa **Detectar de nuevo**. Si aparece un PDF, usa su extracción. Si aparece **LECTOR HTML**, revisa el texto, las páginas candidatas y el aviso de alcance. Si vuelve a fallar, copia el diagnóstico nuevo: ahora permite distinguir un contenedor, una página dibujada y una denegación real.

## Libros completos de muchas páginas (0.5.0)

Los lectores de libros tienen ahora un flujo propio. El límite del selector de figuras no limita la lectura del libro.

1. Recarga la extensión y abre el lector. Debe aparecer **LECTOR HTML** con el número de páginas localizadas; para el ejemplo del curso, comprueba que sean 55.
2. Pulsa **Extraer libro completo**. Se transfieren las páginas una a una al servicio local y se muestra el avance. Puede desplazarse por el lector para cargar sus páginas; al terminar restaura el scroll. No pulsa botones ni cambia de lección.
3. Al acabar debe aparecer **55/55 páginas capturadas**. Se conserva el texto HTML y se aplica OCR local a las páginas gráficas que lo necesitan. No se presenta una extracción incompleta como completa: si falla una página, se indica su número y se conservan las recibidas para reintentar.
4. Pulsa **Preparar y abrir revisión** con IA. Se leen todas las páginas por lotes, por defecto de seis, y después se sintetiza el libro completo y se proponen relaciones con el vault. Los lotes ya completados se reutilizan tras un fallo o reintento con la misma configuración e intención.
5. Las imágenes del selector son figuras candidatas para adjuntar a la nota. Desmarcarlas no elimina esas páginas de la lectura del libro. La revisión permite decidir qué figuras conservar.

La detección enumera páginas sin rasterizar el libro repetidamente. Los cambios de estilo del lector ya no disparan capturas que vacían y reconstruyen el panel. Las páginas se transfieren en fragmentos, evitando un mensaje enorme con las 55 imágenes.

**Opciones → Libros, PDF y vídeo → Páginas por lote** permite ajustar entre una y ocho por solicitud. Se procesan todos los lotes. La lectura visual respeta la política configurada: con **Sin visión**, solo se usa HTML/OCR; si una página carece de texto recuperable, se pide activar visión antes de afirmar que se ha leído el libro completo.

El texto, las páginas y las lecturas intermedias se conservan en `~/.local/share/anaco-ob/readers/`, separados por extracción y vinculados al vault. Las notas y adjuntos finales siguen requiriendo revisión. La reanudación de transferencia utiliza el mismo lector y captura; si recargas o cambias el libro, vuelve a detectar para evitar mezclar páginas distintas.

La versión admite hasta 500 páginas localizables en el DOM del lector. Un visor que recicla unas pocas páginas y no expone las restantes puede requerir una adaptación específica; comprueba el número localizado antes de empezar. Las páginas no dibujadas o protegidas se notifican sin omitirlas en silencio.

## Panel vinculado y cola de enlaces (1.2.1)

1. Abre una clase con tu sesión iniciada y pulsa Anaco. Cambia a otra pestaña: el panel conserva la clase de origen y cualquier trabajo continúa. Para capturar la nueva pestaña, pulsa el icono o **Usar la pestaña actual**.
2. Cambia el panel a **Varios enlaces**, pega los enlaces (uno por línea) y elige el contenido. Para clases de vídeo puedes seleccionar **Vídeo o audio de la clase**. La cola tiene su propia intención y organización; la IA y el modo salen de **Ajustes de captura**, que siguen visibles debajo; el modo automático pide una captura individual si encuentra varios recursos posibles.
3. Pulsa **Preparar enlaces** y concede los permisos de los dominios. El permiso opcional de cookies permite abrir las pestañas en el mismo contenedor; Anaco no exporta las cookies. Puedes cerrar el panel y seguir navegando, manteniendo el navegador abierto.
4. Comprueba el estado de cada enlace. **Autorizar y reintentar** solicita los dominios adicionales detectados. Si falta iniciar sesión, abre el origen con el icono ↗ de la fila, inicia sesión y reintenta. Los errores de una clase no impiden preparar las siguientes.
5. **Revisar nota ↗** en una fila, o **Revisar pendientes** en la cabecera de la cola, abre la revisión habitual. El lote no guarda automáticamente en el vault. Las imágenes y recursos opcionales del artículo se eligen en una captura individual; PDF, lectores y vídeo conservan su extracción habitual.
6. **Pausar después del actual** deja los restantes pendientes. **Continuar cola** los retoma; tras reiniciar el navegador también debes pulsarlo. Los borradores preparados siguen disponibles en Capturas pendientes aunque empieces otra cola.

Prueba reproducible: `.venv/bin/python tests/e2e_zen.py --batch` usa un vault temporal, una clase con cookie de sesión, un formulario de acceso y un artículo. Las plataformas privadas reales pueden requerir permisos o interacción adicional en su reproductor.

### Corregir un lote que eligió PDF en vez de vídeos (1.2.2)

Pausa la cola y carga el paquete 1.2.2 como complemento temporal sin desinstalar Anaco. En la cola, abre **Más → Reprocesar como vídeos**: vuelve a extraer los enlaces no guardados con el modo vídeo, conservando los borradores anteriores en Capturas pendientes. No reutiliza las extracciones PDF del intento anterior. Si se descubre otro dominio del reproductor, concede su permiso con **Autorizar y reintentar**.

En automático se excluyen los PDF de navegación (por ejemplo, la guía general del alumnado), se espera al reproductor y se prioriza el vídeo sobre documentos auxiliares. Las actividades URL de Moodle pueden abrir su enlace de contenido en la misma pestaña de trabajo, sin activarla. El modo vídeo nunca se sustituye por PDF o texto de la página.

### Permisos de Drive y foco del panel (1.2.3)

Los marcos auxiliares de Google Feedback ya no bloquean la lectura del vídeo. La autorización de Google Drive incluye los dominios de redirección de sus descargas, igual que el flujo individual. Si una cola anterior quedó fallida, pulsa **Autorizar y reintentar fallidos** para solicitar juntos los permisos pendientes y repetir los enlaces fallidos sin volver a preparar los que ya están listos. El mensaje de permiso indica ahora los dominios concretos.

Al iniciar una cola, el panel muestra su progreso y resultados y oculta la captura de la página y el formulario de nuevos enlaces. Mantiene esa vista al pausarse o terminar. **Esta página** recupera la captura individual cuando la cola no está en marcha y **Preparar otros enlaces** permite introducir otra lista cuando no quedan enlaces pendientes. La bienvenida separa los botones de cada paso de los campos anteriores, también en pantallas estrechas.

### Editar la cola y vídeos grandes de Drive · misma versión 1.2.3

Cada enlace ofrece una × para quitarlo de la cola. **Más → Quitar fallidos** retira solo los enlaces con error y **Más → Vaciar cola** permite empezar otra lista. Estos controles no eliminan capturas preparadas ni notas guardadas. Los enlaces que aún esperan pueden quitarse mientras se procesa otro; el enlace en curso debe terminar o cancelarse antes de quitarlo o vaciar toda la cola.

Drive muestra una confirmación especial para algunos archivos grandes. Anaco reconoce únicamente el formulario de descarga de Drive para el mismo archivo solicitado y continúa la descarga. Una página real de inicio de sesión o una redirección ajena no se acepta como vídeo. Los vídeos descargados desde el navegador admiten hasta 1 GB; los PDF conservan su límite de 100 MB.

La corrección de Drive de la misma 1.2.3 admite confirmaciones GET y POST y una alternativa sin cookies para enlaces públicos. Para cargar el código actualizado, selecciona de nuevo el ZIP con **Cargar complemento temporal** en `about:debugging`; después usa **Autorizar y reintentar fallidos**. Si Drive vuelve a devolver HTML, la cola conserva el diagnóstico del intento, sin cookies ni tokens.

### Revisión seguida y notas borradas · misma 1.2.3

En una nota preparada desde la cola, **Guardar y siguiente** guarda y abre la siguiente propuesta pendiente en la misma pestaña. Los enlaces fallidos o aún en preparación no se abren como notas. Al terminar la última, **Guardar y volver a la cola** muestra la lista. **Volver a la cola** conserva el borrador sin marcarlo como revisado.

Las filas guardadas se marcan con un punto verde y **Guardada**; las preparadas, con un punto amarillo y **Por revisar**; las que fallan, en rojo con **Necesita acción** y su motivo. La cabecera de la revisión muestra **Nota N de M** con una barra de progreso, junto al botón de guardar.

Si borras una nota del vault y vuelves a generarla, el historial comprueba que el archivo siga existiendo antes de bloquear el guardado. La revisión vuelve a comprobar un guardado bloqueado al recuperar el foco. Se siguen protegiendo los archivos existentes y las partes de colecciones que no hayas borrado.

### Buscar enlaces de un curso · misma 1.2.3

1. Abre el curso con la sesión y el contenedor que uses normalmente. En el panel, cambia a **Varios enlaces → Desde un curso**. Si estás viendo una cola terminada, pulsa antes **Preparar otros enlaces**.
2. Pega el enlace del curso (en AWS Academy, la página `/courses/…/modules`), elige la profundidad de la búsqueda y pulsa **Buscar enlaces**. Autoriza el dominio cuando Firefox lo solicite.
3. La búsqueda lee los módulos y sus páginas internas en segundo plano. Puedes cerrar el panel, detener la búsqueda o continuar después. El árbol conserva módulos, secciones e indentación; los elementos bloqueados no se pueden seleccionar. Si falta acceso a un dominio, **Autorizar y continuar** reintenta las páginas pendientes.
4. Marca módulos completos o enlaces individuales. **Todos** omite los elementos bloqueados. **Añadir N a la cola** rellena la lista de enlaces sin iniciar su preparación; puedes comprobarla antes de pulsar **Preparar enlaces**.
5. Se conservan el contenedor del curso y las selecciones. Se eliminan enlaces duplicados. Cada búsqueda está limitada a 40 páginas y 500 enlaces, y la profundidad elegida; si llega al límite muestra que los resultados son parciales. Cada lista para preparar admite hasta 100 enlaces.

Canvas se lee mediante su catálogo paginado de módulos e ítems. Si ese catálogo no está disponible, se usan los enlaces de la página y se avisa de que pueden faltar módulos. La búsqueda sigue enlaces accesibles: no activa botones de laboratorios ni desbloquea actividades, y las páginas que solo exponen navegación interna sin enlaces pueden requerir una captura individual.

En la revisión, **Seleccionar todas las relaciones** y **Desmarcar todas** afectan a las conexiones disponibles de la nota activa, incluidas las conexiones entre notas derivadas. Las relaciones cuya evidencia haya quedado desactualizada no se activan automáticamente.

### Interfaz unificada · misma 1.2.3

1. Abre el panel en una página: el selector muestra **Esta página**. Cambia a **Varios enlaces**: la captura se oculta y **Ajustes de captura** sigue visible debajo.
2. Escribe una intención en la captura de la página y otra distinta en la cola. Prepara la cola y abre una de sus notas: la nota usa la intención de la cola.
3. Mientras la cola se prepara, **Esta página** está desactivado; al pausarla o terminar, vuelve a funcionar y recupera la captura.
4. Al terminar, la cola muestra una sola acción principal: **Revisar pendientes** si hay notas por revisar, **Autorizar y reintentar fallidos** si solo quedan fallos o **Preparar otros enlaces** si todo está guardado. **Reprocesar como vídeos**, **Quitar fallidos** y **Vaciar cola** están en **Más**.
5. En **Desde un curso**, cuando ya hay resultados, la única acción principal es **Añadir N a la cola**; **Buscar de nuevo** queda como secundaria.

Pruebas reproducibles: `.venv/bin/python tests/e2e_zen.py --batch`, `--batch --batch-video`, `--course-links` y `--panel-ux`.


## Publicación 1.3.0: contexto y actualización

Actualizar extensión y servicio a 1.3.0. En una clase enlazada desde un curso, comprobar en la revisión que se conservan título y URL originales, página contenedora, curso, unidad/módulo y sección conocidos. Drive identifica alojamiento, no autor. Comparar una clase de la profesora, una sección de AWS, un caso de estudio y una captura sin contexto suficiente; esta última no debe recibir curso ni sección por el tema.

Guardar una nota en un vault de pruebas con su índice existente: debe añadirse el enlace sin reemplazar el contenido anterior. Revisar la copia recuperable en `update-backups/<captura>/` del estado local. Volver a capturar la misma URL con un título o transcripción diferentes debe detectar la nota individual existente. No usar este chequeo para impedir las colecciones o ampliaciones solicitadas explícitamente.

Paquetes y textos para AMO: [docs/amo/README.md](docs/amo/README.md). Ejemplos de títulos, propiedades y destinos: [docs/CONTEXTO_FUENTES.md](docs/CONTEXTO_FUENTES.md).
