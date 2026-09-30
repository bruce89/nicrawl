# I7 — recorrer UI, API y casos de uso

La pregunta de este corte es: **¿cómo presentan dos interfaces la misma operación sin duplicar su lógica?** En nicrawl, la CLI y el adaptador HTTP llaman a funciones Python de `queries.py` y `personal.py`. El navegador solo pide datos y muestra el resultado. Si cambia la regla de ranking, se cambia `personal.py`, no el JavaScript.

## Recorrido rápido

En una terminal:

```powershell
Set-Location C:\Bruze\nicrawl
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
& $nicrawl serve
```

Se abre `http://127.0.0.1:8765/`. Explorá una palabra y una fuente, abrí un aviso y revisá su procedencia y fecha observada. En **Priorizar**, escribí por ejemplo `Python` en “Busco” y elegí modalidad remota; observá puntuación y razones. El ranking es una ayuda explicable, no una predicción ni confirmación de elegibilidad. Guardar favorita/descartada/nota modifica tu base local, no el aviso del proveedor. Ctrl+C detiene el servidor.

En una segunda terminal, mientras `serve` corre:

```powershell
$base = 'http://127.0.0.1:8765'
$jobs = Invoke-RestMethod "$base/api/jobs?query=Python&limit=5"
$jobs.total
$jobs.jobs | Select-Object job_key,title

$key = $jobs.jobs[0].job_key
$encoded = [uri]::EscapeDataString($key)
$detail = Invoke-RestMethod "$base/api/jobs/$encoded"
$detail.job.title

$rank = Invoke-RestMethod "$base/api/rank?want=Python&mode=remote&limit=5"
$rank.results[0].score
$rank.results[0].reasons

& $nicrawl list --query Python --limit 5
& $nicrawl show $key
& $nicrawl rank --want Python --mode remote --limit 5
```

`$key` viene de la API: evitás adivinar el identificador. En la ruta HTTP se codifica con `EscapeDataString`; en CLI se pasa tal como sale del JSON. Ejemplo de **formato ficticio**: `greenhouse%3Agitlab:12345` es la clave, y `greenhouse%253Agitlab%3A12345` sería su segmento de URL. El `%3A` de la clave ya forma parte de su identidad; no hay que anteponer `remotive:`.

Para practicar la escritura con un aviso que hayas elegido conscientemente:

```powershell
$body = @{state='favorite'; note='Comprobar requisitos de residencia'} | ConvertTo-Json
Invoke-RestMethod -Method Patch -Uri "$base/api/jobs/$encoded/personal" -ContentType 'application/json' -Body $body
& $nicrawl show $key
```

La última lectura debería mostrar la misma nota. Para deshacerla, usá `@{state='unreviewed'; clear_note=$true}` en el cuerpo del `PATCH`. No hace falta ejecutar esa escritura para entender la arquitectura.

## Seguir una petición en el código

1. `src/nicrawl/ui/app.js` arma el URL a partir del formulario y usa `fetch`.
2. `src/nicrawl/server.py` valida ruta, parámetros y cuerpo; transforma HTTP a llamadas Python.
3. `src/nicrawl/queries.py` o `src/nicrawl/personal.py` ejecuta el caso de uso con SQLite.
4. `server.py` serializa JSON. `app.js` usa `textContent` para datos externos y dibuja los estados de carga/error/vacío.
5. `src/nicrawl/cli.py` llega a las mismas funciones desde otro adaptador.

Abrí las herramientas de desarrollador del navegador (F12), pestaña **Network/Red**. Al filtrar verás `GET /api/jobs?...`; al priorizar, `GET /api/rank?...`; al abrir, `GET /api/jobs/<clave>`; al guardar, `PATCH .../personal`. Compará el cuerpo JSON con `Invoke-RestMethod` y el comando CLI. El navegador no habla con Remotive ni GitLab: estas operaciones son offline sobre la última colección guardada.

## Experimentos pequeños

- Cambiá solo `query` entre la UI, API y CLI. Comprobá `total` y las primeras claves. Si difieren, anotá filtros y `limit` antes de buscar un bug.
- Pedí `/api/rank` sin preferencias: recibirás 400. Identificá dónde se valida y por qué UI evita la petición hasta tener un criterio.
- Usá una clave ficticia en `/api/jobs/...`: 404. Luego repetí con una clave real; distinguí identidad de URL.
- Observá que `serve` termina con Ctrl+C y `list` sigue funcionando: el proceso web es una capa de presentación opcional.

El contrato completo y sus límites están en [API](../docs/API.md); la decisión de arquitectura en [ADR-010](../docs/adr/010-local-ui-api.md). El siguiente corte propuesto es estudiar herramientas de lectura para agentes con evidencia y permisos explícitos, a partir de estos mismos casos de uso. No se implementan en I7.
