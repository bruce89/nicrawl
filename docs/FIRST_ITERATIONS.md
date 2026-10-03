# Fichas de las primeras iteraciones

**Actualizado 2026-09-30: I0–I10 aprobados e implementados técnicamente; I11+ pendiente de aprobación.** Las fichas conservan el alcance de referencia. Evidencia en [VALIDATION](../VALIDATION.md); ejercicios personales aún pendientes.

## I0 — base reproducible

**Objetivo:** poder ejecutar y estudiar una CLI mínima desde un checkout limpio en Windows.

Entregas: `pyproject.toml`, Python fijado, lockfile, paquete `src/nicrawl`, comando `--help`/`--version`, configuración de calidad e instrucciones reales. Incorporar solo Typer y herramientas de desarrollo; las bibliotecas de datos esperan su corte. Revisar qué hay instalado sin modificar instalaciones globales innecesariamente.

Tareas: verificar intérprete y compatibilidad; crear paquete preservando docs; resolver versiones; configurar Ruff y mypy con alcance explícito; probar instalación reproducible; documentar comandos y ruta del intérprete. Preparar exclusiones de `.venv`, caches, datos y secretos si se usa Git; publicar remoto no forma parte de este corte.

**Aceptación:** Q01; ayuda funciona desde el entorno del proyecto; lock reproducible; lint/formato/tipos pasan sobre el código existente. No añadir tests triviales que solo comprueben un literal de versión.

**Aprendizaje:** explicar intérprete vs entorno vs paquete; localizar el entrypoint; demostrar que la CLI usa la dependencia fijada. [Etapa A](../LearnDocs/01-learning-roadmap.md).

Dependencias y riesgo: disponibilidad de Python 3.14 y compatibilidad de ruedas en Windows; si falla una dependencia, documentar alternativa antes de cambiar el objetivo de versión. Costo relativo: pequeño.

**Estado:** aprobado el 2026-09-25, implementado y verificado. Entorno y comandos reales en [IMPLEMENTATION](IMPLEMENTATION.md).

## I1 — scraping HTML sin red

**Objetivo:** convertir HTML propio en ofertas normalizadas con errores comprensibles.

Entregas: fixtures HTML originales, parser Beautiful Soup, modelos y normalización, comando `demo`, reporte de válidos/rechazos y pruebas Q02–Q05. Escenario base: tres ofertas válidas y una sin título; variantes con opcionales ausentes, entidades/Unicode, lista legítimamente vacía y estructura rota. Fixtures con URL base `https://jobs.example/` y datos explícitamente ficticios.

Tareas: definir contenedor/marcador de página y selector por tarjeta; resolver enlaces relativos sobre la base de fixture; extraer y limpiar campos; rechazar invariantes; construir salida reproducible. No escribir ofertas de demo en la colección real.

**Aceptación:** demo funciona sin Internet; resultado base y variantes coinciden con escenarios; un selector roto no genera falso éxito; se puede rastrear una oferta campo por campo. La demo que contiene un rechazo devuelve código 3, con su alcance educativo explicado.

**Aprendizaje:** cambiar HTML, anticipar el resultado y reparar el parser con una prueba que demuestre el problema. Implementar personalmente un campo opcional y explicar dónde pertenece. [Laboratorios](../LearnDocs/04-reverse-engineering-labs.md).

Dependencias: I0 terminado. Riesgo: abstraer demasiadas capas; empezar con funciones y extraer contratos al necesitar sustitución. Costo relativo: pequeño/medio.

**Estado:** aprobado el 2026-09-25, implementado y verificado. Recorrido y ejercicios en [primer corte](../LearnDocs/08-first-working-slice.md).

## I2 — recolección real y persistencia

**Objetivo:** guardar ofertas de una fuente real y repetir la operación sin duplicar.

Entregas: adaptador Remotive si se confirma; HTTPX y política de acceso; Pydantic en el límite externo; SQLite con migraciones mínimas, runs, observaciones y cambios; bloqueo de recolección; comandos `collect` y `status`. Se implementan Q06–Q15 y Q20–Q22 aplicables al API.

Tareas: completar ficha del origen y revisar condiciones vigentes; añadir transporte falso; implementar políticas y almacenamiento; probar rollback e idempotencia; realizar una consulta real acotada; registrar evidencias de mapeo y atribución. Si la primera respuesta real difiere de la documentación, conservar el problema como fixture sintética antes de corregirlo.

**Aceptación:** una colección real útil y atribuida persiste tras cerrar el proceso; la repetición controlada no duplica; un fallo conserva ofertas previas; cuota y cooldown sobreviven al reinicio; los contadores se explican; estado de fuente y base visibles.

**Aprendizaje:** seguir JSON → DTO → dominio → SQL; demostrar por qué no esperar HTTP dentro de una transacción; diferenciar instante observado de publicación. [Fiabilidad](../LearnDocs/05-data-reliability.md).

