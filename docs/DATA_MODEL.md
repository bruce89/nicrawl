# Modelo de datos e invariantes

Estado al 2026-09-28: I2–I6 implementados; I6 migró transaccionalmente el esquema 1 a 2. `source_id` distingue `remotive` y `greenhouse:gitlab`, y runs/attempts/política se registran por fuente. El laboratorio de hockey no entra en estas tablas. I2 implementó los invariantes base. JobDraft incluye modalidad, tags, tipo y fechas de origen. El repositorio guarda identidad, huella, tiempos de observación, runs, observaciones y cambios. Los payloads normalizados se almacenan como JSON; identidad, URL y tiempos de observación son columnas explícitas. Nombres en inglés, tiempos propios UTC con offset explícito. Esquema 2 con migración transaccional inicial y 1→2, más application_id; versiones futuras/ajenas se rechazan.

## Oferta

| Campo | Regla |
| --- | --- |
| `job_key` | Identidad canónica de la tupla `(source_id, source_job_id)`; representación CLI con separadores escapados |
| `source_id` | Proveedor y ámbito estable; `remotive` inicialmente, un board se distingue por su token en futuras fuentes |
| `source_job_id` | String no vacío de ID estable del origen; la demo usa ID sintético |
| `title`, `company` | Texto no vacío después de normalizar espacios |
| `source_url` | URL absoluta HTTP(S) del aviso, preservada para atribución; nunca se descarga automáticamente al mostrarla |
| `description_text` | Texto extraído; opcional si el origen no lo ofrece, advertencia de calidad |
| `location_raw` | Restricción geográfica original o null; sin inferir elegibilidad |
| `work_mode` | `remote`, `hybrid`, `onsite` o `unknown`; requiere evidencia del origen |
| `salary_raw` | Texto original o null; no inferir moneda, intervalo ni periodicidad |
| `employment_type_raw`, `tags` | Valor de origen y lista normalizada; vacíos no implican una categoría concreta |
| `published_raw` | Fecha original de publicación, tal como la provee la fuente, o null |
| `published_at` | UTC solo si la zona/offset está documentada o explícita; si no, null |
| `source_updated_at` | Modificación declarada por origen; no se confunde con publicación |
| `first_seen_at` | Primera observación válida en una corrida publicada |
| `last_seen_at` | Última observación válida publicada, aunque el contenido no cambie |
| `last_changed_at` | Último cambio material; inicialmente igual a `first_seen_at` |
| `content_hash`, `normalizer_version` | Huella determinista del contenido y versión de transformación |

No usar `(title, company)` como clave: puede haber puestos homónimos. Si una fuente futura no tiene IDs, su ADR deberá definir identidad basada en URL estable y evaluar sus colisiones. El parser inicial rechaza registros sin ID.

## Persistencia implementada

| Tabla | Responsabilidad |
| --- | --- |
| `jobs` | Última versión observada; UNIQUE sobre `(source_id, source_job_id)` |
| `runs` | Inicio, fin, fuente, ámbito, estado, cobertura, contadores, versión del adaptador |
| `run_items` | Relación run/oferta observada y tipo `new`, `updated`, `unchanged` |
| `changes` | Antes/después de campos materiales, evento y run; alta sin versión anterior |
| `source_state` | Último intento, próxima oportunidad durable y motivo de deshabilitación |
| `attempts` | Cada intento de red, persistido antes del envío; índice por origen/fecha |
| `schema_migrations` | Versiones aplicadas; una migración por transacción |
| `personal_state` | Estado `favorite`/`dismissed`/`unreviewed`, nota y actualización UTC por `job_key`; FK a `jobs` |

Los rechazos del run se guardan como código, índice/ID si es legible y campos fallidos; no como una copia completa del aviso. Las foreign keys se habilitan explícitamente por conexión. Una consulta `changes --run latest` toma el último run con publicación de datos para la fuente elegida, incluidos parciales, y muestra su estado.

## Datos personales derivados

