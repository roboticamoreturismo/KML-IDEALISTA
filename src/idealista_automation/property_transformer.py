"""Transforma los registros crudos en `PropertyRecord`."""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from .data_models import PropertyRecord
from .enrichment import (
    detectar_sotano,
    extraer_bullets,
    inferir_caracteristicas_extra,
    inferir_entorno,
    inferir_estado,
    inferir_orientacion,
)
from .parsers import (
    extraer_coordenadas,
    extraer_id_desde_url,
    limpiar_bool_texto,
    limpiar_entero,
    limpiar_precio,
    limpiar_superficie,
    normalizar_dataframe,
    parse_direccion,
    parse_fecha_publicacion,
    split_tipo_y_direccion,
)


def _get_val(row: pd.Series, key: str) -> str:
    return row.get(key) if key in row else None


def transformar_registros(df: pd.DataFrame) -> List[Dict]:
    df = normalizar_dataframe(df)
    registros: List[Dict] = []
    for _, row in df.iterrows():
        titulo = str(_get_val(row, "item-link") or "").strip()
        tipo_inmueble, direccion_titulo = split_tipo_y_direccion(titulo)
        descripcion = str(_get_val(row, "ellipsis") or "")
        direccion = parse_direccion(direccion_titulo, descripcion)

        precio = limpiar_precio(_get_val(row, "item-price"))
        sup1 = limpiar_superficie(_get_val(row, "item-detail"))
        sup2 = limpiar_superficie(_get_val(row, "item-detail 2"))
        sup_construida = sup1 if sup1 and sup1 >= (sup2 or 0) else sup2
        sup_util = sup2 if sup1 and sup2 and sup2 < sup1 else None

        if not sup_construida and sup1:
            sup_construida = sup1
        if not sup_construida and sup2:
            sup_construida = sup2

        precio_m2 = None
        if precio and sup_construida:
            precio_m2 = round(precio / sup_construida, 2)

        dormitorios = limpiar_entero(_get_val(row, "item-detail"))
        if dormitorios and dormitorios > 10:
            dormitorios = None
        if not dormitorios:
            dormitorios_alt = limpiar_entero(_get_val(row, "item-detail 2"))
            if dormitorios_alt and dormitorios_alt <= 10:
                dormitorios = dormitorios_alt

        banos = limpiar_entero(_get_val(row, "item-detail 2"))
        if banos and banos > 6:
            banos = None

        garaje = limpiar_bool_texto(_get_val(row, "item-parking"))
        precision = _get_val(row, "no-show-address-feedback-text")
        fotos_num = limpiar_entero(_get_val(row, "item-multimedia-pictures__counter"))
        fecha_publicacion = parse_fecha_publicacion(_get_val(row, "fecha_publicacion"))
        fecha_publicacion_date = None
        if fecha_publicacion:
            fecha_publicacion_date = fecha_publicacion.date()

        lat, lon = extraer_coordenadas(_get_val(row, "map-content src"))

        enrichment_entorno = inferir_entorno(descripcion)
        enrichment_caracteristicas = inferir_caracteristicas_extra(descripcion)

        registros.append(
            PropertyRecord(
                id_idealista=extraer_id_desde_url(_get_val(row, "item-link href")),
                titulo=titulo,
                tipo_inmueble=tipo_inmueble,
                link_anuncio=_get_val(row, "item-link href"),
                link_video=_get_val(row, "video"),
                img_principal=_get_val(row, "item-gallery src") or _get_val(row, "gallery-fallback src"),
                lat=lat,
                lon=lon,
                via_prefijo=direccion["via_prefijo"],
                via_nombre=direccion["via_nombre"],
                via_numero=direccion["via_numero"],
                barrio=direccion["barrio"],
                ciudad=direccion["ciudad"],
                provincia=direccion["provincia"],
                cp=direccion["cp"],
                direccion_completa=direccion["direccion_completa"],
                precision_ubicacion=precision,
                precio_eur=precio,
                sup_construida_m2=sup_construida,
                sup_util_m2=sup_util,
                sup_parcela_m2=limpiar_superficie(_get_val(row, "superficie_parcela")),
                precio_m2=precio_m2,
                dormitorios=dormitorios,
                banos=banos,
                garaje_incluido=garaje,
                garaje_capacidad=limpiar_entero(_get_val(row, "garaje_capacidad")),
                sotano=detectar_sotano(descripcion),
                plantas=_get_val(row, "plantas"),
                orientacion=inferir_orientacion(descripcion),
                estado_conservacion=inferir_estado(descripcion),
                etiquetas_estado=_get_val(row, "listing-tags"),
                necesidad_reforma=_get_val(row, "necesidad_reforma"),
                composicion_estancias=_get_val(row, "composicion"),
                elementos_edificio=enrichment_caracteristicas.get("elementos_edificio"),
                caracteristicas_extra=enrichment_caracteristicas.get("caracteristicas_extra"),
                fotos_num=fotos_num,
                desc_breve=descripcion,
                desc_bullets=extraer_bullets(descripcion),
                agencia_nombre=_get_val(row, "agencia"),
                fecha_publicacion=fecha_publicacion_date,
                anio_construccion=_get_val(row, "anio_construccion"),
                uso_actividad=enrichment_caracteristicas.get("uso_actividad"),
                redistribucion_posible=enrichment_caracteristicas.get("redistribucion_posible"),
                n_viviendas_finca=limpiar_entero(_get_val(row, "n_viviendas_finca")),
                invernadero=_get_val(row, "invernadero"),
                entorno_proximidades=enrichment_entorno.get("entorno_proximidades"),
                entorno_tiempo_capital=enrichment_entorno.get("entorno_tiempo_capital"),
                entorno_tipo=enrichment_entorno.get("entorno_tipo"),
                luminosidad_nivel=enrichment_entorno.get("luminosidad_nivel"),
            ).__dict__
        )
    return registros
