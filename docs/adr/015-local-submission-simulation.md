# ADR-015 — receptor simulado durable y confirmación de instantánea

Aceptado en I12a, 2026-10-04: “Dale con la parte a”.

## Decisión

Un caso de uso local separado guarda una instantánea inmutable de una revisión del
borrador. Confirmar exige su hash; deduplicar usa el ID durable obtenido al preparar,
único para borrador/versión. Los resultados inciertos bloquean el envío hasta consultar
el recibo. CLI, UI y API comparten el servicio; no se añade escritura a MCP.

El receptor simulado se guarda junto al emisor en una SQLite distinta del seguimiento.
Recepción y estado se confirman en una transacción. Los cuatro escenarios modelan
éxito, rechazo y pérdida de respuesta antes/después de recepción. No hay HTTP saliente,
dirección configurable, respuesta generada por un modelo ni candidatura real.

## Motivos y alternativas

Este corte enseña identidad y reconciliación de forma reproducible antes de contar
con un proveedor autorizado. Un receptor HTTP en otro proceso probaría además
conexiones y fallos de transporte, pero añadiría arranque, puertos, autenticación y
gestión de procesos. Se posterga esa frontera para I12b. Un mock solo en memoria no
permitiría recuperar el ensayo al cerrar la aplicación. Cambiar a `submitted` mezclaría
la práctica con el seguimiento personal, por lo que los estados se almacenan aparte.

## Consecuencias y reapertura

La atomicidad local no existe automáticamente entre cliente y proveedor real. En I12b,
un timeout requiere conservar incertidumbre y una ausencia puede ser temporal. Antes
de conectar un destino hay que definir claves durables, garantías del receptor,
reconciliación, campos/adjuntos y confirmación explícita. El hash comprueba contenido,
no autentica a la persona. La deduplicación no cruza revisiones o borradores diferentes.

El archivo de ensayo contiene texto personal sin cifrar; el laboratorio utiliza datos
ficticios. No hay borrado selectivo. Reabrir al necesitar otro proceso receptor, red,
varios usuarios o un proveedor real. Validación: carreras de preparación/envío,
instantáneas, rollback, reconciliación y paridad de CLI/API en pruebas sintéticas.
