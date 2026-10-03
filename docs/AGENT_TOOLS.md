# I8 — contrato de herramientas para agentes

Implementado en 0.8.0, 2026-09-30. Tres herramientas MCP locales reutilizan los casos de uso de CLI/API. No hay modelo, clave de API, recolección ni postulación automática. [Guía práctica](../LearnDocs/16-agent-tools.md) y [ADR-011](adr/011-agent-tools-mcp.md).

## Instalar y probar

```powershell
Set-Location C:\Bruze\nicrawl
$uv = '.\.tools\uv\Scripts\uv.exe'
& $uv --system-certs sync --locked --extra agents
.\.venv\Scripts\nicrawl.exe agent-demo
# Opcional: leer tu colección existente, sin modificarla
.\.venv\Scripts\nicrawl.exe agent-demo --local
```

El extra instala el SDK MCP; `uv.lock` resuelve mcp 2.2.0. Un `uv sync` posterior sin `--extra agents` puede retirarlo. La CLI y UI básicas no lo necesitan. La demo crea una base temporal sintética por defecto, ejecuta un servidor como subproceso, descubre herramientas, busca Python, ordena y consulta hasta dos detalles. Elimina la base temporal al terminar. `--local` usa la base seleccionada con `--db`, sin escribirla.

## Herramientas y argumentos

El SDK publica esquemas JSON de entrada/salida. Los argumentos tienen un objeto exterior **`request`**; estos ejemplos son para `tools/call`, no comandos de PowerShell:

```json
{"name":"search_jobs","arguments":{"request":{"query":"Python","limit":5}}}
{"name":"rank_jobs","arguments":{"request":{"query":"Python","want":["Python"],"mode":"remote","limit":5}}}
{"name":"get_job","arguments":{"request":{"job_key":"greenhouse%3Agitlab:demo-202","description_chars":3000}}}
```

La clave del ejemplo es ficticia y solo existe en la demo sintética. Copiar siempre una clave completa de resultados. En MCP se envía como string JSON sin codificación URL adicional: `%3A` permanece `%3A`.

| Entrada | Contrato |
| --- | --- |
| Búsqueda | `query`, `company`, `location_text`: hasta 120 caracteres; `source`: vacío (todas), `remotive` o `greenhouse:gitlab`; `limit`: entero 1–20, default 5 |
| Ranking | Lo anterior más `want`/`avoid` (máximo 20 términos entre ambos, 1–80 caracteres), `mode` remote/hybrid/onsite, `fields` title/tags/description y `include_dismissed` booleano; requiere alguna preferencia |
| Detalle | `job_key`: 1–512 caracteres; `description_chars`: entero 0–6000, default 3000 |

Tipos estrictos y campos desconocidos rechazados. No se aceptan rutas de base, SQL ni nombres de funciones arbitrarios. La ruta de base la configura quien inicia el proceso. `search_jobs` llama `queries.search`, `get_job` llama `queries.show`, `rank_jobs` llama `personal.rank`. Los filtros, desempates y razones son los existentes. El ranking omite descartados por defecto: aunque no exporta estados, esa selección refleja una preferencia personal. `include_dismissed=true` permite compararlo con una selección sin ese descarte.

## Respuesta y límites

`schema_version`, `tool`, `generated_at`, `selection`, `total`, `returned`, `omitted`, `items`, `rules_version`, `truncation` y `content_notice`. Cada item incluye `job`; ranking añade `score` y `reasons`. El job expone clave, fuente/URL, título, empresa, ubicación, modalidad, primera/última observación, `stale` y detalle opcional. No contiene notas, estado personal, rutas de base ni informe interno de fuente. La proyección es una lista explícita; campos futuros no se exportan automáticamente.

- Máximo **24 KiB del JSON estructurado compacto UTF-8** por respuesta. No es un tope de todo el mensaje MCP: el SDK también serializa contenido textual y envolturas del protocolo.
- Si no cabe una lista, se retiran items del final, preservando orden, puntaje y razones de los restantes. `omitted` declara cuántos faltan; `truncation` señala `result_limit` o `response_bytes`.
- Título/empresa/ubicación tienen topes de 400/200/500 caracteres. `truncated_fields` declara recortes, incluido el detalle. El resumen no incluye descripción. Clave y URL nunca se recortan; una identidad excesiva produce error.
- `--max-calls` permite 1–1000 invocaciones que llegan al adaptador por proceso (default 100). Los rechazos de esquema del SDK anteriores al adaptador no consumen ese contador. Reiniciar crea otro presupuesto; no es una cuota durable ni un límite de mensajes del protocolo.
- La demo admite cuatro consultas, un plazo total de 30 segundos y espera de lectura de 10 segundos. Las consultas reutilizadas recorren la colección; estos límites no garantizan cancelación de CPU ni tamaño máximo de la base. No existe presupuesto monetario de LLM porque I8 no llama a ninguno.

Errores de aplicación: `invalid_arguments`, `unknown_tool`, `not_found`, `database_unavailable`, `record_too_large`, `call_budget_exhausted`. El SDK también puede rechazar argumentos según su esquema. Los errores del adaptador no reproducen notas, SQL o rutas internas.

## Conectar un cliente compatible con MCP stdio

Ejemplo de configuración de servidor; el formato exterior depende del cliente:

```json
{
  "mcpServers": {
    "nicrawl": {
      "command": "C:\\Bruze\\nicrawl\\.venv\\Scripts\\python.exe",
      "args": ["-m", "nicrawl", "--db", "C:\\Bruze\\nicrawl\\data\\nicrawl.sqlite3", "mcp", "--max-calls", "100"]
    }
  }
}
```

El cliente inicia y cierra el proceso. No requiere `serve`, puerto HTTP ni un directorio de trabajo específico. Ejecutar `nicrawl mcp` a mano deja el proceso esperando mensajes del protocolo: no es una consola interactiva. stdout queda reservado para MCP; diagnósticos van a stderr. No se ha registrado automáticamente en ningún cliente del usuario.

Las lecturas abren SQLite en modo readonly. Las anotaciones MCP `readOnlyHint` son metadatos, no la protección: la lista cerrada de herramientas y el código de lectura imponen el alcance. No se ofrecen shell, navegación, escritura o envío. Esto tampoco aísla las otras capacidades de un cliente que tenga más herramientas.

Los textos de ofertas siguen siendo datos externos no confiables. Un texto que diga “ignorá instrucciones” se conserva como dato; no se ejecuta ni genera otra herramienta. Los tests prueban esta frontera, **no demuestran inmunidad de un futuro LLM a prompt injection**. El cliente debe citar clave, URL, fecha observada, razones y dudas; modalidad remota no prueba residencia admitida ni vigencia. Si el cliente usa un modelo externo, puede transmitir resultados: configurar destino, datos y presupuesto conscientemente antes de usar la base personal.

Referencias del SDK oficial: [servidores y herramientas](https://py.sdk.modelcontextprotocol.io/servers/tools/), [cliente](https://py.sdk.modelcontextprotocol.io/client/) y [ejecución](https://py.sdk.modelcontextprotocol.io/run/).

## Extensión compatible I9

search_jobs y rank_jobs aceptan `title_query` (hasta 120 caracteres): coincidencia solo en título, combinada con los otros filtros. No se exponen perfiles guardados ni herramientas de escritura. Los tres nombres y los límites de I8 se conservan.

## I10 y privacidad

Candidaturas e historial no se exponen a MCP. Se conservan las tres herramientas de lectura de ofertas; no existe herramienta para crear candidaturas ni declarar envíos.
