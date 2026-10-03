# I8 — de una consulta a una herramienta para agentes

Objetivo: seguir una petición tipada hasta sus datos y verificar su respuesta. Una **herramienta** es una función con contrato; el **cliente MCP** descubre ese contrato e invoca la función; un **agente** puede elegir qué invocar usando un modelo y un ciclo de decisiones. I8 entrega las herramientas y un cliente de demo con secuencia fija. No interpreta lenguaje natural.

## Recorrido rápido (10–15 minutos)

```powershell
Set-Location C:\Bruze\nicrawl
$uv = '.\.tools\uv\Scripts\uv.exe'
& $uv --system-certs sync --locked --extra agents
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
$demo = & $nicrawl agent-demo | ConvertFrom-Json
$demo.tools
$demo.search.items.job | Select-Object job_key,title,location_raw,work_mode
$demo.ranking.items | Select-Object @{n='key';e={$_.job.job_key}},score,reasons
$demo.details | ConvertTo-Json -Depth 12
```

Buscamos responder: “Mostrame cinco ofertas Python y qué restricciones de ubicación debo revisar”. La demo traduce esa pregunta a llamadas predeterminadas, no a razonamiento de un modelo. Deben aparecer dos resultados Python, hasta cinco solicitados. Revisá LATAM frente a Remote, US y modalidad `unknown`: ninguna permite asegurar elegibilidad. La URL `jobs.example` es ficticia. Verificá `job_key`, `source_url`, `last_seen_at`, `score` y razones; la fecha observada no certifica que una oferta esté abierta.

Hay una nota privada sembrada en la base temporal: `NOTA_PRIVADA_DEMO_NO_EXPORTAR`. No debe aparecer en el JSON:

```powershell
($demo | ConvertTo-Json -Depth 20) -match 'NOTA_PRIVADA_DEMO_NO_EXPORTAR'
# Esperado: False
```

## Comparar con tu colección

Todos estos comandos leen; no recolectan ni marcan:

```powershell
$local = & $nicrawl agent-demo --local | ConvertFrom-Json
$lista = & $nicrawl list --query Python --limit 5 | ConvertFrom-Json
$ranking = & $nicrawl rank --query Python --want Python --mode remote --include-dismissed --limit 5 | ConvertFrom-Json
$lista.jobs.job_key
$local.search.items.job.job_key
$ranking.results | Select-Object @{n='key';e={$_.job.job_key}},score
$local.ranking.items | Select-Object @{n='key';e={$_.job.job_key}},score
$key = $local.search.items[0].job.job_key
& $nicrawl show $key
```

Esperado: mismas claves y orden, puntajes y razones. La demo incluye descartados para mantener una comparación controlada; el ranking habitual los excluye. Hacé las lecturas sobre la misma base y sin cambios entre ellas. Si hay recorte por tamaño, compará el prefijo retornado y mirá `omitted`/`truncation`. Si no hay resultados Python, no indexes `[0]`: probá la demo sintética o revisá filtros desde CLI. `show` puede mostrar notas personales; no copies su JSON completo a un modelo.

La comparación técnica comprueba que las interfaces no cambian las reglas. Para saber si el orden **te resulta útil**, sigue vigente la [evaluación manual rank vs list](14-i6-evaluation-quick-guide.md). Son dos preguntas diferentes.

## Mapa del código

1. [agent_demo.py](../src/nicrawl/agent_demo.py): cliente, proceso, secuencia y presupuesto.
2. [mcp_server.py](../src/nicrawl/mcp_server.py): registro de las tres herramientas y esquemas.
3. [agent_tools.py](../src/nicrawl/agent_tools.py): validación, contador, proyección y recorte.
4. [queries.py](../src/nicrawl/queries.py) / [personal.py](../src/nicrawl/personal.py): búsqueda y ranking compartidos con CLI/UI.
5. [storage.py](../src/nicrawl/storage.py): snapshot de lectura.

La analogía con arquitectura iOS es un adaptador de presentación y un DTO específico: otro cliente consume el mismo caso de uso, pero no recibe todo el modelo interno. Un prompt que pide “no mostrar notas” sería una instrucción al consumidor; la proyección evita exportarlas desde el productor.

Ejercicio corto: cambiá solo `limit` o `description_chars` en una llamada de prueba y predecí `returned`, `omitted` y `truncated_fields`. Leé [tests I8](../tests/test_i8_agents.py) para contrastar casos de Unicode, claves codificadas y texto que pretende dar instrucciones. No confundas acotar la salida con acelerar la consulta completa.

## Dudas frecuentes

| Síntoma | Qué revisar |
| --- | --- |
| Falta MCP | Repetir instalación con `--extra agents`; la CLI básica no instala el extra |
| `mcp` queda esperando | Es normal: requiere cliente de protocolo; usar `agent-demo` para ver el recorrido |
| Clave no encontrada | Copiar la clave completa, sin prefijo añadido ni `%` recodificado; ejemplo ficticio `greenhouse%3Agitlab:demo-202` |
| Argumentos rechazados | Objeto `request`, nombres exactos, enteros reales, máximo 20 resultados y alguna preferencia de ranking |
| Menos resultados que el límite | Revisar `total`, `omitted` y `truncation`; límite no significa cantidad garantizada |
| Presupuesto agotado | El proceso alcanzó `--max-calls`; revisar por qué el cliente repite antes de reiniciarlo |
| El modelo afirma residencia admitida | Pedir evidencia de fuente; remote/unknown no responde esa pregunta |

El [contrato y configuración MCP](../docs/AGENT_TOOLS.md) permite conectar después un cliente real. La demo local no envía tus datos a un modelo. El siguiente corte propuesto es **I9: búsquedas guardadas y pertinencia de fuentes**, pendiente de aprobación.
