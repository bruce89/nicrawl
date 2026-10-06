# I11 — perfiles y borradores locales

I11 prepara material para revisar una candidatura. El usuario aporta el CV como texto, lo versiona y registra afirmaciones con una cita literal del CV. Cada borrador queda asociado a una candidatura y a una versión concreta del perfil; sus revisiones anteriores se conservan.

## Contrato de privacidad y evidencia

El CV y sus afirmaciones viven en `<base>.applications.sqlite3`, separado de las ofertas y excluido de Git por estar bajo `data/`. El archivo no está cifrado: protegé el equipo, respaldá conscientemente y no uses una base compartida. `GET /api/profiles/<version>` y `profile show --include-cv` devuelven el texto íntegro; el listado no lo devuelve. La API es loopback y no hay herramientas MCP de escritura ni acceso de agentes a este almacén.

Las citas deben ser substrings exactos del CV de esa misma versión. Esta comprobación solo acredita que el texto citado aparece en el archivo; no verifica que una afirmación sea verdadera, actual, completa ni pertinente. La apertura opcional la escribe el usuario y se etiqueta como tal. Las preguntas quedan pendientes; no se responden. El generador no usa un LLM ni inventa datos. Revisá puesto, empresa, citas y preguntas antes de copiar el resultado.

No se envía ninguna candidatura, no se suben CV/adjuntos y no se automatiza navegador. Descargar Markdown desde la UI crea un archivo local; la CLI exporta con creación exclusiva y falla si el destino ya existe.

## Esquema y ciclo de vida

La base personal pasa de esquema 1 a 2 en la primera escritura compatible. Las versiones de perfil y de borrador son aditivas. Un borrador contiene versiones inmutables y un puntero a la actual. `expected_version` evita guardar una edición sobre una versión obsoleta. Si cambia el CV, guardá otra versión; no se altera el borrador previo.

Un claim E01, E02, etc. identifica una cita dentro de una versión, no una identidad global entre versiones. El SHA-256 permite detectar cambios en CV/citas/contenido, no aporta firma ni confidencialidad.

La exportación CLI se limita a Markdown y no sobrescribe; la UI permite descargar la vista previa. Para borrar CV todavía se debe retirar el archivo local completo con nicrawl detenida; no existe borrado selectivo en I11. Evitá incluir datos personales innecesarios.

## Interfaces

- CLI: `nicrawl profile save/list/show`; `nicrawl applications draft create/list/show/revise/export`.
- API loopback: `GET/PUT /api/profiles`, `GET /api/profiles/<version>`, `POST /api/applications/<id>/drafts`, `GET /api/applications/<id>/drafts`, `GET/PUT /api/drafts/<id>`.
- UI: `/applications`, formulario local de perfil y sección de borradores dentro de la candidatura.

`profile save` recibe `--cv-file`, `--label` y pares repetidos `--statement`/`--evidence`. No imprimas el CV en logs ni compartas el archivo de datos. Las entradas JSON rechazan propiedades desconocidas y tienen límites de longitud.

## Límites conocidos

Una candidatura puede tener varios borradores, pero la interfaz inicial crea y muestra el nuevo en la sesión actual; todavía no ofrece un editor de historial completo ni eliminación selectiva. No hay análisis del aviso para extraer requisitos. El usuario compara requisitos con evidencia y redacta respuestas. No hay envío automático ni integración personal de postulación de LinkedIn.
