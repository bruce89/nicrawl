# ADR-005 — extensiones y enriquecimiento

Estado: propuesto · 2026-09-24.

## Contexto y decisión

Interesa conservar un camino hacia AI y aplicaciones adicionales sin convertir el MVP en una plataforma. Proponer puertos solo en fronteras usadas: fuente, repositorio y reloj. Ranking/enriquecimiento se introduce cuando haya un caso real, como anotación separada del dato de origen.

El hook es una responsabilidad prevista y un contrato conceptual documentado; no se construye infraestructura vacía. Una futura UI o API reutiliza consultas de aplicación sin importar Typer. Un LLM no debe controlar la recolección ni modificar ofertas originales.

## Alternativas

- Scraping directo mediante un agente general: puede ser flexible, pero hace menos reproducibles el acceso, formato y costo.
- FastAPI desde el día uno: interesante si hay otro cliente; innecesario para una CLI local.
- Base vectorial inicial: añade infraestructura antes de tener criterios de relevancia y un corpus.
- Modelo único que mezcle dato observado y conclusión AI: simple al principio, difícil de auditar y reevaluar.

## Consecuencias y validación

Las funciones de dominio deben poder invocarse desde pruebas sin CLI ni red. Evaluar una extensión contra baseline y guardar versión/evidencia por resultado. Si falla, la búsqueda original sigue funcionando. Reabrir cuando aparezca un segundo cliente concreto o una necesidad de ranking que filtros explícitos no resuelvan.

El alcance y los experimentos están en [EXTENSIONS_AI](../EXTENSIONS_AI.md).
