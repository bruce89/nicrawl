# I9 — guardar un criterio y medir si sirve

Pregunta central: ¿puedo repetir mi búsqueda y comprobar si priorizar me ayuda a revisar menos ofertas irrelevantes? Empezá con el perfil **senior-uy**, preparado para Senior Software Engineer remoto desde Uruguay o presencial en Uruguay. La [referencia técnica](../docs/SAVED_SEARCHES.md) amplía contratos y límites.

## 1. Recuperar el perfil

```powershell
Set-Location C:\Bruze\nicrawl
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
& $nicrawl saved show senior-uy
$resultados = & $nicrawl saved run senior-uy | ConvertFrom-Json
$resultados.results | Select-Object score,@{n='titulo';e={$_.job.title}},@{n='ubicacion';e={$_.job.location_raw}}
```

En UI: `nicrawl serve`, seleccionar **senior-uy** y pulsar **Cargar búsqueda**. Para guardar cambios, abrir **Guardar configuración actual**; otro nombre crea otra búsqueda, y **Reemplazar si ya existe** reemplaza la configuración completa. El objetivo escrito ayuda a recordar qué buscabas, pero no altera los filtros.

Para reconstruir el perfil en una copia nueva (en tu instalación ya existe):

```powershell
& $nicrawl saved save senior-uy --view rank --query Software --title-query Engineer `
  --want Senior --want 'Software Engineer' `
  --goal 'Senior Software Engineer; remoto desde Uruguay o presencial en Uruguay.'
```

`--query` busca en título, empresa y descripción. `--title-query` exige además una coincidencia en el título. Ambos son subcadenas sin distinción de mayúsculas; “Engineer” también puede aparecer en “Engineering”. El ranking premia términos y conserva razones: no entiende el rol como una persona. No fijamos `location_text=Uruguay` porque perdería LATAM/Worldwide, ni `mode=remote` porque también te sirve presencial en UY. Eso deja una revisión geográfica pendiente, no un supuesto de elegibilidad.

## 2. Abrir la muestra que quedó preparada

Ya están creados estos archivos locales, fuera de Git:

```powershell
$snapshot = '.\data\i9-senior-uy-v1.json'
$labels = '.\data\i9-senior-uy-v1-labels.json'
$muestra = Get-Content $snapshot -Raw -Encoding utf8 | ConvertFrom-Json
$muestra.sample.jobs | Select-Object job_key,title,location_raw,source_url
```

Son 20 ofertas: unión de los primeros diez de ambos órdenes sobre una misma instantánea. No hay etiquetas inferidas. Para leer una descripción congelada sin buscar ni escapar IDs:

```powershell
$oferta = $muestra.sample.jobs[0]
$oferta | Select-Object job_key,title,location_raw,work_mode,last_seen_at
$oferta.description_text
$oferta.source_url
```

Revisá el contenido que quedó en la muestra para mantener fija la comparación. Si abrís la fuente y cambió, registrá esa diferencia en `reason`; no reescribas la muestra. La fecha de observación no garantiza que hoy siga abierta.

## 3. Etiquetar con un criterio explícito

Antes de puntuar, fijá qué significa útil: **vale la pena revisar como candidato Senior Software Engineer y hay evidencia compatible con trabajar desde/en Uruguay**. Ajustá ese criterio si preferís medir solo afinidad técnica, pero mantenelo igual en toda la muestra.

| Valor | Cuándo usarlo |
| --- | --- |
| `useful` | Encaja con rol/seniority y la ubicación publicada es compatible con el objetivo; no equivale a oferta confirmada ni contratación garantizada |
| `not_useful` | Hay un motivo claro de descarte: rol ajeno, nivel distinto o restricción explícita incompatible |
| `unknown` | Falta información para decidir, por ejemplo remote sin países admitidos |
| `pending` | Todavía no la revisaste |

Abrí el archivo de etiquetas con tu editor y cambiá solo `verdict` y `reason`. No cambies claves ni `snapshot_id`. Formato ilustrativo con ID ficticio:

```json
{"job_key":"greenhouse%3Agitlab:12345","verdict":"unknown","reason":"Remoto, pero no aclara contratación desde Uruguay"}
```

