# Guía rápida: evaluar I6 para diseñar I7

**Objetivo:** comprobar si el orden de `rank` te ayuda a encontrar ofertas útiles más rápido que el orden por descubrimiento de `list`. No buscamos demostrar que el puntaje predice contratación ni que una oferta remota acepta postulaciones desde Argentina. La UI local ya es la dirección preferida para I7; esta evaluación **orienta qué mostrar y facilitar en ella**, sin bloquear técnicamente el corte ni aprobarlo automáticamente.

## 1. Leer una oferta sin perderse en el JSON

En tu salida de `show 'greenhouse%3Agitlab:8592950002'`, `job` pertenece a GitLab, `personal` era tu favorito y nota, y `source_status` debía referirse a GitLab; se corrigió la salida que mostraba Remotive. `location_raw` dice `Remote, US`, pero `work_mode` sigue `unknown`: el sistema no tiene evidencia estructurada suficiente para afirmar modalidad o elegibilidad. La nota “Revisar requisitos de residencia” era una pregunta tuya, no una conclusión del scraper. El último comando, `mark ... --state unreviewed --clear-note`, **quitó** favorito y nota; no hay que repetirlo salvo que quieras borrar ambos.

Para ver solo lo esencial de cualquier aviso en PowerShell:

```powershell
$key = 'greenhouse%3Agitlab:8592950002'
$detalle = & $nicrawl show $key | ConvertFrom-Json
$detalle.job | Select-Object job_key,title,company,location_raw,work_mode,source_url
$detalle.personal
```

Si querés recuperar el favorito de ese ejemplo: `& $nicrawl mark $key --state favorite --note 'Revisar requisitos de residencia'`. Abrí `source_url` para revisar el aviso vigente; los datos guardados son una observación anterior y `stale=false` solo significa observado hace menos de siete días.

## 2. Elegir una pregunta y mantener el mismo conjunto

Escribí una frase antes de medir, por ejemplo: “Busco puestos Python que yo consideraría revisar y quiero ver si `rank` me presenta más útiles entre los primeros diez”. Cambiá Python, términos y modalidad según **tu** objetivo; no uses el ejemplo como perfil asumido. `--query` define el conjunto de candidatos; `--want`, `--avoid` y `--mode` cambian el orden dentro de él. Si filtrás por Python, la evaluación no dice nada sobre ofertas útiles que no mencionan Python.

Ejemplo reproducible con la base actual, sin red ni escrituras:

```powershell
$base = & $nicrawl list --query Python --limit 200 | ConvertFrom-Json
$ordenado = & $nicrawl rank --query Python --want Python --mode remote --include-dismissed --limit 200 | ConvertFrom-Json
$base.total
$ordenado.total
$base.jobs | Select-Object -First 10 job_key,title,company,location_raw
$ordenado.results | Select-Object -First 10 score,@{n='job_key';e={$_.job.job_key}},@{n='title';e={$_.job.title}}
```

Con la instantánea revisada había 41 candidatos para `--query Python`, por debajo del límite 200. Las dos cifras `total` deben coincidir; si no, revisá filtros, `--include-dismissed` y si hubo una recolección entre comandos. Este ejemplo prueba ordenamiento **dentro de esa selección**, no cobertura de todo el mercado. Para ver por qué un aviso subió o bajó, buscá su `job_key` en `$ordenado.results` y mirá `score` y `reasons`.

### Del razonamiento a los comandos

| Pregunta | Comando / dato que mirás |
| --- | --- |
| ¿Estoy comparando las mismas ofertas? | `$base.total` y `$ordenado.total`; mismos `--query`/filtros y `--include-dismissed` en `rank` |
| ¿Qué cambió en los primeros diez? | `$base.jobs` frente a `$ordenado.results`, usando `job_key` como identidad |
| ¿Por qué subió una oferta? | `score` y `reasons` del resultado de `rank` |
| ¿Es útil para **mi** búsqueda? | `show`, descripción y enlace original; anotá una etiqueta manual, no la deduzcas del puntaje |

Ejemplo de **formato ficticio**, no son claves existentes: `remotive:demo-101` y `greenhouse%3Agitlab:demo-202`. En la práctica, dejá que la CLI te entregue la clave; no la armes vos. Estos comandos toman la primera oferta del ranking real y muestran su explicación y detalle, sin escribir nada:

```powershell
$primero = $ordenado.results[0]
$key = $primero.job.job_key
$primero.score
$primero.reasons | Format-Table rule,term,field,points
$detalle = & $nicrawl show $key | ConvertFrom-Json
$detalle.job | Select-Object job_key,title,company,location_raw,work_mode,source_url
$detalle.personal
```

Hoy la superficie pública operable desde terminal es la **CLI**, que devuelve JSON; `ConvertFrom-Json` lo transforma en objetos de PowerShell para practicar el contrato de datos. Una API HTTP local para la futura UI aún no está implementada. Si además querés guardar una decisión personal sobre esa oferta, esta operación sí escribe en tu base:

