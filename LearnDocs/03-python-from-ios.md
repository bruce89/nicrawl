# Python desde experiencia en iOS e ingeniería

Las analogías orientan; no son equivalencias exactas de lenguaje, runtime o garantías.

| Punto conocido | En Python/nicrawl | Diferencia que importa |
| --- | --- | --- |
| Target/package y dependencias | Paquete, entorno y pyproject | El intérprete y el entorno deben ser los correctos al ejecutar |
| Struct/DTO | dataclass o modelo Pydantic | Una dataclass no valida automáticamente tipos de runtime |
| Optional | `T \| None` | El type hint no prohíbe asignaciones inválidas al ejecutar |
| Protocol | `typing.Protocol` | Tipado estructural; comprobaciones de runtime son limitadas y opt-in |
| Inyección por initializer | Constructor/parámetros | Normalmente basta composición manual |
| URLSession | HTTPX Client | Reutilización y cierre explícitos del cliente |
| Core Data/SQLite | sqlite3 y SQL | Identidad, esquema y transacciones se diseñan explícitamente |
| Structured concurrency | `asyncio.TaskGroup` | Loop cooperativo; I/O síncrono lo puede bloquear |
| `defer` y gestión de recursos | `with`, `try/finally` | Context managers expresan apertura/cierre y protocolos de recursos |
| ViewModel y estado de pantalla | Caso de uso y RunResult | El estado importante sobrevive a procesos distintos en la base |

Las anotaciones y protocolos se describen en [typing](https://docs.python.org/3.14/library/typing.html); los grupos de tareas y cancelación en [asyncio](https://docs.python.org/3.14/library/asyncio-task.html).

## Tipos: tres preguntas distintas

**¿Qué espera el código?** Lo expresa una anotación. **¿Puede el analizador detectar un uso incoherente?** Lo revisa un checker como mypy. **¿Qué llegó realmente por red?** Lo valida código de runtime, por ejemplo Pydantic en una frontera externa. Ninguna de las tres tareas sustituye completamente a las otras.

Pydantic puede convertir valores según configuración; eso exige decidir cuándo coercionar y cuándo rechazar. En nicrawl se especifica campo por campo: un ID numérico externo se convierte deliberadamente a string; un salario ambiguo no se convierte a float por conveniencia. [Modelos Pydantic](https://pydantic.dev/docs/validation/latest/concepts/models/).

## Mutabilidad y aliasing

Dos variables pueden referirse a la misma lista. Copiar una dataclass no garantiza duplicar sus colecciones internas. `frozen=True` impide reasignar atributos mediante el mecanismo normal de dataclass, pero no vuelve inmutable todo el grafo de objetos. Preferir colecciones inmutables cuando se publica un resultado que otras capas no deben modificar.

Ejercicio futuro: construir un JobDraft con tags y compartirlo entre normalizador y exporter. Intentar modificar tags desde la presentación; decidir si la representación permite un estado que el diseño quería prohibir.

## Recursos y errores

Abrir cliente HTTP, archivo o conexión implica decidir quién los cierra. Un context manager vuelve visible esa vida útil. No confiar en que “cuando salga de scope ya se liberará todo” tenga la misma semántica que otra plataforma.

Capturar excepciones donde se puede tomar una decisión útil. El parser reporta formato; el transporte reporta red; la CLI traduce el resultado a un mensaje y código. `except Exception: return []` convierte un bug en una colección vacía aparentemente correcta.

## Iteración y memoria

Un iterable describe algo recorrible; un iterador mantiene posición y puede agotarse. Un generador puede producir registros de a uno. Eso reduce materialización, pero no elimina límites de memoria si después se convierte todo a lista.

nicrawl propone lotes pequeños acotados y publicación atómica. No necesita streaming distribuido. Si crece el volumen, revisar adquisición y staging sin romper las reglas de cobertura: guardar parcialmente no autoriza concluir ausencias.

## Async y paralelismo

Una coroutine avanza cuando recibe ejecución y cede en operaciones adecuadas. `async def` que llama un cliente síncrono sigue bloqueando. Concurrencia de I/O y paralelismo de CPU son decisiones diferentes. El número de tareas debe corresponder a un presupuesto, no a la cantidad de enlaces hallados.

Ejercicio I5: dos fuentes simuladas esperan por red; comparar una corrida secuencial con dos tareas, conservando una sola request por host. Cancelar en medio y observar el estado de la transacción y el cierre de recursos.

## Arquitectura familiar, foco distinto

El principio de separar responsabilidades sigue vigente. Lo que cambia es el centro de atención: el pipeline necesita identidad, procedencia y consistencia entre ejecuciones. No trasladar mecánicamente una clase por pantalla a una clase por función de parsing. Una función pura corta puede ser la mejor unidad de diseño.
