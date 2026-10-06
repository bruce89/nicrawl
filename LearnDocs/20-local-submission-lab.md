# I12a — revisar, simular, reconciliar

Reservá 20–30 minutos. El objetivo es explicar por qué **no recibir respuesta no
significa que el receptor no recibió el envío**. Usamos datos ficticios y una base
separada. No se consulta example.org ni se transmite una candidatura.

## Preparar el laboratorio desde PowerShell

```powershell
Set-Location C:\Bruze\nicrawl
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
$lab = 'data/i12-lab.sqlite3'
New-Item -ItemType Directory -Force data | Out-Null
Set-Content -Encoding utf8 data/i12-cv.txt 'Experiencia ficticia: Python y SQLite.'

$application = (& $nicrawl --db $lab applications add --url 'https://example.org/jobs/42' --title 'Engineer de prueba' --company 'Empresa ficticia' | ConvertFrom-Json).application
$profile = & $nicrawl --db $lab profile save --cv-file data/i12-cv.txt --label 'Laboratorio ficticio' --statement 'Experiencia con Python' --evidence 'Experiencia ficticia: Python y SQLite.' | ConvertFrom-Json
$draft = & $nicrawl --db $lab applications draft create $application.id --profile-version $profile.version --claim-id E01 | ConvertFrom-Json
$prepared = & $nicrawl --db $lab simulation prepare $draft.id --version $draft.version | ConvertFrom-Json
$prepared.payload.preview
$prepared.destination
```

Revisá puesto, cita y apertura. `prepare` conserva exactamente esa revisión. En una
práctica real, resolvé las preguntas del borrador antes de preparar; no las borres
solamente para pasar la validación. El hash devuelto identifica este contenido, pero
no demuestra que la cita sea verdadera o adecuada para el aviso.

## Caso central: llegó, pero perdimos la respuesta

Después de revisar el contenido:

```powershell
& $nicrawl --db $lab simulation send $prepared.id --confirm-sha256 $prepared.review_sha256 --scenario timeout-after
& $nicrawl --db $lab simulation show $prepared.id
# Intentar send otra vez ahora produce conflicto: primero consultar el recibo.
& $nicrawl --db $lab simulation reconcile $prepared.id
& $nicrawl --db $lab simulation send $prepared.id --confirm-sha256 $prepared.review_sha256
```

Esperado: `uncertain` → `accepted`. El último comando devuelve el mismo `receipt_id`;
no crea un segundo recibo ni un segundo evento de envío. Si reiniciás la terminal,
podés recuperar el ID con `simulation prepare <draft-id> --version <n>`.

La candidatura sigue con el estado que tenía. “Aceptado por el simulador” no equivale
a aceptación de un empleador, entrega externa ni avance de una selección.

## Comparar los otros casos

Creá un borrador nuevo para cada escenario: cada par borrador/versión representa un
ensayo independiente. Repetir `prepare` sobre el mismo par recupera el ensayo anterior.

| Escenario de send | Qué buscar |
| --- | --- |
| accepted | Recibo inmediato, mismo recibo ante reintento |
| rejected | Rechazo definitivo del ensayo; cambiar el escenario no lo convierte en aceptación |
| timeout-before | uncertain; reconcile vuelve a prepared; recién entonces reenviar con accepted |
| timeout-after | uncertain; reconcile recupera accepted; no necesita reenvío |

Anotá: ID del ensayo, estado antes/después, cantidad de eventos y receipt_id. Explicá
por qué un ID nuevo en cada reintento haría perder la deduplicación.

## El mismo flujo por HTTP y UI

Con `nicrawl serve` sobre una colección existente, Candidaturas permite crear o
reabrir un borrador, preparar el ensayo, revisar su instantánea, marcar la casilla de
revisión y elegir el escenario. “Consultar recibo local” reconcilia un resultado
incierto. La base de la UI debe ser la misma que la de la CLI. El servidor requiere
una colección válida; la base sintética de arriba es suficiente para CLI, pero por
sí sola no habilita `serve`.

Si tenés `$draft` de esa misma base y el servidor está abierto:

```powershell
$api = 'http://127.0.0.1:8765'
$p = Invoke-RestMethod "$api/api/simulations" -Method Post -ContentType 'application/json' -Body (@{ draft_id=$draft.id; version=$draft.version } | ConvertTo-Json)
$p.payload.preview  # revisar antes del siguiente paso
Invoke-RestMethod "$api/api/simulations/$($p.id)/send" -Method Post -ContentType 'application/json' -Body (@{ review_sha256=$p.review_sha256; scenario='timeout-after' } | ConvertTo-Json)
Invoke-RestMethod "$api/api/simulations/$($p.id)/reconcile" -Method Post -ContentType 'application/json' -Body '{}'
```

## Recorrido del código y límites

CLI/UI → API opcional → `simulation.prepare/send/reconcile` → SQLite del simulador.
`applications.show_draft` solo aporta el borrador. El receptor no es un servidor ATS:
emisor y receptor se simulan en una transacción local, por eso podemos reproducir los
resultados sin esperar timeouts reales. Leé [el contrato](../docs/SIMULATION.md) y
[la decisión](../docs/adr/015-local-submission-simulation.md) antes de extrapolar a I12b.

La etiqueta de evaluación de I6 mide pertinencia; `mark` conserva favoritos/notas;
I10 registra tu seguimiento; I12a registra un ensayo. Son preguntas diferentes.