Dependencias: I1 y elección de ámbito/fuente. Riesgos: contrato externo, pertinencia de ofertas, timestamps ambiguos y errores de persistencia. Costo relativo: medio/alto. Se completaron tanto la validación con transporte falso como la persistencia y la primera consulta real; no fue necesario dividir la entrega.

**Estado:** aprobado explícitamente e implementado el 2026-09-25. Primera consulta: 19 ofertas válidas, una request. 82 pruebas de la suite pasan. Guía: [I2](../LearnDocs/09-real-ingestion-sqlite.md).

## I3 — MVP utilizable

**Objetivo:** buscar y revisar novedades sin depender de red.

Entregas: `list`, `show`, `changes`, JSON/CSV, escritura segura de archivos, mensajes de frescura, guía de uso real y evidencia Q16–Q19. Integrar las verificaciones pendientes de todos los cortes antes de declarar MVP.

**Aceptación:** recorrido completo de [SPEC](SPEC.md); búsqueda offline; filtros consistentes; atribución en exportaciones; salida sin fórmulas ejecutables ni controles de terminal; benchmark sintético documentado.

**Aprendizaje:** añadir un filtro desde la CLI al repositorio y demostrar que no toca el parser ni produce HTTP. Comparar resultados con una consulta manual pequeña.

Dependencias: I2. Riesgos: diferencias entre filtros de pantalla y exportación, datos viejos presentados como actuales. Costo relativo: medio.

**Estado:** aprobado el 2026-09-26 (“Seguimos con I3”), implementado y verificado. Q16–Q19 cubiertos, benchmark de 10.000 ofertas y guía [I3](../LearnDocs/10-local-search-export.md). Ejercicios personales pendientes.

## I4 — segundo origen y HTML externo

**Objetivo:** incorporar una segunda fuente de empleo sin mezclar identidades y practicar extracción/paginación HTML externa con acceso acotado.

Entregas: adaptador fijo de Greenhouse/GitLab; cuota y estado propios en la misma base; consultas `--source all` o por fuente; `lab-html` sobre dos páginas del sandbox Hockey Teams con revisión de robots; pruebas de fallos de contrato, DOM, paginación y acceso; guía [I4](../LearnDocs/11-second-source-html-lab.md).

**Aceptación:** una consulta real publica puestos GitLab, Remotive se conserva, la cuota de cada fuente no bloquea a la otra, la consulta unificada funciona, un lote incompleto no se publica; el laboratorio no contamina empleos y no sigue enlaces externos o excluidos. El límite de dos páginas representa una muestra explícita, no cobertura total del sandbox.

**Aprendizaje:** comparar DTOs y normalizadores; seguir `source_id` en runs/jobs/attempts; explicar por qué la muestra HTML tiene otra frontera de datos. Reconstruir un fallo de DOM con fixture propia.

**Estado:** aprobado el 2026-09-28 (“Vamos con I4”), implementado y verificado. Primera consulta Greenhouse: 200 ofertas válidas/una petición. Laboratorio: robots permitido, 2 páginas, 50 filas, cero escrituras. 120 pruebas pasan. Ejercicios personales pendientes.

## I5 — experimento de concurrencia y preparación operativa

**Objetivo:** aprender concurrencia estructurada, cancelación y backpressure con una comparación reproducible, y hacer visible la próxima oportunidad de cada fuente sin alterar su cuota.

Entregas: `lab-concurrency` con transporte sintético, dos tareas y cola acotada; `plan` read-only; `collect-all` manual secuencial que reutiliza las políticas; pruebas de límites, cancelación, cierre y continuidad; [guía I5](../LearnDocs/12-concurrency-and-planning.md) y [ADR-008](adr/008-concurrency-experiment.md).

**Aceptación:** la suite no abre conexiones externas; máximo dos requests simultáneas y una por host en el laboratorio, un escritor sintético, cola acotada, cancelación propagada y recursos cerrados. El plan no escribe ni reserva; collect-all continúa tras un estado fallido de la primera fuente y no inventa un pipeline alternativo.

**Estado:** aprobado el 2026-09-28 (“Perfecto, vamos con I5”), implementado y verificado. Cinco repeticiones sintéticas: medianas 0,6685 s secuencial y 0,4524 s concurrente. 129 pruebas pasan. No se instaló scheduler: la medición no justifica migrar el recolector SQLite real y faltan decisiones de horario, sueño/reinicio y avisos. Ejercicios personales pendientes.

## I6 — ranking explicable y estado personal

**Objetivo:** priorizar avisos con preferencias explícitas y guardar decisiones personales sin cambiar los datos del proveedor.

