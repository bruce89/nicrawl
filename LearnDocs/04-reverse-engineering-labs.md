# Ingeniería inversa y laboratorios

I1 ya tiene código ejecutable; empezar por [el recorrido real](08-first-working-slice.md). L1–L3 pueden practicarse sobre las fixtures actuales; L3–L6 ya pueden recorrerse con [I2](09-real-ingestion-sqlite.md); filtros, async y AI esperan cortes posteriores. Completar resultados personales en la bitácora; no confundir validación técnica con haber realizado el ejercicio.

## L1 — seguir una oferta, I1

Entrada: fixture `basic` futura. Elegir el ID `demo-01`. Dibujar recorrido HTML → selector → candidato → validación → JobDraft → salida. Para cada flecha, anotar función real, tipo de entrada/salida y posible error.

Cambiar solo el nombre de empresa y predecir qué pasos vuelven a ejecutarse. Después quitar el título. Evidencia: la primera modificación cambia el campo correcto; la segunda produce un rechazo que señala su causa y no altera otra tarjeta.

Pregunta de arquitectura: ¿la CLI conoce `.company` como selector CSS? Si la respuesta es sí, localizar la fuga de responsabilidades.

## L2 — romper un selector, I1

Cambiar `article.job` a otra clase en una copia de fixture. Antes de ejecutar, decidir si eso debería significar cero ofertas o estructura desconocida. Comprobar el marcador de página y la regla de integridad.

Reparar la extracción y conservar una prueba para el caso antiguo y otra para el nuevo si ambos layouts son admitidos. Una prueba que solo replica el selector no es suficiente; debe afirmar los valores extraídos.

Pregunta: ¿qué evidencia permite distinguir un rediseño de una lista vacía legítima?

## L3 — normalizar sin inventar, I1–I2

Entradas: empresa con `&amp;`, salario vacío, localización “Remote — US only”, fecha sin offset y una descripción con `C++`. Predecir cada campo resultante. Verificar que limpieza de puntuación no convierta tecnologías distintas ni borre restricciones.

Salida esperada: texto legible, salario desconocido, restricción original, instante de publicación desconocido y tecnología preservada. Anotar cuáles decisiones son transformaciones deterministas y cuáles necesitarían inferencia.

## L4 — hacer fallar la red sin usar Internet, I2

Transporte falso: timeout; 503 seguido de 200; 429 con `Retry-After`; 200 con HTML de error. Dibujar de antemano los intentos máximos, tiempos lógicos y estados finales. Usar reloj falso para avanzar sin esperar.

Evidencia: no hay reintentos fuera del presupuesto, el cooldown persiste al reconstruir objetos y la colección previa no cambia. Si aparecen dos reintentos donde se esperaba uno, buscar políticas duplicadas en capas diferentes.

## L5 — probar idempotencia, I2

Primera corrida: A y B. Segunda: mismos datos con distinto orden y espacios normalizables. Tercera: B cambia una frase real. Cuarta: error durante escritura.

Antes de ejecutar, escribir número esperado de ofertas, altas, cambios y observaciones. La cuarta no puede dejar el título de B nuevo con el hash anterior. Inspeccionar la base temporal después del rollback.

Pregunta: ¿por qué `last_seen_at` puede cambiar aunque no haya un evento `updated`?

## L6 — sustituir la fuente, I2–I4

Conectar una fuente fake que entrega JobDraft mediante el mismo contrato. Confirmar que filtros y exportador no importan el proveedor original. Después agregar un campo específico del proveedor: decidir si debe llegar al dominio o quedarse en el adaptador.

Evidencia: tests de consulta idénticos para datos equivalentes de las dos fuentes. No se exige que compartan DTO ni parser.

## L7 — añadir una funcionalidad vertical, I3

Añadir filtro por empresa desde la CLI. Localizar parseo de argumentos, predicado de consulta, repositorio y exportación. No tocar parser de HTML ni transporte. Comparar tres casos: mayúsculas distintas, coincidencia parcial y combinación con texto general.

Evidencia: resultado coherente en tabla y exportación, sin llamadas de red. Registrar si fue necesario duplicar lógica de filtrado y cómo se corrigió.

## L8 — comparar secuencial y async, I5

Preparar servidor local controlado o transportes de prueba, nunca usar un proveedor externo como benchmark. Definir latencias, errores y hosts simulados. Medir tiempo, solicitudes simultáneas y recursos antes de cambiar implementación.

Luego usar concurrencia acotada manteniendo las mismas reglas por host. Cancelar una fuente mientras otra concluye. Evidencia: mejora medida, cuota intacta, recursos cerrados y escritor controlado. Si no hay beneficio observable, conservar la opción simple.

## L9 — evaluar enriquecimiento, I6–I7

Tomar el mismo conjunto etiquetado para reglas y modelo. Pedir skills explícitas con fragmentos de evidencia. Incluir salario ausente, restricción geográfica ambigua y una instrucción ficticia incrustada en la descripción.

Evidencia: no se inventan importes ni permisos de trabajo; la instrucción externa no produce tool calls; se reporta abstención donde falta evidencia. Comparar errores y costo antes de elegir.

## Prueba de comprensión sin herramientas

Dibujar el pipeline de memoria y responder: quién conoce el DOM, quién es dueño de reintentos, dónde empieza/termina la transacción, qué persiste tras un crash y qué dato permite identificar el mismo aviso mañana. Después contrastar el dibujo con el código real.
