# Supuestos, decisiones abiertas y aprobación

Actualizado: 2026-09-30. Referencia organizativa: documentación existente de ForeKast, revisada en modo lectura.

## Defaults para poder documentar

| Tema | Propuesta revisable | Cuándo resolver |
| --- | --- | --- |
| Nombre | nicrawl | Antes de empaquetar/publicar |
| Dominio | Ofertas de empleo | Antes de I0 si se prefiere otro dataset |
| Sector/región | Tecnología, remoto internacional | Antes de I2; se pidió preferencia al usuario |
| Interfaz | CLI local en español | Antes de I0 |
| Nivel Python | Ingeniería sólida, Python por diagnosticar | I0 mediante LearnDocs |
| Fuente | Remotive, categoría software-dev | I2; validar pertinencia y reglas |
| Persistencia | SQLite, un escritor | I2 |
| Ritmo | Manual, oportunidades separadas 12 h | I2 |
| Distribución | Personal; sin publicación web ni monetización | Revisar si cambia el objetivo |
| AI | Opcional después de baseline útil | I6/I7 |

La región y fuente son supuestos, no respuestas confirmadas. La preparación documental puede avanzar sin ellos; la selección definitiva afecta I2 y los filtros. No asumir que una oferta remota permite contratación desde Argentina.

## Registro de aprobación

| Alcance | Estado | Evidencia |
| --- | --- | --- |
| D0 — documentación | Solicitada, preparada para revisión | Pedido inicial del usuario |
| I0 — base | APROBADO; entrega técnica implementada | 2026-09-25: “Arrancamos con eso”, sobre I0 + I1 recomendado |
| I1 — HTML local | APROBADO; entrega técnica implementada | 2026-09-25: mismo bloque I0 + I1 |
| I2 — fuente y SQLite | APROBADO; implementado y verificado | 2026-09-25: “Aprobado, vamos con I2”; fuente y ámbito propuestos: Remotive/software-dev |
| I3 — MVP | APROBADO; implementado y verificado | 2026-09-26: “Seguimos con I3” |
| I4 — segunda fuente y HTML externo | APROBADO; implementado y verificado | 2026-09-28: “Vamos con I4” |
| I5 — concurrencia y planificación | APROBADO; implementado y verificado | 2026-09-28: “Perfecto, vamos con I5” |
| I6 — ranking y estado personal | APROBADO; implementado y verificado | 2026-09-28: “Bien, seguimos con I6” |
| I7 — UI y API locales desacopladas | APROBADO; implementado y verificado | 2026-09-28: “Genial, entonces arrancamos I7?”; UI, API y CLI operables desde terminal |
| I8 — herramientas de lectura para agentes | APROBADO; implementado y verificado | 2026-09-30: “Bien, vamos con I8”; MCP stdio y demo sin modelo |
| I9 — búsquedas guardadas y pertinencia | APROBADO; implementado | 2026-09-30: “Bien, vamos con I9”; Senior Software Engineer desde Uruguay |
| I10 — candidaturas y referencias | APROBADO; implementado | 2026-09-30: “Vamos con I10” |
| I11+ — preparación y envío autorizado | Hitos futuros propuestos | 2026-09-30: explorar LinkedIn y milestones hacia eventual autopostulación |

Cuando llegue una aprobación, registrar fecha, cortes incluidos, fuente/ámbito si corresponde y cualquier cambio de alcance. La exigencia de esperar proviene del pedido del usuario, no de una limitación de herramientas o una política externa.

## Preguntas que puede resolver una revisión

- ¿La colección laboral es el producto que queremos o preferimos precios, artículos u otro dataset?
- ¿Qué búsquedas reales deberían servir como demo: Python, iOS, backend, datos u otra especialidad?
- ¿Se prioriza cobertura de Argentina/LatAm o aprendizaje general de fuentes internacionales?
- ¿El primer resultado práctico debe ser una CLI o vale reservar una interfaz visual para después del MVP?

No es necesario responder todo para aprobar I0 + I1; el bloque no depende de una fuente real.

## Perfil confirmado en I9

El usuario indicó Senior Software Engineer, remoto o presencial desde Uruguay. Sustituye el supuesto anterior de Argentina. Perfil inicial senior-uy, muestra fija y guía preparados; valoración manual y nuevas fuentes pendientes.

## I8 aprobado

2026-09-30: el usuario indicó “Bien, vamos con I8”. Implementadas tres herramientas MCP de lectura, extra opcional y demo sin modelo; [contrato](AGENT_TOOLS.md). I9 aprobado posteriormente; I10 aprobado posteriormente; I11+ pendiente y evaluación personal pendiente.

## Historial

2026-09-30: se concreta I8 como siguiente corte documental y se registran hitos hacia postulaciones asistidas, con fuentes oficiales sobre LinkedIn. La evaluación pendiente se aclara como `rank` vs `list`; `mark` es la escritura de revisión personal.

2026-09-30: el usuario creó el repositorio `bruce89/nicrawl` y autorizó publicar allí el código y la documentación de I7. Los datos locales y entornos siguen excluidos.

v0.8 documental / app 0.7.0, 2026-09-28: I7 aprobado e implementado. `serve` ofrece UI y API en loopback, con casos de uso compartidos con CLI. I8+ agentes queda para discusión posterior, sin aprobación ni implementación.

2026-09-28: el usuario pidió mantener la UI como dirección futura aunque el experimento de ranking no resulte concluyente, preservar la operación de API y CLI desde terminal y registrar extensibilidad hacia agentes. Se actualizaron roadmap y arquitectura; no se inició I7 ni se eligió tecnología de UI/API.

v0.7 documental / app 0.6.0, 2026-09-28: I6 aprobado. Ranking determinista, notas/estados locales y migración transaccional a esquema 2 con respaldo. 139 pruebas; evaluación personal aún pendiente. I7+ sin aprobación.

v0.6 documental / app 0.5.0, 2026-09-28: I5 aprobado. Laboratorio asyncio, plan de cuota y collect-all manual secuencial; 129 pruebas y medición sintética de cinco repeticiones. Scheduler no instalado por ADR-008; I6+ pendiente.

v0.5 documental / app 0.4.0, 2026-09-28: I4 aprobado e implementado. GitLab/Greenhouse: 200 ofertas; sandbox HTML: robots permitido y dos páginas/50 filas. 120 pruebas. I5+ pendiente. Entradas previas conservan su contexto histórico.

v0.4 documental / app 0.3.0, 2026-09-26: I3 implementado; consultas offline, novedades históricas y exportación JSON/CSV. 102 pruebas. I4+ pendiente. Entradas anteriores describen el estado de su fecha.

v0.3 documental / app 0.2.0, 2026-09-25: I2 aprobado explícitamente e implementado. Remotive/software-dev, SQLite, política durable y 19 ofertas reales en una petición. 82 pruebas. I3+ pendiente.

v0.2, 2026-09-25: I0 + I1 implementados y verificados. CLI offline, cinco fixtures, 41 pruebas y guía del primer corte. Ejercicios personales pendientes. I2+ sigue sin aprobación.

v0.1, 2026-09-24: primera propuesta documental. Organización inspirada en ForeKast; diseño adaptado a adquisición y calidad de datos. Se separaron producto y aprendizaje y se dejaron fichas de implementación pendientes. No se modificó ForeKast.
