# ADR-008 — concurrencia medida, recolección real secuencial

Estado: aceptado e implementado en I5, 2026-09-28.

## Contexto

I4 dejó dos fuentes independientes, pero ambas publican en una sola base SQLite bajo un bloqueo de proceso. El [roadmap](../ROADMAP.md) propone estudiar `asyncio`, cancelación y backpressure antes de comprometer el recolector real con un modelo concurrente.

## Decisión

I5 agrega `lab-concurrency`, un experimento **sin sockets externos ni SQLite**. Usa un `httpx.AsyncClient` con transporte sintético que espera cooperativamente. Compara dos feeds secuenciales y concurrentes bajo la misma latencia y trabajo de escritura simulado. La variante concurrente usa `asyncio.TaskGroup`, semáforo global de dos requests, candado de una por host, `asyncio.Queue(maxsize=1)` y un único consumidor que representa al escritor. Un tercer escenario cancela una fuente durante la espera; la otra concluye, la cancelación se propaga y el cliente/transport se cierran.

Cinco repeticiones con 200 ms de espera por request, ocho registros por feed y 10 ms de escritura ficticia por registro dieron medianas de **0,6685 s secuencial** y **0,4524 s concurrente**, razón **1,48×** en esta máquina. Solo demuestra el solapamiento de esperas simuladas. No mide el servidor, TLS, parsing ni SQLite reales; tampoco prueba que dos descargas reales deban lanzarse juntas.

La adquisición real sigue con `collect` y el bloqueo único por base. `collect-all` invoca secuencialmente los dos casos de uso existentes y conserva cuotas, runs, transacciones y diagnósticos de cada fuente. Continúa con la segunda fuente cuando la primera devuelve un estado fallido o diferido. `plan` lee fuente, cooldown y ventanas de intentos para estimar cuándo iniciar manualmente; `collect` vuelve a validar bajo bloqueo. No instala un servicio ni una tarea programada. No hay evidencia de un beneficio operativo suficiente para reemplazar el pipeline real y complicar su publicación.

## Alternativas y consecuencias

`asyncio.to_thread(collect)` dos veces mantendría el I/O bloqueante y competiría por el bloqueo de la misma base; no es una conversión real a cliente asíncrono ni mejora demostrable. Reescribir la adquisición para `AsyncClient` más un coordinador de reserva de cuota y un escritor único exige una frontera transaccional nueva. Un scheduler local en Windows necesita resolver sueño/reinicio, horario, ejecución superpuesta y política de avisos. Esas decisiones se dejan para una necesidad operativa concreta.

El laboratorio separa los límites de concurrencia de las cuotas durables: **no consume ni simula como disponibles oportunidades reales**. En producción, `collect-all` no lanza requests simultáneas. `plan` es orientativo; no reserva un turno. Ninguna operación fuerza una fuente detenida.

## Validación y condición para reabrir

Tests verifican máximo dos requests globales, una por host, cola de capacidad uno, una sola escritura sintética, cancelación de una fuente y del padre, cierre del transporte, plan de cooldown/cuota/fuente detenida y continuidad de `collect-all` tras fallo. [VALIDATION](../../VALIDATION.md) registra la medición. Reabrir si varias fuentes elegibles en la misma ventana vuelven relevante el tiempo de adquisición, si se añaden páginas suficientes para justificar concurrencia o si se pide explícitamente automatizar la ejecución. Preservar reserva durable previa a red y publicación atómica por run.

Referencias: [TaskGroup y cancelación](https://docs.python.org/3.14/library/asyncio-task.html), [cola acotada](https://docs.python.org/3.14/library/asyncio-queue.html), [HTTPX AsyncClient](https://www.python-httpx.org/async/).
