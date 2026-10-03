# nicrawl — recolector de ofertas y laboratorio de Python

**Aplicación 0.10.0 · 30 de septiembre de 2026 · I0–I10 implementados.**

nicrawl reúne ofertas de Remotive y del board GitLab en Greenhouse, las valida y guarda en SQLite con identidad, tiempos de observación e historial de cambios. También conserva la demo HTML offline de I1. El objetivo paralelo es aprender Python y sistemas de datos desde experiencia en ingeniería de software/iOS.

## Probarlo

Para abrir la UI local:

```powershell
Set-Location C:\Bruze\nicrawl
.\.venv\Scripts\nicrawl.exe serve
```

Se abre `http://127.0.0.1:8765/`; Ctrl+C detiene el servidor. En otra terminal podés usar la CLI y la [API HTTP](docs/API.md), ambas sobre la misma base. [Guía I7](LearnDocs/15-local-ui-api.md).

Otros comandos:

```powershell
Set-Location C:\Bruze\nicrawl
.\.venv\Scripts\nicrawl.exe list --query python
.\.venv\Scripts\nicrawl.exe changes --run latest
.\.venv\Scripts\nicrawl.exe status --source remotive
.\.venv\Scripts\nicrawl.exe status --source greenhouse:gitlab
.\.venv\Scripts\nicrawl.exe lab-html --pages 2
.\.venv\Scripts\nicrawl.exe plan
.\.venv\Scripts\nicrawl.exe lab-concurrency
.\.venv\Scripts\nicrawl.exe rank --want Python --mode remote --limit 5
.\.venv\Scripts\nicrawl.exe mark '<JOB_KEY_COMPLETO>' --state favorite --note 'Revisar requisitos'
.\.venv\Scripts\nicrawl.exe collect --source remotive
.\.venv\Scripts\nicrawl.exe demo --scenario unicode
```

Remotive guardó **19 ofertas** en I2 y Greenhouse/GitLab **200** en I4, cada fuente con un HTTP 200, una petición y cero rechazos. La base contiene 219 ofertas consultables con `list --source all`. Está en `data/nicrawl.sqlite3` y no se incluye en los paquetes de entrega. `status` es solo lectura y no hace red. `collect` devuelve **4** durante el cooldown, sin descargar nada. La segunda invocación de Remotive en I2 quedó diferida localmente.

Política: una oportunidad cada 12 horas, máximo cuatro intentos en 24 horas y dos en un minuto, contados antes de enviar. Un retry transitorio como máximo. La cuota es por base local: mantener la misma base para ambas fuentes; otras copias no comparten automáticamente el historial de acceso.

