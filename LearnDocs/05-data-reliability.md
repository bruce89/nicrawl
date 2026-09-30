# Fiabilidad de datos: pensar más allá del parser

## Correcto, completo y reciente son propiedades distintas

Un título puede estar bien extraído de una página vieja. Una colección puede estar actualizada pero haber perdido media paginación. Un lote grande puede contener duplicados. No resumir toda la calidad en “se descargaron 200 registros”.

| Dimensión | Pregunta | Señal posible |
| --- | --- | --- |
| Validez | ¿Cumple las reglas mínimas? | Proporción de candidatos válidos |
| Cobertura | ¿Terminó el ámbito consultado? | Fin verificado, sin truncamientos |
| Frescura | ¿Cuándo se observó? | Edad de última observación |
| Identidad | ¿Es el mismo registro? | Clave estable y conflictos detectados |
| Exactitud | ¿Coincide con el origen? | Muestra manual y pruebas del mapper |
| Trazabilidad | ¿Podemos explicar su procedencia? | Fuente, URL, run y versión |

La validez formal no demuestra exactitud: “Salario: 100” puede pasar un tipo numérico y representar el campo equivocado. Las pruebas deben incluir ejemplos cuyo significado se conozca.

## Ejemplo: un falso cierre masivo

R1 recolectó 100 avisos. R2 devuelve cinco porque se añadió por error un límite. Si el programa marca los otros 95 como cerrados, propagó una decisión local como si fuera un hecho del mercado.

Preguntas previas a cualquier razonamiento por ausencia: ¿mismo ámbito?, ¿mismo filtro?, ¿mismo proveedor?, ¿paginación completa?, ¿formato válido?, ¿el proveedor garantiza que lista todos los activos? nicrawl v0.1 evita el cierre automático incluso cuando esas señales parecen buenas.

## Dos relojes y cuatro fechas

El reloj de pared permite decir “se observó a las 15:00 UTC” y guardar un cooldown entre procesos. El reloj monotónico mide duración sin verse alterado por un ajuste normal del reloj del sistema. Ninguno resuelve por sí solo la zona de una fecha externa.

Las fechas de publicación, primera observación, última observación y último cambio material contestan preguntas diferentes. Agregar `Z` a una fecha sin zona inventa una interpretación. Si el origen no define zona, conservar el texto y dejar desconocido el instante.

Ejercicio: un aviso publicado el lunes se descubre el miércoles y cambia el jueves. Escribir esos cuatro campos tras cada corrida, incluyendo un intento fallido el viernes.

## La idempotencia es una propiedad observable

Repetir la misma entrada no debe crear otra oferta ni otro cambio. Sí puede añadir una observación y actualizar el tiempo de verificación. Eso muestra por qué “misma salida byte por byte” no es la definición útil para todo el sistema.

El hash excluye campos volátiles. Ordenar tags y normalizar espacios puede evitar falsos cambios, pero borrar puntuación indiscriminadamente puede ocultar uno real. Cada normalización debe tener un caso positivo y uno que no deba colapsarse.

## Atomicidad y recuperación

Un run descarga fuera de la transacción y publica dentro de una transacción corta. Si el proceso muere antes del commit, la colección anterior debe seguir coherente. El registro del intento puede existir aunque no se publique nada: es necesario para diagnosticar y conservar cuota.

Recuperar un run interrumpido no significa repetirlo inmediatamente. Primero se respeta el presupuesto persistido. Un identificador de run relaciona logs y datos; no reemplaza la clave de una oferta.

## Deriva del sitio

Cambian clases CSS, nombres de campos, envolturas y convenciones. No toda deriva causa excepción: puede producir valores vacíos plausibles. Por eso se miden también cantidades, presencia de campos y conflictos.

Conservar fixtures propias de casos representativos ayuda a reproducir sin castigar el sitio. Guardar indefinidamente páginas externas completas no es requisito de depuración; se puede construir un ejemplo sintético equivalente, documentando qué propiedad reproduce.

## Pensar en costo de mantenimiento

Costo total aproximado: desarrollo inicial + revisar roturas + operar red/almacenamiento + evaluar calidad + cambiar fuentes. Una fuente extra añade un contrato más para mantener. Una API puede ser estable y poco pertinente; una web rica puede ser demasiado frágil para el valor que aporta.

Antes de ampliar nicrawl, medir minutos ahorrados por consulta, ofertas útiles encontradas y errores corregidos. La cantidad de requests es costo y actividad, no valor por sí misma.

## Autoevaluación

Podés explicar por qué la oferta está ahí, de dónde viene, qué transformaciones recibió, cuán vieja es y qué no se sabe de ella. Podés mostrar una prueba que detecta la pérdida de una de esas propiedades. Ese es el criterio de confianza del proyecto.
