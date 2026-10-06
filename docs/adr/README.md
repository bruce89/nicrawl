# Registro de decisiones

Actualizado el 2026-09-30. ADR-001–004 y 006–013 están aceptados en sus cortes; ADR-005 continúa propuesto. HTML laboral externo, más boards y async siguen como alternativas futuras.

| ADR | Decisión | Corte |
| --- | --- | --- |
| [001](001-python-tooling.md) | Python moderno, CLI y herramientas pequeñas | I0–I2 |
| [002](002-source-strategy.md) | HTML controlado para aprender y API para primera utilidad real | I1–I2 |
| [003](003-storage-identity.md) | SQLite, identidad de origen y publicación atómica | I2 |
| [004](004-execution-policy.md) | Ejecución secuencial con límites durables | I2; revisión I5 |
| [005](005-extension-boundary.md) | Dominio independiente y enriquecimiento futuro separado | I3+ |
| [006](006-local-queries-exports.md) | Consultas en snapshot, Unicode y exportación atómica; aceptado | I3 |
| [007](007-second-source-html-lab.md) | Segundo origen fijo y laboratorio HTML acotado; aceptado | I4 |
| [008](008-concurrency-experiment.md) | Experimento medido; producción secuencial | I5 |
| [009](009-personal-state-ranking.md) | Estado separado y ranking explicable | I6 |
| [010](010-local-ui-api.md) | UI y API HTTP locales sobre casos de uso compartidos | I7 |
| [011](011-agent-tools-mcp.md) | MCP stdio opcional, proyección privada y límites explícitos | I8 |
| [012](012-saved-searches-evaluation.md) | Perfiles locales y muestras reproducibles con etiquetas humanas | I9 |
| [013](013-application-tracking.md) | Candidaturas separadas con historial transaccional y revisión | I10 |
| [014](014-profile-drafts.md) | Perfil versionado y borradores con citas | I11 |
| [015](015-local-submission-simulation.md) | Ensayo durable, confirmación e idempotencia | I12a |
| [016](016-http-test-receiver.md) | Dos procesos HTTP locales, incertidumbre y reintento explícito | I12b |

Una decisión nueva debe describir contexto, elección, alternativas, consecuencias, validación y condición para reabrirla. Cambiar de opinión con evidencia es parte del método.
