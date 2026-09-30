# Fuentes primarias consultadas

Fecha de consulta inicial: **2026-09-24**. El 2026-09-25 también se revisaron [instalación de uv](https://docs.astral.sh/uv/getting-started/installation/), [build backend](https://docs.astral.sh/uv/concepts/build-backend/) y [opción version en Typer](https://typer.tiangolo.com/tutorial/options/version/) durante I0 + I1; las versiones se resolvieron desde PyPI y se verificaron localmente. La investigación original fue documental; la validación posterior del stack I0 + I1 está en [VALIDATION](../VALIDATION.md). En I2 se volvieron a consultar las páginas oficiales de Remotive, HTTPX y Pydantic y se hizo una petición real al API; eso verifica esa corrida, no disponibilidad futura. Los enlaces apoyan hechos del proveedor; los límites, arquitectura y roadmap son decisiones de nicrawl. Revalidar condiciones al integrar una fuente.

## Fuentes de datos y protocolos

| Referencia | Qué sustenta | Revisión siguiente |
| --- | --- | --- |
| [Remotive: términos de API](https://remotive.com/remote-jobs/api) | Atribución, restricciones y demora declarada | I2 y antes de compartir datos |
| [Remotive: contrato oficial](https://github.com/remotive-com/remote-jobs-api) | Endpoint, parámetros, campos y recomendación de frecuencia | I2 |
| [Greenhouse Job Board](https://docs.greenhouse.io/job-board.html) | Lectura de boards e información de posts | Antes de segundo adaptador |
| [Scrape This Site](https://www.scrapethissite.com/) | Existencia de sandbox educativo | Antes de laboratorio externo |
| [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html) | Robots Exclusion Protocol | Antes de HTML externo |
| [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) | Semántica HTTP y Retry-After | Al implementar transporte |

## Python y herramientas

| Referencia | Uso |
| --- | --- |
| [Python oficial](https://docs.python.org/3/) | Rama estable, lenguaje y biblioteca |
| [Typing](https://docs.python.org/3.14/library/typing.html) | Anotaciones y contratos estructurales |
| [Asyncio](https://docs.python.org/3.14/library/asyncio-task.html) | Tareas, cancelación y grupos |
| [sqlite3](https://docs.python.org/3.14/library/sqlite3.html) | Conexiones, parámetros y transacciones |
| [uv: proyectos](https://docs.astral.sh/uv/guides/projects/) | Entorno, declaración y lock |
| [Typer](https://typer.tiangolo.com/) | CLI declarativa |
| [HTTPX](https://www.python-httpx.org/) | Cliente HTTP sync/async |
| [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/) | Límites por fase de I/O |
| [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) | Extracción HTML y selectores |
| [Pydantic](https://pydantic.dev/docs/validation/latest/concepts/models/) | Validación/modelos de entrada |
| [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) | Datos y recursos controlados en pruebas |
| [Ruff linter](https://docs.astral.sh/ruff/linter/) y [formatter](https://docs.astral.sh/ruff/formatter/) | Feedback de calidad distinto de tipado |
| [Mypy](https://mypy.readthedocs.io/en/stable/) | Verificación estática candidata; revisar configuración en I0 |
| [Scrapy](https://docs.scrapy.org/en/latest/intro/overview.html) | Alternativa si crece el crawling |
| [Playwright Python](https://playwright.dev/python/docs/intro) | Alternativa si una fuente requiere navegador |

## Casos de producto

| Fuente | Naturaleza de evidencia |
| --- | --- |
| [Google: cómo funciona Search](https://developers.google.com/search/docs/fundamentals/how-search-works) | Explicación del operador del buscador |
| [Indeed: agregación](https://www.indeed.com/help/employers/articles/what-is-aggregation?co=GB&hl=en) | Flujo documentado de incorporación de ofertas |
| [Common Crawl: overview](https://commoncrawl.org/overview) | Descripción del corpus por su organización |
| [Common Crawl: acceso](https://commoncrawl.org/get-started) | Formatos y acceso al dataset |
| [Zyte / Debunk EU](https://www.zyte.com/case-study/debunk-eu-scrapes-millions-of-news-articles-with-zyte/) | Caso comercial publicado el 2021-12-03; cifras históricas declaradas por proveedor |
| [Zyte / PriceEdge](https://www.zyte.com/case-study/price-edge-the-repricing-platform-for-small-merchants/) | Caso comercial publicado el 2021-04-27; no auditoría independiente |

La interpretación educativa de estos casos está en [LearnDocs: casos reales](../LearnDocs/06-real-world-cases.md). No se extrapolan cifras históricas como resultados actuales ni como retorno esperado de nicrawl.
