# ADR-013 — seguimiento separado con historial transaccional

Aceptado en I10, 2026-09-30. Usuario: “Vamos con I10”.

## Decisión y motivos

Crear un almacén SQLite local asociado a la base elegida, pero separado de ofertas y favoritos. La entidad application captura referencia, estado y revisión; identities registra claves únicas; events conserva la historia. UI y CLI comparten funciones de aplicación. El alta manual no llama fuentes de red y marcar submitted solo registra una afirmación del usuario.

SQLite permite confirmar estado y evento en la misma transacción y arbitrar escritores simultáneos. BEGIN IMMEDIATE más claves únicas evita duplicados concurrentes; expected_revision detecta una edición basada en una versión vieja. La interfaz permite corregir/reabrir con motivo porque el seguimiento registra hechos, no controla el proceso del empleador.

## Alternativas y consecuencias

- Reutilizar favorite/nota mezclaría interés, descarte y candidatura. No existe conversión automática entre ambos.
- Un JSON como los perfiles de I9 sería pequeño al principio, pero reescribir todo el historial y manejar concurrencia sería más costoso. SQLite ya es parte del proyecto.
- Añadir tablas a ofertas permitiría foreign keys hacia jobs; se eligió otro archivo para aislar datos personales y soportar referencias sin colección. Se pierde integridad referencial entre archivos: se valida job_key al crear y se conserva una copia mínima del aviso. Respaldar el seguimiento por separado.
- Deducción por similitud de títulos puede unir vacantes distintas. Se usan clave y URL normalizada con límites documentados; no se fusionan identidades ni notas automáticamente.
- Un grafo rígido de estados dificultaría registrar procesos ya avanzados o errores humanos. Se admite corrección explícita con historial; no se borra pasado ni se pretende demostrar envío externo.

No se agrega borrado, adjuntos, datos de CV, contactos, automatización de navegación ni escrituras MCP. Reabrir al necesitar múltiples candidaturas al mismo aviso, fusión manual, sincronización, cifrado o varios usuarios.

## Verificación

Duplicados y ediciones concurrentes, rollback ante fallo de historial, almacén ajeno intacto, base de ofertas sin cambios, exclusión de datos personales de agentes, y equivalencia API/CLI. [Evidencia](../../VALIDATION.md), [contrato](../APPLICATIONS.md).
