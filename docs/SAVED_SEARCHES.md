# I9 — búsquedas guardadas y evaluación de pertinencia

Aplicación 0.9.0, 2026-09-30. Aprobación: “Bien, vamos con I9”. Objetivo confirmado: **Senior Software Engineer, remoto desde Uruguay o presencial en Uruguay**. [Guía de uso y aprendizaje](../LearnDocs/17-saved-searches-and-relevance.md), [ADR-012](adr/012-saved-searches-evaluation.md).

## Qué está disponible

- Perfiles con nombre: filtros, modo list/rank, preferencias, límite y un objetivo escrito para la revisión humana. Guardar, listar, consultar, ejecutar, reemplazar explícitamente y eliminar desde CLI. UI permite guardar/reemplazar y cargar; API permite leer, ejecutar y guardar/reemplazar.
- `title_query`: subcadena sin distinguir mayúsculas, aplicada **solo al título**, combinada mediante AND con los filtros existentes. Disponible en list/rank/export, perfiles, UI/API y las herramientas MCP de búsqueda/ranking. No usa regex, sinónimos, tokens ni interpretación semántica.
- Una muestra fija con los primeros k de list y rank, razones, descripciones, URL/fecha y diagnóstico por fuente; plantilla de etiquetas y cálculo de precisión con incertidumbre explícita.

Los perfiles no agregan fuentes, no recolectan ni prueban elegibilidad. El objetivo `goal` es contexto humano, no un filtro ni una instrucción para un modelo. Una modalidad deseada puntúa; no excluye automáticamente otras modalidades.

## Perfil y persistencia

El archivo se deriva de `--db`: `data/nicrawl.sqlite3.searches.json`. Queda fuera de Git como el resto de `data/`. La base de ofertas no se modifica ni migra. Nombres: 1–48 caracteres, minúsculas ASCII/números/guion/guion bajo, empezando por letra o número. Máximo 100 perfiles y 1 MiB por libro. Filtros hasta 120 caracteres, objetivo hasta 240, límite 1–200; mismas restricciones de preferencias que el ranking.

Lecturas no crean archivos. Escrituras usan bloqueo de sistema operativo, temporal en el mismo directorio, flush/fsync y reemplazo atómico. Un error de validación o escritura conserva la versión anterior. Un archivo corrupto o de versión desconocida se rechaza; no se reinicializa silenciosamente. Cambiar o mover de base cambia el libro asociado; respaldar ambos si se desea conservar perfiles. La eliminación por nombre retira solo el perfil y no tiene papelera.

## CLI

```powershell
$nicrawl = '.\.venv\Scripts\nicrawl.exe'
& $nicrawl saved save senior-uy --view rank --query Software --title-query Engineer `
  --want Senior --want 'Software Engineer' `
  --goal 'Senior Software Engineer; remoto desde Uruguay o presencial en Uruguay.'
& $nicrawl saved list
& $nicrawl saved show senior-uy
& $nicrawl saved run senior-uy
# Para modificar: repetir saved save con TODA la configuración y --replace.
# Eliminar un perfil que vos ya no necesites: saved delete <nombre>
```

`save --replace` reemplaza el perfil completo, no fusiona campos. `saved run` devuelve el mismo JSON que list o rank. `source` admite all/vacío, remotive o greenhouse:gitlab. La UI representa términos como una lista separada por comas; para términos literales que contengan comas usar CLI, sin regrabar ese perfil desde la UI.

## API local

| Método/ruta | Resultado |
| --- | --- |
| GET `/api/searches` | Libro de perfiles |
| GET `/api/searches/<nombre>` | Perfil completo |
| GET `/api/searches/<nombre>/run` | Reporte list o rank |
| PUT `/api/searches` | Guardar con cuerpo `{"profile": {...}, "replace": false}` |

PUT exige JSON, Host local y Origin local si se informa; máximo 8192 bytes. Errores de perfil/nombre/reemplazo devuelven 400. La UI llama estas mismas operaciones. No se exponen lectura de archivos arbitrarios, creación de muestras ni etiquetas por HTTP; esas tareas se hacen desde la terminal. Las herramientas MCP mantienen solo las tres lecturas de I8 y no exportan perfiles ni agregan herramientas de escritura.

## Comparación reproducible

`saved snapshot` usa la API de backup SQLite para copiar una instantánea consistente a un directorio temporal. Consulta y puntúa esa copia con el mismo reloj, preferencias y filtros. Incluye descartadas en **ambos** órdenes para que las diferencias provengan del orden y no de selecciones distintas. La copia temporal puede contener datos personales; se elimina al terminar y la proyección JSON no exporta notas ni estados.

La muestra exportada contiene hasta 2k ofertas únicas (k entre 1 y 20), órdenes, score/razones, fecha, versión de reglas, perfil y contadores por fuente. El límite de salida se verifica antes de publicar; la lectura admite hasta 16 MiB. Las consultas y el backup siguen recorriendo la colección completa: no hay promesa de rendimiento para bases enormes. Los archivos de salida nuevos se publican de forma exclusiva; si existen, se rechaza la operación.

`snapshot_id` es SHA-256 de la muestra normalizada. Detecta edición accidental y vincula las etiquetas; no es una firma contra manipulación intencional. `saved evaluate` lee exclusivamente muestra y etiquetas, sin consultar la base actual. El perfil o la colección pueden cambiar después sin alterar la evaluación. Para otro experimento, generar otros archivos e identidad.

Etiquetas por clave: `pending`, `unknown`, `useful`, `not_useful`, más `reason` opcional. Se exige exactamente una fila por oferta, sin duplicados ni claves ajenas y con la misma identidad. Los favoritos/notas no se convierten en etiquetas automáticamente.

`precision` = útiles/n, con n=min(k,candidatos); queda null si n=0 o hay pending/unknown. `precision_lower` supone que todos los no resueltos son negativos; `precision_upper`, positivos. `precision_delta` solo existe cuando ambos órdenes están resueltos. Las útiles exclusivas de un orden ayudan a detectar omisiones dentro de la muestra; no estiman recall sobre todo el universo laboral.

## Pertinencia y decisiones sobre fuentes

El perfil inicial combina `query=Software`, `title_query=Engineer`, want Senior/Software Engineer, sin restricción literal de país ni modalidad. Es un punto de partida amplio: evita excluir LATAM/Worldwide, pero exige revisar país de contratación, especialidad, seniority y lugar de trabajo. “Presencial desde Uruguay” significa un puesto ubicado en Uruguay; compartir huso horario no demuestra contratación admitida.

La instantánea local del 2026-09-30 contiene 102 candidatos: 98 GitLab y 4 Remotive. La unión de top-10 tiene 20 ofertas, todas GitLab; no permite medir precisión de Remotive. La búsqueda previa sin filtro de título devolvía 212 candidatos por coincidencias también en descripciones. Es una reducción de ruido potencial, **no una mejora de relevancia demostrada**. Varias ofertas del top indican UK/Canadá/US u otros países: el perfil no corrige la cobertura geográfica de las fuentes.

Siguiente decisión basada en uso: etiquetar la muestra, separar rechazos por especialidad/ubicación, y evaluar Remotive con un perfil específico por fuente si su muestra sigue vacía. Elegir luego un board que publique ingeniería senior y contratación desde UY/LATAM o vacantes presenciales en Uruguay. Antes de habilitarlo: confirmar acceso permitido, identidad, paginación, cuota, frescura, campos geográficos y una muestra representativa. Este corte entrega el diagnóstico y herramientas de evaluación; no instala un nuevo board ni declara que la colección ya sea suficiente.
