# ADR-012 — perfiles locales y muestras reproducibles

Aceptado en I9, 2026-09-30. El usuario aprobó I9 y precisó Senior Software Engineer, remoto o presencial desde Uruguay.

## Decisión

Guardar perfiles Pydantic estrictos en un JSON versionado junto a la base, con límite, nombres estables, bloqueo y publicación atómica. La lectura/ejecución reutiliza queries y personal; CLI y API/UI consumen el mismo servicio. Un filtro adicional por título reduce coincidencias incidentales del texto empresarial sin reescribir el ranking ni introducir inferencia geográfica.

Para comparar list/rank, usar SQLite backup hacia un temporal y el mismo reloj para ambas consultas. Exportar solo una muestra acotada, sin notas, con órdenes, evidencia, razones e identidad SHA-256. Etiquetas aparte, vinculadas por identidad y job_key. Mantener unknown/pending explícitos y calcular precisión solo cuando el denominador esté resuelto. Ambos órdenes incluyen descartadas para comparar el mismo universo.

## Alternativas y consecuencias

- Una tabla de perfiles permitiría transacciones conjuntas con ofertas, pero no necesitamos esa atomicidad; el archivo evita migrar SQLite y facilita entender/respaldar configuración. El costo es respaldar dos archivos y manejar bloqueo/validación del libro.
- Parámetros en una URL o localStorage servirían solo a la UI. El libro asociado a la base funciona también en terminal; no se copia automáticamente a clientes MCP.
- Dos consultas sucesivas a la base viva pueden observar colecciones distintas. Backup cuesta espacio/tiempo y contiene temporalmente datos personales, pero conserva una instantánea consistente; se elimina tras proyectar datos públicos de ofertas.
- Medir favoritos como etiquetas evitaría trabajo manual pero mezclaría conductas, dudas y relevancia. I9 requiere decisiones humanas explícitas; no las fabrica ni convierte desconocidos en negativos.
- Añadir boards sin conocer el criterio incrementaría volumen. Primero documentamos cobertura, muestra y motivos de descarte; otro origen requiere evidencia y su propio contrato de acceso.

## Validación y reapertura

Pruebas de paridad, restricciones, colisión/reemplazo, fallo atómico, bloqueo, captura ante cambios concurrentes, datos privados, muestras vacías/pequeñas, etiquetas incompletas/ajenas y filtro compartido con agentes. Ver [VALIDATION](../../VALIDATION.md).

Reabrir al necesitar múltiples usuarios, sincronización, cientos de perfiles, evaluación masiva o permisos remotos. Los archivos locales no son un sistema de secretos ni el hash una firma. I10 separará candidaturas de favoritos; I9 no envía ni prepara postulaciones.
