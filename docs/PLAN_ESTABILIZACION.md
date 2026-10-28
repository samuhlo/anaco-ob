# Plan de estabilización de Anaco

Este plan convierte la [auditoría del 28 de octubre](AUDITORIA_2026-10-28.md) en cambios revisables. El objetivo es proteger datos y credenciales, hacer previsible el guardado y completar las garantías de uso en los sistemas anunciados. Los PRs se abren conforme pasan sus comprobaciones; quedan pendientes de revisión del propietario, sin fusión ni publicación automática.

## Entregas

| Orden | PR previsto | Hallazgos | Resultado y criterio de aceptación | Dependencias |
| --- | --- | --- | --- | --- |
| 0 | Auditoría y plan | Todos | Hallazgos y criterios versionados, estado enlazado a PRs reales | Ninguna |
| 1 | Credenciales y redirecciones | A01, A02 | Cambiar endpoint no reutiliza su clave; ninguna redirección transfiere credenciales a otro destino. Pruebas con servidores locales y claves ficticias | Ninguna |
| 2 | Integridad de capturas largas | A04, A10 | La captura manual no se recorta silenciosamente; huella calculada sobre toda la transcripción conservada; duplicados anteriores tratados explícitamente | 1 como base de revisión |
| 3 | Aislamiento de vaults | A05 | Cola, subida y trabajo conservan su vault. Cambiarlo no traslada el contenido; el perfil anterior no se hereda por accidente. Reanudación y datos de versiones previas cubiertos | 2 como base de revisión |
| 4 | Procesos y lanzadores portables | A03, A11 | Consulta de procesos no destructiva, cancelación de hijos y progreso de transcripción portables; rutas literales en lanzadores. CI en Windows, macOS y Linux | 3 como base de revisión; dividido en #19 y #20 |
| 5 | Plan único de publicación | A06, A15 | Vista previa y guardado incluyen los mismos archivos e índices, aprobación y copias. Se conserva LF/CRLF y se prueban conflictos e interrupciones | Ninguna |
| 6 | Proveedor explícito y transporte cancelable | A07, A09 | Manual no deriva a Codex implícitamente; proveedor efectivo visible; cancelación, plazo total y tamaño de respuesta acotados | 1 |
| 7 | Recuperación de estado corrupto | A08 | Un registro dañado no bloquea los demás; aviso identificable y originales conservados, sin ocultar errores de configuración | 4 como base de revisión |
| 8 | Contraste y navegación accesible | A12 | Texto y foco legibles en ambos temas; teclado, diálogos, zoom y panel estrecho comprobados | Ninguna |
| 9 | Instalación de una versión reproducible | A14 | La extensión publicada instala un servicio compatible e inmutable; canal de desarrollo explícito y procedimiento de retorno | Coordinar versión/tag disponible antes de cambiar la URL pública |
| 10 | Almacenamiento local | A13 | Mostrar tamaños y permitir limpieza selectiva con vista previa, conservando referencias, recuperaciones y notas del vault | 3, 5, 7 |
| 11 | Búsqueda incremental de relaciones | A16 | Evitar lecturas repetidas; invalidar al editar/borrar; mantener evidencias literales y aislamiento de vaults; benchmark reproducible de 1.000 y 10.000 notas | 3 |
| 12 | Verificación de entrega y diagnóstico | Mejoras transversales | E2e de cursos sincronizado con el botón habilitado; matriz funcional por sistema y mínimo Python declarado; artefacto probado verificable; errores con códigos sin datos sensibles | Adaptar a las interfaces finales de 4, 5 y 6 |

Las ramas independientes parten de `main`. Los cambios funcionales se presentan en cadena porque comparten configuración y módulos: **#16 → #17 → #18 → #19 → #20 → #21**. Cada PR muestra solo su propio cambio respecto del anterior. El plan (#15) es independiente. Cuando se fusione una base, ajustar la base del siguiente PR a `main` si GitHub no lo hace automáticamente. Si la fusión usa squash, rebasar el siguiente para retirar los commits ya integrados antes de revisarlo de nuevo. No fusionar estos cambios en orden inverso.

## Primera tanda

Las entregas 0, 1, 2 y 3 forman el primer corte implementado. Sus PRs están abiertos para revisión; todavía no están fusionados. El resto mantiene el estado de sus entregas, sin marcarlo como resuelto hasta tener su cambio y verificación.

