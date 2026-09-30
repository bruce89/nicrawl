# Fuentes de datos: selección y acceso

Investigación documental realizada el 2026-09-24. En esa ronda no se hicieron recolecciones. Actualización I2 del 2026-09-25: condiciones revisadas otra vez y una petición real a Remotive/software-dev, HTTP 200, 19 ofertas válidas. La segunda invocación fue diferida localmente con cero requests. Toda integración real depende de la aprobación de su iteración y de verificar la fuente en ese momento.

## Comparación

| Fuente | Mecanismo | Valor para nicrawl | Coste o límite | Decisión propuesta |
| --- | --- | --- | --- | --- |
| HTML sintético propio | Archivos locales | Selectores, campos opcionales, paginación y fallos reproducibles | No ofrece empleos reales | I1 obligatorio |
| Remotive | API JSON pública | Ofertas reales con contrato explícito | Condiciones de uso y frecuencia; cobertura de su propio catálogo | Candidato inicial I2 |
| Greenhouse Job Board | API por empresa/board | Segunda fuente para practicar adaptadores | Board GitLab fijo; no es un buscador global | I4 implementado |
| Scrape This Site | Sandbox HTML educativo | Práctica externa de scraping | Los ejemplos no son una fuente de empleos | Laboratorio I4 implementado |
| Careers HTML de una empresa | HTML/JSON-LD o renderizado | Scraping real del dominio laboral | URL, acceso y estructura por confirmar | Pendiente de elegir fuente |
| Portales con login o controles de acceso | Navegación autenticada | Mayor complejidad y dependencia operativa | No hay acuerdo ni fuente revisada | Fuera del alcance inicial |

No se afirma que Indeed, LinkedIn u otro portal permita recolectarlo por haber sido citado como caso de producto. Una API de lectura accesible tampoco concede por sí sola derechos de redistribución.

## Remotive: condiciones del candidato

Su página pública exige mencionar Remotive y enlazar a la URL proporcionada; prohíbe reenviar sus avisos a bolsas de terceros y usar los listados para capturar registros/emails. Informa una demora de 24 horas en las ofertas de la API y una alternativa privada comercial. nicrawl propone lectura personal con procedencia visible. Revisar nuevamente antes de publicar cualquier interfaz compartida. [Condiciones de la API](https://remotive.com/remote-jobs/api).

El repositorio oficial documenta `GET https://remotive.com/api/remote-jobs`, filtros opcionales y un máximo recomendado de cuatro consultas diarias. Recomienda no consultar frecuentemente y advierte bloqueo por exceso. nicrawl propone dos oportunidades diarias, separadas al menos 12 horas. No usar el techo de bloqueo como ritmo de operación. [Contrato oficial](https://github.com/remotive-com/remote-jobs-api).

## Adaptación propuesta

Una descarga del listado de `category=software-dev`, sin `limit` y sin `search`, seguida de filtros locales. El filtro temático es una propuesta de nicrawl y puede cambiar cuando se elija el objetivo de empleo. Registrar categoría exacta como ámbito. No simular páginas con parámetros que el contrato no documenta.

Mapeo: `id` → ID de origen; `title` → título; `company_name` → empresa; `url` → enlace de origen; `description` → texto; `candidate_required_location` → localización bruta; `salary` → salario bruto; `publication_date` → fecha bruta. Campos que el proveedor no suministre quedan desconocidos. El contrato documentado sirve de referencia para este adaptador; su presencia y tipos deben probarse con una respuesta real en I2. [Contrato oficial](https://github.com/remotive-com/remote-jobs-api).

La ausencia de zona horaria explícita deja `published_at=null`. No se toma “Worldwide” como comprobación legal de que alguien puede trabajar desde cualquier país. No se consultan logos ni enlaces de postulación.

## Greenhouse: board GitLab integrado en I4

La Job Board API documenta GET públicos sin autenticación y listados por `board_token`; `content=true` agrega contenido. I4 fija el board GitLab y usa `greenhouse:gitlab` más el ID del post. Otros boards requieren selección y revisión propias; el mecanismo técnico no demuestra permiso para cualquier reutilización. [Documentación de Greenhouse](https://docs.greenhouse.io/job-board.html).

Si Remotive no encaja con la región elegida, reabrir la selección. No reemplazarla silenciosamente por crawling masivo. Una primera demo real sobre un solo board puede tener más valor que una fuente amplia poco pertinente.

## Aprender HTML real

[Scrape This Site](https://www.scrapethissite.com/) se presenta como un sandbox público para aprender scraping. I4 usa únicamente `/pages/forms/`, dos páginas y revisión de robots en cada ejecución. No se usa el sitio completo como objetivo abierto.

Para empleos HTML externos, preferir una página pública de careers cuyo uso esté permitido, con IDs o enlaces estables y HTML legible. Si ofrece API oficial, usarla para producto y conservar HTML como comparación educativa. El sitio definitivo queda abierto; este paquete no inventa una autorización de scraping.

## Ficha de habilitación de una fuente

Antes de su primera integración registrar: ID; URL de documentación; origen y rutas admitidas; ámbito; condiciones y fecha de revisión; atribución; frecuencia; tamaño/páginas; forma de identificar registros; mecanismo de fin; tratamiento de fechas; campos obligatorios; responsable de mantenimiento; prueba de contrato y fecha.

Actualización I4 del 2026-09-28: Greenhouse/GitLab verificó GET público con content=true y publicó 200 ofertas en una petición; empresa e ID vienen del board/post. El laboratorio de Scrape This Site revisó robots.txt (200; excluye /lessons/ y /faq/, permite /pages/forms/) y leyó dos páginas, 50 filas, sin guardarlas como empleos. [API oficial](https://docs.greenhouse.io/job-board.html), [board GitLab](https://job-boards.greenhouse.io/gitlab), [sandbox](https://www.scrapethissite.com/pages/forms/).

Estado histórico al 2026-09-25: `demo-html` implementada con cinco fixtures propias instalables; `remotive` integrada y verificada para software-dev; el resto pendiente. La revisión de robots para HTML y las reglas HTTP están en [OPERATIONS](OPERATIONS.md). Si las condiciones cambian o la fuente deja de servir el objetivo, se deshabilita el adaptador y continúan las consultas locales.
