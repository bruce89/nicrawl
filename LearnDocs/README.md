# LearnDocs — aprender construyendo y reconstruyendo nicrawl

Esta carpeta enseña conceptos y propone experimentos. [docs](../docs/SPEC.md) define el producto. El punto de partida es experiencia en ingeniería de software y arquitectura iOS; el nivel de Python se diagnostica, no se presupone desde cero.

## Recorrido

| Orden | Lectura | Pregunta central |
| --- | --- | --- |
| I7 | [UI y API local](15-local-ui-api.md) | ¿Cómo comparten casos de uso el navegador, la API y la CLI? |
| I6 | [Ranking y estado personal](13-ranking-and-personal-state.md) · [Guía rápida de evaluación](14-i6-evaluation-quick-guide.md) | ¿Cómo evalúo reglas visibles sin mezclar mis decisiones con el origen? |
| I5 | [Concurrencia y planificación](12-concurrency-and-planning.md) | ¿Cuándo ayuda async y cómo se conservan límites/cancelación? |
| I4 | [Segundo origen y HTML externo](11-second-source-html-lab.md) | ¿Cómo agrego un proveedor y pagino un sandbox respetando acceso? |
| I3 | [Consulta local y exportación](10-local-search-export.md) | ¿Cómo convierto la colección en resultados utilizables? |
| I2 | [Ingesta real y SQLite](09-real-ingestion-sqlite.md) | ¿Cómo se publica una colección sin duplicar ni perder datos? |
| 0 | [Primer corte ejecutable](08-first-working-slice.md) | ¿Cómo pruebo y sigo el código ya construido? |
| 1 | [Hoja de aprendizaje](01-learning-roadmap.md) | ¿Qué puedo demostrar en cada corte? |
| 2 | [Cómo funciona un scraper](02-how-scrapers-work.md) | ¿Qué convierte una descarga en datos útiles? |
| 3 | [Python desde iOS e ingeniería](03-python-from-ios.md) | ¿Qué se parece y qué cambia realmente? |
| 4 | [Ingeniería inversa y laboratorios](04-reverse-engineering-labs.md) | ¿Puedo seguir y modificar el recorrido completo? |
| 5 | [Fiabilidad de datos](05-data-reliability.md) | ¿Cómo sé que el resultado es correcto? |
| 6 | [Casos reales](06-real-world-cases.md) | ¿Dónde se transforma la recolección en valor? |
| 7 | [Bitácora y glosario](07-workbook.md) | ¿Qué aprendí y cómo lo comprobé? |

## Método

Antes de ejecutar, predecir. Después observar entrada, transformaciones y salida. Cambiar una sola condición y explicar el resultado con evidencia. Finalmente repetir el recorrido sin ayuda, o dibujarlo de memoria. La implementación futura debe añadir rutas reales de archivos y puntos de breakpoint a estos ejercicios.

No hace falta estudiar todo Python antes de I1. Sí hace falta entender qué parte del sistema se está ejecutando, quién posee los recursos y qué invariantes protege. Una sesión puede terminar con una hipótesis falsa bien explicada; eso también es progreso.

**I0–I7 están implementados y técnicamente verificados.** Empezá por la [guía I7](15-local-ui-api.md) si querés comparar navegador, HTTP y CLI; las guías anteriores recorren adquisición, consulta, concurrencia y ranking. Tus laboratorios y bitácora personales siguen pendientes. I8+ continúa como propuesta.
