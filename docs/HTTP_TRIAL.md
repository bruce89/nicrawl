# I12b — receptor propio por HTTP

Aplicación 0.13.0, 2026-10-04. Aprobado: “Vamos con el primer camino, y dejamos en el
SPEC o en algún lado evaluar luego el segundo”. La evaluación de un ATS/portal real
se desplaza a I12c; ver [SPEC](SPEC.md#evaluación-posterior-i12c-integración-real).
[Guía](../LearnDocs/21-http-receiver-lab.md) · [ADR-016](adr/016-http-test-receiver.md).

## Arquitectura y datos

El emisor (`http_trial.py`) llama a un receptor en otro proceso (`test-receiver`).
UI y CLI usan el mismo emisor; el navegador nunca lee el token ni llama directamente
al receptor. I12a permanece disponible con `simulation` y su almacén anterior.

| Archivo derivado de --db | Contenido |
| --- | --- |
| `.http-trials.sqlite3` | Snapshot preparado, destino/identidad, hash, estado, escenario e historial del emisor |
| `.test-receiver.sqlite3` | Identidad durable, claves recibidas y recibos con copia del snapshot |
| `.test-receiver.token` | Token generado al iniciar el receptor; no se imprime ni se devuelve en JSON |

Las dos bases tienen identidad SQLite propia y esquema 1; rechazan archivos ajenos.
No se modifica la colección, el CV ni el estado de candidatura. El snapshot contiene
el borrador con citas seleccionadas, no el CV completo. Estos archivos están excluidos
de Git; permanecen sin cifrar y heredan permisos del directorio local. No es un servicio
multiusuario ni accesible desde el celular. Respaldar ambos almacenes y token con los
procesos detenidos; no borrar recibos para resolver un ensayo incierto.

## Frontera HTTP

Receptor: `127.0.0.1:8766` por defecto. CLI permite otro puerto local; no acepta host ni
URL remotos. Emisor: destino construido con loopback literal, `trust_env=False`, sin
redirecciones, sin proxies de entorno ni reintentos automáticos. Host exacto y token
Bearer requeridos; peticiones con Origin se rechazan. La API de UI conserva su control
Host/Origin y actúa como adaptador de comandos. El token no constituye una frontera
contra otro programa con acceso a los archivos del mismo usuario.

Preparar consulta `/v1/info` autenticado y congela identidad del receptor, puerto y
contenido. El hash cubre esos datos; enviar exige confirmarlo. El receptor verifica su
identidad y el hash antes de guardar. Si el puerto ahora pertenece a otro receptor o
la respuesta no coincide con la clave/hash, el emisor conserva incertidumbre.

| Operación del receptor | Contrato |
| --- | --- |
| GET `/v1/info` | Protocolo `nicrawl-test-receiver-v1` e identidad estable |
| POST `/v1/submissions` | `id`, `receiver_id`, `digest`, `payload`, `scenario` |
| GET `/v1/receipts/<id>` | Recibo: protocolo, receptor, id, digest, receipt_id, result; 404 autenticado si no hay recibo |

Un ID repetido con mismo contenido/escenario recupera el recibo. Con contenido o
escenario distinto: 409. Una clave única durable y transacción SQLite arbitran carreras.
Cuerpo máximo 2 MB; respuesta leída por emisor hasta 8 KiB. Timeout del cliente: 2 s
por operación de socket, no un deadline total de negocio. El receptor no realiza
llamadas externas ni ejecuta instrucciones del borrador. No hay adjuntos ni LLM.

## Incertidumbre y recuperación

Antes de HTTP el emisor confirma `sending` en su base. Después valida la respuesta y
guarda accepted/rejected, o uncertain si no puede confirmar. No mantiene una transacción
SQLite durante la red. Si el emisor cae entre recepción y registro, `sending` permite
consultar el recibo al volver a abrirlo. Un resultado final nunca se degrada por una
respuesta tardía de otro intento.

**404 no significa entrega descartada:** una solicitud previa puede estar en vuelo.
La consulta deja uncertain y no reenvía. Después de consultar, `retry` exige confirmar
otra vez el mismo hash, usa el mismo ID/payload/escenario y se apoya en la deduplicación
del receptor. No se genera una nueva clave por reintento. Repetir send sobre un estado
incierto se rechaza. Una revisión de borrador diferente constituye otro ensayo.

Los escenarios se fijan al primer send:

- accepted/rejected: recibo inmediato y durable.
- timeout-before: el receptor registra la clave pero omite el recibo en la primera
  llamada; demora 3 s la respuesta. La consulta sigue incierta; retry con la misma clave
  completa la recepción. El fallo inyectado se aplica una sola vez por clave.
- timeout-after: confirma recibo y demora 3 s la primera respuesta. El cliente vence a
  los 2 s; reconcile recupera accepted. El reintento no duplica recibos.

Son fallos de transporte reales provocados de forma controlada en loopback; no prueban
DNS, TLS, Internet, un ATS ni garantías de otro proveedor. Si se pierde la base receptora,
su nueva identidad impide reconciliar intentos anteriores. No preparar un intento nuevo
como sustituto silencioso de un reintento: cambia la identidad y se pierde deduplicación.

## API y UI de nicrawl

`POST /api/http-trials` recibe `draft_id` y `version`. `GET /api/http-trials/<id>` muestra
snapshot/estado. POST `/<id>/send`: `review_sha256`, `scenario`; POST `/<id>/reconcile`:
`{}`; POST `/<id>/retry`: `review_sha256`. Todas con prefijo `/api/http-trials`, sin campos
adicionales. La UI usa el puerto 8766; CLI prepare permite `--port` y lo conserva.
Rechazos del ensayo llegan en `state`, no como un fallo de la API de nicrawl.

En Candidaturas, “Preparar ensayo HTTP” muestra la instantánea y exige marcar revisión.
“Consultar recibo local” consulta sending/uncertain. “Reintentar con la misma clave”
se habilita tras la consulta si el resultado continúa incierto. Iniciar el receptor en
otra terminal con la misma --db que `serve`. La prueba local no es una postulación real.
