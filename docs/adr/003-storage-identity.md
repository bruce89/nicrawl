# ADR-003 — persistencia e identidad

Estado: aceptado e implementado en I2 · 2026-09-25. Verificados identidad, publicación atómica, diffs y preservación por ausencia.

## Contexto y decisión

Repetir la colección debe conservar novedades sin multiplicar avisos ni borrar datos tras fallos. Proponer SQLite local, clave única por fuente e ID externo, última versión en `jobs`, observaciones por run y cambios materiales. Publicar un lote validado en una transacción corta. No cerrar empleos por ausencia.

SQLite no requiere un servidor aparte y permite estudiar SQL y transacciones con un alcance local. El módulo sqlite3 expone parámetros ligados y gestión transaccional; el modo de transacción se configura explícitamente en la implementación. [Documentación sqlite3](https://docs.python.org/3.14/library/sqlite3.html).

## Alternativas

- CSV/JSON como persistencia principal: fáciles de leer, pero difíciles para actualizaciones, identidad, historial y recuperación; se conservan como exportación.
- SQLAlchemy: valioso con consultas/modelos mayores o varias bases; SQLite directo expone los fundamentos y reduce superficie inicial.
- PostgreSQL: adecuado para múltiples usuarios/escritores; sin necesidad actual de servidor.
- Event sourcing completo: gran trazabilidad, pero reconstrucción y evolución de eventos más costosas que una tabla actual más historial acotado.
- Deduplicación por similitud de título: puede fusionar vacantes distintas; queda como experimento con evaluación.

## Consecuencias y validación

Gestionar migraciones y transacciones explícitas es responsabilidad del proyecto. No mantener red dentro de transacciones; habilitar claves foráneas; impedir dos recolectores simultáneos. Validar Q07, Q08, Q13, Q14, Q20 y Q22.

Reabrir si hay escrituras concurrentes sostenidas, un servicio compartido o requisitos de historial que superen la retención propuesta. [Modelo canónico](../DATA_MODEL.md).
