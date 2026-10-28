# Auditoría de calidad de Anaco 1.3.0

Anaco tiene una base funcional sólida y una cobertura de pruebas considerable, pero necesita corregir problemas de credenciales, integridad del contenido y aislamiento entre vaults antes de considerarlo listo para una distribución amplia. La prioridad es reforzar esas garantías y la compatibilidad con Windows. La interfaz ya tiene una identidad coherente; sus principales mejoras son legibilidad, claridad sobre el destino de los datos y fidelidad de la vista previa.

Auditoría del código local en `d418f17`, realizada el 28 de octubre de 2026. Resultado: **16 hallazgos, con 5 de prioridad alta, 10 de prioridad media y 1 mejora de gestión de datos**. Las prioridades expresan el orden recomendado de trabajo, no una puntuación CVSS.

## Alcance y comprobaciones

Se revisaron la extensión, Native Messaging, el servicio Python, los proveedores de IA, la captura multimedia, las colas, los perfiles, la publicación y recuperación de notas, el instalador, la interfaz, la privacidad y la CI. Se ejecutaron reproducciones con vaults temporales, claves ficticias y servidores HTTP de loopback. Las pruebas de navegador usaron una copia del proyecto y un HOME temporal, sin cambiar el registro del servicio ni los vaults personales.

| Comprobación | Resultado de esta auditoría |
| --- | --- |
| `npm test` | 124 pruebas superadas |
| `python -m unittest discover -s tests -v` | 213 pruebas superadas |
| `python scripts/i18n.py check` | 819 claves usadas, 0 problemas |
| `npm run lint` | 0 errores, 2 advertencias |
| Construcción con `web-ext build` | ZIP de auditoría generado correctamente |
| Bibliotecas de renderizado | Marked y DOMPurify empaquetados coinciden por SHA256 con los archivos instalados de npm |
| `npm audit --json` | 3 entradas de severidad baja, de una misma cadena de dependencias de desarrollo |
| Zen real con `--options` | Captura de artículo, cita e imagen, opciones, revisión, saneamiento, guardar y descartar superados |
| Zen real con `--workflow` | Revisión por apartados, deshacer, integración, ampliación aprobada, cancelación y reanudación superadas; anchos de 480, 640 y 950 px |
| Zen real con `--batch --batch-video` | Cola, reproductor tardío, enlaces lanzadores, subtítulos con sesión y reprocesamiento superados |
| Zen real con `--course-links` | Primera ejecución falló en desmarcado masivo de relaciones; repetición sin cambios superada. Incidencia intermitente, no resultado uniformemente verde |

Entorno de ejecución: Linux, Python 3.14.7, Node 26.10.0 y Zen 1.22.3b. Las ejecuciones con IA del flujo de edición usan el proveedor simulado de las pruebas. No constituyen una evaluación de calidad de modelos reales, de todos los proveedores ni de cursos privados en producción. Las incompatibilidades de Windows se sustentan en el código y el contrato documentado de Python; esta auditoría no ejecutó Windows ni macOS. La comprobación de accesibilidad incluye código, contraste y capturas, no una certificación con lector de pantalla.