`personal_state` está fuera de `jobs.payload`, `content_hash` y `changes`. Una nueva publicación conserva estado y nota; `unreviewed` sin nota elimina la fila opcional. `rank` calcula puntajes en memoria con reglas versión 1 y no persiste preferencias ni resultados. El esquema 1 se migra al primer acceso de escritura con 0.6.0; una lectura anterior a migrar falla con instrucción de respaldo. [ADR-009](adr/009-personal-state-ranking.md).

## Idempotencia y cambios

La huella se calcula sobre JSON canónico de campos materiales: título, empresa, URL, descripción en texto, localización, modalidad, salario original, tipo y tags ordenados sin repetidos. Se normalizan espacios y saltos de línea de forma documentada. No incluye tiempos de recolección, orden de llegada ni el timestamp de actualización del proveedor.

- ID nuevo: insertar y registrar `new`.
- Mismo ID y misma huella: actualizar `last_seen_at` y registrar observación `unchanged`; no crear evento de cambio.
- Mismo ID y otra huella: actualizar contenido, `last_seen_at` y `last_changed_at`, registrar diff `updated`.
- Mismo ID dos veces con igual contenido en un lote: colapsar y contar duplicado exacto.
- Mismo ID dos veces con distinto contenido en un lote: rechazar ese ID completo, reportar conflicto; el resto puede producir run parcial.

Cambiar `normalizer_version` exige una migración/reprocesamiento explícito. No producir una avalancha de “ofertas actualizadas” causada únicamente por un algoritmo de limpieza nuevo.

## Cobertura, ausencia y frescura

`coverage` vale `complete` o `incomplete`. Se refiere al ámbito exacto de consulta, no a todo el mercado. Un listado de una categoría no permite razonar sobre otra. El ámbito se guarda como parámetros canónicos y versión de fuente.

`complete` exige adquisición entera, formato reconocido, todos los candidatos válidos o duplicados exactos y condición de fin verificada. Rechazos de registros producen `partial`/`incomplete`. Una página vacía sin marcadores esperados es `failed`, no éxito vacío.

En v0.1 **no existe cierre automático por ausencia**. Se muestran “observada hace…” y “no observada en esta colección completa” solo cuando la cobertura lo permite. No se retira una oferta guardada porque deje de venir en un feed. Si transcurren más de siete días desde `last_seen_at`, mostrar “dato antiguo”; esto tampoco afirma cierre.

Un run fallido no avanza `last_seen_at`. Un GET nuevo que entrega contenido igual sí lo avanza. La fecha de publicación del aviso no se sustituye por la hora de descarga. Fechas sin offset conservan su valor bruto y dejan el instante normalizado desconocido.

## Minihistoria de aceptación

Ejemplo ficticio: R1 observa A y B; R2 observa A igual y B con otra descripción; R3 falla por timeout; R4 observa solo A en una colección completa.

Resultado esperado: dos ofertas persistidas, dos altas en R1, un cambio en R2, ningún cambio de ofertas en R3, B con `last_seen_at` de R2 y sin etiqueta de cierre en R4. R4 puede informar que B no fue observada en ese ámbito. No se afirma que perdió vigencia.

## Retención propuesta, aún sin purga automática

I2 conserva ofertas e historial. No se implementó borrado automático ni rotación de logs: el diagnóstico durable vive en SQLite. La siguiente política se mantiene como diseño futuro y debe probarse antes de activarse.

Ofertas normalizadas: sin purga automática en MVP. Runs, observaciones y cambios: 90 días. Logs rotados: hasta cinco archivos de 5 MiB. No conservar cuerpos externos completos por defecto. La purga de historial respeta foreign keys y no elimina ofertas; antes de habilitarla se prueba su efecto sobre consultas de novedades. Borrado completo solo mediante una acción explícita sobre la base seleccionada.

## I10: almacén personal de candidaturas

Archivo SQLite separado, esquema 1: applications (UUID, job_key opcional, título/empresa/URL capturados, estado, revisión, fechas), identities (identidad única → candidatura), events (candidatura + revisión, fecha, tipo, estado anterior/nuevo y motivo). La colección mantiene esquema 2. No hay FK entre archivos; el vínculo se valida al alta. [Contrato](APPLICATIONS.md).
