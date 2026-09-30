# ADR-006 — consultas locales y exportación consistente

Estado: aceptado e implementado en I3, 2026-09-26.

## Contexto y decisión

La colección ya existe en SQLite. Hace falta buscar sin descargar, revisar cambios aunque el último intento haya fallado y exportar una selección reproducible. No se modifica el esquema 1 ni se agregan dependencias.

queries.py abre Repository en modo solo lectura, inicia una transacción y obtiene estado y resultados de esa instantánea. Filters es una dataclass inmutable compartida por list/export. Se filtra en Python para obtener Unicode casefold correcto: SQLite LIKE/NOCASE no representa por sí solo ese contrato. El orden se fija en SQL y las identidades se consultan con parámetros. Para 10.000 ofertas la medición fue menor a un segundo; se acepta escaneo O(n) y memoria proporcional al conjunto coincidente.

Las consultas emiten JSON por stdout y los errores van a stderr. Esto simplifica PowerShell, pruebas y comparación con el contrato de datos. Una tabla humana queda como mejora posterior. JSON escapa controles sin mutar el dominio. El detalle usa show JOB_KEY como argumento posicional, concretando el contrato antes propuesto como show --id.

changes usa el último run publicado (incluidos parciales) y las instantáneas guardadas en changes; no recalcula el pasado a partir de jobs actual. Muestra estado/cobertura y el intento más reciente por separado.

## Archivos y consecuencias

El exportador recibe un reporte materializado, no una conexión ni un cliente HTTP. El temporal vive junto al destino. flush/fsync preceden la publicación; os.replace permite reemplazo explícito, os.link permite publicación exclusiva sin carrera de check-then-write. finally retira el temporal. Si no hay soporte de enlaces duros, se informa error; no se degrada a sobrescribir silenciosamente.

Se rechazan la base y sus auxiliares como destinos, incluso alias existentes de la misma base. CSV conserva delimitación/saltos con csv.writer y antepone apóstrofo ante fórmulas o controles iniciales; JSON conserva los valores semánticos y un esquema de exportación independiente del esquema SQLite.

Alternativas: abrir destino directamente puede truncar datos; comprobar exists y después replace puede sobrescribir una creación concurrente. Full-text search o índices de texto normalizado exigirían migración y otra semántica de búsqueda; no se justifican aún. Un DataFrame solo para escribir CSV agrega una dependencia innecesaria.

## Validación y reapertura

Q16–Q19 cubren filtros, Unicode, novedades después de fallo, round-trip, controles, destino existente, fallo parcial y carrera de creación. Se midieron 10.000 ofertas sintéticas; ver [VALIDATION](../../VALIDATION.md). Reabrir si se supera la meta medida, se requieren tablas/paginación o se soportan otros sistemas de archivos. No se garantiza durabilidad frente a cortes eléctricos durante cambios de directorio; sí se evita publicar archivos parcialmente escritos ante fallos normales de I/O.
