# Fixtures de I1

HTML original creado para nicrawl el 2026-09-25. Empresas, puestos, salarios y URLs son ficticios. No se descargó contenido de portales externos. `jobs.example` es una referencia ilustrativa y la demo no la visita.

`basic`: tres ofertas válidas y una sin título. `optional-fields`: campos mínimos. `unicode`: entidades, puntuación y contenido no visible. `empty`: estado vacío explícito. `broken-layout`: clase de tarjeta modificada intencionalmente.

Estos archivos son recursos del paquete porque la CLI de demostración los necesita después de instalarse. Los tests los reutilizan y crean variantes puntuales en memoria. No existe una segunda copia en tests que pueda divergir silenciosamente.
