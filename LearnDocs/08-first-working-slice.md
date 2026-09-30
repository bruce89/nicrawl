# Primer corte ejecutable — I0 + I1

Implementado y verificado el 2026-09-25. La aplicación es una demo de extracción HTML local: no descarga ofertas reales ni crea una base. Tus ejercicios de aprendizaje siguen pendientes; las pruebas técnicas no los reemplazan.

## Probarlo ahora

Desde PowerShell, en la instalación preparada:

```powershell
Set-Location C:\Bruze\nicrawl
.\.venv\Scripts\nicrawl.exe --help
.\.venv\Scripts\nicrawl.exe demo --scenario basic
$LASTEXITCODE
```

Vas a ver tres ofertas ficticias y un rechazo por título ausente. El código **3 es deliberado**: informa un resultado parcial. No es un fallo de instalación. Para un escenario enteramente válido:

```powershell
.\.venv\Scripts\nicrawl.exe demo --scenario unicode
```

## Escenarios y predicciones

| Escenario | Entrada | Resultado esperado | Código |
| --- | --- | --- | --- |
| `basic` | 4 tarjetas, una sin título | 3 ofertas + rechazo explicado | 3 |
| `optional-fields` | 1 tarjeta con campos mínimos | Opcionales como “No informado” | 0 |
| `unicode` | Entidades, acentos, C++, restricciones y script ficticio | Texto legible, sin script en descripción | 0 |
| `empty` | 0 tarjetas y marcador de vacío | Lista vacía legítima | 0 |
| `broken-layout` | 1 tarjeta cambia `job` por `vacancy` | Error estructural, sin resultado de éxito | 1 |

Los recursos viven en [src/nicrawl/fixtures](../src/nicrawl/fixtures/basic.html). Son originales, ficticios y se instalan con el paquete. La demo acepta un nombre de escenario, nunca una URL.

## Seguir `demo-01` en el código real

1. [pyproject.toml](../pyproject.toml): el entrypoint `nicrawl` apunta a `nicrawl.cli:run`.
2. [cli.py](../src/nicrawl/cli.py): `run` prepara salida UTF-8; Typer despacha a `demo`.
3. [demo_html.py](../src/nicrawl/sources/demo_html.py): `load_scenario` lee el recurso mediante `importlib.resources`, independientemente del directorio actual.
4. En el mismo archivo, `parse_jobs` verifica página, lista, cantidad y marcador vacío; luego convierte cada tarjeta en `JobCandidate`.
5. [domain.py](../src/nicrawl/domain.py): `normalize_job` exige ID/título/empresa/enlace y normaliza sin inventar opcionales; devuelve `JobDraft`.
6. El parser devuelve `ExtractionResult` con tuplas de ofertas y rechazos. La CLI muestra datos en stdout y advertencias en stderr.

Breakpoints sugeridos: construcción de `candidate`, llamada a `normalize_job`, `except InvalidCandidate` y bucle de presentación. Observar primero tipos y valores, después avanzar paso a paso.

## Contrato de las fixtures

Una página declara un único `main[data-page="jobs"]`, `data-count` y una lista `[data-job-list]`. Las tarjetas son hijos directos `article.job`. Una lista vacía necesita `data-count="0"` y un único marcador `data-empty="true"`.

El contador es una decisión del laboratorio que permite detectar un selector roto incluso si todavía extrae algunas tarjetas. No se presupone que una web externa tenga ese atributo ni que todos los scrapers puedan garantizar cobertura con esta técnica. Cada fuente futura necesita su propio contrato.

Los campos se buscan dentro de cada tarjeta para evitar cruzar título de una con empresa de otra. La extracción preserva puntuación inline y separa bloques antes de normalizar espacios. No renderiza JavaScript.

## Tres ejercicios para esta versión

**1. Cambiar una observación.** Editar la empresa de `demo-01` en `basic.html`. Predecir cuántos válidos/rechazos habrá y qué campo cambiará. Ejecutar y registrar la evidencia. Restaurar el texto al terminar o actualizar deliberadamente la prueba que depende de él.

**2. Romper la estructura.** Cambiar una sola clase `job` a `vacancy` en una copia del escenario y llamar a `parse_jobs` desde un test. Antes de ejecutar, explicar por qué debe fallar toda la página. La prueba `test_structure_failures_never_look_like_successful_empty_collection` muestra variaciones.

**3. Agregar un campo opcional.** Proponer `employment_type_raw`, definir su significado y añadirlo a candidato/modelo, parser, fixture y presentación. Escribir un caso con valor y otro sin valor. Esta es una tarea para vos: el campo todavía no está implementado en I1.

## Leer las pruebas como especificación

- [test_demo_html.py](../tests/test_demo_html.py): Q02–Q05, ámbitos de selectores, puntuación, cambios parciales de estructura.
- [test_domain.py](../tests/test_domain.py): normalización, obligatorios y URLs inválidas.
- [test_cli.py](../tests/test_cli.py): códigos, canales de salida, directorio independiente y texto no interpretado.
- [conftest.py](../tests/conftest.py): bloquea conexiones socket durante las pruebas. Una futura regresión que intente conectarse falla.

Para ejecutar:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m mypy src/nicrawl
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\ruff.exe format --check src tests
```

## Continuación en I2 (ya implementada)

HTTP, validación de una API con Pydantic, IDs duplicados/conflictivos, fechas, hash de contenido, SQLite, runs, cuotas y retries. No deducir que esas capacidades existen por encontrar su diseño en `docs/`. I2 ya fue aprobado e implementado sobre Remotive; esta página conserva el alcance histórico de I1. Ver [la guía siguiente](09-real-ingestion-sqlite.md).

Anotá una primera sesión en [la bitácora](07-workbook.md): explicar por qué `basic` termina con código 3 y `broken-layout` con 1 es un buen punto de partida.
