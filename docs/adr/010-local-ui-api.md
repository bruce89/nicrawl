# ADR-010 — UI y API local sobre casos de uso compartidos

Fecha: 2026-09-28. Estado: aceptada para I7.

## Contexto y decisión

La CLI ya ofrece búsqueda, detalle, ranking y revisión personal sobre SQLite. El usuario quiere una superficie visual que permita explorar la colección sin transferir reglas de negocio a la presentación, y mantener CLI y API operables desde terminal. I7 agrega un servidor HTTP local con `ThreadingHTTPServer` de la biblioteca estándar y una UI HTML/CSS/JavaScript sin framework. `serve` inicia ambos bajo `127.0.0.1`; el navegador llama a rutas `/api/*` y el servidor invoca `queries.search`, `queries.show`, `personal.rank` y `personal.mark`, las mismas funciones usadas por CLI. Los archivos estáticos viajan dentro del wheel.

```text
CLI ────────────────┐
                    ├── casos de uso Python ── SQLite
Navegador → API HTTP┘
```

No se añade un framework web para cuatro operaciones de una app local de un usuario. Si el alcance crece (autenticación, varias personas, publicación remota, muchas rutas), se reconsidera el adaptador HTTP sin reescribir casos de uso. La UI mantiene solo estado de pantalla (filtros, selección, texto de formulario); no calcula puntuaciones ni abre SQLite. La API no adquiere datos: la recolección sigue explícita por CLI y con sus cuotas.

## Límites y consecuencias

- El servidor no escucha en interfaces de red. `Host` debe coincidir con `127.0.0.1:<puerto>`; `PATCH` exige además un `Origin` local si el cliente lo envía. No se habilita CORS.
- La UI inserta títulos, descripciones y razones externas como texto, no HTML ejecutable. Se añaden CSP, `nosniff` y límites de parámetros/cuerpo.
- La fuente se atribuye y se muestran frescura y advertencia de elegibilidad: la observación reciente no garantiza aviso vigente ni residencia aceptada.
- Una lectura API abre la base existente en modo lectura, de acuerdo con el caso de uso. `PATCH` conserva datos de proveedor separados de la tabla personal.
- Un puerto ocupado causa error de arranque; el usuario puede elegir `--port`. Ctrl+C termina el servidor. No hay daemon, cuenta, despliegue ni sincronización.
- Un agente posterior puede reutilizar funciones Python o contratos HTTP de lectura. No obtiene autoridad de escritura por existir `PATCH`; I8 deberá decidir interfaz, permisos, evidencia y límites.

La equivalencia de contratos CLI/API y la escritura personal se prueban con una base temporal. La inspección visual en navegador completa la prueba de la presentación. Ver [API](../API.md) y [guía I7](../../LearnDocs/15-local-ui-api.md).
