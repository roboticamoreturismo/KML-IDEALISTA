"""Interfaz Streamlit para el sistema Geolocalizador Idealista para Google Earth."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

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

st.set_page_config(page_title="Geolocalizador Idealista", layout="wide")

st.title("Geolocalizador Idealista para Google Earth")
st.caption("Desarrollado por Moreturismo INT SL")

with st.sidebar:
    st.header("Configuración")
    google_api_key = st.text_input("Google Maps API Key", type="password")
    openai_key = st.text_input("OpenAI API Key", type="password")
    output_folder = st.text_input("Carpeta de salida", value="clientes")

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

@st.cache_data(show_spinner=False)
def _convert_df(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

if process_button:
    if not raw_properties.strip():
        st.error("Por favor, introduce los datos de las propiedades.")
        st.stop()
    if not raw_client.strip():
        st.error("Por favor, introduce la transcripción del cliente.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    extractor = PropertyExtractor(google_maps_api_key=google_api_key or None)
    status.write("Extrayendo propiedades...")
    property_records, property_df = extractor.parse_properties(raw_properties)
    progress.progress(20)

    enricher = PropertyEnricher(openai_api_key=openai_key or None)
    status.write("Enriqueciendo información del anuncio...")
    enriched_records = enricher.enrich(property_records)
    progress.progress(40)

    env_analyzer = EnvironmentAnalyzer(google_maps_api_key=google_api_key or None)
    status.write("Analizando entorno...")
    enriched_records = env_analyzer.analyze(enriched_records)
    progress.progress(60)

    client_analyzer = ClientAnalyzer()
    status.write("Analizando perfil del cliente...")
    client_profile = client_analyzer.analyze(raw_client, nombre_cliente="Cliente")
    progress.progress(75)

    matcher = MatchingEngine()
    status.write("Calculando afinidad...")
    match_results = matcher.match(client_profile, enriched_records)
    progress.progress(90)

    exporter = Exporter(output_root=output_folder)
    status.write("Generando archivos de salida...")
    export_path = exporter.export(enriched_records, client_description=client_profile.nombre_cliente)
    progress.progress(100)

    status.success("Proceso completado")

    st.subheader("Resumen de propiedades")
    st.dataframe(pd.DataFrame([record.__dict__ for record in enriched_records]))

    st.subheader("Perfil del cliente")
    st.json(client_profile.__dict__)

    st.subheader("Resultados del matching")
    st.dataframe(pd.DataFrame([result.__dict__ for result in match_results]))

    st.download_button(
        label="Descargar datos en CSV",
        data=_convert_df(pd.DataFrame([record.__dict__ for record in enriched_records])),
        file_name="propiedades.csv",
        mime="text/csv",
    )

    if export_path.suffix == ".kml":
        with open(export_path, "rb") as kml_file:
            st.download_button("Descargar KML", data=kml_file, file_name=export_path.name)
    else:
        with open(export_path, "rb") as excel_file:
            st.download_button("Descargar Excel", data=excel_file, file_name=export_path.name)

    st.info(f"Archivos guardados en {export_path.parent}")
