"""Interfaz Streamlit para el sistema Geolocalizador Idealista para Google Earth."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from statistics import mean

import streamlit as st
import folium
from streamlit.components.v1 import html

APP_ROOT = Path(__file__).resolve().parent
SRC_PATH = APP_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from idealista_geolocator import (
    ClientAnalyzer,
    EnvironmentAnalyzer,
    Exporter,
    MatchingEngine,
    PropertyEnricher,
    PropertyExtractor,
)
from idealista_geolocator.config import settings
from idealista_geolocator.llm_clients import build_llm_from_selection
from idealista_geolocator.service_endpoints import load_file_bytes

def _build_map_component(records):
    """Construye el componente HTML del mapa con los registros geolocalizados."""

    points = [
        (record.latitud, record.longitud, record)
        for record in records
        if record.latitud is not None and record.longitud is not None
    ]
    if not points:
        return ""

    avg_lat = sum(lat for lat, _, _ in points) / len(points)
    avg_lon = sum(lon for _, lon, _ in points) / len(points)
    fmap = folium.Map(location=[avg_lat, avg_lon], zoom_start=13, tiles="CartoDB positron")

    for lat, lon, record in points:
        color = "#2E7D32" if (record.precio_total or 0) < 150000 else "#1B5E20"
        if record.requiere_revision:
            color = "#D32F2F"

        folium.CircleMarker(
            location=(lat, lon),
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            popup=f"{record.titulo[:40]}... | Afinidad: {record.afinidad_porcentaje or 'N/D'}%",
        ).add_to(fmap)

    return fmap._repr_html_()


st.set_page_config(page_title="Geolocalizador Idealista", layout="wide")

st.title("Geolocalizador Idealista para Google Earth")
st.caption("Desarrollado por Moreturismo INT SL")

with st.sidebar:
    st.header("Configuración")
    st.caption(f"Claves Google Maps detectadas en .env: {len(settings.google_maps_keys.keys)}")
    st.caption(f"Claves Bing Maps detectadas en .env: {len(settings.bing_maps_keys.keys)}")
    manual_google_key = st.text_input("Añadir Google Maps API Key", type="password")
    manual_bing_key = st.text_input("Añadir Bing Maps API Key", type="password")
    st.markdown("---")
    provider = st.selectbox("Proveedor IA", ["openai", "perplexity", "ninguno"], index=0)
    default_models = settings.available_models()
    default_model = default_models[0] if default_models else "gpt-4o-mini"
    model_name = st.text_input("Modelo IA", value=default_model)
    manual_llm_key = st.text_input("API Key IA (opcional)", type="password")
    output_folder = st.text_input("Carpeta de salida", value=settings.default_output_root)

st.markdown("### 1. Datos de propiedades")
raw_properties = st.text_area(
    "Pega aquí el bloque de texto con las propiedades",
    height=220,
    placeholder="Título\nDirección\nURL\nPrecio...",
)

st.markdown("### 2. Conversación con el cliente")
raw_client = st.text_area(
    "Pega la transcripción o notas del cliente",
    height=180,
    placeholder="Cliente comenta que busca...",
)

process_button = st.button("🧠 Generar KML y Excel")

if process_button:
    if not raw_properties.strip():
        st.error("Por favor, introduce los datos de las propiedades.")
        st.stop()
    if not raw_client.strip():
        st.error("Por favor, introduce la transcripción del cliente.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()
    start = time.perf_counter()

    google_keys = list(settings.google_maps_keys.keys)
    if manual_google_key:
        google_keys.append(manual_google_key)
    bing_keys = list(settings.bing_maps_keys.keys)
    if manual_bing_key:
        bing_keys.append(manual_bing_key)

    llm_client = None
    if provider != "ninguno":
        llm_client = build_llm_from_selection(provider, model_name, manual_llm_key)

    extractor = PropertyExtractor(google_maps_api_keys=google_keys, bing_maps_api_keys=bing_keys)
    status.write("Extrayendo propiedades...")
    property_records, _ = extractor.parse_properties(raw_properties)
    progress.progress(20)

    enricher = PropertyEnricher(
        language_model_provider=provider,
        language_model_name=model_name,
        language_model_api_key=manual_llm_key,
        llm_client=llm_client,
    )
    status.write("Enriqueciendo información del anuncio...")
    enriched_records = enricher.enrich(property_records)
    progress.progress(40)

    env_analyzer = EnvironmentAnalyzer(google_maps_api_keys=google_keys)
    status.write("Analizando entorno...")
    enriched_records = env_analyzer.analyze(enriched_records)
    progress.progress(60)

    client_analyzer = ClientAnalyzer(
        language_model_provider=provider,
        language_model_name=model_name,
        language_model_api_key=manual_llm_key,
        llm_client=llm_client,
    )
    status.write("Analizando perfil del cliente...")
    client_profile = client_analyzer.analyze(raw_client, nombre_cliente="Cliente")
    progress.progress(75)

    matcher = MatchingEngine()
    status.write("Calculando afinidad...")
    match_results = matcher.match(client_profile, enriched_records)
    progress.progress(90)

    exporter = Exporter(output_root=output_folder)
    status.write("Generando archivos de salida...")
    export_result = exporter.export(enriched_records, client_description=client_profile.nombre_cliente)
    progress.progress(100)

    status.success("Proceso completado")
    elapsed = time.perf_counter() - start

    st.subheader("Indicadores clave")
    col1, col2, col3 = st.columns(3)
    col1.metric("Propiedades procesadas", len(enriched_records))
    col2.metric(
        "Propiedades a revisar",
        sum(1 for record in enriched_records if record.requiere_revision),
    )
    afinidades = [result.afinidad_porcentaje for result in match_results if result.afinidad_porcentaje is not None]
    afinidad_media = round(mean(afinidades), 2) if afinidades else 0
    col3.metric("Afinidad media", f"{afinidad_media}%")
    st.caption(f"Tiempo total: {elapsed:.2f} s")

    st.subheader("Mapa de propiedades")
    map_component = _build_map_component(enriched_records)
    if map_component:
        html(map_component, height=420)
    else:
        st.info("No hay coordenadas válidas para mostrar en el mapa.")

    st.subheader("Descargas disponibles")
    download_cols = st.columns(3)
    with download_cols[0]:
        excel_bytes = load_file_bytes(export_result.excel_path)
        st.download_button(
            label="Descargar Excel",
            data=excel_bytes,
            file_name=export_result.excel_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    if export_result.kml_path is not None:
        with download_cols[1]:
            kml_bytes = load_file_bytes(export_result.kml_path)
            st.download_button(
                label="Descargar KML",
                data=kml_bytes,
                file_name=export_result.kml_path.name,
                mime="application/vnd.google-earth.kml+xml",
            )
    with download_cols[2]:
        json_bytes = load_file_bytes(export_result.resumen_json_path)
        st.download_button(
            label="Descargar JSON",
            data=json_bytes,
            file_name=export_result.resumen_json_path.name,
            mime="application/json",
        )

    st.info(f"Archivos guardados en {export_result.carpeta}")
