# Roadmap de producto y aprendizaje

Actualizado 2026-10-04: **I0–I12b aprobados e implementados técnicamente**. I12c sigue como evaluación pendiente. Los ejercicios del usuario son una etapa de aprendizaje separada; no se presumen completados.

| Corte | Entrega | Aprendizaje principal | Estado |
| --- | --- | --- | --- |
| D0 | SPEC, arquitectura, fuentes, ADR, LearnDocs y plan verificable | Formular un sistema de datos | Documentado para revisión |
| I0 | Paquete CLI reproducible, toolchain y ayuda | Entornos, módulos, packaging y tipos | Implementado; validación técnica pasada |
| I1 | Extractor HTML local con escenarios sintéticos | DOM, selectores, normalización y pruebas | Implementado; ejercicios personales pendientes |
| I2 | Una fuente real, SQLite, idempotencia y runs | HTTP, contratos, transacciones y observabilidad | Implementado y verificado; 19 ofertas reales |
| I3 | Consultas, novedades, exportaciones y pulido | UX de CLI, consultas y calidad end-to-end | Implementado; MVP técnico verificado |
| I4 | Segundo adaptador; laboratorio de HTML externo permitido | Extensibilidad, cobertura y paginación | Implementado; GitLab 200 ofertas y HTML 2 páginas |
| I5 | Experimento de concurrencia acotada y eventual scheduler | asyncio, cancelación, backpressure y operación | Laboratorio, plan y collect-all implementados; scheduler aún no instalado |
| I6 | Ranking explicable y estados personales | Reglas de producto y evaluación | Implementado; evaluación personal pendiente |
| I7 | UI y API locales, con CLI plenamente operable | Contratos entre presentación y casos de uso; consistencia entre interfaces | Implementado; guía y evaluación de UX disponibles |
| I8 | Herramientas de lectura para agentes | Contratos, evidencia, proyección de datos privados y límites | Implementado: MCP stdio, demo y [contratos](AGENT_TOOLS.md) |
| I9 | Búsquedas guardadas, filtro por título y evaluación reproducible | Perfiles, snapshots, etiquetas e incertidumbre | Implementado; [guía](../LearnDocs/17-saved-searches-and-relevance.md); evaluación personal pendiente |
| I10 | Candidaturas y referencias manuales con historial | Identidad, transacciones y concurrencia optimista | Implementado; [guía](../LearnDocs/18-application-tracking.md) |
| I11 | Perfil versionado y borradores locales con evidencia | Procedencia y versiones | Validación manual confirmada el 2026-10-04 |
| I12a | Receptor simulado local durable | Idempotencia, instantáneas y reconciliación | Implementado y verificado; [guía](../LearnDocs/20-local-submission-lab.md) |
| I12b | Receptor HTTP propio y emisor en procesos separados | Transporte, autenticación local e incertidumbre | Implementado; [guía](../LearnDocs/21-http-receiver-lab.md) |
| I12c | Evaluar un portal/ATS real | Acceso, datos y garantías del proveedor | Pendiente; [criterios en SPEC](SPEC.md#evaluación-posterior-i12c-integración-real) |

## Primer corte entregado

I0 + I1 se aprobaron como bloque y la demo funciona offline. I2 incorporó Remotive/software-dev; I3, consultas y exportaciones; I4, Greenhouse/GitLab y HTML acotado; I5, laboratorio de concurrencia y plan local; I6, ranking explicable y anotaciones personales. I7 agrega UI y API locales que reutilizan esos casos de uso. Las fichas detalladas están en [FIRST_ITERATIONS](FIRST_ITERATIONS.md).

## I7 implementado y dirección para agentes

La UI consume una [API local](API.md) para listar y filtrar, ver detalle/procedencia, explicar ranking y cambiar estados/notas personales. La adquisición, puntuación y persistencia permanecen en casos de uso Python compartidos con CLI. `serve` escucha solo en `127.0.0.1`, se termina con Ctrl+C y no recolecta. API y CLI tienen ejemplos PowerShell y pruebas de equivalencia. Ver [ADR-010](adr/010-local-ui-api.md) y [guía I7](../LearnDocs/15-local-ui-api.md).

I8 ofrece herramientas de consulta a agentes con operaciones explícitas y acotadas, empezando por búsqueda, detalle y razones del ranking. El texto externo de las ofertas sigue siendo dato no confiable. Acciones que escriben, recolectan, envían información o navegan fuera del ámbito requieren una decisión de permisos y límites por separado; no se conceden por estar disponible una interfaz de lectura. La [ficha de extensiones](EXTENSIONS_AI.md) detalla esta frontera. El experimento manual de [I6](../LearnDocs/14-i6-evaluation-quick-guide.md) sirve para definir qué necesita mostrar la UI, pero no condiciona su existencia.

La funcionalidad real empieza en I2. El MVP cierra con I3. I1 no se venderá como un agregador de empleo operativo: su utilidad es enseñar y verificar extracción.

## Siguiente paso

I12b está implementado: receptor HTTP propio local, confirmación y reconciliación entre procesos. I12c queda pendiente para evaluar destinos reales antes de decidir cualquier integración. La [secuencia detallada](NEXT_STEPS.md) define aceptación y hitos hacia postulaciones asistidas, incluyendo la viabilidad de LinkedIn revisada el 2026-09-30. El experimento pendiente compara `rank` vs `list`; `mark` guarda decisiones personales.

## Candidatos posteriores

| Mejora | Valor | Dependencias | Costo relativo / motivo para postergar |
| --- | --- | --- | --- |
| Greenhouse por boards elegidos | Ofertas más pertinentes por empresa | I3 y ficha de cada fuente | Medio; múltiples ámbitos |
| HTML de careers permitido | Practicar scraping del caso real | Selección y reglas de acceso | Medio/alto; deriva del DOM |
| Búsquedas guardadas | Entregado en I9: UI, API y CLI | Evaluación de uso | Mejoras según evidencia |
| Deduplicación entre fuentes | Unificar avisos repetidos | I4 y corpus de evaluación | Alto; riesgo de fusionar puestos distintos |
| Scheduler local | Reducir trabajo manual | Cuotas durables y recuperación | Medio; Windows dormido y corridas superpuestas |
| Alertas opt-in | Enterarse de novedades | Scheduler y deduplicación de eventos | Medio; configurar destino y envío explícitamente |
| Full-text search | Consultas más ricas | Medir limitaciones de filtros actuales | Medio; no necesario para primera colección |
| Navegador Playwright | Fuente autorizada dependiente de JavaScript | Caso concreto y presupuesto | Alto; consumo y mantenimiento |
| Panel local/API | Entregado en I7; mejoras de UX basadas en uso real | Evaluación de flujos | Bajo/medio |
| Herramientas para agentes | Consultar y explicar resultados por funciones acotadas | Contratos de aplicación y pruebas de evidencia | Medio/alto; permisos y presupuestos explícitos |
| Extracción de skills con LLM | Estructurar texto difícil | Evaluación y evidencia por campo | Alto; errores, costo y privacidad |

## Cuándo adoptar frameworks mayores

Evaluar Scrapy si aparecen varias fuentes HTML con scheduling, middleware, colas y reglas de rastreo repetidas. Evaluar PostgreSQL si hay múltiples escritores o usuarios reales. I7 usa HTTP de la biblioteca estándar en loopback; si la API crece hacia autenticación, múltiples usuarios o despliegue, reconsiderar el adaptador web. Ninguna de estas migraciones es obligatoria para completar el proyecto.

El costo principal de una nueva fuente es mantener su contrato y vigencia, no escribir el primer selector. Antes de añadir una, definir una pregunta de uso, un criterio de aceptación y qué pieza actual reutiliza.
