# Calidad y aceptación

Estado al 2026-09-28: **Q01–Q30 aplicables y el laboratorio I4 verificados**, con 143 casos automatizados y colecciones reales I2/I4. Q16–Q19 cubiertos por consultas y exportación I3. Q21 cubre bytes, registros, redirects y deadline para las fuentes; paginación HTML externa del sandbox se verificó en I4 con límite explícito de dos páginas y sin publicación laboral. Validación de esta entrega en [VALIDATION](../VALIDATION.md).

## Escenarios trazables

| ID | Riesgo o entrada | Evidencia esperada | Iteración / requisito |
| --- | --- | --- | --- |
| Q01 | Clon limpio y entorno vacío | Instalar con lock y ejecutar ayuda según instrucciones | I0 |
| Q02 | Demo base: tres válidos, uno sin título | Tres resultados y un rechazo visible | I1 / F01,F03 |
| Q03 | Campo opcional ausente, Unicode y entidades HTML | Texto correcto; faltante desconocido, sin valores inventados | I1 / F03 |
| Q04 | Marcador/contenedor HTML desaparece | Error estructural, no éxito con cero | I1 / F01 |
| Q05 | Lista vacía con marcador válido | Cero ofertas legítimas, distinto de Q04 | I1 / F01 |
| Q06 | Respuesta HTTP sintética válida | Mapeo y ámbito completos; procedencia preservada | I2 / F02,F10 |
| Q07 | Mismo lote dos veces | Sin duplicados ni nuevos cambios; avanza última observación | I2 / F04 |
| Q08 | Mismo ID cambia título; otro queda igual | Solo el primero genera diff | I2 / F04 |
| Q09 | Timeout o 503 persistente | Intentos acotados, salida 1, ofertas previas intactas | I2 / F09 |
| Q10 | 429 con segundos, fecha o header inválido | Cooldown durable correcto; reinicio no habilita otra request | I2 / F10 |
| Q11 | 403 o desafío con HTTP 200 | Fuente detenida para revisión, sin evasión ni bucle | I2 / F09,F10 |
| Q12 | Un candidato inválido y otro válido | Run parcial, contadores coherentes, solo válido publicado | I2 / F03,F12 |
| Q13 | Error SQL a mitad de publicación | Rollback completo de ofertas/cambios; fallo visible | I2 / F04,F09 |
| Q14 | Aviso ausente en colección o run fallido | Nunca etiquetar cerrado; tiempos previos preservados | I2 / F08 |
| Q15 | Fecha sin offset y salario ambiguo | Datos brutos preservados, instante/importe no inventados | I2 / F03 |
| Q16 | Búsqueda/detalle offline | AND, casefold, orden estable y cero llamadas de red | I3 / F05,F11 |
| Q17 | Novedades tras corrida fallida | `latest` apunta a último run publicado y muestra su estado | I3 / F06 |
| Q18 | JSON/CSV con coma, comillas, salto, Unicode y fórmula | Selección íntegra, atribución y salida segura | I3 / F07,F10 |
| Q19 | Archivo destino existente y fallo a mitad de exportación | No sobrescribir sin opción; destino anterior íntegro | I3 / F07 |
| Q20 | Dos recolectores o crash | Segundo no descarga; recuperación marca run interrumpido | I2 / F09,F12 |
| Q21 | Límite de tamaño, registros, loop o página incompleta | Abortar adquisición sin publicar lote truncado | I2; HTML de red en I4 |
| Q22 | Dos candidatos con mismo ID y distinto contenido | Conflicto explícito; ese ID no se publica | I2 / F03,F04 |

## Escenarios I6

| ID | Riesgo | Evidencia |
| --- | --- | --- |
| Q23 | Ranking opaco o modalidad desconocida | Suma de razones verificable; `unknown` no presume ajuste |
| Q24 | Nota mezclada con proveedor | Estado persiste tras publicar; huella y `changes` no cambian por nota |
| Q25 | Base antigua o migración parcial | Lectura antigua se rechaza; migración conserva payloads e identidad |
| Q26 | Descarte irreversible u opción confusa | Oculto por defecto, visible con `--include-dismissed`; limpiar nota y estado posible |

## Escenarios I7

| ID | Riesgo | Evidencia |
| --- | --- | --- |
| Q27 | API y CLI discrepan | Lista y ranking comparados sobre la misma base temporal |
| Q28 | La UI altera datos del proveedor | `PATCH` modifica solo estado personal; `show` refleja nota y payload intacto |
| Q29 | Activos faltantes o rutas inseguras | HTML/JS/CSS en wheel; CSP, Host, Origin y errores HTTP comprobados |
| Q30 | Pantalla no usable con datos reales | Navegador local muestra lista, detalle, procedencia y controles |

## Pirámide pequeña

Pruebas unitarias para normalización, identidad, huellas, filtros, tiempo y políticas. Parsers con fixtures sintéticas que varían por riesgo. Integración con base SQLite temporal para transacciones y migraciones, y transporte HTTP falso para errores. Unos pocos tests de CLI validan argumentos, códigos y separación entre datos y mensajes.

No se requiere cobertura porcentual arbitraria. Las pruebas deben fallar ante el riesgo que nombran; no replicar línea por línea la implementación. Usar reloj, jitter y transporte inyectados para no esperar segundos reales ni depender de ofertas que desaparecen. [Fixtures de pytest](https://docs.pytest.org/en/stable/how-to/fixtures.html).

## Verificación real

I2 necesita una consulta manual de bajo volumen a la fuente habilitada, dentro de presupuesto, para verificar contrato, mapeo y atribución. Se registra fecha, versión, cantidad y resultado, sin guardar corpus completo en Git. Los tests automáticos corrientes no dependen de la web. Aprobar un mock no equivale a probar la integración real.

Medir las metas de rendimiento con 10.000 ofertas sintéticas y documentar máquina, Python y tamaño de base. Un resultado de laboratorio no se convierte en garantía para toda instalación.

## Definition of done por corte

Demostración reproducible; escenarios del corte cumplidos; instrucciones con comandos reales; limitaciones anotadas; ADR actualizado a aceptado solo si se implementó; ejercicio de aprendizaje con evidencia y una modificación explicada por el usuario. No iniciar el corte siguiente automáticamente: respetar el alcance aprobado.

## Escenarios I8

`tests/test_i8_agents.py` comprueba paridad CLI, exclusión de notas/campos futuros, claves codificadas, entradas estrictas, límites Unicode y de llamadas, errores seguros y hash de base intacto. Incluye cliente MCP en proceso y subproceso stdio real. El texto externo malicioso queda como dato; no se afirma resistencia de un modelo que todavía no existe. Ver [contrato](AGENT_TOOLS.md).

## Escenarios I9

`test_i9_saved.py`: 18 casos de perfiles, validación, fallo atómico/bloqueo, instantánea frente a cambios concurrentes, exclusión de notas, identidad/etiquetas, muestras vacías/pequeñas y filtro por título. `test_i7_server.py` añade paridad de perfiles API/CLI y permisos de escritura. La relevancia real sigue necesitando juicio del usuario.

## Escenarios I10

18 casos en test_i10_applications.py y un caso de API adicional: contratos/URL, identidad, notas separadas, instantánea de título, rollback, concurrencia real entre escritores, revisión obsoleta, base ajena y comandos. Los tests prueban registro local, no éxito de postulaciones externas.
