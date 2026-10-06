# I12b — dos procesos, una clave de envío

Para cuando vuelvas a la PC. Reservá 20–30 minutos; no requiere cuenta de un portal ni
credenciales externas. Vamos a perder una respuesta HTTP y recuperar un recibo sin duplicarlo.

## Terminal 1: receptor

```powershell
Set-Location C:\Bruze\nicrawl
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
& $nicrawl --db data/i12-http.sqlite3 test-receiver
```

Dejá esta terminal abierta. Escucha en `127.0.0.1:8766`, genera un token local y guarda
recibos en `data/i12-http.sqlite3.test-receiver.sqlite3`. No imprime el token. Ctrl+C
detiene el proceso; reiniciarlo con la misma base conserva identidad y recibos.

## Terminal 2: material ficticio

```powershell
Set-Location C:\Bruze\nicrawl
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
$lab = 'data/i12-http.sqlite3'
Set-Content -Encoding utf8 data/i12-http-cv.txt 'Experiencia ficticia en Python y SQLite.'
$application = (& $nicrawl --db $lab applications add --url 'https://example.org/jobs/http-lab' --title 'Engineer de prueba' --company 'Empresa ficticia' | ConvertFrom-Json).application
$profile = & $nicrawl --db $lab profile save --cv-file data/i12-http-cv.txt --label 'Perfil ficticio HTTP' --statement 'Experiencia en Python' --evidence 'Experiencia ficticia en Python y SQLite.' | ConvertFrom-Json
$draft = & $nicrawl --db $lab applications draft create $application.id --profile-version $profile.version --claim-id E01 | ConvertFrom-Json
$p = & $nicrawl --db $lab http-trial prepare $draft.id --version $draft.version | ConvertFrom-Json
$p.payload.preview
$p.destination
$p.receiver_id
```

Preparar congela identidad del receptor, puerto y material. Revisá esos datos. La URL
example.org es una referencia ficticia; no se consulta. Si hay preguntas pendientes,
resolverlas en una nueva versión antes de preparar. Se transmite solo el borrador con
sus citas al receptor propio; no se envía el CV completo.

## Llegó, pero perdimos la respuesta

```powershell
& $nicrawl --db $lab http-trial send $p.id --confirm-sha256 $p.review_sha256 --scenario timeout-after
& $nicrawl --db $lab http-trial show $p.id
& $nicrawl --db $lab http-trial reconcile $p.id
```

Esperado: el cliente deja de esperar tras unos dos segundos y guarda `uncertain`.
El receptor ya guardó el recibo. Reconcile lo consulta y termina en `accepted`.
Repetir send devuelve el mismo receipt_id. La candidatura sigue en `draft`: el ensayo
no es una postulación real ni una aceptación del empleador.

Probá detener el receptor antes de reconcile: sigue uncertain. Reiniciá Terminal 1 y
repetí reconcile; recupera el recibo. No borres archivos para “destrabar” el ensayo.

## Sin recibo todavía: diferencia respecto de I12a

```powershell
$draft2 = & $nicrawl --db $lab applications draft create $application.id --profile-version $profile.version --claim-id E01 | ConvertFrom-Json
$q = & $nicrawl --db $lab http-trial prepare $draft2.id --version $draft2.version | ConvertFrom-Json
$q.payload.preview
& $nicrawl --db $lab http-trial send $q.id --confirm-sha256 $q.review_sha256 --scenario timeout-before
& $nicrawl --db $lab http-trial reconcile $q.id
& $nicrawl --db $lab http-trial retry $q.id --confirm-sha256 $q.review_sha256
```

Reconcile conserva uncertain aun sin recibo: puede haber una solicitud en vuelo. Retry
es explícito y mantiene la clave; la deduplicación del receptor evita un segundo efecto.
El fallo inyectado se aplica una sola vez por clave, por eso retry termina en accepted.
Para practicar rejected, prepará otro borrador y elegí ese escenario al primer send.
No confundas crear un ensayo nuevo con reintentar el anterior.

## Desde Candidaturas y API

Usá una colección existente para `serve`, y en otra terminal iniciá `test-receiver`
con **la misma --db**. El formulario admite “Preparar ensayo HTTP”, revisión, escenario,
consulta y reintento. La UI usa 8766; CLI permite otro puerto con `test-receiver --port 8767`
y `http-trial prepare --port 8767`. El puerto queda guardado en el ensayo.

Las rutas del emisor: POST `/api/http-trials` con draft_id/version, GET `/api/http-trials/<id>`,
POST `/<id>/send` con review_sha256/scenario, POST `/<id>/reconcile` con `{}` y POST
`/<id>/retry` con review_sha256. Todas llevan el prefijo `/api/http-trials`.
Con el servidor de la misma base abierto:

```powershell
$api = 'http://127.0.0.1:8765'
Invoke-RestMethod "$api/api/http-trials/$($p.id)"
Invoke-RestMethod "$api/api/http-trials/$($p.id)/reconcile" -Method Post -ContentType 'application/json' -Body '{}'
```

El navegador no lee el token; la API de nicrawl lo usa internamente. La base sintética
de esta guía permite todo el recorrido CLI, pero no crea una colección de ofertas válida
para `serve`. Para UI, elegí una colección existente y un borrador de esa misma base.

## Errores y preguntas

| Situación | Qué revisar |
| --- | --- |
| Primero iniciá test-receiver | Misma --db y token generado por el receptor |
| No se pudo conectar | Terminal 1 abierta y puerto correcto |
| Resultado incierto | Consultar recibo; no crear otra clave como reemplazo |
| Confirmación incorrecta | Hash del snapshot que revisaste |
| Receptor distinto/token cambiado | Recuperar archivos originales; conservar incertidumbre |
| Emisor interrumpido | show y reconcile recuperan sending sin envío automático |

Preguntate: ¿qué ocurre si el receptor confirma y el emisor cae antes de guardar?
¿Por qué un 404 no prueba que nunca llegó? ¿Qué protege la clave única y qué pierde
al crear otra clave? ¿Por qué el token y el hash cumplen funciones distintas?

[Contrato](../docs/HTTP_TRIAL.md) · [ADR-016](../docs/adr/016-http-test-receiver.md).
La evaluación de un portal/ATS real queda en [SPEC, I12c](../docs/SPEC.md#evaluación-posterior-i12c-integración-real).