Entregas: `rank` con reglas y razones visibles, `mark` para favorito/descarte/nota, migración SQLite 1→2, [ADR-009](adr/009-personal-state-ranking.md) y [guía I6](../LearnDocs/13-ranking-and-personal-state.md).

**Aceptación:** cada razón suma el puntaje; campos y modalidad desconocida se manejan explícitamente; la recolección preserva anotaciones; la migración conserva avisos y revierte ante error; comandos sin red.

**Aprendizaje:** etiquetar una muestra propia y comparar precisión@10 frente al orden de descubrimiento; analizar falsos positivos y negativos. Esta evaluación personal sigue pendiente.

**Estado:** aprobado el 2026-09-28 (“Bien, seguimos con I6”), implementado y verificado. 139 pruebas pasaban entonces; base real migrada de esquema 1 a 2 con respaldo local.

## I7 — UI local desacoplada

**Objetivo:** explorar y revisar ofertas visualmente sin mover las reglas de consulta, ranking o anotación fuera de los casos de uso; la CLI permanece operable desde terminal.

Entregas: UI en navegador y [API HTTP local](API.md) iniciadas con `serve`, lista/filtros, detalle con fuente y frescura, razones de ranking, favorito/descarte y nota; [ADR-010](adr/010-local-ui-api.md) y [guía I7](../LearnDocs/15-local-ui-api.md). API y CLI se operan desde PowerShell y llaman a los mismos casos de uso; la UI no escribe SQL.

**Aceptación:** equivalencia API/CLI en lista y ranking; anotación API visible en CLI; UI funcional con datos locales; wheel con assets; servidor en loopback sin recolección automática. La [evaluación manual I6](../LearnDocs/14-i6-evaluation-quick-guide.md) sigue siendo útil para mejorar la presentación, no una condición de I7.

**Estado:** aprobado el 2026-09-28 (“Genial, entonces arrancamos I7?”), implementado y verificado. Evaluación personal I6 pendiente.

**Extensión posterior:** diseñar herramientas de lectura acotadas para agentes sobre esos mismos casos de uso, con contratos, límites y evidencia. Escrituras, recolección o acciones externas requieren autorización y diseño específicos. Ver [roadmap](ROADMAP.md) y [extensiones](EXTENSIONS_AI.md). I8 implementa esa extensión de lectura; I9 implementa perfiles/evaluación; I10 implementa seguimiento; I11+ queda pendiente.

## I8 — herramientas de lectura para agentes

Buscar ofertas, leer detalle y consultar ranking mediante contratos acotados sobre los casos de uso existentes. Excluir notas privadas del DTO para agentes por defecto; demostrar equivalencia con CLI/API y límites aplicados en código. Una demo con llamadas controladas permite verificar el adaptador antes de elegir un modelo. Aceptación y aprendizaje en [NEXT_STEPS](NEXT_STEPS.md).

Estado al 2026-09-30: aprobado (“Bien, vamos con I8”), implementado con MCP stdio opcional, tres herramientas y demo sin modelo. [Contrato](AGENT_TOOLS.md) y [guía](../LearnDocs/16-agent-tools.md). Los hitos de seguimiento y postulaciones asistidas son posteriores y dependen de uso real y acceso autorizado por destino.

## Regla de cierre y continuidad

Cada revisión deja demo, evidencia y aprendizaje pendiente. Aprobar un bloque no aprueba automáticamente todos los siguientes. Las fichas son una propuesta de alcance y pueden ajustarse antes de implementarse; un cambio queda registrado junto con su motivo.

## I9 — búsquedas guardadas y pertinencia

Aprobado el 2026-09-30 (“Bien, vamos con I9”). Implementado en 0.9.0: perfiles compartidos UI/API/CLI, filtro de título, captura consistente y etiquetas/precisión con incertidumbre. Objetivo confirmado: Senior Software Engineer remoto o presencial desde Uruguay. [Contrato](SAVED_SEARCHES.md), [guía](../LearnDocs/17-saved-searches-and-relevance.md) y [ADR-012](adr/012-saved-searches-evaluation.md).

La aceptación técnica cubre paridad, persistencia atómica, identidad de muestra, cambios concurrentes, privacidad y métricas sobre datos sintéticos. La muestra real queda pendiente de juicio personal; no se incorporaron nuevos boards ni se afirma mejora de relevancia medida.

## I10 — seguimiento de candidaturas

Aprobado el 2026-09-30 (“Vamos con I10”). Implementado en 0.10.0: aplicación separada de favoritos, altas desde oferta o referencia manual, estados con motivo/historial, deduplicación y revisión optimista; UI/API/CLI sobre el mismo servicio. [Contrato](APPLICATIONS.md), [guía](../LearnDocs/18-application-tracking.md), [ADR-013](adr/013-application-tracking.md). Sin extracción de referencias ni envíos. I11+ pendiente.