```powershell
& $nicrawl mark $key --state favorite --note 'Revisar requisitos de residencia'
(& $nicrawl show $key | ConvertFrom-Json).personal
```

Hacé esto solo con una oferta que elegiste revisar. `favorite` expresa tu decisión, **no** la etiqueta `útil` del experimento; esa etiqueta va en la tabla de evaluación. Para deshacer la marca, usá `mark $key --state unreviewed --clear-note` conscientemente.

Para construir la lista **sin repetidos** que vas a etiquetar, uní los diez primeros de cada orden. `Sort-Object -Unique` reordena solo esta lista de revisión; no cambia el orden original de ninguna comparación:

```powershell
$keysBase = @($base.jobs | Select-Object -First 10 -ExpandProperty job_key)
$keysRank = @($ordenado.results | Select-Object -First 10 | ForEach-Object { $_.job.job_key })
$keysRevisar = @($keysBase + $keysRank | Sort-Object -Unique)
$keysRevisar.Count
$keysRevisar
```

Para revisar otra de esas claves, asigná `$key = $keysRevisar[1]` y repetí `show` del bloque anterior. Antes de abrir el enlace, el JSON guardado sirve para una primera lectura; para decidir si el puesto sigue disponible o si admite tu ubicación, comprobá `source_url` en el origen. Ninguno de estos comandos marca favoritos ni guarda etiquetas de evaluación.

## 3. Etiquetar antes de sacar conclusiones

Revisá al menos la **unión de los primeros diez** de ambas listas (pueden repetirse, así que quizá sean menos de 20 avisos). Si podés, ampliá a 20–50 del mismo conjunto para detectar ofertas útiles omitidas. Por cada aviso, anotá una etiqueta independiente del puntaje: `útil`, `no útil` o `incierto`. Leé título, descripción y enlace original; registrá una razón breve y cualquier dato que falte. `favorite`/`dismissed` sirven para tu flujo personal, pero **no sustituyen** estas etiquetas de evaluación. Podés copiar esta tabla a la [bitácora](07-workbook.md):

| job_key | etiqueta | evidencia / duda | puesto en `list` | puesto en `rank` | razón del puntaje que revisar |
| --- | --- | --- | ---: | ---: | --- |
| `<clave copiada>` | útil / no útil / incierto | requisito concreto o dato faltante |  |  |  |

Para el aviso GitLab del ejemplo, una anotación razonable sería `incierto` **respecto de residencia** hasta comprobar el requisito actual; no corresponde marcarlo útil solo porque dijiste `favorite` ni descartarlo solo porque `work_mode=unknown`. Tu criterio de utilidad puede incluir otros factores, como nivel de experiencia o tipo de rol: escribilos antes de etiquetar.

## 4. Comparar y decidir la siguiente pregunta

Contá `útiles confirmadas entre los primeros 10 / 10` para cada orden (precisión@10) e informá por separado cuántas quedaron `inciertas`. Si hay menos de diez candidatos, usá el número disponible y anotá el denominador. Mirá además cuántas ofertas etiquetadas `útil` quedaron fuera de los primeros diez de `rank`. Dos o tres ejemplos concretos de falsos positivos y omisiones explican más que un puntaje aislado. Probá **un solo cambio** —por ejemplo `--fields title,tags` para quitar descripción— y repetí el cálculo sobre las mismas etiquetas.

Registrá en la [bitácora](07-workbook.md): objetivo, comandos/preferencias, fecha de la base, etiquetas, ambas precisiones, incertidumbres, ejemplos de errores y qué cambio probaste. La dirección preferida para I7 es una **UI local** separada de la lógica, manteniendo la CLI usable; este ejercicio ayuda a decidir qué filtros, razones, dudas y estados debe mostrar. Si las reglas fallan por matices de texto que ya etiquetaste, conservá esos casos para un experimento AI posterior. Si el problema es falta de ofertas relevantes, también habrá que revisar fuentes o filtros. El [roadmap](../docs/ROADMAP.md) registra la dirección y la futura extensión para agentes; todavía no son implementaciones aprobadas.

## Si algo no cuadra

- **Clave no encontrada:** copiá `job_key` entero de `list`/`rank`; no antepongas `remotive:` a una clave GitLab. `greenhouse%3Agitlab:8592950002` ya incluye su fuente.
- **JSON demasiado largo:** usá `ConvertFrom-Json` y `Select-Object` como arriba; `show` contiene la descripción completa para no perder evidencia.
- **`work_mode=unknown` o ubicación ambigua:** marcá la duda en la tabla y comprobá el aviso de origen; el ranking no resuelve elegibilidad.
- **El favorito desapareció:** `--state unreviewed --clear-note` lo deshace. Volvé a `mark --state favorite` si querés conservarlo.
- **Las dos listas no tienen el mismo total:** igualá filtros, incluí descartadas en `rank` y no recolectes entre comparaciones.

La [guía I6](13-ranking-and-personal-state.md) explica las reglas y la arquitectura con más detalle; esta página es el recordatorio operativo.
