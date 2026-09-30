# ADR-007 — segundo origen y laboratorio HTML acotado

Estado: aceptado e implementado en I4, 2026-09-28.

## Contexto

Remotive aporta una colección general y la demo I1 enseña selectores sobre fixtures propios. Para comprobar que el diseño admite otra fuente real y practicar paginación externa se necesitan límites claros: la aplicación guarda ofertas laborales, mientras el sandbox HTML contiene equipos de hockey.

## Decisión

El segundo origen es **el board GitLab de Greenhouse**, fijado en código. Greenhouse documenta GET públicos sin autenticación y `content=true` para obtener descripciones completas. No se habilita un token de board arbitrario: el host y la ruta de adquisición son constantes revisadas. El adaptador valida `meta.total`, como señal de lote completo, DTO estricto, identidad del post (`id`), URL, título y ubicación. Asigna `source_id=greenhouse:gitlab`, empresa GitLab, modalidad `unknown` y fechas del origen solo cuando tienen zona horaria. HTML escapado de la descripción se convierte en texto. Remotive y GitLab conservan identidades, runs y cuotas propios; comparten base, transacciones, bloqueo, consultas y exportación. El esquema SQLite permanece en versión 1.

El laboratorio externo usa exclusivamente las primeras dos páginas de [Hockey Teams](https://www.scrapethissite.com/pages/forms/) de Scrape This Site. Antes de la página lee robots.txt; una exclusión o respuesta incierta detiene el ejercicio. Verifica misma ruta/host/HTTPS, espera dos segundos entre inicios, limita bytes y filas, rechaza DOM incompleto, duplicados y paginación irregular. La salida es una muestra JSON; no entra en `jobs` porque los equipos no son ofertas. `has_more=true` significa que el sandbox ofrece más páginas, no que la muestra pretendió cubrirlas.

## Alternativas y consecuencias

Un board configurable sin lista aprobada facilita peticiones a fuentes no revisadas y dispersa el presupuesto de acceso. Un parser universal para API y HTML escondería contratos diferentes. Publicar los equipos de hockey como ofertas contaminaría las búsquedas. Se mantienen dos adaptadores de empleo concretos y un laboratorio independiente.

La misma política conservadora de Remotive (oportunidad cada 12 h, máximo cuatro intentos por 24 h y dos por minuto) se aplica por fuente al board GitLab; son límites propios hasta tener condiciones más específicas. La lectura unificada usa `--source all` por defecto. La fuente se puede inspeccionar y recolectar individualmente. No se intenta deduplicar entre proveedores por título o URL: una coincidencia aparente puede ser otro puesto.

## Verificación y reapertura

Pruebas con transporte falso cubren contrato incompleto, conflictos, cuotas independientes, consultas de ambas fuentes, robots, límites, paginación y fallos. Una petición real Greenhouse el 2026-09-28 publicó 200 ofertas; el laboratorio real verificó robots y leyó dos páginas/50 filas. Ver [VALIDATION](../../VALIDATION.md).

Reabrir al incorporar otros boards, cambiar requisitos de regiones, necesitar más páginas o encontrar una política distinta del origen. Un cambio del DOM o del JSON debe reproducirse primero con fixtures propias y no inducir una publicación truncada.