Si preferís practicar PowerShell, este ejemplo toma una clave **real** de la muestra y la deja en unknown (ejecutalo solo cuando esa sea tu conclusión):

```powershell
$etiquetas = Get-Content $labels -Raw -Encoding utf8 | ConvertFrom-Json
$key = $muestra.sample.jobs[0].job_key
$fila = $etiquetas.labels | Where-Object job_key -eq $key
$fila.verdict = 'unknown'
$fila.reason = 'Debo confirmar contratación desde Uruguay'
$etiquetas | ConvertTo-Json -Depth 20 | Set-Content $labels -Encoding utf8
```

`mark` sigue sirviendo para favoritos/notas en tu colección; no reemplaza la etiqueta del experimento. No hace falta marcar las 20 ofertas para evaluarlas.

## 4. Obtener y leer el resultado

```powershell
$evaluacion = & $nicrawl saved evaluate --snapshot $snapshot --labels $labels | ConvertFrom-Json
$evaluacion.list
$evaluacion.rank
$evaluacion.precision_delta
$evaluacion.sources | ConvertTo-Json -Depth 8
$evaluacion.useful_only_in_list
```

Con etiquetas pendientes, `precision` es null: no significa cero. Los límites inferior/superior muestran qué falta por resolver. Si rank obtiene 7 útiles de 10 y list 4, delta=0,3; si solo había tres candidatos, el denominador es tres, no diez. El programa informa `n` para evitar esa confusión. Una oferta útil exclusiva de list es una omisión del top de rank; no permite calcular recall global.

La muestra inicial tiene 20 ofertas GitLab y ninguna Remotive: su `sample.n=0` significa que no la evaluamos. Para estudiar esa fuente, crear otro perfil con `--source remotive` y otra muestra; no concluir que una fuente es mala por quedar fuera de este top. Si las restricciones de países dominan los descartes, ampliar fuentes con cobertura UY/LATAM puede ayudar más que ajustar puntos.

## 5. Repetir sin destruir evidencia

Para otro experimento, cambiá nombres de archivos:

```powershell
& $nicrawl saved snapshot senior-uy --k 10 --output .\data\senior-uy-v2.json
& $nicrawl saved label-template --snapshot .\data\senior-uy-v2.json --output .\data\senior-uy-v2-labels.json
```

La captura copia SQLite a un temporal consistente y ejecuta ambos órdenes sobre esa copia. Así no comparás ofertas observadas antes de una colección con otras posteriores. `evaluate` ya no depende de la base. Comparar estrategias de filtrado en muestras diferentes es otro experimento; no atribuir toda diferencia al ranking.

## Dudas y mapa del código

| Problema | Acción |
| --- | --- |
| Nombre existente | Usar otro nombre o `--replace` con todos los campos deseados |
| No encuentro el perfil | Verificar `--db`: cada base tiene su libro asociado |
| snapshot pide preferencias | Guardar want/avoid/mode: comparar rank requiere una regla |
| Archivo de salida existente | Elegir v2/v3; no se sobrescribe evidencia |
| La muestra cambió | Recuperar el original; las etiquetas deben corresponder al mismo snapshot_id |
| Clave duplicada/faltante | Conservar exactamente una fila por oferta; no agregar un prefijo al job_key |
| Error de JSON | Revisar comas, comillas y codificación UTF-8; no cambiar la estructura |

Ruta de ingeniería inversa: [saved_cli.py](../src/nicrawl/saved_cli.py) o [server.py](../src/nicrawl/server.py) → [saved_searches.py](../src/nicrawl/saved_searches.py) → queries/personal. Para evaluación: [evaluation.py](../src/nicrawl/evaluation.py). Leé [tests I9](../tests/test_i9_saved.py): uno cambia la base real durante la captura y verifica que la muestra conserva la instantánea. La configuración guardada se parece a estado de presentación persistido; la muestra es evidencia del experimento, por eso son archivos y ciclos de vida distintos.

La evaluación personal queda a tu cargo; los tests no demuestran utilidad laboral. **I10**, seguimiento de candidaturas, continúa pendiente de aprobación.
