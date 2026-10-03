# CLI — aplicación 0.10.0

I0–I7 implementados al 2026-09-28. Ejecutar desde C:\Bruze\nicrawl; no requiere uv global. La opción global --db va **antes** del subcomando. Default: data/nicrawl.sqlite3, relativo al directorio actual.

`nicrawl serve [--port 8765] [--open/--no-open]` inicia la [UI y API local](API.md) en `127.0.0.1`. Por defecto abre el navegador; Ctrl+C detiene el servidor. La CLI de consulta, ranking y anotación sigue funcionando en otra terminal.

```powershell
.\.venv\Scripts\nicrawl.exe --help
.\.venv\Scripts\nicrawl.exe --version
.\.venv\Scripts\nicrawl.exe demo --scenario unicode
.\.venv\Scripts\nicrawl.exe status --source remotive
.\.venv\Scripts\nicrawl.exe collect --source remotive
.\.venv\Scripts\nicrawl.exe collect --source greenhouse:gitlab
.\.venv\Scripts\nicrawl.exe status --source greenhouse:gitlab
.\.venv\Scripts\nicrawl.exe lab-html --pages 2
.\.venv\Scripts\nicrawl.exe plan
.\.venv\Scripts\nicrawl.exe lab-concurrency
.\.venv\Scripts\nicrawl.exe rank --want Python --avoid Senior --mode remote --limit 5
.\.venv\Scripts\nicrawl.exe mark '<JOB_KEY_COMPLETO>' --state favorite --note 'Revisar residencia'
# Hace red y usa las cuotas existentes de ambas fuentes:
.\.venv\Scripts\nicrawl.exe collect-all
.\.venv\Scripts\nicrawl.exe list --query python --limit 20
.\.venv\Scripts\nicrawl.exe list --company ejemplo --location-text worldwide
.\.venv\Scripts\nicrawl.exe show remotive:12345
.\.venv\Scripts\nicrawl.exe changes --source remotive --run latest
.\.venv\Scripts\nicrawl.exe export --query python --format json --output .\data\python.json
.\.venv\Scripts\nicrawl.exe export --query python --format csv --output .\data\python.csv
```

El ID es ilustrativo: copiar el `job_key` completo de `list` o `rank`, sin agregarle otro prefijo. GitLab usa una clave como `greenhouse%3Agitlab:8592950002`; `%3A` codifica el `:` de la fuente. La carpeta de destino debe existir. collect, collect-all y lab-html hacen red. `rank` lee localmente y `mark` escribe solo el estado personal en la base. plan y lab-concurrency no descargan ni escriben datos. demo usa fixtures integradas; status, list, show, changes y export leen la base sin red ni creación implícita. Las fuentes de empleo habilitadas son remotive y greenhouse:gitlab. lab-html consulta un sandbox de hockey por separado y no escribe en jobs.

## Filtros, límites y orden

list y export comparten --query, --company, --source y --location-text. Subcadenas literales con Unicode casefold, sin eliminar acentos. query coincide en título, empresa o descripción; los distintos filtros se combinan con AND. Fuente es una identidad exacta; list/export usan `--source all` por defecto, mientras status/collect/changes piden una fuente concreta. % no es un comodín; no se interpreta SQL del usuario.

Orden: first_seen_at descendente, job_key ascendente. list muestra hasta 20 ofertas (máximo 200 con --limit) e informa total. export incluye **todos** los coincidentes por defecto; --limit N aplica un tope positivo. Para exportar exactamente lo listado, repetir filtros y límite.

show JOB_KEY devuelve descripción completa como texto, salario bruto, ubicación declarada y fechas; `source_status` corresponde a la fuente de esa oferta. La publicación puede ser desconocida. stale true significa más de siete días desde la última observación, nunca vacante cerrada. No se deduce elegibilidad desde Argentina.

## Novedades y frescura

changes --run latest elige la última corrida publicada (succeeded o partial), no una fallida/diferida/interrumpida posterior. --run ID consulta otra publicación. --limit tiene default 20 y máximo 200; total siempre se informa. Sin publicación previa, falla con mensaje explícito.

Cada novedad contiene kind (new/updated), fields, before y after. Son instantáneas históricas; no se sustituyen por valores actuales. Una publicación sin cambios tiene total 0. No se generan bajas por ausencia. published_run y source_status.run distinguen publicación e intento más reciente.

## Formatos y escritura

Las consultas emiten JSON por stdout, con controles y Unicode escapados. Un consumidor recupera el texto original; la terminal no recibe secuencias ANSI/bidi externas. Esta versión prioriza un formato reutilizable desde PowerShell; una tabla visual queda como mejora. Errores y resumen de exportación van a stderr.

