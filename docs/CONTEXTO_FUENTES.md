# Contexto de futuras importaciones

La referencia revisada es `07_Clases/02_Master_Nube/MP5160 - Inicio de servicios en la nube/`: índice de asignatura, índices de profesora y AWS, módulos 1, 2, 3 y 9 y apuntes de ambos orígenes. No se han modificado ni renombrado las notas actuales.

## Dónde se perdía el contexto

El catálogo conservaba la jerarquía para seleccionarla, pero transfería solo URLs a la cola. La extracción de medios creaba otra captura con el título del archivo o reproductor y perdía la página contenedora. El servicio descartaba los campos no previstos al registrar la captura. Por último, el frontmatter no recibía curso de origen, módulo ni sección, y la identidad dependía del texto exacto de la transcripción.

Ahora la cola conserva la ascendencia del catálogo y su posición original cuando la API la proporciona. La captura conserva título, descripción, migas y encabezados disponibles. Los marcos y las redirecciones a reproductores mantienen el contexto contenedor. La extracción de vídeo, subtítulos, PDF y lectores adjunta ese contexto antes de generar la nota, sin solicitar acceso a páginas adicionales.

El contrato editorial pide títulos específicos y hechos de procedencia respaldados por citas literales. El servicio reconoce etiquetas explícitas y comprueba los valores propuestos contra la evidencia capturada. Una mención temática en la transcripción no activa el reconocimiento automático de pertenencia. Las etiquetas contradictorias no se completan con números supuestos.

## Propiedades y destinos

Se mantienen las propiedades del perfil y se añaden `fuente_url`, `fuente_titulo`, `fuente_alojamiento`, el contexto original disponible y los hechos identificados. Para archivos locales se usa `fuente_archivo`. `fuente_original_url` conserva la URL recibida, antes de normalizarla para identificar duplicados. `fuente_page_url` conserva la página contenedora. El alojamiento no se utiliza como autor.

`modulo` sigue siendo el código académico; `modulo_aws` identifica el módulo interno de AWS. `seccion_fuente` conserva la numeración explícita. `fuente_catalog_position` conserva una posición proporcionada por el catálogo: no se convierte en sección ni en `orden_lectura`.

La selección determinista de carpeta requiere una coincidencia única con metadatos de notas existentes en destinos admitidos por el perfil. Se hereda la pertenencia académica de ese destino. Si no hay coincidencia única, permanece la propuesta revisable del flujo habitual. No se crean carpetas automáticamente. La búsqueda y validación de relaciones sigue usando candidatas y extractos de ambas notas.

Al guardar, se añade un enlace al `index.md` más cercano, sin reemplazar tablas ni numerarlas de nuevo. El enlace identifica la sección conocida y deja el orden de lectura pendiente de revisión. Nota e índice se publican con comprobación de cambios concurrentes, recuperación y copia del índice anterior en el estado local de Anaco (`update-backups/<captura>/`).

Para capturas completas individuales se busca también la URL normalizada en las notas existentes: cambiar el título, la ruta o la transcripción no basta para crear una copia. Se conservan los flujos explícitos para derivar nuevas colecciones, ampliar notas y capturar citas distintas de la misma página.

## Ejemplos

Los títulos siguientes simulan una propuesta editorial; el reconocimiento de propiedades y carpetas se comprobó contra el vault real en modo de solo lectura. Las rutas son relativas a la carpeta de MP5160 indicada al principio. El perfil actual usa el título como nombre para `apunte`.

| Título | Propiedades contextuales | Ruta de la futura nota |
| --- | --- | --- |
| MP5160 · Profesora · UD01 · Apartado 05 · Infraestructura física y recursos lógicos | `origen: Profesora`, `modulo: MP5160`, `unidad_didactica: UD01`, `seccion_fuente: "05"`, `tipo_recurso: clase`, alojamiento Drive | `teoria/01_Profesora/UD01/<título>.md` |
| AWS Cloud Foundations · M02 · S03 · AWS Organizations | `origen: AWS Academy`, `curso_fuente: AWS Academy Cloud Foundations`, `modulo: MP5160`, `modulo_aws: 2`, `seccion_fuente: "3"`, `tipo_recurso: clase` | `teoria/02_AWS_Academy_Cloud_Foundations/02_Economía_y_facturación/<título>.md` |
| AWS Cloud Foundations · M02 · Caso Delaware North · Evaluación de la migración | Mismo curso y módulo; `tipo_recurso: caso de estudio`; sin `seccion_fuente`; `contexto_pendiente` explica la ausencia | `teoria/02_AWS_Academy_Cloud_Foundations/02_Economía_y_facturación/<título>.md` |
| Comparación de recursos físicos y virtuales | URL y título originales; sin origen, curso ni sección atribuidos; `contexto_pendiente` señala lo desconocido | Destino propuesto por el perfil y confirmado en revisión; no se atribuye a MP5160 por tratar sobre cloud |

En los cuatro casos se conserva la URL y el título originales. Una demostración sin sección conocida recibe el mismo tratamiento que el caso: no se rellena un hueco en la numeración.

## Validación y alcance

`tests/test_provenance.py` cubre los cuatro casos, reimportación con título cambiado, copia del índice, reversión si falla su actualización, rechazo de evidencia inventada y menciones de otros cursos en la transcripción. Las pruebas JavaScript comprueban que el contexto del contenedor sobrevive a marcos anidados y al recurso alternativo cuando fallan subtítulos.

Las pruebas usan generación simulada y vaults temporales. No equivalen a una nueva sesión de captura autenticada en AWS Academy ni a una evaluación de la calidad de un modelo real. El código de la extensión debe recargarse o instalarse en el navegador para usar los cambios; no se ha sustituido la extensión instalada.
