# API HTTP local — I7

`nicrawl serve` abre una interfaz en `http://127.0.0.1:8765/`. El servidor escucha solo en loopback, usa la base indicada por `--db` y se detiene con Ctrl+C. No recolecta ofertas ni hace peticiones a los proveedores. La CLI sigue disponible mientras el servidor corre.

```powershell
Set-Location C:\Bruze\nicrawl
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
& $nicrawl serve --no-open
# En otra terminal:
Invoke-RestMethod 'http://127.0.0.1:8765/api/health'
```

Para otra base: `& $nicrawl --db .\data\otra.sqlite3 serve --port 8766 --no-open`. `--db` es global y va antes de `serve`. El puerto se refleja en la URL.

## Contratos

| Método y ruta | Uso | Parámetros |
| --- | --- | --- |
| `GET /api/health` | Estado del proceso y ruta de la base | Ninguno |
| `GET /api/jobs` | Búsqueda offline, como `list` | `query`, `company`, `source`, `location_text`, `limit` |
| `GET /api/jobs/<job_key>` | Detalle, como `show` | Clave completa codificada como **un segmento de URL** |
| `GET /api/rank` | Ranking explicable, como `rank` | Filtros anteriores, `want`/`avoid` repetibles, `mode`, `fields`, `include_dismissed` |
| `PATCH /api/jobs/<job_key>/personal` | Estado y nota, como `mark` | JSON: `state`, `note`, `clear_note` |

`source` acepta vacío (todas), `remotive` o `greenhouse:gitlab`. `limit` predeterminado es 20 y admite 1–200. `rank` requiere al menos `want`, `avoid` o `mode`; `mode` acepta `remote`, `hybrid` u `onsite`. `fields` es una lista separada por comas de `title,tags,description`. `include_dismissed` usa `true` o `false`. Las respuestas de consulta conservan la estructura JSON de CLI. Los errores son `{"error":"…"}` con códigos 400, 403, 404, 409 o 415 según el caso.

`job_key` es un identificador completo, **no** se le agrega un prefijo de fuente. Una clave ficticia `greenhouse%3Agitlab:12345` se transmite en la ruta como `greenhouse%253Agitlab%3A12345`: el `%` interno se codifica otra vez para el URL. Evitá construirla a mano:

```powershell
$base = 'http://127.0.0.1:8765'
$jobs = Invoke-RestMethod "$base/api/jobs?query=Python&limit=5"
$jobKey = $jobs.jobs[0].job_key
$encoded = [uri]::EscapeDataString($jobKey)
$detail = Invoke-RestMethod "$base/api/jobs/$encoded"
$detail.job.title

$rank = Invoke-RestMethod "$base/api/rank?want=Python&mode=remote&limit=5"
$rank.results | Select-Object -First 3

$body = @{state='favorite'; note='Revisar país de contratación'} | ConvertTo-Json
Invoke-RestMethod -Method Patch -Uri "$base/api/jobs/$encoded/personal" -ContentType 'application/json' -Body $body
& $nicrawl show $jobKey # misma anotación, por CLI
```

El último ejemplo **escribe** solo la revisión local. Para revertirla: `@{state='unreviewed'; clear_note=$true} | ConvertTo-Json` en otro `PATCH`. `state` admite `favorite`, `dismissed`, `unreviewed`. `note` se limita a 2.000 caracteres en el caso de uso. El cuerpo HTTP tiene máximo 4 KiB.

La API está pensada para un equipo personal. No hay autenticación multiusuario ni CORS. El servidor comprueba `Host` en toda petición y `Origin` en escrituras, y entrega HTML/JS/CSS con una política de contenido restringida. No debe exponerse a la red local o Internet mediante un proxy. Cualquier adaptación futura para agentes debe diseñar permisos y límites antes de ofrecer escrituras o recolección.
