# Hoja de aprendizaje

## Diagnóstico breve

Sin buscar una solución, explicar: qué es un entorno virtual; diferencia entre iterable e iterador; qué valida una anotación de tipo; qué ocurre al pasar una lista mutable como argumento; cómo se cierra un archivo; por qué un 200 puede contener datos inválidos; qué garantiza una transacción; qué significa repetir un proceso sin duplicar resultados.

Si podés explicarlo y demostrarlo con un ejemplo, salteá la introducción correspondiente. Si no, convertí la duda en un ejercicio. La experiencia en arquitectura ayuda a ubicar responsabilidades, pero no reemplaza estudiar las reglas del runtime de Python.

## A — entorno y lenguaje, I0

Conceptos: intérprete, `.venv`, módulo, paquete, import, entrypoint, `pyproject.toml` y lock. Funciones, colecciones, comprehensions, `None`, excepciones y anotaciones.

Ejercicio: localizar qué archivo ejecuta el comando CLI y qué intérprete carga sus dependencias. Escribir una normalización de espacios que conserve Unicode. Comparar una función con efecto de I/O y otra pura.

Dominio: explicar por qué instalar una biblioteca en otro Python no la hace disponible en este entorno; distinguir declaración de versión de resolución concreta. Cambiar una función sin modificar el entrypoint.

## B — HTML y extracción, I1

Conceptos: HTML, árbol DOM, atributos, selectores CSS, enlaces relativos, texto y entidades. Registro individual frente a estructura de página. Campos obligatorios y opcionales.

Ejercicio: dibujar una tarjeta de oferta y su relación con el contenedor. Elegir selectores que dependan de significado y no de posición accidental. Convertir tres tarjetas y explicar el rechazo de una cuarta.

Dominio: reconocer lista legítimamente vacía y layout roto; demostrar que mover un elemento irrelevante no altera la oferta. Explicar por qué una expresión regular global no sustituye un parser HTML.

## C — tipos y fronteras, I1–I2

Conceptos: dataclass, enum, `Protocol`, DTO, validación de runtime y tipado estático. Excepciones específicas y datos parciales.

Ejercicio: introducir un salario desconocido y un ID faltante. El primero se acepta como desconocido; el segundo produce rechazo. Decidir en qué capa ocurre cada operación.

Dominio: explicar por qué una anotación `int` no transforma un string de JSON ni rechaza mágicamente un valor equivocado. Probar que el dominio puede ejecutarse sin importar el cliente HTTP.

## D — HTTP y políticas, I2

Conceptos: request/response, estado, headers, encoding, JSON, timeouts, cuotas, retries y backoff. HTML descargado frente a DOM renderizado por JavaScript.

Ejercicio: simular 503, luego éxito; después 429 y reinicio del proceso. Dibujar cuántos intentos pueden hacerse y cuándo. Identificar quién decide reintentar.

Dominio: interpretar por qué “más requests por segundo” puede empeorar un recolector; demostrar que un 200 con página de error no se publica. Diferenciar límite documentado del proveedor y límite elegido por nicrawl.

## E — persistencia y tiempo, I2

Conceptos: SQL, clave única, upsert, transacción, migración, idempotencia, diff, timestamp UTC y reloj monotónico.

Ejercicio: ejecutar la historia R1–R4 de [DATA_MODEL](../docs/DATA_MODEL.md) con datos controlados. Interrumpir una escritura antes del commit. Cambiar solo la hora de adquisición y comprobar que no genera cambio material.

Dominio: explicar por qué la última observación no equivale a publicación, por qué ausencia no demuestra cierre y qué información hace falta para afirmar que una colección fue completa.

## F — producto y calidad, I3

Conceptos: búsqueda, filtros, orden determinista, exportación, seguridad de representación y códigos de salida.

Ejercicio: añadir filtro por empresa; seguirlo desde argumentos hasta consulta y exportación. Exportar un título con coma y un campo que empiece con `=`. Inspeccionar el archivo sin ejecutar contenido.

Dominio: demostrar que consultas locales no hacen red, que pantalla y exportación usan la misma selección y que el texto original no fue modificado para resolver un problema de presentación.

## G — concurrencia y arquitectura, I4–I5

Conceptos: composición, segundo adaptador, scheduler, límites por host, `asyncio`, cancelación y cola acotada.

Ejercicio: reemplazar una fuente sin tocar filtros; luego comparar fetch secuencial y concurrente sobre un servidor local de prueba. Mantener igual política por origen y medir tiempo/error/memoria.

Dominio: explicar qué gana la concurrencia y qué no; detectar trabajo bloqueante dentro del event loop; justificar cuántas tareas existen simultáneamente. No migrar a async solo para usar sintaxis nueva.

## H — ranking y AI, I6–I7

Conceptos: baseline, etiquetas, evaluación, evidencia, errores de extracción, límites de herramientas y costos.

Ejercicio: construir un ranking por reglas y compararlo con una variante AI sobre los mismos avisos. Introducir una instrucción maliciosa ficticia dentro de la descripción y verificar que se trate como texto.

Dominio: distinguir observación, inferencia y preferencia; explicar una abstención; poder retirar el modelo sin romper el producto principal.

## Cierre de una sesión

Registrar una hipótesis, un resultado observable, una explicación y una pregunta nueva en [la bitácora](07-workbook.md). Una buena medida de progreso es reducir la cantidad de pasos del sistema que todavía se explican como “acá hace magia”.
