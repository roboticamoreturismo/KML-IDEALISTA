# Automatización Idealista → Excel + Google Earth

Este proyecto proporciona una herramienta lista para usar en inmobiliarias que
necesitan transformar los datos capturados de Idealista (mediante Instant Data
Scraper) en un informe enriquecido: un Excel completo, un archivo KML apto para
Google Earth y un mapa interactivo en HTML.

## Problema que resuelve

1. Limpia y normaliza los datos de los anuncios, con especial énfasis en la
   dirección (prefijo, número, barrio, ciudad, provincia y CP cuando es posible).
2. Enriquece los inmuebles con información semántica generada mediante reglas
   NLP sencillas (entorno, características adicionales, luminosidad, etc.).
3. Analiza automáticamente las necesidades de un cliente potencial descritas en
   texto libre y genera un perfil estructurado.
4. Calcula la afinidad entre cada inmueble y el cliente, produciendo una tabla
   de matching con puntuaciones y recomendaciones.
5. Exporta todo a un Excel con varias hojas, genera un fichero KML y un mapa
   interactivo para compartir fácilmente con el comprador.

## Requisitos

```bash
pip install -r requirements.txt
```

Los requisitos son ligeros (pandas, openpyxl, folium y simplekml), pensados para
funcionar en un PC estándar sin infraestructura compleja.

## Uso rápido

1. **Exporta** los anuncios desde Instant Data Scraper a CSV o JSON.
2. **Prepara** un archivo de texto (UTF-8) con la descripción del cliente.
3. Ejecuta la herramienta:

```bash
PYTHONPATH=src python -m idealista_automation.cli datos_propiedades.csv cliente.txt \
    --nombre-cliente "Nombre Cliente" --output output
```

Se crearán:

- `output/YYMMDD_Descripcion_NombreCliente.xlsx` con dos hojas (`Propiedades` y
  `Matching`).
- `output/propiedades.kml` listo para abrir en Google Earth (si hay
  coordenadas).
- `output/mapa_propiedades.html` con un mapa interactivo (si hay coordenadas).

## Estructura del Excel

- **Propiedades**: contiene todos los campos solicitados en la especificación
  (identificación, dirección, superficies, descripción, entorno, etc.).
- **Matching**: puntuaciones del 1 al 5 para cada criterio, porcentaje de
  afinidad y recomendaciones para acercar el inmueble a las necesidades del
  cliente.

## Adaptaciones

- Las reglas de inferencia están pensadas para España pero son fácilmente
  ampliables editando `src/idealista_automation/parsers.py` y
  `src/idealista_automation/enrichment.py`.
- Para añadir nuevos campos en el Excel solo hay que extender
  `PropertyRecord` y ajustar `property_transformer.py`.

## Notas

- Si el scraping no incluye coordenadas en `map-content src`, no se generarán el
  KML ni el mapa interactivo; el Excel se produce igualmente.
- Todo el código está comentado para facilitar su mantenimiento por personal no
  técnico.
