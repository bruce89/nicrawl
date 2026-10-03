# I10 — seguimiento de candidaturas

Implementado en 0.10.0, 2026-09-30, aprobado con “Vamos con I10”. [Guía práctica](../LearnDocs/18-application-tracking.md) y [ADR-013](adr/013-application-tracking.md).

Una candidatura registra una decisión propia respecto de una oferta. Es independiente de favorito/descarte/nota de I6: marcar una favorita no crea candidatura, y cambiar una candidatura no modifica la oferta ni sus notas. I10 no envía formularios, no descarga referencias, no prepara CV y no incorpora herramientas MCP de escritura.

## Entradas, estados e historial

Crear desde `job_key` completo copia título, empresa y URL de esa oferta. Crear desde una referencia manual exige URL HTTP(S), título y empresa; puede ser LinkedIn u otro sitio. No se consulta esa URL. Ambos caminos comienzan en **draft**. Cada registro tiene UUID, origen opcional, estado, revisión y fechas UTC.

| Estado | Significado |
| --- | --- |
| draft | Seguimiento iniciado; todavía no declaraste envío |
| submitted | Declaraste que postulaste por fuera de nicrawl |
| interview | Registraste avance a entrevista |
| closed | Seguimiento cerrado; indicar el motivo en el historial |

Toda actualización exige `reason` (1–2000 caracteres no vacíos) y `expected_revision`. Se permite cualquier cambio, incluida reapertura o corrección hacia un estado anterior: el usuario registra hechos, no sigue un workflow rígido. Repetir el mismo estado agrega un avance/nota al historial. No se editan ni eliminan eventos desde las interfaces. Las fechas son momentos de registro; si el hecho ocurrió antes, aclararlo en reason. No se interpreta el motivo como una fecha ni como instrucción ejecutable.

Si otra interfaz modificó la candidatura, la revisión ya no coincide: se rechaza con conflicto y no se guarda nada. Recargar, revisar el nuevo historial y decidir qué registrar. Un reintento del mismo update con revisión vieja produce conflicto, no duplica un evento. Estado actual e inserción del evento se confirman juntos en una transacción.

## Identidad y límites de deduplicación

Una candidatura por `job_key` o URL canónica conocida. Crear un duplicado devuelve `created=false` y el registro original, sin alterar título, nota o estado ni agregar historial. Una URL conocida no vincula silenciosamente otro job_key; el origen de la candidatura original se conserva. Si clave y URL apuntan a dos registros distintos se devuelve conflicto, sin fusión automática.

La normalización local baja el host a minúsculas, retira puertos por defecto, fragmentos y parámetros utm_*, preservando otros parámetros y su orden. Para URLs HTTPS reconocidas de linkedin.com/www/m con `/jobs/view/<id>` o `/jobs/view/<slug>-<id>`, usa el ID numérico y descarta el tracking. Es una regla de identidad de nicrawl, no una integración con LinkedIn. Se guarda también la URL original.

No se unifican anuncios con URLs distintas, shortlinks o referencias de diferentes portales por semejanza de título/empresa. Una URL compartida por varios puestos puede causar una coincidencia excesiva; usar la URL individual del aviso. No hay fusión, edición de identidad, segunda candidatura al mismo puesto ni eliminación en I10. Para volver a trabajar un registro, reabrirlo con motivo. Si una referencia manual se detectó como duplicada de una oferta, conserva su origen manual; una URL cambiada posteriormente no cuenta con un enlace de job_key añadido automáticamente.

## Persistencia y privacidad

`<base>.applications.sqlite3` se crea en la primera escritura válida, junto a la base elegida por `--db`. Por ejemplo `data/nicrawl.sqlite3.applications.sqlite3`. Tiene identidad SQLite propia y esquema 1; tablas applications, identities y events. No migra ni escribe en SQLite de ofertas. La creación manual puede funcionar aun sin colección; crear por job_key requiere una oferta existente. `serve` sigue requiriendo una colección válida.

Las lecturas sin archivo devuelven lista vacía o no encontrado y no crean archivos. SQLite serializa escritores mediante BEGIN IMMEDIATE; índices únicos protegen identidades. Un archivo ajeno/incompatible se rechaza sin migrarlo. Respaldar este archivo además de ofertas/perfiles, con la aplicación detenida o mediante SQLite backup. `data/` no se publica en Git. No hay cifrado añadido; notas e historial son datos personales locales. Las herramientas MCP de I8 no acceden a este almacén.

Listas: hasta 200 registros por llamada, default CLI 50/API 20; filtro por estado. No hay paginación en I10. `show` devuelve todo el historial. La UI solicita los primeros 200 y declara cantidad/total; la CLI puede abrir un UUID conocido aunque quede fuera del listado. La escala prevista es seguimiento personal. Título manual hasta 400 caracteres, empresa 200, URL 2048. Credenciales, esquemas distintos de HTTP(S), controles y espacios en URL se rechazan.

## Interfaces

CLI: `applications add`, `list`, `show`, `update`; ejemplos en la guía. UI: enlace **Candidaturas** y botón **Crear seguimiento** en el detalle de una oferta. La vista `/applications` permite crear referencias manuales, filtrar, ver historial y registrar avances.

| Método/ruta | Contrato |
| --- | --- |
| GET `/api/applications?state=draft&limit=50` | total, limit, applications; state opcional |
| GET `/api/applications/<uuid>` | application e history |
| POST `/api/applications` | `{ "job_key": "...", "reason": "opcional" }` o `{ "url": "...", "title": "...", "company": "...", "reason": "opcional" }` |
| PATCH `/api/applications/<uuid>` | `{ "state": "submitted", "expected_revision": 1, "reason": "Envié desde el sitio del empleador" }` |

POST devuelve `created` y detalle, HTTP 200 tanto en alta como duplicado. PATCH devuelve detalle. Escrituras: JSON, Host/Origin locales, cuerpo máximo 16384 bytes y timeout de lectura. Campos desconocidos y tipos incorrectos: 400; no encontrado: 404; revisión/identidad en conflicto: 409. El servidor permanece en loopback. Los mensajes se muestran como texto, no HTML.

I11 es preparación de candidaturas con perfil/CV aportados por el usuario y borradores revisables. I12 tratará eventuales envíos autorizados con su propio contrato; no quedan aprobados por implementar seguimiento.
