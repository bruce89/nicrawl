# Casos reales: de recolectar datos a construir un producto

Consulta: 2026-09-24. Se combinan aplicaciones conocidas, infraestructura pública y casos comerciales históricos. “Caso de éxito” aquí significa uso documentado que resolvió una necesidad; no implica rentabilidad auditada ni que toda la aplicación dependa exclusivamente de scraping.

## Google Search — descubrimiento e índice

Google describe un recorrido de rastreo, indexación y presentación de resultados. El crawler descubre páginas y descarga contenido; la indexación analiza y organiza; la búsqueda usa ese índice para responder consultas. No se rastrea toda la web desde cero cada vez que alguien busca. [Explicación oficial](https://developers.google.com/search/docs/fundamentals/how-search-works).

**Lección para nicrawl, interpretación nuestra:** separar recolección y consulta permite buscar offline y controlar la carga. La identidad y la detección de duplicados importan tanto como descargar. nicrawl aplica esa separación a una escala mínima; no replica la arquitectura distribuida de un buscador.

**Ejercicio:** explicar qué se perdería si `list --query python` descargara otra vez todas las ofertas en cada consulta. ¿Cómo cambia el tiempo de respuesta? ¿Qué significa entonces la hora mostrada?

## Indeed — agregación de ofertas

Indeed documenta la incorporación de ofertas desde páginas de empleo o ATS, además de otros mecanismos de publicación. Su flujo pide campos y URL válidos y contempla integraciones y feeds. Es evidencia de un producto de agregación con múltiples formas de adquisición; no demuestra que todas sus ofertas provengan de scraping HTML. [Guía de agregación de Indeed](https://www.indeed.com/help/employers/articles/what-is-aggregation?co=GB&hl=en).

**Lección para nicrawl, interpretación nuestra:** el usuario necesita una vacante reconocible y un camino al aviso original. El proveedor puede cambiar de HTML a feed sin cambiar la intención del producto. Un adaptador por fuente mantiene ese cambio localizado.

**Ejercicio:** diseñar dos entradas, HTML y JSON, que representen el mismo puesto. Señalar qué información alcanza para normalizarlas y cuál sigue siendo específica del origen. Este caso no autoriza usar Indeed como fuente de nicrawl.

## Common Crawl — recolección como infraestructura

Common Crawl describe un corpus recolectado periódicamente desde 2008, con páginas, metadatos y texto extraído. Su documentación de acceso distingue archivos WARC, WAT y WET. Es un ejemplo de separar adquisición de usos posteriores del dataset. [Overview](https://commoncrawl.org/overview), [acceso y formatos](https://commoncrawl.org/get-started).

**Lección para nicrawl, interpretación nuestra:** dato bruto, representación normalizada y salida de producto tienen funciones diferentes. Guardar el origen o su evidencia puede permitir reprocesar; también agrega costo de retención. Para nuestro alcance, fixtures sintéticas y metadatos suelen bastar, sin construir un archivo web completo.

**Ejercicio:** decidir qué se podría recalcular a partir de texto normalizado y qué requeriría la representación original. Explicar por qué un archivo histórico no garantiza que una oferta siga activa.

## Debunk EU — corpus para análisis de noticias

Un caso de Zyte publicado el **3 de diciembre de 2021** describe cómo Debunk EU utilizó extracción automatizada para reunir noticias y apoyar análisis de desinformación. El proveedor reportó alrededor de **1,5 millones de artículos por mes**. Es una cifra histórica declarada en un caso comercial, no una medición nuestra ni una afirmación de volumen actual. [Caso Zyte / Debunk EU](https://www.zyte.com/case-study/debunk-eu-scrapes-millions-of-news-articles-with-zyte/).

**Lección para nicrawl, interpretación nuestra:** la adquisición alimenta una actividad posterior que da valor. Recolectar no determina por sí mismo la veracidad de una noticia; reunir un aviso tampoco demuestra que una empresa contratará o que el puesto sigue abierto. Mantener esa distinción evita conclusiones exageradas.

**Ejercicio:** definir qué parte puede automatizar nicrawl y qué afirmaciones deberían reservarse para lectura humana del anuncio original.

## PriceEdge — datos para decisiones de pricing

Un caso de Zyte publicado el **27 de abril de 2021** presenta PriceEdge como una herramienta para comercios que reúne información competitiva y la convierte en análisis y recomendaciones de precios. La evidencia consultada es un relato del proveedor con declaraciones del cliente; no una auditoría independiente de beneficios. [Caso Zyte / PriceEdge](https://www.zyte.com/case-study/price-edge-the-repricing-platform-for-small-merchants/).

**Lección para nicrawl, interpretación nuestra:** un dato aislado tiene menos valor que un cambio relevante explicado en contexto. “Esta oferta cambió sus requisitos” puede ser más útil que volver a listar todo. El paralelo con precios tiene límites: empleo y productos usan identidades y reglas distintas.

**Ejercicio:** elegir tres cambios de una oferta que merezcan atención y tres modificaciones cosméticas que no. Diseñar una prueba para cada grupo.

## Patrones que podemos reutilizar

| Patrón | Valor al usuario | Primer equivalente en nicrawl |
| --- | --- | --- |
| Adquirir una vez, consultar muchas | Menor espera y carga | SQLite + búsqueda local |
| Mantener procedencia | Comprobar y profundizar | Fuente y enlace por oferta |
| Comparar versiones | Detectar novedades relevantes | Huella material + cambios |
| Separar adquisición de análisis | Cambiar una pieza sin rehacer todo | Adaptadores y dominio |
| Medir calidad | Evitar decisiones basadas en fallos silenciosos | Runs, rechazos y cobertura |

Una aplicación sostenible necesita una pregunta útil y mantenimiento de calidad. Scraping es un mecanismo de adquisición; el producto aparece cuando esos datos ayudan a decidir o ahorran trabajo.
