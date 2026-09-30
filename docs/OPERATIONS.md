# Operación y fiabilidad propuestas

I2 implementa la política de Remotive/API descrita aquí. I3 implementa también CSV y escritura segura a archivos. I4 implementa un laboratorio HTML externo acotado; I5 agrega plan local y collect-all manual secuencial, más experimento asyncio sin red; crawling de empleos HTML, scheduler y retención automática siguen como diseño futuro. No hay nicrawl.toml ni overrides de política en CLI. Las cifras son límites propios, no promesas del proveedor.

## Presupuesto de red

| Parámetro | Default del proyecto |
| --- | --- |
| Ejecución | Manual; un proceso recolector por base |
| Frecuencia Remotive | Una oportunidad cada 12 h; máximo cuatro intentos HTTP en 24 h y dos en 60 s |
| Paralelismo | Una request en vuelo |
| Reintentos | Como máximo uno adicional por request elegible; siempre consume presupuesto |
| Timeouts HTTPX | Connect 5 s, read 15 s, write 5 s, pool 5 s |
| Presupuesto total de fuente | 120 s, incluidas esperas y procesamiento; verificar antes de cada nueva operación |
| Tamaño | 10 MiB descomprimidos por documento; 25 MiB por lote |
| Registros | Hasta 10.000 candidatos por lote |
| HTML futuro | Máximo 10 páginas, profundidad 1 y al menos 2 s entre inicios de requests al mismo host, salvo regla más restrictiva |

