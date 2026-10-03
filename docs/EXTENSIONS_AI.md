# Extensiones y posible rama de AI

Estado al 2026-09-30: I6 implementó reglas y estado personal; I7 implementó UI y API locales. I8 implementa herramientas MCP de lectura para agentes, con [contrato](AGENT_TOOLS.md) y demo sin modelo; alcance y hitos posteriores en [NEXT_STEPS](NEXT_STEPS.md). AI sigue como experimento opcional posterior.

## Baseline antes de modelos

I6 implementó un ranking local por preferencias explícitas: palabras deseadas, tecnologías, modalidad declarada y restricciones conocidas. Mostrar contribución de cada regla y permitir desactivarla. No convertir “no encontré una restricción” en “sos elegible”.

Dataset de evaluación personal aún propuesto: 50 ofertas sintéticas o permitidas, revisadas manualmente, con etiquetas de relevancia y campos desconocidos. Medir precisión entre los primeros diez resultados y cantidad de ofertas útiles omitidas. El objetivo no es predecir contratación; es reducir el tiempo de revisión del usuario.

## Frontera prevista

`JobEnricher.enrich(job, preferences) -> EnrichmentResult` sería un puerto de aplicación futuro. Primero implementación de reglas, después modelo opcional. Las anotaciones derivadas se guardan aparte: `job_key`, huella de entrada, versión de reglas/modelo, evidencia, estado, tiempos y costo si aplica. No sobrescriben el texto original.

I7 ya dispone de un servidor HTTP para la UI. No hace falta añadir otra capa HTTP, cola, sistema de plugins o base vectorial solo para reservar esta posibilidad. Una interfaz pequeña en el momento de tener dos implementaciones es suficiente. [ADR-005](adr/005-extension-boundary.md).

## Experimentos concretos

| Idea | Baseline | Qué debe demostrar AI |
| --- | --- | --- |
| Resumen breve de oferta | Plantilla de campos conocidos | Mayor utilidad sin añadir requisitos ni salarios |
| Skills explícitas | Diccionario + reglas de tokens | Mejor cobertura con fragmento de evidencia por skill |
| Explicar ranking | Lista de contribuciones | Texto más claro manteniendo las mismas razones |
| Agrupar duplicados | IDs y URLs exactos | Mejor recall con tasa de fusiones falsas aceptable |

Las métricas y umbrales se acuerdan antes de ejecutar un experimento. Propuesta para skills: cada extracción debe incluir evidencia verificable y abstenerse si no puede citarla. Comparar errores, latencia y costo, no solo si el resumen “suena bien”.

## Agentes acotados

Un futuro agente podría consultar la base, aplicar filtros y explicar resultados usando herramientas de lectura sobre los mismos casos de uso que la CLI y la UI. Un adaptador de herramientas con entradas/salidas tipadas deberá ser independiente de la presentación visual; la CLI seguirá funcionando sin un agente. La descripción de una oferta es contenido no confiable: frases como “ignora instrucciones” nunca habilitan comandos, nuevos destinos de red ni cambios de política.

Herramientas iniciales del agente: buscar ofertas y leer detalle. Límites: cantidad máxima de llamadas, presupuesto temporal, esquema de salida y evidencia por afirmación. Fuera de ese alcance: enviar CV, aplicar a puestos, contactar personas, subir datos personales o navegar URLs arbitrarias.

La adquisición debe seguir funcionando cuando el modelo falle. Los resultados AI se marcan como derivados, con versión y fuente. El usuario elige si compartir preferencias con un proveedor externo cuando esa integración se plantee.

## Conexión con ForeKast

El aprendizaje común es separar datos observados, reglas deterministas y explicación generada. Ambos proyectos pueden comparar contratos de enriquecimiento y evaluación, pero no hay necesidad de conectarlos en runtime ni compartir una base. Primero demostrar valor en cada dominio.

## I9

Perfiles, filtro de título y muestras fijas implementados sin modelos. Las etiquetas manuales y los límites de incertidumbre permiten evaluar futuros cambios; no se infiere relevancia a partir de favoritos. [Contrato](SAVED_SEARCHES.md).
