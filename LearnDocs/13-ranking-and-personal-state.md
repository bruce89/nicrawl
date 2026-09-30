# I6 — ranking explicable y estado personal

Aplicación 0.6.0. En este corte se separan tres cosas: **lo observado** en el proveedor, **tu decisión personal** sobre un aviso y **una puntuación calculada** con preferencias explícitas. Esta distinción evita que una nota propia parezca una actualización del empleo.

## Recorrido

Desde `C:\Bruze\nicrawl`, con el entorno del proyecto:

```powershell
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
& $nicrawl list --limit 3
& $nicrawl rank --want Python --want Kotlin --avoid Senior --mode remote --limit 5
& $nicrawl rank --want Python --fields title,tags --source greenhouse:gitlab
& $nicrawl mark '<JOB_KEY_COMPLETO>' --state favorite --note 'Revisar requisitos de residencia'
& $nicrawl show '<JOB_KEY_COMPLETO>'
& $nicrawl mark '<JOB_KEY_COMPLETO>' --state unreviewed --clear-note
```

Reemplazá `<JOB_KEY_COMPLETO>` por un `job_key` obtenido en `list` o `rank` y copialo **completo, sin agregarle otra fuente**. Por ejemplo, GitLab usa `greenhouse%3Agitlab:8592950002`: `%3A` representa el `:` interno de `source_id=greenhouse:gitlab`; `remotive:greenhouse%3Agitlab:8592950002` es otra clave y no existe. También podés tomarla directamente de la salida estructurada en PowerShell:

```powershell
$resultado = & $nicrawl list --source greenhouse:gitlab --limit 1 | ConvertFrom-Json
$key = $resultado.jobs[0].job_key
& $nicrawl show $key
```

`mark` modifica **solo tu base local**. `rank`, `show` y `list` no hacen red. Se admiten `favorite`, `dismissed` y `unreviewed`; `--note` reemplaza la nota, omitirla la conserva y `--clear-note` la vacía. `rank` excluye descartadas salvo `--include-dismissed`. `list` conserva su orden de descubrimiento: la funcionalidad nueva no cambia la consulta anterior.

## Cómo se calcula

Para cada término deseado, una aparición literal sin distinción de mayúsculas suma 5 en título, 3 en tags y 1 en descripción. Para un término evitado, esos valores se restan. Una modalidad declarada que coincide con `--mode` suma 2; una distinta resta 2; `unknown` no aporta. Se suman todas las coincidencias y la salida `reasons` deja ver cada una. `--fields title,tags` desactiva la regla de descripción; también podés usar un solo campo o una lista vacía con `--fields ''` para estudiar únicamente modalidad. El desempate es `first_seen_at` descendente y después `job_key`.

Ejemplo sintético: título “Python Engineer”, tag `Python`, descripción sin la palabra, modalidad `remote`; con `--want Python --mode remote` obtiene 5 + 3 + 2 = **10**. No hay aprendizaje automático ni sinónimos. “Python” dentro de un texto genérico puede sumar 1 aunque el puesto no requiera programar en Python. Una condición de residencia ausente o ambigua nunca equivale a elegibilidad. Abrí el aviso original para decidir.

## Propiedad del dato y migración

La [tabla `personal_state`](../docs/DATA_MODEL.md) está fuera del JSON del aviso. Una recolección posterior puede actualizar la descripción sin borrar tu nota, y cambiar la nota no genera un evento en `changes`. La base pasó de esquema 1 a 2 con una migración transaccional. Antes de migrar la base real se guardó `data/nicrawl-pre-i6.sqlite3`; ambos archivos tienen 219 ofertas y las mismas cargas de avisos. El respaldo se conserva localmente y **no se incluye** en el ZIP de código. Si copiás una base antigua a otra máquina, respaldala antes de abrirla para escribir con 0.6.0. El comando de lectura detectará el esquema antiguo y pedirá migración; una escritura válida con 0.6.0 la aplicará. Ver [ADR-009](../docs/adr/009-personal-state-ranking.md).

## Laboratorio personal de evaluación

Para hacerlo paso a paso con comandos y una tabla breve, usá la [guía rápida de evaluación](14-i6-evaluation-quick-guide.md). Lo siguiente resume el método.

1. Elegí un objetivo concreto, por ejemplo puestos Python remotos adecuados a tu experiencia, y anotá tus reglas antes de mirar el orden. No uses el puntaje como etiqueta de verdad.
2. Tomá 20–50 avisos de tu base o fixtures propios. Leé cada descripción y enlace original y etiquetá `útil`, `no útil` o `incierto`, con motivo. Si no podés verificar requisitos geográficos, marcá `incierto`.
3. Compará los primeros diez del orden de `list` con los primeros diez de `rank` sobre el **mismo conjunto y filtros**; usá `--include-dismissed` si tu muestra contiene descartadas. Calculá precisión@10: útiles entre esos diez dividido por diez. Registrá también útiles que el ranking dejó fuera. No conviertas `incierto` en positivo.
4. Inspeccioná tres falsos positivos y tres falsos negativos. Probá quitar `description` con `--fields`, o cambiar términos; documentá antes qué esperás que mejore y qué puede empeorar.
5. Repetí con otra muestra. No uses etiquetas de la primera muestra para afirmar una mejora general. Podés anotar resultados en la [bitácora](07-workbook.md).

Las pruebas técnicas verifican cálculo y persistencia, pero no miden utilidad real para vos: no existe aún un corpus etiquetado por vos. Esta evaluación es la entrada correcta para I7 si se quisiera comparar reglas con una alternativa AI.

## Puente de arquitectura

La tabla personal se parece a un modelo local de preferencias separado del DTO de red en una app iOS. La función de puntuación es pura: recibe una oferta y parámetros, devuelve puntos y razones; no conoce Typer, SQLite ni HTTP. La capa de aplicación lee una instantánea SQLite, filtra, calcula y ordena. Este límite facilita evaluar otra estrategia después sin romper la recolección. El texto de una oferta se usa como **dato**, incluso si contiene instrucciones dirigidas a un asistente.
