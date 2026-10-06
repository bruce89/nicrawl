# ADR-014 — perfil versionado y borrador revisable

Aceptado en I11, 2026-10-03. Usuario: “Perfecto, vamos con I11”.

## Decisión

Guardar el CV como texto aportado por el usuario en el almacén SQLite personal separado. Registrar claims por versión solo cuando cada cita es literal del CV. Crear versiones inmutables de borrador asociadas a una candidatura y al perfil que las originó. Exponer casos de uso compartidos por CLI, API local y UI desacoplada. Mantener la generación determinista: afirmaciones seleccionadas, cita, apertura opcional escrita por la persona y preguntas explícitamente pendientes.

## Motivos y límites

La cita visible permite inspeccionar qué texto apoya una afirmación. No prueba su veracidad ni que el resumen sea adecuado, por lo que el usuario verifica antes de copiar. No se usa un modelo externo porque CV y datos laborales son sensibles y porque la primera entrega debe enseñar procedencia y control de versiones. La exportación exclusiva reduce el riesgo de reemplazar otro archivo. Las revisiones optimistas conservan cambios anteriores.

El archivo local no cifra datos. El usuario controla la máquina y la ubicación del `--db`; una futura opción de borrado/cifrado requiere diseño de respaldo y recuperación. No se añaden adjuntos, respuestas inferidas, envío, navegación automatizada ni escritura desde MCP. I12 se mantiene separado y pendiente.

## Alternativas consideradas

- Pegar CV directamente en cada borrador duplicaría y desincronizaría información.
- Sustituir el perfil in-place rompería reproducibilidad de un borrador anterior.
- Generación con LLM ampliaría el alcance de privacidad y evaluación antes de contar con un corpus de calidad.
- Almacenar en la base de ofertas mezclaría información personal con datos recolectados.

## Consecuencias

Una base personal puede contener datos sensibles y debe respaldarse/protegerse como tal. Claims conservan un ID local a su versión; no se sincronizan. El borrador no se convierte en prueba de envío, igual que el estado `submitted` de I10 solo registra una acción declarada.
