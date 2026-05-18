"""Helpers compartidos para reporte selectivo.

El frontend envía `secciones_incluidas: list[str]` dentro del dict del proyecto.
Si la lista es None o vacía, todos los reportes incluyen todas las secciones
(comportamiento por defecto, backward-compatible). Si la lista está poblada,
sólo las claves presentes se renderizan en el documento generado.
"""
from typing import Iterable


# Catálogo canónico de claves de sección. Debe estar sincronizado con el
# frontend (tabReporte / generadorReportePersonalizado).
SECCIONES_DISPONIBLES = {
    # Identificación
    "portada_kpis":         "Portada con KPIs principales",
    "resumen_ejecutivo":    "Resumen narrativo en lenguaje ejecutivo",
    # Sitio y consumo
    "sitio":                "Ubicación, coordenadas, recurso solar (PVGIS + NASA)",
    "consumo":              "Cargas RIC, recintos, factor demanda y simultaneidad",
    "balance_fases":        "Balance L1/L2/L3 y desbalance (trifásico)",
    # Diseño FV
    "fv_dimensionamiento":  "Potencia kWp, N° paneles, inversor, pérdidas",
    "generacion_grafica":   "Gráfico de generación mensual vs consumo",
    "bess":                 "Sistema de baterías y autonomía",
    "respaldo":             "Generador / empalme reducido / netbilling",
    "layout":               "Disposición de paneles y aprovechamiento de superficie",
    "unifilar":             "Diagrama unifilar con protecciones DC/AC",
    "puesta_tierra":        "Sistema de puesta a tierra (PAT)",
    # Económico
    "capex":                "Desglose de inversión (CAPEX por partida)",
    "flujo_caja":           "Gráfico y tabla de flujo de caja 25 años",
    "metricas_economicas":  "VAN, TIR, payback, LCOE",
    "presupuesto_equipos":  "BOM con specs de equipos chilenos cotizables",
    "analisis_tarifario":   "Detalle empalme reducido + tarifa BT1/BT2 (Lote E)",
    "comparativa_escenarios": "Comparativa de 3 escenarios A/B/C con TCO 25 años (Lote E)",
    # Impacto y cumplimiento
    "co2_ambiental":        "Reducción CO2 y aporte ambiental",
    "normativa":            "Cumplimiento Ley 21.118, RIC SEC, TE-1",
    "advertencias":         "Disclaimers y limitaciones del predimensionamiento",
}


# Presets pensados para los 3 contextos de envío al cliente.
PRESETS = {
    "cliente_final": [
        "portada_kpis", "resumen_ejecutivo",
        "fv_dimensionamiento", "generacion_grafica", "layout",
        "capex", "metricas_economicas", "co2_ambiental",
        "normativa", "advertencias",
    ],
    "tecnico_sec": [
        "portada_kpis", "resumen_ejecutivo",
        "sitio", "consumo", "balance_fases",
        "fv_dimensionamiento", "generacion_grafica",
        "bess", "respaldo", "layout", "unifilar", "puesta_tierra",
        "capex", "flujo_caja", "metricas_economicas",
        "analisis_tarifario", "comparativa_escenarios",
        "normativa", "advertencias",
    ],
    "presupuesto_comercial": [
        "portada_kpis", "resumen_ejecutivo",
        "fv_dimensionamiento", "bess", "respaldo",
        "presupuesto_equipos", "capex",
        "metricas_economicas", "flujo_caja",
        "comparativa_escenarios", "analisis_tarifario",
        "advertencias",
    ],
}


def seccion_incluida(proyecto: dict, key: str) -> bool:
    """¿Debe incluirse la sección `key` en el reporte de este proyecto?

    - Si `proyecto["secciones_incluidas"]` es None o lista vacía → True (default).
    - Si está poblada → True sólo si `key` está en la lista.
    """
    sel = proyecto.get("secciones_incluidas")
    if not sel:
        return True
    return key in sel


def normalizar_seleccion(seleccion: Iterable[str] | None) -> list[str]:
    """Filtra una selección a las claves válidas del catálogo."""
    if not seleccion:
        return []
    return [k for k in seleccion if k in SECCIONES_DISPONIBLES]