Datos con origen y URL individual, sin republicación a terceros. Las ofertas de Remotive tienen la demora declarada en [su API](https://remotive.com/remote-jobs/api); una descarga reciente no garantiza que una vacante continúe abierta.

## Seguimiento de candidaturas (I10)

Abrí `nicrawl serve` y entrá en **Candidaturas**, o usá **Crear seguimiento** en el detalle de una oferta. También disponible por terminal con `nicrawl applications`. Historial, estados y referencias manuales, sin enviar postulaciones ni descargar URLs. [Guía I10](LearnDocs/18-application-tracking.md) · [Contrato](docs/APPLICATIONS.md).

## Búsquedas guardadas y pertinencia (I9)

```powershell
.\.venv\Scripts\nicrawl.exe saved run senior-uy
```

En esta instalación quedó configurado `senior-uy`: Senior Software Engineer, remoto desde Uruguay o presencial en Uruguay. En una copia nueva se crea siguiendo la [guía I9](LearnDocs/17-saved-searches-and-relevance.md). UI/CLI/API comparten perfiles y filtro por título; evaluación sobre una muestra fija con etiquetas humanas y diagnóstico por fuente. [Contrato](docs/SAVED_SEARCHES.md).

## Herramientas para agentes (I8)

```powershell
.\.tools\uv\Scripts\uv.exe --system-certs sync --locked --extra agents
.\.venv\Scripts\nicrawl.exe agent-demo
```

Demo MCP local con datos sintéticos, sin API key. `agent-demo --local` lee tu colección. [Guía I8](LearnDocs/16-agent-tools.md) · [Contrato y configuración](docs/AGENT_TOOLS.md).

## Aprender con esta versión

1. [I7: UI y API local](LearnDocs/15-local-ui-api.md): comparar navegador, HTTP y CLI sobre casos de uso compartidos.
2. [I6: ranking y estado personal](LearnDocs/13-ranking-and-personal-state.md) y [guía rápida de evaluación](LearnDocs/14-i6-evaluation-quick-guide.md): razones visibles, favoritos y comparación de órdenes.
3. [I5: concurrencia y planificación](LearnDocs/12-concurrency-and-planning.md): laboratorio `asyncio`, cancelación y lectura de cuotas.
4. [I4: dos fuentes y HTML externo](LearnDocs/11-second-source-html-lab.md): adaptadores, robots y paginación acotada.
5. [I3: búsqueda y exportación](LearnDocs/10-local-search-export.md): recorrido offline, historia y archivos seguros.
6. [I2: ingesta real y SQLite](LearnDocs/09-real-ingestion-sqlite.md): comandos, recorrido del código, SQL de lectura y laboratorios.
7. [I1: primer corte HTML](LearnDocs/08-first-working-slice.md): fixtures y extracción offline.
8. [LearnDocs](LearnDocs/README.md): fundamentos, analogías con iOS y casos reales.
9. [Arquitectura](docs/ARCHITECTURE.md), [modelo](docs/DATA_MODEL.md) y [ADR](docs/adr/README.md).
10. [Roadmap](docs/ROADMAP.md) y [fichas](docs/FIRST_ITERATIONS.md): I11+ pendiente de aprobación.

## Implementación y evidencia

Python 3.14.6, uv 0.12.19, Typer, Beautiful Soup, HTTPX 0.28.1, Pydantic 2.13.5 y sqlite3. Resolución completa en `uv.lock`. Instalación y controles en [IMPLEMENTATION](docs/IMPLEMENTATION.md).

**197 pruebas pasan**, sin red real en la suite. Ruff y mypy pasan. Se probaron publicación atómica, duplicados/conflictos, ausencia sin borrado, fallos HTTP, cooldown durable, límite de bytes, bloqueo entre procesos y recuperación tras crash. [Evidencia](VALIDATION.md).

I7 agrega UI y API locales con `serve`, sin duplicar reglas de negocio ni adquirir datos en segundo plano. I6 agrega `rank` con razones visibles, `mark` para notas/estados personales y esquema SQLite 2. I5 agrega `plan`, `collect-all` secuencial y `lab-concurrency` sin red real; cinco mediciones sintéticas dieron una mejora mediana de 1,48×. La publicación de ofertas permanece secuencial y no hay scheduler instalado. I4 agrega el board GitLab/Greenhouse y un laboratorio HTML externo que revisa robots.txt y extrae una muestra de dos páginas sin persistirla. I3 agrega list, show, changes y export JSON/CSV sin red. Filtros Unicode compartidos, historia por corrida, frescura y escritura atómica. Las consultas emiten JSON reutilizable desde PowerShell. La búsqueda sobre 10.000 ofertas sintéticas se midió en aproximadamente 0,36 s (sin arranque CLI). I8 ofrece herramientas MCP de lectura y una demo sin modelo; no hay agente autónomo ni publicaciones automáticas. Los ejercicios personales del usuario siguen pendientes; no se confunden con las pruebas técnicas.

## Referencia

| Documento | Uso |
| --- | --- |
| [SPEC](docs/SPEC.md) | Objetivo del MVP completo I0–I3 |
| [CLI](docs/CLI.md) | Disponible vs futuro |
| [Fuentes](docs/DATA_SOURCES.md) | Contratos y alcance de Remotive, Greenhouse y HTML de laboratorio |
| [Operación](docs/OPERATIONS.md) | Políticas y recuperación |
| [Calidad](docs/QUALITY.md) | Escenarios trazables |
| [Registro de aprobación](docs/OPEN_QUESTIONS.md) | I10 aprobado e implementado; I11+ pendiente |
| [Extensiones](docs/EXTENSIONS_AI.md) | Ideas posteriores |
| [Próximos cortes](docs/NEXT_STEPS.md) | I8 y camino hacia postulaciones asistidas |

El código y la documentación se versionan en [GitHub](https://github.com/bruce89/nicrawl). La entrega excluye bases, entornos, logs y archivos temporales.
