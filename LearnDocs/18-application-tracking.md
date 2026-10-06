# I10 — de “me interesa” a “qué pasó con esta candidatura”

Favorito es una marca sobre un aviso. Candidatura es una entidad con identidad e historia: puede avanzar, cerrarse o corregirse aunque cambie el aviso. El objetivo de este corte es registrar ese proceso sin enviar nada a terceros.

## Recorrido rápido por UI

```powershell
Set-Location C:\Bruze\nicrawl
.\.venv\Scripts\nicrawl.exe serve
```

Abrí una oferta → **Crear seguimiento** → **ver seguimiento**. O entrá en **Candidaturas** y completá una referencia manual con URL, puesto y empresa. Una URL de LinkedIn queda guardada; nicrawl no entra al sitio ni extrae su contenido.

Elegí estado y escribí un motivo. **Guardar estado local** registra tu afirmación. Seleccionar Enviada no postula: hacelo cuando efectivamente hayas enviado por otro medio. Para corregir un error, elegí el estado correcto y explicá la corrección. Ambos eventos quedan visibles.

## Terminal: tomar una clave real

Estos comandos escriben solo cuando invocás add/update. Primero obtené una oferta que vos quieras seguir:

```powershell
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
$ofertas = & $nicrawl saved run senior-uy | ConvertFrom-Json
$ofertas.results | Select-Object @{n='key';e={$_.job.job_key}},@{n='titulo';e={$_.job.title}}
# Elegí una de las claves mostradas y asignala a $key.
# Ejemplo de formato ficticio: greenhouse%3Agitlab:12345
$key = $ofertas.results[0].job.job_key
# Ejecutá add si decidís iniciar su seguimiento:
$alta = & $nicrawl applications add --job-key $key --reason 'Revisar contratación desde Uruguay' | ConvertFrom-Json
$id = $alta.application.id
$alta.created
& $nicrawl applications show $id
```

La selección `[0]` ilustra cómo recuperar una clave, no recomienda ese puesto. Si no hay resultados, no la indexes. Copiá el job_key entero sin añadir fuente ni recodificar `%`. El **UUID de candidatura** es otro identificador: show/update de applications usan `$id`, no el job_key.

## Practicar sin llenar tu seguimiento real

Este ejemplo usa un almacén separado de práctica y una URL ficticia. No necesita recolectar ni crear una colección de ofertas:

```powershell
$practica = '.\work\i10-practica.sqlite3'
$alta = & $nicrawl --db $practica applications add `
  --url 'https://jobs.example/senior-uy?utm_source=demo' `
  --title 'Senior Software Engineer — ficticio' --company 'Empresa de ejemplo' `
  --reason 'Ejercicio de seguimiento' | ConvertFrom-Json
$id = $alta.application.id
$actual = & $nicrawl --db $practica applications show $id | ConvertFrom-Json
& $nicrawl --db $practica applications update $id --state submitted `
  --revision $actual.application.revision --reason 'Simulación: envío realizado fuera de nicrawl'
& $nicrawl --db $practica applications list --state submitted
& $nicrawl --db $practica applications show $id
```

Esperado: estado submitted, revisión 2 si era nueva, dos eventos y ninguna conexión al aviso. Solo se creó `work/i10-practica.sqlite3.applications.sqlite3`; el nombre de base funciona como ámbito del seguimiento. Si repetís el alta, `created=false` y recuperás la misma candidatura con su historial, sin resetearla.

Repetí update con la revisión vieja: debe rechazarlo. Después volvé a show, leé la revisión y probá interview/closed/draft con otro motivo. También podés registrar un avance manteniendo el mismo estado. Para vacantes reales, escribí hechos reales; no copies motivos de la simulación.

## API desde PowerShell

Con serve abierto en otra terminal, una consulta equivalente:

```powershell
$base = 'http://127.0.0.1:8765'
Invoke-RestMethod "$base/api/applications?state=draft&limit=50"
# Solo cuando exista una candidatura real y quieras registrar un avance:
$actual = Invoke-RestMethod "$base/api/applications/$id"
$body = @{state='interview'; expected_revision=$actual.application.revision; reason='Entrevista confirmada por el empleador'} | ConvertTo-Json
# La siguiente línea ES una escritura; usar únicamente si describe lo ocurrido:
Invoke-RestMethod "$base/api/applications/$id" -Method Patch -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Usá el UUID de la **misma base** que atiende serve. El `$id` de la práctica aislada no existe en el servidor de tu base habitual. Los ejemplos muestran la correspondencia entre razonamiento y operación, no una secuencia que deba ejecutarse ciegamente.

## Qué observar y dónde mirar

| Duda/error | Explicación |
| --- | --- |
| Duplicado | Se encontró la clave o URL canónica. El nuevo motivo no reemplaza al anterior; usar update para añadirlo |
| Revisión desactualizada | Otra edición ya se guardó o repetiste una petición. Leer show y decidir después |
| Favorito sin candidatura | Es correcto: son decisiones distintas |
| Oferta cambió, título de candidatura no | Conservamos título/empresa/URL al crearla; no hay sincronización silenciosa |
| Referencia manual con país desconocido | Se conserva como referencia; no hay extracción ni validación de elegibilidad |
| Estado incorrecto | Registrar corrección con motivo; no se borra el evento previo |
| UUID no encontrado | Revisar --db y no confundir UUID con job_key |

Ruta de código: [application_cli.py](../src/nicrawl/application_cli.py) o [server.py](../src/nicrawl/server.py) → [applications.py](../src/nicrawl/applications.py). La [UI](../src/nicrawl/ui/applications.js) solo consume esa API. Mirá [tests I10](../tests/test_i10_applications.py): una prueba fuerza el fallo al insertar historial y confirma que tampoco cambió el estado; otra lanza dos ediciones con la misma revisión y solo una gana.

Esto conecta tres conceptos: identidad estable (evitar duplicados), transacción (estado e historia juntos) y concurrencia optimista (rechazar una versión vieja). Se parecen a editar un recurso con ETag o versión de entidad; acá la revisión es explícita y local.

El [contrato](../docs/APPLICATIONS.md) detalla límites. No se crearon candidaturas reales por vos durante la implementación. I11 agrega perfil/CV y borradores locales; consultá la [guía práctica](19-profile-and-drafts.md).
