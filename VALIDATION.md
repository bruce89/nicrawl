# Validación — I10

## Evidencia técnica I10 (2026-09-30)

Aprobado con “Vamos con I10”. Aplicación **0.10.0**: candidaturas vinculadas a ofertas o referencias manuales, UUID/identidad, estados con historial y revisión optimista. UI/API/CLI comparten servicio. [Contrato](docs/APPLICATIONS.md), [guía](LearnDocs/18-application-tracking.md), [ADR-013](docs/adr/013-application-tracking.md).

**197 pruebas pasan**: 178 anteriores, 18 casos del seguimiento y un caso API. Ruff, formato y mypy estricto pasan. Se probaron entradas/URLs inválidas, clave codificada, duplicados por URL/clave, normalización de referencias LinkedIn sin red, historial de correcciones/reapertura, privacidad frente a agentes, fallo de inserción de evento con rollback de estado, altas simultáneas y conflicto de revisión entre escritores. Base ajena rechazada sin cambios, ausencia de archivos en lecturas y paridad API/CLI comprobadas.

Prueba UI con colección ficticia en work/i10-ui.sqlite3: referencia manual creada, estado submitted registrado con motivo de simulación, historial con dos eventos visible y alta vinculada a oferta desde “Crear seguimiento”. No se abrió ni descargó la URL de LinkedIn usada como ejemplo. Ninguno de estos registros pertenece al almacén real del usuario.

Wheel y sdist construidos offline. Verificados módulos y assets applications.html/applications.js dentro del wheel; instalación no editable en work/i10-clean-env sin extra MCP. Ejecutado desde fuera del repositorio: alta manual, update a interview, historial y reintento con URL utm duplicada. Las lecturas sobre la base real devolvieron cero candidaturas y no crearon el archivo personal. La base de ofertas mantuvo su SHA-256.

No se migró SQLite de ofertas, no se recolectaron datos, no se crearon candidaturas reales y no se enviaron postulaciones. I11 pendiente de aprobación; evaluaciones personales I6/I9 pendientes.

## Evidencia técnica I9 (2026-09-30)

Aprobado con “Bien, vamos con I9”. El usuario precisó Senior Software Engineer, remoto o presencial desde Uruguay. Aplicación **0.9.0**: perfiles compartidos entre CLI/API/UI, filtro adicional por título, muestra consistente y evaluación de etiquetas humanas. [Contrato](docs/SAVED_SEARCHES.md), [ADR-012](docs/adr/012-saved-searches-evaluation.md), [guía práctica](LearnDocs/17-saved-searches-and-relevance.md).

**178 pruebas pasan** (159 anteriores, 18 casos de perfiles/evaluación y un caso API adicional). Ruff y mypy estricto pasan. Se verificaron colisiones/reemplazo, configuración inválida, fallo atómico y bloqueo de escritores, lectura sin crear archivos, paridad CLI/API/agentes del filtro de título, instantánea estable cuando otra operación cambia la base viva, exclusión de notas, hash de muestra, etiquetas duplicadas/ajenas y métricas con pendientes, desconocidos, muestras vacías o menos de k candidatos. La suite usa fixtures y no consulta fuentes externas.

Se creó el perfil local `senior-uy`, con query Software, title_query Engineer, want Senior/Software Engineer y objetivo explícito Uruguay. No se impuso un filtro literal de país o modalidad. Sobre las 219 ofertas existentes: 102 candidatos (98 GitLab, 4 Remotive); unión de top-10 de ambos órdenes: 20 ofertas, todas GitLab. Quedaron `data/i9-senior-uy-v1.json` y `data/i9-senior-uy-v1-labels.json`, con etiquetas pending. La precisión inicial es null, no cero. No se declara utilidad demostrada ni cobertura suficiente de Uruguay. Una captura exploratoria anterior sin filtro de título quedó conservada con el nombre i9-senior-uy-snapshot.json; la guía usa exclusivamente la v1 final.

