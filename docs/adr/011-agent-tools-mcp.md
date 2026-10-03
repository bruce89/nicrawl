# ADR-011 — herramientas de lectura con MCP stdio opcional

Estado: aceptado en I8 el 2026-09-30. Usuario: “Bien, vamos con I8”.

## Contexto y decisión

CLI y API ya comparten consultas y ranking. Un cliente de agentes necesita descubrir operaciones tipadas, conservar evidencia y recibir solo los datos necesarios. Elegimos tres herramientas MCP por stdio, SDK oficial 2.2.0 fijado por lock dentro del extra `agents`. El transporte vive en `mcp_server.py`; contratos, límites y proyección viven en `agent_tools.py`, sin importar MCP ni proveedor de modelos.

La aplicación sigue siendo usable sin ese extra. Una demo con cliente y subproceso reales verifica descubrimiento y llamadas sin API key ni modelo. SQLite permanece en lectura y no cambia el esquema. La salida excluye notas/estados mediante lista explícita. Se conserva la semántica de descarte del ranking, documentando que influye en la selección.

## Alternativas y consecuencias

- Reutilizar todo el JSON HTTP sería sencillo, pero exportaría detalles personales innecesarios. Se reutilizan los casos de uso y se proyecta otro DTO.
- Agregar endpoints HTTP para agentes permitiría acceso remoto; hoy introduce puerto y autenticación sin necesidad. Stdio tiene ciclo de vida ligado al cliente local.
- Un script con funciones Python serviría como laboratorio, pero no probaría descubrimiento ni contratos en un cliente estándar. MCP agrega dependencias, aisladas como extra.
- No escribimos el protocolo manualmente ni incorporamos un proveedor de LLM; el SDK genera esquemas y gestiona el intercambio.

La salida estructurada se limita a 24 KiB, las listas a 20 y el detalle a 6000 caracteres, con recortes explícitos. El proceso limita invocaciones admitidas; no es una cuota durable ni un sandbox del cliente. El SDK añade envolturas y contenido textual fuera de ese presupuesto de JSON. Los datos externos se etiquetan como no confiables; esto no garantiza el comportamiento de futuros modelos.

## Validación y reapertura

Pruebas de paridad CLI, exclusión de datos privados, argumentos inválidos, claves codificadas, Unicode, límites, texto malicioso inerte y transporte real. La demo local conserva el hash de SQLite. Evidencia en [VALIDATION](../../VALIDATION.md).

Reabrir al necesitar escrituras, acceso remoto, colecciones grandes, presupuestos durables o un agente autónomo. Cada uno exige contrato y evaluación propios. [Contrato completo](../AGENT_TOOLS.md).
