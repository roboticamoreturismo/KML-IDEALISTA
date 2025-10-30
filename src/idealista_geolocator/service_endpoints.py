"""Funciones auxiliares para exponer descargas en la interfaz."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict

from .data_models import ExportResult, PropertyRecord


def build_property_payload(records: Dict[str, PropertyRecord]) -> Dict[str, Dict[str, str]]:
    return {identifier: asdict(record) for identifier, record in records.items()}


def load_file_bytes(path: Path) -> bytes:
    return path.read_bytes()


def export_paths_to_dict(result: ExportResult) -> Dict[str, str]:
    payload = {"excel": str(result.excel_path), "json": str(result.resumen_json_path)}
    if result.kml_path is not None:
        payload["kml"] = str(result.kml_path)
    return payload