UI abierta en navegador local: carga de senior-uy, filtros y preferencias visibles, consulta de 102 candidatos, guardado de un perfil temporal y rechazo al repetir el nombre sin reemplazo. El perfil de prueba se retiró después por CLI; senior-uy se conserva. Los controles de guardado se agruparon en una sección plegable para mantener accesibles los filtros. No se modificaron notas ni estados de ofertas.

Wheel y sdist 0.9.0 construidos offline. Wheel instalado sin modo editable en work/i9-clean-env, **sin extra MCP**, ejecutado desde fuera del repositorio: versión, saved run, snapshot, label-template y evaluate completos. La evaluación del wheel con k=3 devolvió seis ofertas en la unión y tres pendientes por orden. SHA-256 de la base SQLite sin cambios. Solo se escribieron perfiles/archivos de evaluación; no hubo migración, recolección ni consumo de cuotas.

I10 pendiente de aprobación. El usuario aún debe etiquetar la muestra; nuevos boards se seleccionarán según cobertura y motivos observados, sin interpretar la ausencia de datos como elegibilidad.

## Evidencia técnica I8 (2026-09-30)

El usuario aprobó I8 con “Bien, vamos con I8”. Aplicación **0.8.0**: tres herramientas MCP de lectura (`search_jobs`, `get_job`, `rank_jobs`), SDK opcional y demo con cliente/subproceso real sin modelo ni API key. [Contrato](docs/AGENT_TOOLS.md), [ADR-011](docs/adr/011-agent-tools-mcp.md) y [guía práctica](LearnDocs/16-agent-tools.md).

**159 pruebas pasan**: 143 previas y 16 casos nuevos. Ruff, formato y mypy estricto pasan. Se comprueban paridad CLI, claves codificadas, campos desconocidos y tipos inválidos, exclusión de notas y futuros campos internos, Unicode, recortes explícitos, presupuesto de llamadas y base intacta. Los tests de MCP cubren descubrimiento, esquemas, errores y transporte stdio real. Se usan bases sintéticas y no se consulta a proveedores externos.

La primera ejecución completa detectó un TCP reset intermitente en Windows al rechazar un PATCH de I7 con cuerpo pendiente. El servidor ahora consume el cuerpo dentro del límite de 4096 bytes y con timeout antes de rechazar cabeceras. La suite completa pasó después de la corrección; además se reforzó y volvió a pasar la prueba I7 repitiendo diez rechazos con cuerpo y verificando que no modifican el estado personal.

`agent-demo` devolvió dos ofertas Python sintéticas, descubrió exactamente tres herramientas y no exportó el marcador de nota privada. `agent-demo --local` encontró **41 candidatos Python**; se compararon las primeras cinco claves de lista/ranking y sus puntajes con CLI, sin diferencias. SHA-256 de `data/nicrawl.sqlite3` idéntico antes/después. No hubo migración, colección ni consumo de cuotas. Las llamadas de la demo son predeterminadas; esto no evalúa razonamiento de un modelo ni relevancia personal.

Wheel y sdist 0.8.0 construidos offline. Wheel verificado con módulos MCP y los tres assets de UI. Instalación sin modo editable en `work/i8-clean-env`, ejecutada desde fuera del repositorio: CLI base y lista funcionan sin MCP; `agent-demo` indica cómo instalar el extra y sale con código 1. Tras instalar `[agents]`, la demo stdio completa funciona. La instalación de dependencias utilizó TLS del sistema; el runtime de demo es local.

I9+ permanece pendiente de aprobación. La evaluación manual `rank` vs `list` sigue pendiente. No se registró el servidor en un cliente personal, ni se enviaron datos a un modelo, ni se publicaron candidaturas. Las evidencias anteriores se conservan como historial de cada corte.

## Evidencia técnica I7 (2026-09-28)

