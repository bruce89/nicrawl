# ADR-001 — Python y toolchain

Estado: aceptado e implementado (I0–I2) · 2026-09-25. Python 3.14.6, uv, Typer, Beautiful Soup, HTTPX, Pydantic y SQLite verificados. Detalles exactos en [IMPLEMENTATION](../IMPLEMENTATION.md).

## Contexto y decisión

Se busca un sistema pequeño que permita aprender Python actual, datos y arquitectura. I0 + I1 incorporaron Python 3.14.6 y un paquete con layout `src`, entorno/lock mediante uv, CLI Typer y Beautiful Soup para HTML. pytest, Ruff y mypy proporcionan feedback durante desarrollo. Las versiones exactas quedaron fijadas y verificadas en I0. I2 incorporó HTTPX, validación Pydantic y SQLite mediante biblioteca estándar.

Estas herramientas cubren fronteras concretas. [uv](https://docs.astral.sh/uv/guides/projects/), [Typer](https://typer.tiangolo.com/), [HTTPX](https://www.python-httpx.org/), [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) y [Pydantic](https://pydantic.dev/docs/validation/latest/concepts/models/) documentan esas capacidades. El conjunto y su introducción gradual son decisiones propias del proyecto.

## Alternativas

- `venv` + pip: suficientes y útiles para aprender fundamentos; uv concentra resolución y lock. LearnDocs explica el entorno para no esconder el concepto bajo una herramienta.
- argparse: elimina una dependencia; Typer aporta una CLI declarada desde tipos. Si el paquete complica compatibilidad o enseñanza, argparse es alternativa razonable.
- requests: opción válida para HTTP síncrono; HTTPX facilita evaluar API sync/async con una familia de cliente, sin prometer migración automática.
- Scrapy: framework apropiado para crawling con infraestructura recurrente; en un único feed añade conceptos antes de necesitarlos. [Scrapy](https://docs.scrapy.org/en/latest/intro/overview.html).
- Playwright: adecuado cuando se necesita navegador; se reserva para una fuente dependiente de JS que justifique ese costo. [Playwright Python](https://playwright.dev/python/docs/intro).

## Consecuencias y validación

Hay más dependencias que en un script mínimo, pero cada una llega con un requisito concreto. Mantener dominio con dataclasses/enums y funciones; Pydantic no obliga a usar sus modelos en todas las capas. Ruff no reemplaza un verificador de tipos y las anotaciones Python no validan por sí mismas entradas externas.

Validar instalación bloqueada, comandos reales en Windows, ayuda de CLI y tests del corte. Reabrir por incompatibilidad comprobada o porque una herramienta añade más complejidad que la tarea que resuelve.
