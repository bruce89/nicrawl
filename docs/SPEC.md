# SPEC v0.1 — nicrawl

Estado: MVP técnico I0–I3 y extensiones I4–I6 aprobados e implementados al 2026-09-28. El alcance futuro que sigue en este documento no está implementado por el solo hecho de estar especificado.

Actualización 2026-10-04: I12a añade el simulador SQLite y **I12b implementa un receptor
HTTP propio en otro proceso local**, con revisión, token, deduplicación y reconciliación.
El usuario eligió este camino y pidió dejar la evaluación de una integración real para
más adelante. Contrato: [HTTP_TRIAL](HTTP_TRIAL.md). No se habilitan envíos a terceros.

## Evaluación posterior I12c: integración real

**Pendiente; no implementada ni aprobada para enviar candidaturas.** Antes de elegir un
portal o ATS, comparar destinos concretos y registrar evidencia de:

1. API de postulación disponible para nuestro caso como candidato o acceso autorizado
   equivalente; una API para publicar ofertas/operar un ATS no acredita ese acceso.
2. Permisos, condiciones vigentes, credenciales, cuotas/costos y entorno de pruebas.
3. Campos y adjuntos requeridos, datos que saldrían del equipo y tratamiento/retención.
4. Garantías de idempotencia y reconciliación: cómo consultar un resultado incierto,
   cuánto dura una clave, qué ocurre con errores, cierre de vacantes y reintentos.
5. Revisión humana del contenido, destino y autorización de cada envío concreto.

Entregable de esa evaluación: una ficha comparativa con fuentes oficiales y una
recomendación fundada (integrar, postergar o mantener postulación manual). No se
presupone que LinkedIn u otro portal permita automatizar postulaciones. Si no existe
un mecanismo permitido, conservar el flujo manual apoyado por borradores y seguimiento.
La autorización de I12b no aprueba I12c ni el uso de credenciales o datos reales externos.

## Problema y propósito

Las ofertas están repartidas, cambian y se repiten. nicrawl ofrecerá una colección local consultable, con origen y antigüedad visibles. Permitirá responder: qué encontré, qué cambió desde la recolección anterior y dónde puedo leer el aviso original.

El proyecto debe poder estudiarse siguiendo una oferta desde bytes de entrada hasta una fila persistida y su presentación. Un resultado útil requiere extracción correcta, identidad estable y errores visibles; conseguir un HTTP 200 no alcanza.

## Supuestos de esta propuesta

- Uso personal y educativo, una persona, Windows y ejecución manual.
- CLI en español; código y nombres técnicos en inglés; texto de los avisos conservado en su idioma.
- Caso inicial: tecnología y trabajo remoto internacional, pendiente de preferencia del usuario.
- Fuente real inicial candidata: Remotive. El filtro local no garantiza elegibilidad desde Argentina: “remoto” puede exigir residencia o huso horario.
- Datos locales y enlaces al origen; sin cuentas, postulaciones automáticas ni publicación de una bolsa de empleo propia.
- No se promete cobertura de todo el mercado, disponibilidad permanente del proveedor ni detección instantánea.

## Requisitos funcionales

| ID | Capacidad | Resultado observable | Corte |
| --- | --- | --- | --- |
| F01 | Procesar HTML controlado | Una entrada sintética produce ofertas normalizadas y rechazos explicados | I1 |
| F02 | Recolectar fuente real configurada | La ejecución informa fuente, alcance, cantidades y estado final | I2 |
| F03 | Validar y normalizar | Campos ausentes permanecen desconocidos; registros inválidos no contaminan los válidos | I1–I2 |
| F04 | Persistir sin duplicar | Repetir la misma colección no crea otra oferta ni un cambio ficticio | I2 |
| F05 | Consultar sin conexión | Buscar texto, empresa y fuente sobre datos guardados | I3 |
| F06 | Consultar novedades | Ver altas y cambios de la última corrida que publicó datos | I3 |
| F07 | Exportar | JSON y CSV con fuente, URL y tiempos; misma selección que la búsqueda | I3 |
| F08 | Explicar frescura | Última observación por oferta y última ejecución por fuente son distinguibles | I2–I3 |
| F09 | Tolerar fallos | Un timeout, error de parser o fuente bloqueada conserva datos previos | I2 |
| F10 | Respetar política de origen | Presupuesto de red, atribución y habilitación por fuente verificables | I2 |
| F11 | Consultar detalle | Descripción como texto, restricciones geográficas y salario tal como constan | I3 |
| F12 | Diagnosticar una corrida | Ver errores clasificados, rechazos y si la colección fue completa | I2–I3 |
| F13 | Priorizar con reglas explícitas | Puntaje y contribuciones visibles, sin afirmar elegibilidad | I6 |
| F14 | Anotar revisión personal | Favorito, descarte y nota locales sobreviven a recolecciones | I6 |