JSON exportado incluye schema_version 1, generated_at (consulta), exported_at, filters, source_status, total, limit y jobs. Cada oferta incluye fuente, URL y tiempos. CSV lleva encabezados fijos, UTF-8 sin BOM y las mismas ofertas; tags como JSON y null como celda vacía. Para diagnóstico completo de runs, usar status o JSON.

Comas, comillas y saltos se escapan con csv.writer. Prefijos de fórmula y controles iniciales reciben un apóstrofo en CSV; SQLite y JSON conservan el dato. Otra aplicación puede reinterpretar celdas al guardar nuevamente: la protección describe la salida original.

Se escribe un temporal junto al destino, se vacía a disco y se publica completo. Sin --overwrite se rechaza incluso un archivo creado durante la exportación. Con la opción se reemplaza al final. Un fallo no trunca el archivo anterior. Se rechazan base, auxiliares, alias por hardlink de la base y destinos simbólicos. El modo exclusivo requiere soporte de enlaces duros; si falta, falla conservando el destino. Ver [ADR-006](adr/006-local-queries-exports.md).

## Laboratorio de concurrencia

`lab-concurrency --delay-ms 200 --records 8 --write-ms 10` compara secuencial, concurrente y cancelación con dos hosts ficticios. Un `httpx.AsyncClient` usa transporte sintético: cero sockets externos, cero SQLite. Informa tiempos, requests activas (máximo dos globales y una por host), cola (capacidad uno), eventos de backpressure, filas escritas y cierre del transporte. La mejora medida no se atribuye al recolector real. `plan` y el laboratorio son seguros para repetir; `collect-all` puede consumir solicitudes reales.

## Ranking y anotaciones personales

`rank` exige al menos `--want`, `--avoid` o `--mode`. Las opciones `--want` y `--avoid` se repiten; `--fields title,tags,description` activa o desactiva reglas de texto. Puntos: título ±5, tags ±3, descripción ±1; modalidad declarada coincidente +2 y distinta -2; desconocida 0. La salida incluye `score` y `reasons` por aviso, sin descripción completa. Aplica los mismos filtros de `list`; omite descartadas salvo `--include-dismissed`. Las preferencias no se guardan. `mark JOB_KEY --state favorite|dismissed|unreviewed` y `--note TEXTO`/`--clear-note` afectan solo la tabla local `personal_state`. `show` revela el estado y la nota; `list` y `changes` mantienen sus contratos. Una base de esquema 1 requiere copia de seguridad y apertura para escritura con 0.6.0, que migra transaccionalmente a esquema 2. [Guía I6](../LearnDocs/13-ranking-and-personal-state.md).

## Códigos

| Código | Significado |
| --- | --- |
| 0 | Éxito, incluyendo consultas vacías |
| 1 | Error de red/formato/almacenamiento o recurso ausente |
| 2 | Argumentos inválidos |
| 3 | Publicación parcial; demo basic también lo devuelve intencionalmente |
| 4 | Recolección diferida por cuota/cooldown; collect-all devuelve 4 si ninguna falla o es parcial y al menos una se difiere |
| 130 | Interrupción controlada de la recolección |

collect y collect-all mantienen cuotas separadas por fuente en [OPERATIONS](OPERATIONS.md). `collect-all` invoca primero Remotive y luego GitLab en secuencia, aunque el primer estado sea failed/deferred. plan estima ready_at en UTC sin reservar; la recolección revalida bajo bloqueo. lab-html revisa robots.txt cada vez, como máximo dos páginas y espera dos segundos entre requests al mismo host. Leer datos guardados no consume intentos ni reinicia la política.

## I8: MCP y demo

- `nicrawl agent-demo`: crea datos sintéticos temporales y prueba las tres herramientas mediante un subproceso MCP, sin modelo.
- `nicrawl --db data/nicrawl.sqlite3 agent-demo --local`: mismo recorrido sobre una base existente, en lectura.
- `nicrawl --db data/nicrawl.sqlite3 mcp --max-calls 100`: servidor stdio para un cliente MCP; no es una consola interactiva.

Requieren `uv sync --locked --extra agents`. [Contrato y límites](AGENT_TOOLS.md), [guía de comandos](../LearnDocs/16-agent-tools.md).

## I9: perfiles y evaluación

`nicrawl saved` agrupa save/list/show/run/delete/snapshot/label-template/evaluate. `list`, `rank` y `export` admiten además `--title-query`, combinado con el resto de filtros. [Comandos completos](SAVED_SEARCHES.md) y [recorrido con muestra local](../LearnDocs/17-saved-searches-and-relevance.md).

## I10: candidaturas

`nicrawl applications add/list/show/update`: crear desde `--job-key` o `--url`/`--title`/`--company`, listar por estado, consultar historial y registrar avances con `--state`, `--revision`, `--reason`. [Recorrido PowerShell](../LearnDocs/18-application-tracking.md) y [contrato](APPLICATIONS.md). Un estado submitted no envía formularios.
