# ADR-009 — anotaciones personales separadas y ranking por reglas visibles

Estado: aceptado e implementado en I6, 2026-09-28.

## Contexto

Los avisos guardados vienen de dos proveedores. Una persona necesita recordar qué revisó y ordenar resultados según sus intereses, sin cambiar la verdad observada del proveedor ni su historial de cambios. Aún no hay preferencias personales definidas por el usuario ni un corpus etiquetado de relevancia.

## Decisión

El esquema SQLite 2 agrega `personal_state(job_key, state, note, updated_at)`, con FK hacia `jobs`. La migración 1→2 se hace en una transacción al abrir la base para escritura; una lectura de esquema 1 se rechaza para evitar resultados incompletos. `mark` acepta `favorite`, `dismissed` o `unreviewed`, y notas locales de hasta 2000 caracteres. `show` presenta esos datos. Recolectar de nuevo la misma oferta no los sobrescribe. No se suman al `content_hash` ni a `changes` del proveedor.

`rank` calcula un puntaje al consultar, a partir de términos `--want`/`--avoid` y modalidad `--mode` explícitos. Coincidencia literal Unicode `casefold` en título, tags y descripción: pesos 5, 3 y 1; un término evitado resta el mismo peso. Modalidad declarada coincidente suma 2 y distinta resta 2; `unknown` suma cero. `--fields` permite desactivar reglas de texto. La salida enumera cada contribución y una suma verificable; desempata por primer hallazgo descendente y clave. Por defecto omite descartadas, con opción para incluirlas. Las notas y favoritos no alteran el puntaje.

El puntaje es una heurística de revisión, no una predicción de contratación, vigencia ni elegibilidad geográfica. Las preferencias se pasan en cada invocación; no se envían a terceros ni se guardan. El ranking no es un filtro duro: puede devolver puntajes negativos. No se agrega modelo AI, perfil de CV ni campos inferidos.

## Alternativas y consecuencias

Guardar estado en `jobs.payload` mezclaría anotaciones propias con datos externos y produciría cambios falsos. Ordenar solo por una puntuación opaca impediría explicar un resultado. Pedir un modelo AI antes de una línea base evaluable agregaría costo y dificultad de depuración. Un diccionario de sinónimos o extracción de skills exigiría un corpus etiquetado; la coincidencia literal puede producir falsos positivos y omisiones. La [guía I6](../../LearnDocs/13-ranking-and-personal-state.md) propone medirlo con etiquetas manuales antes de ajustar pesos.

El esquema 2 requiere copia de seguridad y migración de bases existentes. La instalación limpia fue comprobada; el respaldo local previo a I6 se conserva fuera de la entrega. Si una migración falla, SQLite revierte la transacción; no hay downgrade automático. Ver [validación](../../VALIDATION.md).