El usuario aprobó I7 con “Genial, entonces arrancamos I7?”. La aplicación 0.7.0 agrega `serve`, UI y API HTTP en loopback; [ADR-010](docs/adr/010-local-ui-api.md) documenta la frontera. **143 pruebas pasan** (139 previas y cuatro nuevas de API); Ruff, formato y mypy estricto pasan. Las pruebas comparan JSON de lista y ranking con CLI, verifican que `PATCH` afecte solo estado personal y que CLI lo lea, y cubren activos, errores de entrada, Host, Origin y CSP. No se realizaron nuevas colecciones ni se consumieron cuotas de las fuentes.

Se abrió la UI sobre la base real: 219 avisos, lista y detalle visible con origen y revisión personal. La verificación de escritura se hizo solo en una base temporal. El wheel y sdist 0.7.0 se construyeron offline y el wheel contiene `index.html`, `app.js` y `style.css`. Instalado **sin modo editable** en `work/i7-clean-env`, ejecutado desde un directorio externo, respondió UI, búsqueda y ranking sobre la base real sin alterarla (SHA-256 igual antes/después). El primer intento de instalar dependencias totalmente offline falló por falta de `pydantic-core` en caché; se completó con TLS del sistema y no afectó la prueba de runtime offline.

La entrega I7 tiene **88 archivos** de código y documentación y **200 enlaces locales** comprobados; el ZIP se verificó miembro por miembro. Excluye bases, entornos y archivos de trabajo. Quedan pendientes la evaluación personal de ranking y la discusión de I8+ para agentes; no se implementaron herramientas para agentes.

## Historial I6

Fecha: **2026-09-28** · Aplicación **0.6.0** · Windows / Python 3.14.6.

El usuario aprobó I6 con “Bien, seguimos con I6”. `rank` y `mark` implementados; [ADR-009](docs/adr/009-personal-state-ranking.md) registra la separación de datos personales y de proveedor. I7+ pendiente de aprobación. La evaluación personal de relevancia sigue pendiente.

## Evidencia técnica I6

**139 pruebas pasan**: 129 anteriores y diez nuevas. Ruff, formato y mypy estricto pasan; la suite no hace peticiones externas. Los casos I6 cubren puntos y razones, modalidad desconocida, reglas desactivadas, filtros, descarte reversible, notas conservadas tras publicación, errores de entrada, CLI, migración 1→2 idempotente y rollback de una migración fallida. Se verificó que `mark` sobre una base inexistente no crea un archivo vacío.

Antes de migrar `data/nicrawl.sqlite3` se creó `data/nicrawl-pre-i6.sqlite3` con la API de respaldo de SQLite. La base anterior tiene esquema 1 y la actual esquema 2; ambas contienen **219 ofertas**, idénticos `job_key` y `payload`, y `PRAGMA integrity_check = ok`. La tabla personal comenzó vacía. El script de respaldo completó estas comprobaciones, aunque su último mensaje de consola falló por un carácter Unicode no soportado en la codificación de esa terminal; una comprobación independiente posterior confirmó todos los invariantes. No se descargaron ofertas nuevas ni se consumieron cuotas.

`rank --want Python --mode remote` se ejecutó contra la base real en modo de lectura, con 219 candidatos y razones visibles. Es una demostración funcional, **no una medición de relevancia**: todavía no hay etiquetas personales ni precisión@10 calculada. La [guía I6](LearnDocs/13-ranking-and-personal-state.md) propone cómo evaluar falsos positivos y omisiones antes de modificar pesos o considerar AI.

Wheel y sdist 0.6.0 se construyeron offline. El wheel instalado sin modo editable en un entorno limpio ejecutó `--version`, `list` y `rank` contra la base real en solo lectura; después migró una **copia** del respaldo de esquema 1 mediante `mark`, recuperó la nota con `show` y volvió a consultar `rank`. La copia terminó en esquema 2 con 219 ofertas; el SHA-256 de la base real no cambió y no hubo solicitudes de red.

