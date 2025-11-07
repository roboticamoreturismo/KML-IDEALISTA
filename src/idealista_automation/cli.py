"""Interfaz de línea de comandos para ejecutar la automatización."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import pandas as pd

from .pipeline import IdealistaAutomation


def cargar_propiedades(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return pd.DataFrame(data)
    return pd.read_csv(path, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automatización de Idealista para Google Earth")
    parser.add_argument("propiedades", type=Path, help="Ruta al CSV/JSON exportado por Instant Data Scraper")
    parser.add_argument("cliente", type=Path, help="Archivo de texto con las necesidades del cliente")
    parser.add_argument("--nombre-cliente", required=True, help="Nombre del cliente para nombrar los archivos")
    parser.add_argument("--output", default="output", help="Carpeta donde guardar Excel/KML/mapa")
    return parser.parse_args()


def main() -> Dict[str, str]:
    args = parse_args()
    propiedades_df = cargar_propiedades(args.propiedades)
    cliente_texto = args.cliente.read_text(encoding="utf-8")

    automation = IdealistaAutomation(output_dir=args.output)
    resultado = automation.procesar(propiedades_df, args.nombre_cliente, cliente_texto)

    for clave in ["excel", "kml", "mapa"]:
        ruta = resultado.get(clave)
        if ruta:
            print(f"{clave}: {ruta}")
        else:
            print(f"{clave}: no se generó (faltan coordenadas)")

    print("Resumen cliente:")
    for campo, valor in resultado.get("cliente", {}).items():
        print(f"  - {campo}: {valor}")
    return resultado


if __name__ == "__main__":
    main()
