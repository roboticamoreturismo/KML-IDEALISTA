# Geolocalizador Idealista para Google Earth

Aplicación diseñada para automatizar el análisis de anuncios inmobiliarios
copiados desde portales como Idealista y generar entregables listos para clientes
de agencias pequeñas o medianas.

## Características principales

- **Paso 1 – Extracción estructurada**: interpreta texto sin formato y genera una
  tabla limpia con precios, m², descripciones y URLs.
- **Paso 2 – Enriquecimiento**: amplía la información con datos del anuncio,
  analiza la descripción y clasifica imágenes.
- **Paso 3 – Entorno**: consulta servicios y clasifica la zona usando Google
  Places y/o OpenStreetMap.
- **Paso 4 – Cliente**: transforma la conversación transcrita en un perfil
  estructurado.
- **Paso 5 – Matching**: calcula afinidad entre cada propiedad y el cliente.
- **Paso 6 – Exportación**: genera archivos Excel y KML listos para Google
  Earth, además de un JSON de respaldo.
- **Interfaz Streamlit**: una interfaz tipo Apple minimalista que guía el flujo
  completo de pegar datos, procesar y descargar resultados.

## Instalación rápida

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows usar .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Uso de la aplicación

```bash
streamlit run app.py
```

1. Pega el bloque de propiedades en el primer cuadro de texto.
2. Pega la transcripción del cliente en el segundo cuadro.
3. Opcionalmente introduce tus claves de Google Maps y OpenAI.
4. Pulsa **"🧠 Generar KML y Excel"** y espera a que finalice el proceso.
5. Descarga los archivos y revisa el mapa interactivo en Google Earth.

## Notas y configuración

- Las claves de API se solicitan desde la barra lateral. Si no se facilitan,
  el sistema intenta trabajar con fuentes abiertas (OSM) o omite los pasos
  dependientes.
- Los archivos generados se almacenan en la carpeta `clientes/` agrupados por
  fecha y nombre del cliente.
- Para entornos sin `simplekml`, el sistema sigue generando el Excel y el JSON.

## Estructura del proyecto

```
src/idealista_geolocator/
├── __init__.py
├── data_models.py
├── step1_property_extractor.py
├── step2_enrichment.py
├── step3_environment.py
├── step4_client_analysis.py
├── step5_matching.py
└── step6_export.py
app.py
requirements.txt
```

Cada módulo representa un paso del flujo descrito y puede reutilizarse en otros
contextos (scripts por lotes, automatizaciones n8n, etc.).