La entrega I6 actualizada incluye 79 archivos de código y documentación, con 184 enlaces locales comprobados. El ZIP se abrió y verificó archivo por archivo contra el proyecto; excluye bases reales, entornos y archivos de trabajo.

Corrección del recorrido I6: un `job_key` de GitLab ya contiene la fuente codificada (`greenhouse%3Agitlab:8592950002`). Ante un prefijo extra como `remotive:greenhouse%3Agitlab:8592950002`, `show` y `mark` sugieren ahora la clave existente con el mismo ID, sin aplicar automáticamente una marca a otra oferta. La documentación usa `<JOB_KEY_COMPLETO>` y muestra cómo extraerlo de `list` en PowerShell. Se verificó que la oferta “Engineering Manager, Data Foundations” quedó `favorite` con la nota solicitada; una nueva invocación con la clave errónea mostró la sugerencia.

Seguimiento del recorrido del usuario: el comando `mark --state unreviewed --clear-note` posterior retiró el favorito y la nota, como estaba diseñado. El `show` de esa oferta reveló otro defecto de presentación: `source_status` apuntaba a Remotive aunque `job.source_id` era `greenhouse:gitlab`. Ahora toma la fuente de la oferta; la prueba con dos fuentes y la consulta real confirman `greenhouse:gitlab`. La [guía rápida](LearnDocs/14-i6-evaluation-quick-guide.md) aclara cómo comparar `list` y `rank`, registrar etiquetas y resolver dudas. Los comandos PowerShell de la guía devolvieron 41 candidatos para `--query Python` en ambos órdenes, sin red ni escrituras.

Seguimiento documental: la guía rápida enlaza cada pregunta con un comando, muestra claves ficticias solo como formato y extrae claves reales de JSON. Se probó en PowerShell la unión de los primeros diez de ambos órdenes: 18 claves distintas en la instantánea actual. Un ejemplo opcional de `mark` está identificado como escritura personal y separado de la etiqueta manual. El roadmap registra UI y API locales desacopladas como dirección de I7, conservando CLI/API operables desde terminal; herramientas acotadas para agentes quedan como extensión posterior, todavía sin implementar ni aprobar.

Una ejecución de la suite detectó una afirmación temporal frágil de I5: bajo carga, una sola corrida concurrente tardó más que la secuencial. La prueba ahora verifica sus resultados y límites deterministas; la comparación de velocidad sigue documentada como experimento de cinco repeticiones, sin garantía por corrida individual.

## Historial I5

# Validación — I5

Fecha: **2026-09-28** · Aplicación **0.5.0** · Windows / Python 3.14.6.

El usuario aprobó I5 con “Perfecto, vamos con I5”. `plan`, `collect-all` manual secuencial y laboratorio asyncio sintético implementados. I6+ pendiente de aprobación. Ejercicios personales pendientes.

## Evidencia automatizada

**129 pruebas pasan**: 120 anteriores y nueve nuevas. La suite impide conexiones externas; Windows asyncio necesita una conexión de loopback para su event loop y el fixture permite solo ese caso local. Ruff, formato y mypy estricto pasan. Nuevos casos: dos hosts y un escritor con cola capacidad uno; dos feeds del mismo host serializados; límite global de dos; cancelación de una fuente y del padre; transporte cerrado; límites de parámetros; plan sin base/mutación, cooldown, fuente deshabilitada y cuatro intentos en 24 h; collect-all continúa tras un estado fallido.

## Medición sintética

Cinco rondas en Windows/Python 3.14.6 con dos feeds, 200 ms de espera cooperativa por request, ocho registros por feed y 10 ms de escritura ficticia por registro. Segundos secuenciales: 0,6685 / 0,6689 / 0,6501 / 0,6670 / 0,6694. Concurrentes: 0,4508 / 0,4643 / 0,4641 / 0,4513 / 0,4524. Medianas: **0,6685 s** y **0,4524 s**; razón **1,48×**. La cola nunca superó su capacidad y el pico por host fue uno. En cancelación, Remotive produjo cero filas y GitLab completó ocho; el transporte cerró. Cero solicitudes reales y cero escrituras SQLite.

