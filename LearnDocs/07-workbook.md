# Bitácora de aprendizaje y glosario

Plantilla vacía para completar durante las iteraciones. No representa trabajo ya ejecutado.

## Registro de sesión

```text
Fecha y corte:
Pregunta que quiero responder:
Hipótesis antes de ejecutar:
Entrada / escenario:
Recorrido esperado:
Comando o prueba real:
Resultado observado:
Evidencia (log, test, diff o captura):
Explicación de la diferencia:
Qué responsabilidad entendí mejor:
Cambio que puedo hacer sin ayuda:
Pregunta que queda abierta:
```

## Mapa del código, a completar como ejercicio

I0 + I1 ya existen. Usar [el recorrido real](08-first-working-slice.md) para completar las filas aplicables; adquisición HTTP y persistencia ya tienen su [guía I2](09-real-ingestion-sqlite.md).

| Paso | Archivo y símbolo reales | Entrada / salida | Error que maneja |
| --- | --- | --- | --- |
| Parsear argumentos | Pendiente | Pendiente | Pendiente |
| Verificar política | Pendiente | Pendiente | Pendiente |
| Adquirir | Pendiente | Pendiente | Pendiente |
| Extraer | Pendiente | Pendiente | Pendiente |
| Normalizar | Pendiente | Pendiente | Pendiente |
| Publicar | Pendiente | Pendiente | Pendiente |
| Consultar/exportar | Pendiente | Pendiente | Pendiente |

## Glosario aplicado

| Término | Significado en este proyecto |
| --- | --- |
| Scraper | Extrae campos desde una representación como HTML |
| Crawler | Descubre y recorre documentos dentro de un ámbito |
| Adapter | Convierte una fuente concreta al contrato de nicrawl |
| DTO | Representación del formato externo antes del dominio |
| Fixture | Entrada controlada con resultado esperado conocido |
| DOM | Árbol de elementos de un documento |
| Selector | Regla que identifica nodos dentro del documento |
| Scope / ámbito | Conjunto definido por fuente, ruta y filtros de adquisición |
| Coverage | Evidencia de si se recorrió completamente ese ámbito |
| Idempotencia | Repetir datos no crea duplicados ni cambios materiales falsos |
| Upsert | Insertar o actualizar según una clave estable |
| Transacción | Grupo de cambios que se confirma o revierte como unidad |
| Provenance | Origen y recorrido que permiten explicar un dato |
| Drift / deriva | Cambio de formato o significado que afecta extracción |
| Backoff | Espera antes de repetir un intento transitorio |
| Cooldown | Periodo durable durante el que no se vuelve a consultar |
| Rate limit | Restricción de frecuencia de solicitudes |
| Backpressure | Control de producción para no desbordar al consumidor |
| Grounding | Vincular una conclusión a evidencia consultable |
| Baseline | Método simple contra el que comparar una mejora |

## Preguntas de repaso

1. ¿Qué distingue un parser de un crawler?
2. ¿Por qué un HTTP 200 puede ser un fracaso de recolección?
3. ¿Qué es obligatorio para reconocer una oferta y qué puede faltar?
4. ¿Cómo se evita reconsultar una fuente demasiado pronto tras reiniciar?
5. ¿Cuándo avanza `last_seen_at` y cuándo `last_changed_at`?
6. ¿Qué demuestra una corrida completa y qué no demuestra?
7. ¿Por qué no fusionar por título y empresa sin más evidencia?
8. ¿Qué prueba evidencia un rollback correcto?
9. ¿Qué parte del sistema cambia al agregar otra presentación?
10. ¿Qué mejoraría async en nuestro caso concreto?
11. ¿Qué resultado debe producir un modelo cuando falta evidencia?
12. ¿Qué dato usarías para comprobar que nicrawl te ahorra trabajo?

## Registro de decisiones personales

Anotar una alternativa que habrías elegido, su beneficio, su costo y qué evidencia te haría cambiar de opinión. Comparar después con los [ADR](../docs/adr/README.md). El objetivo es desarrollar criterio propio, no memorizar el stack propuesto.
