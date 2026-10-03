# Entorno e implementación — I0 a I10

Verificado en Windows el 2026-09-30. Aplicación **0.10.0**. Python 3.14.6 ya estaba instalado. uv está aislado dentro del proyecto; no se modificó PATH ni se instalaron dependencias globales.

## Preparar una copia limpia

Requisito: Python 3.14.6 disponible mediante `py -3.14`, con venv/pip. En la raíz del proyecto:

```powershell
py -3.14 -m venv .tools\uv
.\.tools\uv\Scripts\python.exe -m pip install uv==0.12.19
$uv = '.\.tools\uv\Scripts\uv.exe'
& $uv --system-certs sync --locked
.\.venv\Scripts\nicrawl.exe --help
```

Bootstrap necesita acceso a paquetes; la demo instalada es offline. `--system-certs` permitió usar el almacén TLS del sistema en esta máquina sin desactivar la validación de certificados. [Instalación de uv](https://docs.astral.sh/uv/getting-started/installation/).

Python se fija en `.python-version`, uv en `tool.uv.required-version`; el backend se fija en build-system. `pyproject.toml` declara rangos y `uv.lock` registra versiones resueltas. No editar el lock manualmente. Con paquetes ya cacheados, sincronizar con `--offline`.

## Versiones verificadas

| Herramienta | Versión |
| --- | --- |
| Python | 3.14.6 |
| uv / uv_build | 0.12.19 |
| Typer / Beautiful Soup | 0.27.2 / 4.15.0 |
| HTTPX / Pydantic | 0.28.1 / 2.13.5 |
| pytest / Ruff / mypy | 9.1.1 / 0.16.9 / 2.3.1 |

SQLite se usa mediante sqlite3 de Python. I7 ofrece una UI opcional en navegador mediante un servidor HTTP local; los comandos de terminal no lo requieren.

## Comandos de uso

```powershell
Set-Location C:\Bruze\nicrawl
.\.venv\Scripts\nicrawl.exe --version
.\.venv\Scripts\nicrawl.exe demo --scenario unicode
.\.venv\Scripts\nicrawl.exe status --source remotive
.\.venv\Scripts\nicrawl.exe collect --source remotive
.\.venv\Scripts\nicrawl.exe status --source greenhouse:gitlab
.\.venv\Scripts\nicrawl.exe list --source all --limit 5
.\.venv\Scripts\nicrawl.exe lab-html --pages 2
```

La demo no toca SQLite ni red. `collect` hace red y crea la base si hace falta; `lab-html` hace red solo al sandbox y no toca la base. `status` abre solo lectura y no crea una base faltante. `--db` es global, antes del subcomando; las rutas relativas se resuelven contra el directorio actual. Usar siempre la misma base para ambas fuentes reales: copias independientes no comparten cuotas.

Salida: 0 éxito, 1 fallo, 2 argumentos/configuración, 3 parcial, 4 diferido, 130 interrupción controlada. `demo basic` incluye intencionalmente un rechazo y devuelve 3. collect dentro de cooldown devuelve 4 sin descargar. La salida redirigida usa UTF-8.

También se puede usar `& $uv run --locked nicrawl ...`. uv run puede sincronizar y reemplazar ejecutables; no usarlo en paralelo con otro proceso que esté usando/modificando el entorno en Windows. Tras sincronizar, usar `.venv` directamente o `--no-sync` para ejecuciones paralelas.

## Verificaciones y build

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m mypy src/nicrawl
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\ruff.exe format --check src tests
& $uv build --offline
```

La suite tiene 129 casos, todos sin red real. Build produce wheel y sdist en dist; los recursos HTML se incluyen en el paquete. La validación de distribución usa un entorno separado y ejecución desde otra carpeta. Resultados en [VALIDATION](../VALIDATION.md).

El entorno de la máquina es `C:\Bruze\nicrawl\.venv`. No usar rutas personales dentro del código. Tests usan bases temporales; la base real en `data/` no se exporta ni se incluye en los paquetes. Tampoco se distribuyen `.tools`, `.venv`, caches, `work` o `dist` como parte de los fuentes.

## Arquitectura implementada

Módulos pequeños: domain, collection, acquisition, storage, locking, CLI, dos adaptadores reales (Remotive y Greenhouse/GitLab), la demo HTML y el laboratorio externo independiente. El esquema 2 se crea o migra transaccionalmente y se valida mediante application_id/user_version. Los attempts se confirman antes de enviar; las ofertas/cambios/observaciones se publican juntos después de validar. El bloqueo lo mantiene el SO y se libera al morir el proceso.

La configuración actual habilita dos fuentes fijas (Remotive/software-dev y Greenhouse/GitLab), con políticas fijas por fuente en código. `nicrawl.toml`, scheduler instalado, logs rotados y purga automática siguen fuera de este corte. No hay flag force para saltar cuotas ni desbloqueo automático de fuentes detenidas.

I3 implementa queries.py y exporting.py: consultas en snapshot read-only, filtros compartidos, historial y archivos atómicos. Guía [I3](../LearnDocs/10-local-search-export.md). I4 agrega [greenhouse.py](../src/nicrawl/sources/greenhouse.py) y [html_lab.py](../src/nicrawl/html_lab.py); guía [I4](../LearnDocs/11-second-source-html-lab.md). I5 agrega planning.py y concurrency_lab.py: plan local, collect-all secuencial y comparación asíncrona sintética. Guía [I5](../LearnDocs/12-concurrency-and-planning.md). I6 agrega [personal.py](../src/nicrawl/personal.py), `rank` y `mark`, con esquema 2 y guía [I6](../LearnDocs/13-ranking-and-personal-state.md). I7 agrega [server.py](../src/nicrawl/server.py), UI local y [API](API.md), con [guía I7](../LearnDocs/15-local-ui-api.md). I8 agrega herramientas MCP opcionales; I11+ pendiente de aprobación. Repositorio Git: [bruce89/nicrawl](https://github.com/bruce89/nicrawl).

## Extra de agentes

`uv sync --locked --extra agents` instala MCP 2.2.0 además del entorno base. Usar ese extra para ejecutar toda la suite y mypy sobre el adaptador opcional. Sin extra, las pruebas MCP se omiten y la CLI básica sigue disponible. [Instalación, demo y configuración](AGENT_TOOLS.md).

## I9

No agrega dependencias ni migra SQLite. Los perfiles viven en `<base>.searches.json`. La demo de evaluación se opera desde `saved`; [guía](../LearnDocs/17-saved-searches-and-relevance.md). La muestra local y etiquetas quedan en data y no forman parte del paquete distribuido.

## I10

Sin dependencias nuevas ni migración de la colección. SQLite personal creado en la primera escritura de candidatura; las lecturas sin archivo no lo crean. Respaldar `<base>.applications.sqlite3` junto con los demás datos locales. [Guía](../LearnDocs/18-application-tracking.md).
