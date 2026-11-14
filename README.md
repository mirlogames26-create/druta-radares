# druta-radares

Radares de velocidad, de tramo y camaras de semaforo en rojo de Espana y Portugal, para los avisos de la app DRuta.
Se regenera cada lunes (`.github/workflows/radares.yml`) y la app lo baja de aqui.

- `radares.json`: `[[lat, lon, tipo, limite, rumbo, paralela], ...]`
  - `tipo`: `fijo` (velocidad), `tramo_inicio`, `tramo_fin`, `semaforo`
  - `limite`: km/h (0 si no se sabe) · `rumbo`: grados del sentido de la calzada (-1 si no se sabe)
  - `paralela`: 1 si esta cerca de uno de los ejes de DRuta pero no sobre el (otra carretera, un enlace)
- `meta.json`: fecha, numero de radares por tipo y fuentes.
- `ejes.json`, `base_ejes.json`: ejes de las vias de DRuta y los radares de esos ejes con su sentido (se actualizan
  desde el proyecto cuando cambian).

## Fuentes y licencia

- Inventario de radares de la **DGT** (Punto de Acceso Nacional, nap.dgt.es), CC BY 4.0. No incluye Cataluna ni
  Pais Vasco (gestionan sus carreteras) ni los radares urbanos (son de los ayuntamientos).
- **© colaboradores de OpenStreetMap**, bajo la Open Database License (ODbL): este fichero es una base de datos
  derivada y se publica tambien bajo **ODbL 1.0**.

Puede faltar algun radar, sobre todo en ciudad (solo estan los mapeados en OpenStreetMap): no sustituye a las senales.