HTTPX distingue timeout de conexión, lectura, escritura y pool; un timeout de lectura no equivale por sí solo a deadline total. [Documentación de timeouts](https://www.python-httpx.org/advanced/timeouts/). El deadline de nicrawl limita nuevas operaciones y sus timeouts al tiempo restante; las pruebas deberán medir el tiempo total y cerrar respuestas/clientes al cancelar. Una extracción síncrona no interrumpible puede tardar hasta finalizar su fase acotada por tamaño; no se promete interrupción instantánea.

El contador de intentos se guarda antes de cada envío, incluso si la respuesta no llega. Reiniciar la CLI no reinicia cuotas. Remotive y Greenhouse/GitLab tienen estados y contadores separados **dentro de la misma base**. Usar otra base o copia no comparte el presupuesto; mantener una única base activa para ambas fuentes reales. No hay `--force` para saltarlas. Dos copias del proyecto no comparten automáticamente ese contador: coordinar manualmente su uso hasta tener una política compartida. El laboratorio HTML es una muestra manual independiente, con robots y máximo dos páginas; no usa el contador de ofertas ni persiste filas.

## Reacciones a respuestas y errores

| Situación | Comportamiento |
| --- | --- |
| Timeout, conexión fallida, 502/503/504 | Un reintento si quedan cuota y deadline; espera 2 s más jitter 0–1 s |
| 429 | Guardar cooldown, terminar como `deferred`; sin reintento dentro del run |
| `Retry-After` válido | Respetar segundos o fecha HTTP y elegir la espera más restrictiva |
| 429 sin `Retry-After` válido | Cooldown de 24 h propuesto, visible en estado |
| 503 con `Retry-After` | Si no cabe en el deadline, guardar cooldown y diferir en lugar de esperar bloqueado |
| 401, 403, desafío o CAPTCHA | Detener fuente para revisión; no reintentar ni cambiar identidad para evadir |
| 404 del endpoint | Fallo de configuración/fuente; no interpretar como cero empleos |
| 200 con HTML donde se esperaba JSON | Fallo de formato; no tratarlo como éxito |
| Documento demasiado grande o tope de páginas | Fallo con cobertura incompleta; conservar colección anterior |
| Registros aislados inválidos | Publicar válidos como `partial`; rechazos contados y explicados |
| Envoltura inválida o todos los registros inválidos | `failed`; no publicar colección vacía |

La interpretación de `Retry-After`, estados y representaciones condicionales se apoya en [HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html). Los valores de espera y las decisiones de detener son propios de nicrawl.

No se implementa caché HTTP condicional en MVP. Si se añade después, un 304 solo reutiliza una instantánea guardada del mismo ámbito y con validadores coherentes. Sin instantánea no significa “lista vacía”. No hay reintentos simultáneos en cliente, adaptador y caso de uso: la política pertenece a una sola capa de adquisición.

## HTML, robots y descubrimiento

`robots.txt` comunica reglas de rastreo; no es autenticación ni licencia de reutilización. El estándar está en [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html). Para HTML externo nicrawl propone revisar condiciones de uso y aplicar el grupo de user-agent correspondiente antes de recolectar. Es una política del proyecto, no un dictamen jurídico.

En `lab-html`, robots se consulta antes de cada ejecución; 200 se interpreta con `urllib.robotparser`, y solo `/pages/forms/` del sandbox es destino posible. La política conservadora general para futuros sitios es: robots 200 se interpreta; 404/410 se registra como ausencia de reglas sin sustituir la revisión de uso; 401/403 o fallo de red/5xx suspenden esa fuente. Caché máxima de 24 h; redirects limitados y revisados. No implementar el protocolo a medias con búsquedas de texto. `crawl-delay`, si se decide soportar, se trata como extensión adicional y nunca como parte universal de RFC 9309.

URLs de seeds provienen de configuración revisada, no de texto libre de un LLM. Solo HTTPS para adquisición externa en MVP. Los redirects se procesan manualmente, máximo tres y dentro de orígenes aprobados; no seguirlos antes de validar destino. En crawling futuro: resolver relativos, quitar fragmentos, conservar parámetros significativos, llevar conjunto de visitadas y detectar ciclos. Detenerse ante calendario infinito, enlaces fuera de ámbito o paginación repetida.

## Datos y salida

No ejecutar JavaScript ni interpretar instrucciones del texto recolectado. HTML de descripciones se convierte a texto; no se imprime control ANSI externo. Desactivar interpretación de markup en la salida de contenido. Salarios vacíos se muestran como “No informado”.

CSV lleva encabezados y campos escapados; ante prefijos de fórmula `=`, `+`, `-`, `@` o controles iniciales, anteponer apóstrofo en representación para hojas de cálculo. No alterar el dato persistido. JSON conserva el dato semántico. URL, fuente y tiempos siempre acompañan cada exportación.

La configuración no contiene contraseñas en MVP. Si una fuente futura necesita un secreto, usar variables de entorno o almacén adecuado y redactar logs; no versionarlo. No recopilar CV, perfiles personales ni información de postulantes para cumplir el objetivo actual.

## Runs y observabilidad

Estados: `running`, `succeeded`, `partial`, `failed`, `deferred`, `interrupted`. `succeeded` permite cero resultados solo con formato y fin válidos. `deferred` se usa para cuota/cooldown sin datos publicados; `partial` significa datos válidos publicados con rechazos. Un run `running` que sobrevive a un crash se marca interrumpido al recuperar el bloqueo en la próxima ejecución.

I2 guarda el diagnóstico en `runs.metrics` y tablas relacionadas; no emite archivos de log rotados ni purga historial automáticamente. Registrar `run_id`, fuente, ámbito, adaptador/normalizador, timestamps, duración monotónica, HTTP status, intentos, bytes, candidatos, válidos, rechazados, duplicados y cambios. Los contadores cumplen `candidates = valid_unique + rejected_candidates + duplicate_candidates`; conflictos por ID cuentan todos sus candidatos como rechazados. Además `valid_unique = new + updated + unchanged` en runs publicados.

Las métricas ayudan a detectar deriva: caída de candidatos, aumento de rechazos, pérdida de IDs, descripciones vacías o cambio de content-type. Una caída mayor al 80 % frente a la última colección completa genera advertencia; no implica bajas ni borrado. El umbral es hipótesis de producto y se revisa con evidencia.

## Recuperación

Tras fallo: leer el estado del último run; comprobar formato y cuota; reproducir con fixture sintética; corregir el adaptador y sus pruebas; repetir solo cuando el presupuesto lo permita. Si hay corrupción de SQLite, preservar el archivo y restaurar una copia verificada; no recrearlo silenciosamente. Una migración falla en transacción y explica la acción pendiente.

I5 no instala un scheduler ni alertas. `plan` calcula una oportunidad orientativa por fuente y `collect-all` permite una ejecución manual de ambas fuentes; cada `collect` revalida bajo bloqueo. Scheduler y alertas quedan fuera del MVP. Cuando se incorporen, reutilizarán el mismo comando y las mismas cuotas; no habrá un segundo pipeline distinto.
