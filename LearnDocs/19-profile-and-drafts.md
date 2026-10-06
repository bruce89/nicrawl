# I11 — práctica rápida: CV y borradores

Tiempo estimado: 20–30 minutos. Usá una copia sintética o redactada del CV durante la práctica. No pegues información sensible en terminales compartidas ni subas el archivo de datos: el CV queda sin cifrar en `<base>.applications.sqlite3`.

## Qué se aprende

Seguir un dato desde una cita literal del CV hasta un borrador vinculado a una candidatura. Las capas son: CLI/API/UI → caso de uso (`applications`) → SQLite local. La UI no contiene lógica de persistencia. El borrador guarda el ID de perfil y revisión; no cambia el CV previo ni envía nada.

## Recorrido sugerido

1. Creá una candidatura de práctica desde un aviso ficticio:

```powershell
nicrawl applications add --url https://example.org/jobs/42 --title "Senior Engineer" --company "Empresa ficticia"
```

Copiá el UUID que devuelve. Si vas a practicar sobre tu base real, omití este paso y usá una candidatura existente.

2. Prepará `cv-demo.txt` con texto ficticio y guardá una cita que exista exactamente en el archivo. Ejemplo de contenido ficticio: `Lideré un equipo de cuatro personas durante una migración a Python.`

```powershell
nicrawl profile save --cv-file .\cv-demo.txt --label "Práctica I11" --statement "Lideré un equipo de cuatro personas" --evidence "Lideré un equipo de cuatro personas durante una migración a Python."
```

El ID E01 pertenece a esa versión de perfil. La validación comprueba substring literal, no la verdad de la afirmación.

3. Creá el borrador con el UUID de candidatura:

```powershell
nicrawl applications draft create <UUID> --profile-version 1 --claim-id E01 --question "¿Qué experiencia con sistemas distribuidos solicita el aviso?" --opening "Escribí aquí una apertura propia para revisar."
```

La vista previa devuelve el ID de borrador y su versión. Si no querés usar un claim, omití `--claim-id`. No ingreses respuestas a preguntas hasta confirmar el dato en tu perfil y el aviso.

4. Volvé a consultar y exportá a un destino nuevo:

```powershell
nicrawl applications draft show <BORRADOR-ID>
nicrawl applications draft list <UUID>
nicrawl applications draft export <BORRADOR-ID> --output .\postulacion-demo.md
```

La exportación no sobrescribe un archivo. Elegí otro nombre si ya existe.

## Cómo revisar el resultado

Comprobá que la cita aparezca completa en el CV de esa versión y que el aviso realmente la requiera. Preguntate: ¿la frase afirma algo que el CV respalda?, ¿qué dato falta?, ¿la pregunta sigue sin responder?, ¿el borrador corresponde al aviso correcto? La etiqueta “Enviada” de I10 registra tu propio estado y `mark` de I6 registra favorito/nota; ninguno equivale a esta revisión.

Para una nueva versión, repetí `profile save` con el CV revisado y sus citas nuevas; al crear/revisar un borrador elegí su versión. No se sobrescribe un borrador anterior: se crea una revisión con `--expected-version`.

## Errores frecuentes

- **La evidencia debe ser cita literal:** verificá espacios, puntuación y saltos de línea. La cita debe estar completa dentro del texto almacenado.
- **Afirmación fuera de perfil:** `E01` cambia de significado entre versiones; elegí el ID que devuelve esa versión.
- **Versión desactualizada al revisar:** volvé a `draft show`, compará y usá la versión actual como `--expected-version`.
- **Destino ya existe:** la exportación se niega a reemplazarlo; elegí otro nombre.
- **No aparece la práctica:** los comandos globales aceptan `--db` antes del subcomando. Usá la misma base tanto al crear la candidatura como al guardar perfil/borrador.

La guía de contrato está en [PROFILE_DRAFTS](../docs/PROFILE_DRAFTS.md); la hoja de ruta completa está en [LearnDocs/01](01-learning-roadmap.md).
