# I12a — ensayo local de recepción

Aprobado el 2026-10-04 con “Dale con la parte a”. Aplicación 0.12.0.
[Guía práctica](../LearnDocs/20-local-submission-lab.md) · [ADR-015](adr/015-local-submission-simulation.md).

## Recorrido

`prepare` lee una revisión explícita del borrador y congela su contenido, versión de
perfil, candidatura y destino fijo `local://nicrawl-test-receiver`. Devuelve una vista
previa y `review_sha256`. El usuario revisa el contenido y confirma ese hash al enviar.
Las preguntas pendientes bloquean la preparación: resolverlas primero en una nueva
revisión. El hash vincula confirmación y contenido; no es firma, contraseña ni prueba
de que una persona efectivamente leyó el texto.

El receptor es un **simulador en proceso con persistencia SQLite**, sin sockets ni
HTTP saliente. La API HTTP existente permite operar el simulador desde loopback.
La simulación modela resultados del transporte; no mide latencia ni prueba un ATS.
No acepta una URL destino, archivos adjuntos ni credenciales. No consulta la URL del
aviso. No escribe el estado `submitted`, ni ofertas, favoritos o perfiles.

## Estados y reintentos

| Escenario | Resultado del emisor | Recibo en receptor | Reconciliar |
| --- | --- | --- | --- |
| accepted | accepted | Aceptación | Conserva el estado |
| rejected | rejected | Rechazo | Conserva el estado |
| timeout-before | uncertain | No existe | Vuelve a prepared; el reintento es explícito |
| timeout-after | uncertain | Aceptación guardada | Recupera accepted sin reenviar |

Un resultado incierto impide `send` hasta reconciliar. Repetir un envío aceptado o
rechazado devuelve el resultado registrado, aunque se pida otro escenario. Repetir
`prepare` para el mismo borrador/revisión recupera el mismo identificador. Una revisión
nueva tiene otra identidad y requiere otra revisión humana. No se deduplican distintas
versiones, distintos borradores ni candidaturas por semejanza.

La ausencia de recibo es definitiva únicamente en este simulador: no quedan requests
en vuelo. En un proveedor real, una consulta sin resultado puede ser temporal; I12b
debe definir reconciliación e idempotencia con el contrato del proveedor.

## Almacenamiento

`<base>.simulation.sqlite3` tiene identidad SQLite propia y esquema 1. Tablas:
`submissions` guarda la instantánea, hash e identidad única por borrador/versión;
`receipts` admite un recibo por intento; `events` guarda el historial. Una transacción
`BEGIN IMMEDIATE` serializa recepción simulada y resultado. Ante un error antes del
commit no se publica ninguno. Esto no equivale a una transacción distribuida real.

La instantánea contiene texto personal del borrador, sin cifrar. Usar `data/` para el
laboratorio y datos ficticios. Copiar este archivo con la aplicación detenida si se
quiere conservar el historial del ensayo. No eliminarlo para reintentar un resultado
incierto. Las herramientas MCP no acceden al simulador. No hay borrado selectivo.

## Contrato HTTP

Todas las escrituras requieren JSON, Host/Origin locales, cuerpo de hasta 4096 bytes
y no admiten parámetros de URL. Los campos de comando son pequeños; el borrador se
lee del almacén local. Errores de entrada: 400; inexistente: 404; conflicto: 409.

| Método/ruta | Cuerpo |
| --- | --- |
| POST `/api/simulations` | `{"draft_id":"<uuid>","version":1}` |
| GET `/api/simulations/<id>` | Sin cuerpo; estado, instantánea e historial |
| POST `/api/simulations/<id>/send` | `{"review_sha256":"<hash revisado>","scenario":"timeout-after"}` |
| POST `/api/simulations/<id>/reconcile` | `{}` |

Respuestas exitosas: 200, también para rechazos **simulados**; leer el campo `state`.
`receipt_id` permanece oculto al emisor mientras el estado sea `uncertain`.
La UI muestra estos estados en Candidaturas al crear o reabrir un borrador. Recargar
la página y preparar otra vez la misma revisión recupera su ensayo existente.

## Evidencia y próximos pasos

Pruebas de los cuatro escenarios, carreras concurrentes, confirmación incorrecta,
instantánea tras nueva revisión, bloqueo por preguntas, rollback, base ajena intacta
y recorrido compartido CLI/API. La validación del usuario de I11 se mantiene separada
de esta evidencia. I12b sigue pendiente de elegir un destino con acceso permitido,
contrato verificable y autorización del envío concreto.