Fuera del MVP original: navegador automatizado, crawling abierto, scheduler, nube, panel web, LLM, matching con CV, alertas externas y postulaciones. I4 incorporó una segunda fuente real e I6 agregó ranking/anotaciones locales. Los ejercicios no necesitan conectarse a una web externa.

## Recorridos de uso

**Aprender el pipeline.** Ejecutar una demo de HTML sintético, revisar tres ofertas y un rechazo, cambiar una clase CSS y observar el error. Explicar dónde termina el parser y dónde empieza la validación.

**Reunir ofertas reales.** Pedir una recolección manual, ver la política aplicable y el resultado, luego listar por palabra clave. Si la fuente está en cooldown, ver cuándo podrá intentarse y consultar lo guardado.

**Revisar cambios.** Ejecutar una segunda recolección elegible; ver cuántas ofertas son nuevas y cuáles cambiaron. Un aviso que no apareció no se etiqueta “cerrado”: solo se muestra la antigüedad de su última observación.

**Conservar una selección.** Exportar resultados a un archivo local. Cada fila mantiene el origen y permite volver a la publicación. La exportación no implica redistribución autorizada a terceros.

## Semántica de búsqueda

`--query` busca una subcadena normalizada mediante Unicode casefold en título, empresa y descripción. No es búsqueda semántica. `--company` aplica el mismo criterio sobre empresa; los filtros diferentes se combinan con AND. Se conserva el texto original. No se quitan acentos en v0.1.

`--location-text` busca sobre la restricción geográfica original; no responde “puedo postularme”. El orden predeterminado es `first_seen_at` descendente, desempate por `job_key`. Se indica “descubierta” porque la fecha de publicación puede ser desconocida. El límite por defecto será 20 y máximo 200 en pantalla; son decisiones del producto, no restricciones de la fuente.

## Requisitos de calidad

- No perder datos anteriores cuando una adquisición o una escritura falla.
- No ejecutar red al usar `list`, `show`, `changes` o `export`.
- Correlacionar cada registro con una fuente y cada publicación de datos con un run.
- Separar errores de uso, red, formato y almacenamiento.
- Tratar textos externos como datos: sin ejecutar HTML, secuencias de terminal, fórmulas de CSV o instrucciones incrustadas.
- Mantener un proceso escritor por base y un presupuesto de red por origen.
- Poder reproducir bugs de parsing con fixtures propios sin hacer descargas repetidas.

Consulta I3 medida con 10.000 ofertas sintéticas: máximo 0,357 s en cinco ejecuciones, sin arranque CLI ni renderizado. El presupuesto de adquisición sigue siendo 120 segundos por fuente. Ver metodología y límites en [VALIDATION](../VALIDATION.md).

## Cierre de MVP

Una persona puede instalar el proyecto siguiendo las instrucciones, procesar una demo sin red, recolectar la fuente elegida, buscar offline, comparar dos corridas controladas y exportar. Cada salida real muestra procedencia y antigüedad. Los escenarios Q01–Q22 de [QUALITY](QUALITY.md) tienen evidencia. Si la fuente no está disponible, la demo sigue funcionando y el MVP real permanece sin cerrar.