El experimento mide esperas sintéticas y un consumidor simulado. No incluye TLS, descarga real, parsing ni commits de SQLite. [ADR-008](docs/adr/008-concurrency-experiment.md) conserva la publicación real secuencial.

## Plan de la base real

`plan` leyó la misma base de 219 ofertas sin alterarla: Remotive figuraba ready y GitLab deferred por su cooldown al 2026-09-28 12:56:42 UTC. Esta es una instantánea, no reserva una ejecución futura. `collect-all` se validó con resultados falsos de ambas fuentes; no se invocó contra Internet para medir concurrencia ni para gastar otra oportunidad.

Wheel y sdist 0.5.0 se construyeron offline. El wheel instalado sin modo editable en un entorno limpio ejecutó `--version`, `plan`, `list` y `lab-concurrency` desde otro directorio; la base conservó su SHA-256 y no se hicieron peticiones externas. La entrega I5 contiene 74 archivos fuente/documentación y 150 enlaces locales comprobados; el ZIP se abrió y verificó archivo por archivo contra el proyecto.

## Límites

No hay tarea recurrente instalada. `collect-all` usa los dos caminos existentes secuencialmente y puede descargar si se ejecuta cuando la fuente es elegible. `plan` no sustituye `gate`/`reserve_attempt`: esas verificaciones corren bajo bloqueo al recolectar. La política sigue guardada por fuente y por base, no entre copias. La validación I4 y la primera consulta real de cada proveedor continúan en el historial.

## Historial I4

# Validación — I4

Fecha: **2026-09-28** · Aplicación **0.4.0** · Windows / Python 3.14.6.

El usuario aprobó I4 con “Vamos con I4”. Segunda fuente GitLab/Greenhouse y laboratorio HTML externo acotado implementados. I5+ pendiente. Los ejercicios personales siguen por realizar.

## Evidencia automática

**120 pruebas pasan**: 102 previas más 18 de I4. Sin peticiones reales en la suite. Ruff, formato y mypy estricto pasan. Nuevos escenarios: envoltura incompleta o >10.000 registros; DTO inválido; ID duplicado exacto/conflictivo; fechas y HTML escapado; dos fuentes con cuotas independientes y búsqueda unificada; robots que permite/deniega, 301/403/429/500, límite de bytes, DOM roto, duplicado entre páginas, paginación fuera del host. Esquema SQLite continúa en versión 1.

## Segunda fuente real

[Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html), board público [GitLab](https://job-boards.greenhouse.io/gitlab), endpoint `GET /v1/boards/gitlab/jobs?content=true`. Una petición el 2026-09-28: HTTP 200, 3.157.960 bytes descomprimidos, meta.total 200, 200 válidos, 0 rechazados, 0 duplicados, 200 altas, 2,412 s para adquisición/validación/publicación. Run `802bc090-8d7e-4670-8d70-453f3b688a9e`; status succeeded, coverage complete. No se guardó el cuerpo HTTP entero. El contrato quedó validado con datos reales y la descripción se convirtió a texto.

La base de trabajo contiene ahora **219 ofertas**: Remotive 19 y Greenhouse/GitLab 200. attempts conserva un intento para cada fuente. `PRAGMA integrity_check = ok`; `foreign_key_check` no informó problemas. Las ofertas de ambos orígenes se consultan con `list --source all` y se distinguen por identidad. La fuente GitLab tiene su propia oportunidad siguiente en source_state; no se consulta de nuevo en esta validación.

## Laboratorio HTML real

[Scrape This Site](https://www.scrapethissite.com/pages/) declara su sitio como sandbox de aprendizaje. `robots.txt` respondió 200 con exclusiones `/lessons/` y `/faq/`; la ruta `/pages/forms/` quedó permitida. `lab-html --pages 2` leyó dos páginas de [Hockey Teams](https://www.scrapethissite.com/pages/forms/): **50 filas**, indicador has_more true y persisted false. Después se ajustó el espaciado para esperar también dos segundos entre robots y la primera página; el test de reloj comprueba ambas esperas. El laboratorio no escribe en jobs ni pretende descargar las páginas siguientes.

## Límites

Wheel y sdist 0.4.0 construidos offline. La instalación limpia del wheel, no editable, ejecutó `list` por ambas fuentes y unificado, `status`, `changes`, `show` y el laboratorio con transporte falso desde otro directorio: 219/19/200 ofertas, cero solicitudes reales y SHA-256 de la base sin cambios. El lock registró 32 paquetes. El ajuste final de espaciado HTML se verificó con reloj falso en la suite.

Solo se habilita el board GitLab, no un token arbitrario ni crawling laboral HTML. Las cuotas se conservan por fuente dentro de una base, no entre copias. La práctica HTML usa datos de hockey y verifica acceso en cada ejecución; un cambio del sitio puede hacerla fallar. La ausencia de una oferta en una colección posterior no prueba cierre. Remoto no implica elegibilidad desde Argentina.

La evidencia previa de I3, incluida instalación limpia y benchmark, permanece en el historial de esta entrega; los documentos de aprendizaje I1–I3 conservan el contexto de cada corte.

## Historial I3

# Validación — I3

Fecha: **2026-09-26** · Aplicación **0.3.0** · Windows / Python 3.14.6.

El usuario aprobó I3 con “Seguimos con I3”. MVP técnico I0–I3 completado; I4+ pendiente. Los ejercicios personales siguen pendientes y no se confunden con validación técnica.

## Evidencia automatizada

**102 casos pasan**: los 82 de I2 y 20 de consultas/exportación. La suite bloquea sockets; ninguna prueba depende de Internet. Ruff, formato y mypy estricto (14 archivos de fuente) pasan.

| Escenarios | Evidencia |
| --- | --- |
| Q01–Q05 | Paquete y cinco escenarios HTML conservados |
| Q06–Q15, Q20–Q22 API | Contrato, idempotencia, cambios, errores HTTP, rollback, ausencia, cuotas, crash y límites conservados |
| Q16 | AND, Unicode casefold, acentos, subcadena literal, orden, detalle, frescura y lectura sin mutaciones/red |
| Q17 | Última publicación parcial tras fallo posterior, consulta histórica y corrida sin novedades |
| Q18 | CSV/JSON: comas, comillas, saltos, Unicode, fórmulas/controles, atribución, selección y límite |
| Q19 | Destino existente, fallo tras escritura parcial, fallo al reemplazar y creación concurrente; archivo anterior intacto y temporales retirados |

También se prueba protección de la propia base y un alias hardlink, CSV vacío, exportación de todos los resultados y lectura de base inexistente sin crearla. Q21 de HTML paginado externo sigue fuera del MVP/API, pendiente de I4.

## Rendimiento local

Base sintética: 10.000 ofertas, descripción de 1.280 caracteres por oferta; 42.815.488 bytes de SQLite incluyendo historial. Windows 11 build 22621, Intel64 Family 6 Model 158 Stepping 9, Python 3.14.6.

Cinco consultas con query PYTHON, company ñandú, source remotive, location world, limit 20: 0,356 / 0,357 / 0,345 / 0,357 / 0,356 s; mediana 0,356 s, máximo 0,357 s. Se mide apertura, esquema, estado, orden, decodificación y filtros; se excluyen generación de datos, arranque CLI y renderizado. No es garantía para otras máquinas, descripciones mayores ni caché fría del sistema operativo. La meta de consulta menor a un segundo se cumple para esta carga.

## Límites de la entrega

Wheel y sdist 0.3.0 construidos offline. Instalación limpia desde lock y posterior instalación del wheel sin editable: --version, list, show, changes y ambas exportaciones se ejecutaron desde otra carpeta sobre las 19 ofertas reales. JSON/CSV conservaron selección e identidad; latest ignoró la corrida deferred posterior. El SHA-256 de la base quedó idéntico y hubo cero peticiones de red. Lock verificado: 32 paquetes. El test de destino existente también pasó desde el ejecutable instalado.

Consultas por escaneo O(n); resultados materializados en memoria. Salida JSON, sin tabla ni paginación navegable. Exportación exclusiva requiere hardlinks; validada en el volumen local de Windows. No se afirma durabilidad ante corte eléctrico durante actualización del directorio. CSV incluye datos por oferta; el diagnóstico completo de runs está en JSON/status. No se publica ni redistribuye la colección.

La primera adquisición real es la de I2 que se conserva abajo. I3 se verifica sobre datos locales sin nuevas peticiones. Guía nueva: [I3](LearnDocs/10-local-search-export.md).

## Primera recolección real

Fuente: [Remotive](https://remotive.com/remote-jobs/api). Endpoint configurado: categoría software-dev, sin limit ni búsqueda remota. Se revisaron documentación y condiciones antes de consultar.

| Dato | Observación |
| --- | --- |
| Run publicado | `05603cf2-6e17-4ce9-b53a-89bc11f67154` |
| Inicio | 2026-09-25 21:11:08 UTC |
| Resultado | succeeded; coverage complete para ese ámbito |
| HTTP | 200; **un intento** |
| Bytes descomprimidos recibidos | 209.696 |
| Candidatos / válidos / rechazados | **19 / 19 / 0** |
| Altas / actualizados / sin cambios | 19 / 0 / 0 |
| Tiempo de adquisición y validación medido | 1,082 s; no es una garantía de rendimiento |
| Base local | `C:\Bruze\nicrawl\data\nicrawl.sqlite3` |

Luego se cerró y reabrió la aplicación. status mostró las 19 ofertas persistidas. Una segunda invocación de collect produjo `deferred`, código 4, **cero intentos nuevos**. El total durable permaneció en **un intento**. La próxima oportunidad quedó en 2026-09-26 09:11:08 UTC; consultar la base para estado actualizado.

La inspección read-only encontró 19 ofertas, 19 altas en changes y 19 observaciones en run_items. `PRAGMA integrity_check` devolvió `ok`; `foreign_key_check` no encontró errores. No se guardó el cuerpo HTTP completo: las descripciones persistidas son texto normalizado, con URL individual y atribución de fuente.

## Distribución y límites

Wheel y sdist se construyen con uv_build. La comprobación de instalación usa un entorno nuevo desde lock/caché y el wheel sin editable; ejercita demo y una recolección sintética con transporte falso, nunca una segunda descarga real. Ver comandos en [IMPLEMENTATION](docs/IMPLEMENTATION.md).

Solo se validó Windows. La cuota se guarda por base, no en un coordinador global entre copias. Mantener una única base activa para el uso real; cambiar de base no debe usarse para esquivar límites. No se implementaron scheduler, desbloqueo automático, purga de historial ni archivos de logs rotados; el diagnóstico durable vive en runs/attempts/source_state.

El deadline se comprueba entre operaciones y antes de publicar; una fase síncrona acotada no tiene interrupción instantánea garantizada. No se afirma que ausencia pruebe cierre ni que remoto signifique elegibilidad desde Argentina.

La entrega excluye datos reales, entornos, caches y work. No se modificó ForeKast, no se creó remoto Git y no se publicó un servicio. Los ejercicios personales siguen pendientes: [guía I2](LearnDocs/09-real-ingestion-sqlite.md).
