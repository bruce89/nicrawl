# ADR-016 — emisor y receptor propios separados por HTTP

Aceptado 2026-10-04 para I12b. El usuario eligió construir un receptor propio y posponer
la evaluación de integración real. Aplicación 0.13.0; I12c queda pendiente.

## Decisión

Dos procesos y dos almacenes, protocolo JSON acotado sobre loopback. Token local generado
una sola vez, identidad durable del receptor y snapshot confirmado antes de cada envío.
Persistir sending antes de la red; conservar uncertain si falta una respuesta verificable.
Deduplicar por una clave durable y rechazar cambios de contenido bajo esa clave.

No usar el 404 como permiso de reenvío automático: puede haber requests en vuelo. La
consulta conserva incertidumbre y habilita un retry explícito con la misma clave. El
receptor propio garantiza que ese retry no duplica el efecto. Reiniciar procesos conserva
identidades y recibos; reemplazar el archivo receptor cambia identidad y exige investigar.

## Alternativas y consecuencias

- I12a sigue siendo un laboratorio determinista útil, pero una sola transacción no
  representa fallos entre procesos. Se conserva separado para comparar ambos enfoques.
- Un proveedor externo exige permisos y un contrato que todavía no se han evaluado;
  está fuera de este corte. No se presupone que acepte la misma clave o API.
- No se agrega TLS ni exposición a la LAN: host literal 127.0.0.1, proxies y redirects
  desactivados. El token evita llamadas accidentales de páginas/aplicaciones sin el
  secreto, pero no protege frente al usuario dueño del equipo ni cifra el almacenamiento.
- El receptor conserva el snapshot para que la práctica permita inspeccionar entrega.
  Se usan datos ficticios. No hay autenticación multiusuario, adjuntos, borrado selectivo,
  envío a terceros ni cambio automático del seguimiento de candidaturas.

## Verificación y reapertura

HTTP real con timeout-before/after, reconciliación, confirmación incorrecta, contenido
distinto bajo una clave, origen ajeno, carreras, respuesta inválida, caída del emisor y
receptor arrancado/reiniciado en subprocess. Reabrir antes de otra máquina, Internet,
multiusuario o un ATS: autorizaciones, credenciales, datos, garantías de idempotencia,
errores, límites, adjuntos, permisos por envío y tratamiento de datos deben definirse
para ese destino. Ninguna de esas acciones queda aprobada por este laboratorio.
