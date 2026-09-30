# ADR-002 — estrategia de fuentes

Estado: aceptado e implementado para HTML sintético I1 · 2026-09-25. Adaptador y cinco fixtures propios verificados; I2 integró Remotive/software-dev con una petición real. I4 agregó GitLab/Greenhouse y HTML externo acotado al sandbox educativo; scraping HTML de empleos aún no está habilitado.

## Contexto y decisión

El usuario quiere aprender scraping y obtener algo funcional, posiblemente ofertas laborales. Un único sitio externo como primera dependencia puede mezclar errores de red, DOM, permisos y Python. Se propone I1 con HTML sintético propio; I2 con un adaptador de API pública candidata; I4 con HTML externo permitido o segundo origen.

Remotive es candidato por ofrecer documentación pública y un contrato acotado. Su revisión está centralizada en [DATA_SOURCES](../DATA_SOURCES.md). No se llama “scraping HTML” a consumir su API. El parser de HTML inicial sí enseña extracción real, aunque sobre datos controlados.

## Alternativas

- HTML de una bolsa externa desde I1: aprendizaje directo, pero fragilidad y acceso sin investigar. Reabrir si se identifica un sitio adecuado y el usuario prefiere priorizarlo.
- Solo API: llega antes a utilidad, pero deja sin practicar DOM, selectores y deriva.
- Solo sandbox: útil para aprender, insuficiente para el objetivo de ofertas reales.
- Agregador de múltiples fuentes desde el comienzo: más cobertura, costo alto en normalización y deduplicación antes de tener un recorrido vertical.

## Consecuencias y validación

Habrá dos adaptadores pequeños y explícitos. Comparten normalización de dominio, no un parser universal. La demo permanece offline y separada de la base real. Medir éxito mediante ejercicios HTML y una integración real probada, no por cantidad de fuentes.

Reabrir si cambia el dominio, el foco geográfico vuelve poco útil la fuente o sus condiciones cambian. Un fallback se documenta y aprueba dentro del alcance de la iteración antes de incorporarlo.
