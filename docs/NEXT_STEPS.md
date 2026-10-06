# Próximos cortes: agentes y postulaciones asistidas

Actualizado: 2026-10-04. I0–I12b están implementados. Este documento registra I8 y alternativas futuras; no aprueba envíos de candidaturas. La evaluación manual `rank` vs `list` sigue pendiente y puede hacerse en paralelo al uso de I8.

## I8 — herramientas de lectura para agentes

**Pregunta de producto:** ¿podemos pedir una selección de ofertas y verificar de dónde salió cada recomendación?

Corte implementado: un adaptador de herramientas sobre `queries.search`, `queries.show` y `personal.rank`, independiente de la UI y del proveedor de modelos. Contratos tipados para buscar ofertas, leer detalle y obtener ranking con razones. Probarlo primero mediante llamadas controladas; ofrecer herramientas no equivale todavía a tener un agente autónomo. Se eligió MCP local por stdio con SDK opcional y cliente de demo sin modelo. [Contrato](AGENT_TOOLS.md), [ADR-011](adr/011-agent-tools-mcp.md) y [guía](../LearnDocs/16-agent-tools.md).

Salida mínima: `job_key`, fuente/URL, fecha observada, campos usados y razones del puntaje. El detalle para agentes debe tener un DTO explícito que **excluya notas privadas por defecto**: reutilizar el caso de uso no significa pasar su JSON entero a un modelo. Las descripciones de ofertas son datos externos, nunca instrucciones ejecutables.

**Aceptación implementada y verificada técnicamente:**

- Mismos candidatos y razones que CLI/API con filtros equivalentes; límites de resultados y de tamaño de respuesta, con truncamiento explícito.
- Solo operaciones registradas de lectura; sin SQL, shell o navegación arbitrarios y sin herramientas de recolección, `mark` o envío de CV.
- Pruebas con claves codificadas, campos desconocidos, filtros inválidos y texto de oferta que intente dar instrucciones; los límites se aplican en código.
- Demo reproducible sobre datos sintéticos y base local, sin necesidad de llamadas pagas a modelos. Si se conecta un modelo externo, decidir antes qué datos salen del equipo y el presupuesto de llamadas/tiempo/costo.
- Ejemplo de consulta “Mostrame cinco ofertas Python y qué restricciones de ubicación debo revisar”, con evidencia por oferta y dudas explícitas. No inferir elegibilidad por ausencia de restricciones.

**Aprendizaje:** herramienta vs agente, contrato vs prompt, adaptadores de presentación, proyección de datos y evaluación con ejemplos verificables. El ejercicio manual de I6 aporta casos para comprobar utilidad; los tests técnicos no lo sustituyen.

## Hitos posteriores, en orden propuesto

I12b está aprobado e implementado como receptor HTTP propio. I12c reserva la evaluación de integración real.

| Corte | Entrega | Condición para avanzar |
| --- | --- | --- |
| I9 | Implementado: perfiles UI/API/CLI, filtro por título y comparación sobre una instantánea estable | Perfil senior-uy y muestra preparados; etiquetas personales y elección de nuevos boards según evidencia pendientes. [Contrato](SAVED_SEARCHES.md) |
| I10 | Implementado: candidaturas y referencias manuales | Entidad separada, identidad, historial y estados; URL de LinkedIn guardada sin extracción. [Contrato](APPLICATIONS.md). No envía postulaciones |
| I11 | Implementado: perfiles versionados y borradores locales con citas textuales | Revisión/exportación manual; no se envía ni completa respuestas. [Contrato](PROFILE_DRAFTS.md) y [ADR-014](adr/014-profile-drafts.md) |
| I12a | Implementado: ensayo de recepción local durable, revisión y reconciliación | [Contrato](SIMULATION.md) y [guía](../LearnDocs/20-local-submission-lab.md); no transmite postulaciones |
| I12b | Implementado: receptor HTTP propio en otro proceso local | [Contrato](HTTP_TRIAL.md); token, recibos durables y reintentos explícitos con la misma clave |
| I12c | Evaluar portal/ATS real y eventual integración autorizada | API/permiso verificables para ese caso, entorno de prueba, campos y adjuntos revisados, autorización del envío concreto, trazabilidad e idempotencia; un timeout deja estado incierto hasta reconciliar, sin reenvío ciego |
| Futuro condicional | Mayor automatización de postulaciones | Resultados de I12, límites por corrida, deduplicación entre fuentes, manejo de cambios/cierre de avisos y fallos parciales; no prometer integración con una plataforma sin acceso permitido |

I11 fue aprobado el 2026-10-03 con “Perfecto, vamos con I11” y validado manualmente por el usuario el 2026-10-04 (“Ya valide I11, quedo joya”). Posteriormente se aprobó I12a con “Dale con la parte a”. El usuario luego eligió el receptor propio (I12b) y pidió evaluar portales/ATS reales más adelante (I12c, pendiente en SPEC).

La recolección programada y las alertas siguen como mejoras opcionales del roadmap. Conviene concretarlas cuando la colección sea pertinente y se defina cómo manejar Windows dormido, reinicios, cuotas y avisos. Una búsqueda guardada ya reduce fricción sin incorporar un scheduler.

## LinkedIn: viabilidad revisada

Las fuentes oficiales consultadas el 2026-09-30 muestran que **Apply Connect integra LinkedIn con un ATS**: publica puestos de clientes y recibe candidaturas dentro del ATS. Su configuración requiere ser un desarrollador aprobado; esto no demuestra acceso a una API personal para postularse automáticamente como candidato. No identificamos en esas fuentes una vía pública habilitada para ese uso de nicrawl. Referencias: [Apply Connect](https://learn.microsoft.com/en-us/linkedin/talent/apply-connect/apply-connect-overview?view=li-lts-2026-04) y [requisitos de acceso](https://learn.microsoft.com/en-us/linkedin/talent/apply-connect/create-configure-customer-application?view=li-lts-2026-04).

LinkedIn declara que no permite software de terceros que extraiga datos o automatice actividad en su sitio. Por eso un bot de navegador que recorra ofertas y pulse Easy Apply no es el camino de integración propuesto. Referencia: [actividad automatizada](https://www.linkedin.com/help/linkedin/answer/a1340567/automated-activity-on-linkedin?lang=en).

La opción inicial es usar nicrawl para organizar una referencia ingresada por el usuario, preparar material y registrar el resultado de una postulación hecha manualmente en el sitio. La posibilidad de envío automático se reconsidera si existe un mecanismo autorizado para el destino concreto. La integración con LinkedIn no es requisito para completar I8–I11.

## Medir utilidad antes de automatizar más

Registrar tiempo de revisión por oferta, útiles confirmadas entre las primeras diez, dudas de ubicación, borradores corregidos y candidaturas duplicadas evitadas. Un aumento en cantidad de envíos no prueba mayor utilidad. El objetivo es reducir trabajo repetitivo manteniendo correctos el perfil, la selección y el estado de cada candidatura.
