"""Exportadores a Excel, KML y mapas interactivos."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import simplekml
from folium import Map, Marker, Popup

from .data_models import ClientProfile


def _ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generar_excel(
    propiedades: List[Dict],
    matching: pd.DataFrame,
    cliente: ClientProfile,
    output_dir: str,
) -> str:
    _ensure_output_dir(output_dir)
    fecha = datetime.now().strftime("%y%m%d")
    nombre_fichero = f"{fecha}_Descripcion_{cliente.nombre.replace(' ', '')}.xlsx"
    ruta = os.path.join(output_dir, nombre_fichero)

    propiedades_df = pd.DataFrame(propiedades)
    matching_df = matching
    cliente_df = pd.DataFrame([cliente.__dict__])

    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        propiedades_df.to_excel(writer, sheet_name="Propiedades", index=False)
        matching_df.to_excel(writer, sheet_name="Matching", index=False)
        cliente_df.to_excel(writer, sheet_name="Cliente", index=False)
    return ruta


def generar_kml(propiedades: List[Dict], output_dir: str) -> Optional[str]:
    puntos = [(p.get("titulo"), p.get("lat"), p.get("lon"), p.get("direccion_completa")) for p in propiedades]
    puntos_validos = [p for p in puntos if p[1] is not None and p[2] is not None]
    if not puntos_validos:
        return None
    _ensure_output_dir(output_dir)
    kml = simplekml.Kml()
    for titulo, lat, lon, direccion in puntos_validos:
        punto = kml.newpoint(name=titulo, coords=[(lon, lat)])
        if direccion:
            punto.description = direccion
    ruta = os.path.join(output_dir, "propiedades.kml")
    kml.save(ruta)
    return ruta


def generar_mapa_html(propiedades: List[Dict], output_dir: str) -> Optional[str]:
    puntos = [(p.get("titulo"), p.get("lat"), p.get("lon"), p.get("direccion_completa")) for p in propiedades]
    puntos_validos = [p for p in puntos if p[1] is not None and p[2] is not None]
    if not puntos_validos:
        return None
    _ensure_output_dir(output_dir)
    lat_media = sum(p[1] for p in puntos_validos) / len(puntos_validos)
    lon_media = sum(p[2] for p in puntos_validos) / len(puntos_validos)
    mapa = Map(location=[lat_media, lon_media], zoom_start=13, tiles="OpenStreetMap")
    for titulo, lat, lon, direccion in puntos_validos:
        popup_text = f"<b>{titulo}</b><br/>{direccion or ''}"
        Marker(location=[lat, lon], popup=Popup(popup_text, max_width=300)).add_to(mapa)
    ruta = os.path.join(output_dir, "mapa_propiedades.html")
    mapa.save(ruta)
    return ruta