| Entrega | Estado | PR |
| --- | --- | --- |
| Auditoría y plan | Abierto | [#15](https://github.com/samuhlo/anaco-ob/pull/15) |
| Credenciales y redirecciones | Implementado, pendiente de revisión | [#16](https://github.com/samuhlo/anaco-ob/pull/16) |
| Integridad de capturas largas | Implementado, pendiente de revisión | [#17](https://github.com/samuhlo/anaco-ob/pull/17) |
| Aislamiento de vaults | Implementado, pendiente de revisión | [#18](https://github.com/samuhlo/anaco-ob/pull/18) |
| Procesos portables | Implementado, CI en tres sistemas superada | [#19](https://github.com/samuhlo/anaco-ob/pull/19) |
| Rutas de lanzadores | Implementado, CI en tres sistemas superada | [#20](https://github.com/samuhlo/anaco-ob/pull/20) |
| Recuperación de registros dañados | Implementado y probado en Zen, CI del último texto pendiente | [#21](https://github.com/samuhlo/anaco-ob/pull/21) |
| Resto de entregas | Planificado | Pendiente |

Validación local de la integración: 231 pruebas Python, 129 JavaScript, i18n correcto, ZIP construido y Mozilla sin errores, con las dos advertencias previas. Zen real supera el flujo de proveedor compatible en #16 y la cola de vídeos en la integración. El endurecimiento final para subidas antiguas se volvió a comprobar con las siete regresiones de aislamiento. Los estados de CI vigentes se consultan en cada PR.

Decisiones de compatibilidad que requieren atención al revisar: la captura manual mayor de 100.000 caracteres se rechaza conservando staging; las colas y subidas antiguas sin vault explícito requieren recrear la cola o reimportar, conservando sus archivos y capturas. No se inventa una propiedad basándose en el vault seleccionado al reintentar.

## Segunda tanda

- **#19, A03:** consultas de procesos sin señales destructivas, identidad de creación, cancelación del árbol y lectura de JSONL portable. La matriz funcional de Linux, macOS y Windows con Python 3.11 y 3.13 ha pasado, además de instalación y bootstrap.
- **#20, A11:** escape POSIX y ejecutable Windows generado durante la instalación. El ejecutable usa CreateProcess con handles binarios heredados directamente, evitando shell, conversiones de texto y marcas de codificación. PowerShell y .NET Framework se usan para compilar durante la instalación, sin descargas nuevas. Reinstalar reutiliza el lanzador si su fuente y rutas no cambian.
- **#21, A08:** capturas y trabajos inválidos se excluyen individualmente, con aviso e identificadores acotados, conservando sus originales. Restaurar el archivo recupera su visibilidad. Una configuración ilegible no se reemplaza por defaults.

La integración local ejecuta 251 pruebas Python sin fallos, con una omisión específica de Windows, y supera 131 pruebas JavaScript. Zen `--pending` verifica el archivo dañado conservado, los demás pendientes operables y ausencia de desbordamiento a 240, 300 y 360 px. Los estados remotos definitivos se consultan en cada PR. La siguiente entrega planificada es el plan de publicación e índices revisables (A06 y A15).

## Condiciones de cada PR

1. Reproducir el fallo con datos temporales y una regresión que falle antes de corregirlo.
2. Aplicar el cambio mínimo completo, contemplando datos guardados por versiones anteriores.
3. Ejecutar pruebas del área y después la suite pertinente; verificar i18n al añadir mensajes. Para UI, verificar el flujo real cuando sea necesario; para Windows, añadir ejecución real en CI.
4. Revisar el diff y explicar comportamiento anterior/nuevo, validación y limitaciones en el PR. No incluir credenciales, vaults personales ni artefactos locales.
5. Publicar la rama y abrir el PR. Actualizar esta tabla con el enlace y distinguir comprobaciones locales de CI pendiente.

## Decisiones de implementación

- No migrar ni borrar silenciosamente capturas antiguas, copias o temporales.
- Los límites de tamaño deben producir una advertencia o rechazo accionable antes de perder contenido. Una captura almacenada no equivale a una nota íntegra publicada.
- El proveedor, endpoint y vault efectivos pertenecen a la operación; no deben cambiar por una modificación global posterior.
- No usar una actualización masiva de dependencias como sustituto de corregir los fallos propios.
- No cambiar la versión ni crear releases/tags en estas correcciones. Los tags necesarios para la entrega pública se coordinarán cuando se prepare esa publicación.

## Verificación final del conjunto

Además de los checks de cada PR, ejecutar una integración de las ramas aceptadas con captura manual e IA simulada, edición y deshacer, colecciones, ampliaciones e índices, cola, extracción autenticada de fixtures, cancelación, reanudación, cambios de vault y limpieza. Comprobar que una instalación nueva y una actualización mantienen esos flujos. La evaluación editorial con proveedores reales se mantiene separada de la mecánica simulada: requiere casos, modelos y resultados registrados antes de afirmar calidad o coste.