Los dos avisos de Mozilla corresponden a compatibilidad de `data_collection_permissions` con Firefox Android y a una asignación de HTML en código empaquetado. El renderizador propio usa DOMPurify y una política restrictiva; el aviso por sí solo no demuestra una vulnerabilidad XSS. La cadena `deepmerge → addons-linter → web-ext` tiene un aviso bajo sin versión corregida según el [aviso publicado](https://github.com/advisories/GHSA-gcqx-w48m-w2h4). Esas herramientas no viajan en la extensión; no conviene aplicar el downgrade que propone automáticamente npm sin evaluar sus efectos.

## Hallazgos prioritarios

**P1**: corregir antes de ampliar la distribución. **P2**: corregir en el siguiente ciclo de estabilización. **P3**: mejora planificada. «Reproducido» significa que se observó el comportamiento con el código actual en un entorno controlado; «contrato de plataforma» identifica una incompatibilidad documentada sin ejecución en ese sistema.

| ID | Prioridad | Problema | Evidencia |
| --- | --- | --- | --- |
| A01 | P1 | La clave anterior se envía al cambiar de servidor de IA | Reproducido con transporte simulado |
| A02 | P1 | Una redirección HTTP reenvía la autorización a otro origen | Reproducido con dos servidores locales |
| A03 | P1 | Gestión de procesos y transcripción incompatible con Windows | Código, contrato de plataforma y simulación de API ausente |
| A04 | P1 | La captura manual larga se recorta sin advertencia | Reproducido |
| A05 | P1 | Colas y subidas no quedan vinculadas al vault inicial | Reproducido en servicio y simulador de extensión |
| A06 | P2 | Los índices con finales CRLF bloquean el guardado | Reproducido |
| A07 | P2 | Las herramientas de revisión usan Codex con el modo manual configurado | Reproducido con llamada de IA interceptada |
| A08 | P2 | Una captura JSON corrupta rompe el estado general | Reproducido |
| A09 | P2 | Cancelar no interrumpe la petición al proveedor compatible | Código y servidor local lento |
| A10 | P2 | Las transcripciones largas pueden compartir una huella incorrecta | Reproducido |
| A11 | P2 | El lanzador interpreta expresiones de shell en las rutas | Reproducido con un marcador temporal inocuo |
| A12 | P2 | El texto secundario y el foco tienen contraste insuficiente en claro | Cálculo sobre los colores del CSS |
| A13 | P3 | Falta gestión selectiva del espacio y la retención local | Inspección de persistencia y comandos |
| A14 | P2 | El instalador público sigue `main`, independientemente de la versión de la extensión | Inspección del instalador |
| A15 | P2 | El guardado modifica índices que no aparecen en la revisión | Reproducido |
| A16 | P2 | La búsqueda de relaciones recorre y procesa las notas repetidamente | Medición sintética e inspección |

### A01 La clave debe pertenecer a un servidor concreto

En [core.py](../native/core.py#L239), `set_config()` sustituye `api_base`, pero conserva `api_key` si el formulario no entrega otra clave ni solicita borrarla. El selector de servicio de [options.js](../extension/options.js#L121) cambia URL y modelo sin invalidar la clave guardada. [ai.py](../native/ai.py#L19) añade esa clave al siguiente destino.

Reproducción: configurar `https://first.invalid/v1` con `AUDIT_FAKE_KEY`; cambiar únicamente la base a `https://second.invalid/v1`; interceptar la petición. El segundo servidor recibe `Authorization: Bearer AUDIT_FAKE_KEY`. No se utilizaron credenciales reales ni hubo tráfico a esos dominios.

**Corrección:** asociar las credenciales al endpoint normalizado o a una configuración identificada de proveedor. Al cambiar de destino, seleccionar su propia credencial o exigir una nueva; nunca trasladarla implícitamente. **Aceptación:** cambiar entre dos servidores, incluido un modelo local, no envía la clave anterior.

### A02 Las redirecciones deben respetar el límite de confianza

[ai.py](../native/ai.py#L26) utiliza el seguimiento automático de redirecciones de `urllib.request` con `Authorization`. En la prueba, el endpoint de un puerto local devuelve 302 hacia otro puerto y el receptor obtiene la clave ficticia. El cambio de puerto ya constituye un cambio de origen.

El requisito para explotar este comportamiento es que el endpoint configurado redirija la solicitud. La reproducción demuestra el reenvío del encabezado; no implica que los proveedores predefinidos lo estén haciendo.

**Corrección:** rechazar redirecciones entre orígenes y degradaciones de HTTPS, o aplicar una política explícita que no reenvíe secretos. Restringir HTTP a destinos locales, salvo una configuración deliberada. **Aceptación:** cubrir 301, 302, 303, 307 y 308 y verificar destino, método, cuerpo y encabezados.

### A03 Windows requiere una implementación propia de procesos

Hay tres incompatibilidades en rutas funcionales anunciadas como multiplataforma:

- [jobs.py](../native/jobs.py#L15) comprueba si un proceso vive mediante `os.kill(pid, 0)`. En Windows, Python documenta que los valores distintos de las señales de consola terminan el proceso. Consultar un trabajo marcado como activo puede, por tanto, terminar el host registrado en ese trabajo, incluso si es el propio proceso que está consultando el estado. Véase [os.kill](https://docs.python.org/3/library/os.html#os.kill).
- [jobs.py](../native/jobs.py#L87) usa `os.killpg` al cancelar o agotar el tiempo. Esa API solo está disponible en Unix. Al simular su ausencia se obtiene `AttributeError` y el hijo continúa vivo; el proceso de prueba se terminó después explícitamente.
- [media.py](../native/media.py#L30) registra `process.stdout` en `DefaultSelector`. Los selectores de Windows admiten sockets, pero no estas tuberías. Véase [selectors](https://docs.python.org/3/library/selectors.html#introduction).

**Corrección:** encapsular consulta y terminación de procesos por plataforma, comprobar identidad además de PID y consumir la salida del transcriptor mediante una solución portable. **Aceptación:** en Windows real, consultar trabajos no los termina; cancelar y agotar un timeout eliminan los hijos; un worker JSONL entrega progreso y resultado. La CI actual de instalación no ejercita estas rutas.

### A04 La captura manual debe conservar el contenido o avisar

[core.py](../native/core.py#L570) construye el cuerpo manual con el texto capturado y después [lo limita a 80.000 caracteres](../native/core.py#L605). Una fuente de **90.016 caracteres** produjo un borrador de **80.000**, sin el marcador del final y con `warnings=[]`. La captura original sigue en staging, pero la nota propuesta queda incompleta sin indicarlo.

**Corrección:** separar los límites de elaboración por IA de los de conservación manual. Si el límite de transporte o edición obliga a dividir, ofrecer partes o adjuntar el original y mostrar qué tramo se conserva. **Aceptación:** una captura por encima del límite conserva el final o bloquea/avisa de forma explícita; nunca aparece como íntegra silenciosamente.

### A05 Colas y subidas deben conservar su vault de origen

[batch.js](../extension/batch.js#L17) conserva opciones, URLs y contenedor, pero no el vault. Se reprodujo una cola con dos enlaces: preparar el primero en A, pausar, cambiar a B y continuar; el segundo se capturó en B y ambos quedaron `ready`. La reproducción usa el código de cola real con Native Messaging simulado.

También se reprodujo directamente en [media.py](../native/media.py#L145): iniciar una subida de subtítulos en A, cambiar la configuración a B y finalizarla. La captura resultante pertenece a B porque los metadatos de la subida no contienen el vault. El router de [background.js](../extension/background.js#L884) permite mensajes `native/configure` mientras existe una cola. Los trabajos registrados añaden controles parciales, pero no sustituyen una vinculación persistente de cada objeto.

Además, [core.py](../native/core.py#L265) compara el nuevo vault con su propia ruta normalizada, después de haber sustituido el valor anterior. Con rutas absolutas normalizadas no elimina `profile_path` al cambiar de vault.

**Corrección:** guardar una identidad de vault y una configuración efectiva en colas, subidas y trabajos; verificarla al continuar cada operación. Bloquear el cambio mientras haya trabajo activo o pausar con un estado explícito. **Aceptación:** continuar o finalizar en otro vault se rechaza y conserva el trabajo recuperable en el original; la selección de perfil no se hereda por accidente.

### A06 El hash de los índices debe calcularse sobre sus bytes

[provenance.py](../native/provenance.py#L140) lee `index.md` como texto, normalizando CRLF a LF. Después [calcula el hash esperado](../native/provenance.py#L158) sobre ese texto recodificado. [publication.py](../native/publication.py#L28) compara con los bytes originales y detecta falsamente una modificación.

Con un índice CRLF intacto, guardar una captura de curso falla con «Ya existe una nota o ha cambiado desde la revisión». El mismo escenario con LF guarda correctamente. No hace falta ejecutar Windows para reproducirlo.

**Corrección:** mantener separados los bytes originales y el texto editable; calcular la versión esperada sobre los primeros y conservar la convención de saltos de línea. **Aceptación:** índices LF y CRLF se amplían y se recuperan sin falsos conflictos.

### A07 Las acciones de IA deben identificar su proveedor efectivo

[core.py](../native/core.py#L491) deriva cualquier proveedor distinto de `openai` hacia Codex, incluido `manual`. Preparar manualmente una nota y solicitar `revise` llega a `codex_json`; se comprobó interceptando la llamada. La interfaz ofrece «Explicar mejor», «Reducir» y «Desarrollar» sin identificar en esos botones el cambio de proveedor. [PRIVACY.md](../PRIVACY.md) afirma que la captura manual no envía datos a proveedores.

La preparación manual inicial sí respeta esa promesa. El problema está en las herramientas posteriores y en que no conservan de manera explícita el proveedor de la captura.

**Corrección:** distinguir edición manual de elaboración por IA, mostrar el proveedor antes de una acción que envía contenido y conservar una configuración efectiva por operación. **Aceptación:** con modo manual, una revisión no llama a Codex implícitamente; la interfaz y la privacidad explican de forma consistente cuándo se envían datos.

### A08 Un registro dañado no debe bloquear todos los pendientes

[core.py](../native/core.py#L407) carga cada captura con `json.loads()` sin aislamiento de errores. Basta añadir un archivo `{broken` a `captures/` para que `handle({'action':'status'})` falle con `JSONDecodeError`. Incluso un registro de otro vault se analiza antes de filtrar.

**Corrección:** validar cada registro, aislar los ilegibles, conservarlos para recuperación y devolver el resto junto con un aviso identificable. Aplicar una estrategia equivalente a configuración y cachés. **Aceptación:** un JSON truncado no impide consultar el servicio ni recuperar capturas sanas.

### A09 La cancelación del proveedor compatible no es efectiva durante la petición

[core.py](../native/core.py#L497) consulta la cancelación una sola vez antes de entrar en [ai.py](../native/ai.py#L19). La conexión y lectura HTTP son bloqueantes, con un timeout de socket de 300 segundos y sin límite de bytes de respuesta. Mientras tanto, el host procesa mensajes secuencialmente.

Con un servidor local que tarda 1,2 segundos y una cancelación inmediatamente posterior a recibir la petición, la operación sigue esperando la respuesta. No hay mecanismo para interrumpir esa espera; 300 segundos tampoco es necesariamente un plazo total si siguen llegando datos.

**Corrección:** transporte cancelable, plazo total y máximo de respuesta, conservando los checkpoints. **Aceptación:** cancelar recupera el control en un tiempo acotado también durante cabeceras, cuerpo lento y respuesta parcial. La cancelación de Codex en Linux sí pasó el e2e y debe conservarse.

### A10 La huella debe representar toda la transcripción conservada

[media.py](../native/media.py#L256) llama a `stage()` con los primeros 150.000 caracteres; allí se calcula la huella. Luego guarda hasta 400.000 caracteres sin recalcularla. Dos transcripciones de la misma URL e imágenes, iguales en el prefijo pero distintas después, conservan textos distintos con la misma huella.

**Corrección:** calcular la identidad después de fijar el contenido completo, o incluir un hash del original durante la extracción. Versionar la estrategia para no invalidar el historial sin control. **Aceptación:** cambiar solo el final distingue capturas; repetir la transcripción íntegra mantiene la deduplicación.

### A11 El lanzador necesita escape real de shell

En [installer.py](../native/installer.py#L63), el escape POSIX solo protege las comillas dobles. `$()`, acentos graves y expansiones de variables siguen interpretándose dentro de las rutas emitidas. Una carpeta temporal llamada `state$(touch AUDIT_EXECUTED)` provocó la creación del marcador al ejecutar el lanzador.

El escenario exige que la ruta de datos o instalación contenga esos caracteres; no se ha demostrado una ejecución remota desde una página web. También puede causar fallos con nombres legítimos que incluyan `$`.

**Corrección:** usar `shlex.quote` en POSIX y tratar por separado las reglas de `.bat` para Windows. **Aceptación:** rutas con espacios, comillas, dólar, acentos graves y Unicode se utilizan literalmente y no ejecutan su contenido.

### A12 El tema claro necesita más contraste

En [style.css](../extension/style.css#L1), `--muted: #7b7883` se usa en etiquetas y texto pequeño. Su contraste es **4,32:1 sobre blanco**, **4,00:1 sobre `--bg`** y **4,01:1 sobre `--tint`**. Es inferior al 4,5:1 que corresponde a texto normal en [WCAG 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Las etiquetas de formulario usan ese color a 12 px.

El [foco global](../extension/style.css#L32) amarillo `#ffca40` sobre blanco tiene **1,52:1**. Cuando es el indicador que identifica el foco, no alcanza el contraste 3:1 descrito en [WCAG 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).

**Corrección:** oscurecer texto secundario y usar un foco de mayor contraste, conservando amarillo como acento. **Aceptación:** medir componentes activos en ambos temas y comprobar tabulación, zoom y alto contraste. Las capturas estrechas muestran además una cabecera de opciones que ocupa mucho espacio: conviene reducirla y comprobar que no oculta controles al enfocarlos.

### A13 La retención necesita controles selectivos

[discard](../native/core.py#L925) cambia el estado de la captura y conserva el contenido. Las subidas finalizadas, las transcripciones, los lectores, las cachés y las copias pueden seguir ocupando disco. La limpieza integral existe como `uninstall --purge`, pero no hay una política de retención ni una herramienta de limpieza selectiva en la interfaz.

Con archivos locales admitidos de hasta 1 GB, el crecimiento puede ser considerable. Conservar checkpoints es útil; el problema de producto es que el usuario no ve qué ocupa espacio ni puede decidir qué borrar sin desinstalar.

**Mejora:** panel de almacenamiento con tamaños por categoría, exportación y borrado selectivo; plazos configurables para temporales, manteniendo trabajos recuperables y copias necesarias. **Aceptación:** limpiar un archivo sin referencias libera espacio sin romper una revisión pendiente ni modificar notas del vault.

### A14 El instalador debe apuntar a una versión estable

[install.sh](../scripts/install.sh#L6), [install.ps1](../scripts/install.ps1#L6) y las órdenes de [diagnosis.js](../extension/diagnosis.js#L25) instalan desde `main`. El servicio descargado depende de cuándo se instala, aunque la extensión publicada permanezca en otra versión. El detector de versiones informa después del desajuste, pero no lo previene.

**Corrección:** publicar artefactos o tags inmutables y asociar la extensión con una versión compatible del servicio; separar el canal de desarrollo. Incorporar actualización y retorno a una versión anterior. **Aceptación:** una extensión publicada instala la misma versión compatible antes y después de nuevos commits en `main`.

### A15 Los índices modificados deben aparecer en la revisión

[publication.py](../native/publication.py#L18) incorpora actualizaciones de índices justo al publicar; [provenance.py](../native/provenance.py#L158) las marca `approved=True`. La vista previa de [editorial.py](../native/editorial.py#L193) no incluye esa ampliación.

Reproducción: una captura de curso muestra una sola nota y `update_count=0`; al guardar también cambia el `index.md` preexistente. La respuesta `paths` continúa enumerando solo la nota. Las copias de recuperación existen, pero el usuario no ve todo lo que autoriza antes del guardado.

**Corrección:** preparar un único plan de publicación compartido por vista previa y guardado, con todos los archivos que se crean o modifican, sus diferencias y aprobación. **Aceptación:** los índices aparecen entre los cambios revisables y en el resultado; cancelar no los modifica.

### A16 La búsqueda de relaciones necesita evitar recorridos repetidos

[core.py](../native/core.py#L312) lee y tokeniza las notas de las raíces de relaciones en cada búsqueda. [linking.py](../native/linking.py#L34) repite esa búsqueda por cada nota de una propuesta. [vault_profile.py](../native/vault_profile.py#L72) también recorre carpetas para resolver destinos.

Medición local con **1.000 notas sintéticas de aproximadamente 3,7 kB**, generadas en un vault temporal: **2,419 s, 2,126 s y 2,295 s** en tres búsquedas consecutivas. Es una carga artificial con vocabulario repetido, no una medición de un vault real ni una predicción exacta para otros equipos. Sí evidencia que un conjunto de notas derivadas puede multiplicar un trabajo ya perceptible.

**Corrección:** caché o índice incremental por vault y versión del archivo; resolver varias consultas con una misma lectura y limitar el trabajo por operación. Conservar fragmentos verificables y exclusiones del perfil. **Aceptación:** medir 1.000 y 10.000 notas con distribución representativa, registrar tiempos de búsqueda y asegurar que editar o borrar una nota invalida sus datos.

## Mejoras para profesionalizar el producto

### Mostrar el destino y el alcance de cada acción

Mostrar siempre el vault activo y el proveedor efectivo cerca de «Preparar». Mantener esta información visible en colas y revisiones. Presentar un resumen previo al guardado con notas nuevas, ampliaciones, índices y adjuntos; hacer que ese resumen sea exactamente el plan que ejecuta el servicio.

Explicar «Descartar» como retirar de pendientes cuando se conserva el original, y ofrecer «Eliminar datos locales» como operación distinta. Mostrar los límites de extracción y cualquier recorte junto al resultado. El usuario debería poder distinguir una extracción parcial de una nota resumida deliberadamente.

### Reducir complejidad de la interfaz

Mantener la jerarquía visual actual y agrupar configuración avanzada por tarea: captura, elaboración, destino y almacenamiento. Las capturas inspeccionadas muestran etiquetas pequeñas, mucho texto secundario y una navegación fija alta a 300 px. Priorizar contraste y lectura antes de añadir más opciones.

Añadir pruebas de teclado y foco en menús, diálogos, cambios de modo y errores. Revisar 300, 390 y 768 px, zoom de 200 % y tema oscuro con una matriz repetible. Los atributos de estado y alerta ya presentes son una buena base. No se recomienda rehacer toda la interfaz para resolver problemas de estado o de legibilidad.

### Hacer diagnosticables los errores

[host.py](../native/host.py#L67) imprime solo el nombre de la excepción y devuelve un mensaje genérico. Esto protege contenido sensible, pero dificulta distinguir un fallo de disco, un formato inesperado y un error de programación. Añadir códigos de error estables, identificador de operación y un registro local acotado, redactado y exportable por el usuario. Nunca incluir claves, cuerpos de notas ni URLs firmadas por defecto.

Ampliar `doctor` para verificar el registro efectivo, vault, perfil y herramientas realmente utilizadas. Hoy se basa principalmente en existencia del lanzador y ejecutables; puede dar una impresión de disponibilidad mayor que la comprobada. Un fallo multimedia remite a `scripts/install-media.sh`, una ruta de checkout que no es una solución universal para la instalación empaquetada.

### Reducir el coste de mantener el código

`background.js` tiene 952 líneas y concentra transporte, estado de trabajo, captura, navegación y revisión; `core.py` tiene 935. Varios módulos contienen funciones extensas comprimidas en líneas con numerosos statements. Extraer transporte, contexto de operación y planificación de publicación daría límites más claros para las correcciones anteriores.

Introducir formateo consistente y análisis estático de JavaScript/Python: `npm run lint` ejecuta el validador de Mozilla, que no sustituye un linter general. Documentar el protocolo extensión-servicio y validar los mensajes en el límite. Mantener la separación existente entre contenido no fiable, herramientas de IA deshabilitadas y escritura por el servicio tras revisión.

### Completar la estrategia de pruebas y entrega

La CI ejecuta unidades en Linux y prueba instalación en los tres sistemas. No ejecuta la suite funcional del servicio en Windows/macOS, ni e2e de navegador, contraste o calidad editorial real. Incluir Python 3.11 si se mantiene como mínimo declarado; fijar entornos y dependencias de pruebas, incluido Selenium y la localización configurable de navegador/driver.

El e2e de cursos falló una vez en `tests/e2e_zen.py:906` y pasó al repetir sin cambios. Una ejecución instrumentada, retrasando 1,5 segundos las respuestas de vista previa, mostró que el test intenta pulsar «Desmarcar todas» con el botón deshabilitado y las relaciones internas todavía sin cargar. El estado publicado de `canSave` puede corresponder a la vista anterior. Al añadir a la copia temporal del test una espera por la nueva vista y por el botón habilitado, la misma ejecución con retraso pasó: dos relaciones internas cargadas y cero seleccionadas después de desmarcar. Esta evidencia identifica una sincronización insuficiente del test; no se ha demostrado un defecto del desmarcado del producto. El test original del repositorio sigue pendiente de ajustar.

Añadir primero regresiones para A01–A12 y A15. Incorporar fallos de disco lleno, interrupción entre escritura y actualización de estado, reintentos, cambios concurrentes y formatos de archivo de distintos sistemas. En la entrega, verificar que las bibliotecas vendorizadas coinciden con el lockfile y que el artefacto construido es el probado; la coincidencia se ha comprobado en este checkout.

Para IA, evaluar con un conjunto pequeño versionado de artículos, libros y conversaciones largas: conservación de hechos y código, precisión de citas, atribución, cobertura del final de la fuente, calidad de relaciones y respeto a instrucciones del vault. Medir calidad, tiempo y coste con modelos reales antes de cambiar defaults. Los fixtures actuales verifican mecánica y contratos, no esa calidad editorial.

## Orden recomendado de trabajo

| Fase | Trabajo | Condición de cierre |
| --- | --- | --- |
| 1 Protección de datos | A01, A02, A04 y A05 | Ninguna clave cambia de destino, ningún recorte es silencioso y toda operación conserva su vault |
| 2 Compatibilidad y publicación | A03, A06, A11 y A15 | Flujo funcional probado en Windows, índices LF/CRLF y plan de guardado fiel a la revisión |
| 3 Recuperación y previsibilidad | A07, A08, A09, A10 y A14 | Proveedor explícito, registros dañados aislados, cancelación efectiva e instalación reproducible |
| 4 Uso continuado | A12, A13 y A16 | Contraste corregido, almacenamiento gestionable y búsquedas medidas sin recorridos redundantes |

Las correcciones deberían entregarse en cambios pequeños con su regresión específica. Esta auditoría incorpora documentación y evidencias locales; los defectos descritos permanecen en el código auditado.

## Evidencias locales

Los resultados y reproducciones se guardan en [los artefactos de auditoría](../.test-artifacts/audit-2026-10-28/). Esta carpeta está ignorada por Git. El informe contiene los escenarios y resultados relevantes para que las conclusiones no dependan de conservar archivos temporales.

- `reproduce.py` y `reproductions.json`: cambio de credenciales, recorte manual, proveedor manual, huella de transcripción, subida entre vaults, JSON corrupto y escape del lanzador.
- `extra-reproductions.txt`: índice CRLF, cancelación sin `killpg` y redirección entre orígenes.
- `batch-reproduction.json`: continuación de cola entre vaults.
- Logs de suites, validación, construcción y dependencias; informes JSON y capturas de las ejecuciones de Zen.

Los archivos `docs/amo/listing/` y `scripts/amo_listing.py` ya estaban fuera de Git al empezar y no forman parte de los cambios de esta auditoría.
