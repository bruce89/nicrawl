# ADR-004 — ejecución, límites y concurrencia

Estado: aceptado e implementado en I2 · 2026-09-25. Cuotas durables, cliente síncrono y bloqueo de SO; async sigue como experimento futuro.

## Contexto y decisión

La primera fuente requiere pocas consultas; paralelizar no aporta valor inicial. Proponer cliente síncrono reutilizado, pipeline secuencial y políticas de presupuesto/cooldown persistidas. Un único dueño de reintentos y un bloqueo por base evitan tormentas de requests.

## Alternativas

- Async desde I0: enseña concurrencia temprano, pero añade cancelación y coordinación antes de dominar el pipeline. Se reserva para laboratorio I5.
- Threads: útiles para I/O bloqueante; coordinación de cuotas y conexión SQLite exige atención adicional.
- Framework de crawler desde I0: resuelve scheduling genérico, innecesario con un endpoint.
- Reintento genérico de todo error: oculta bugs y amplifica carga; se eligen fallos transitorios concretos.

## Consecuencias y validación

El diseño inicial optimiza legibilidad y coherencia, no throughput. Un deadline y límites de tamaño son necesarios incluso sin concurrencia. El reloj de pared se usa para timestamps/cooldown durable; duración dentro del proceso con reloj monotónico. Si el reloj de pared retrocede respecto del último intento, diferir con aviso hasta recuperar una ventana consistente; no habilitar ráfagas.

Q09–Q11, Q20 y Q21 verifican políticas sin sleeps reales usando reloj y transporte falsos. I5 reabrió la decisión para medir dos fuentes sintéticas: hubo solapamiento de esperas, pero la recolección real sigue secuencial; ver [ADR-008](008-concurrency-experiment.md). Reabrir otra vez si varias fuentes reales hacen medible una espera evitable, manteniendo límites por host. La futura cancelación debe respetar las garantías de [asyncio](https://docs.python.org/3.14/library/asyncio-task.html), sin tragar `CancelledError`.
