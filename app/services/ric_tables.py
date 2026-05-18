"""Tablas RIC — potencia mínima por uso de recinto, cargas dedicadas y factores
de demanda y simultaneidad.

Las cifras son orientativas y basadas en los pliegos vigentes del Reglamento
de Instalaciones de Consumo (SEC Chile), específicamente:
  • RIC N°06 — Instalaciones interiores BT
  • RIC N°07 — Dimensionamiento de protecciones y conductores
  • NCh Elec 4/2003 (referencia histórica complementaria)

Estos valores deben validarse por un instalador eléctrico autorizado clase A/B/C/D
antes de presentar TE-1 a la SEC. La herramienta entrega predimensionamiento.
"""
from typing import TypedDict


class CargaUso(TypedDict):
    alumbrado_w_m2: float    # W/m² para circuito de alumbrado
    enchufes_w_m2: float     # W/m² para circuito de enchufes generales
    descripcion: str


# Cargas mínimas por uso del recinto (W/m²)
CARGAS_POR_USO: dict[str, CargaUso] = {
    "living":       {"alumbrado_w_m2": 10, "enchufes_w_m2": 15, "descripcion": "Living / sala"},
    "comedor":      {"alumbrado_w_m2": 10, "enchufes_w_m2": 15, "descripcion": "Comedor"},
    "dormitorio":   {"alumbrado_w_m2": 10, "enchufes_w_m2": 15, "descripcion": "Dormitorio"},
    "cocina":       {"alumbrado_w_m2": 15, "enchufes_w_m2": 30, "descripcion": "Cocina (sin cargas dedicadas)"},
    "bano":         {"alumbrado_w_m2": 15, "enchufes_w_m2": 10, "descripcion": "Baño"},
    "oficina":      {"alumbrado_w_m2": 12, "enchufes_w_m2": 20, "descripcion": "Oficina / estudio"},
    "hall":         {"alumbrado_w_m2": 5,  "enchufes_w_m2": 5,  "descripcion": "Hall / recibidor"},
    "pasillo":      {"alumbrado_w_m2": 5,  "enchufes_w_m2": 5,  "descripcion": "Pasillo / circulación"},
    "circulacion":  {"alumbrado_w_m2": 5,  "enchufes_w_m2": 5,  "descripcion": "Circulación"},
    "exterior":     {"alumbrado_w_m2": 5,  "enchufes_w_m2": 5,  "descripcion": "Terraza / balcón"},
    "lavanderia":   {"alumbrado_w_m2": 10, "enchufes_w_m2": 10, "descripcion": "Lavandería / logia"},
    "logia":        {"alumbrado_w_m2": 10, "enchufes_w_m2": 10, "descripcion": "Logia"},
    "bodega":       {"alumbrado_w_m2": 5,  "enchufes_w_m2": 5,  "descripcion": "Bodega / despensa"},
    "comun":        {"alumbrado_w_m2": 8,  "enchufes_w_m2": 10, "descripcion": "Área común edificio"},
    "desconocido":  {"alumbrado_w_m2": 10, "enchufes_w_m2": 15, "descripcion": "Sin asignar (default vivienda)"},
}


class CargaDedicada(TypedDict):
    nombre: str
    potencia_w: float
    aplica_uso: list[str]    # En qué tipo de recinto aplica
    por_defecto: bool        # Se asume presente o el usuario debe confirmarla
    descripcion: str


# Cargas dedicadas típicas en una vivienda chilena. Cada una requiere su propio
# circuito según RIC N°06 (protección dedicada).
CARGAS_DEDICADAS_VIVIENDA: list[CargaDedicada] = [
    {"nombre": "Cocina/horno eléctrico", "potencia_w": 5500, "aplica_uso": ["cocina"], "por_defecto": False,
     "descripcion": "Si la vivienda no usa cocina a gas. Circuito 25A dedicado."},
    {"nombre": "Microondas",             "potencia_w": 1500, "aplica_uso": ["cocina"], "por_defecto": True,
     "descripcion": "Circuito de enchufes encimera 16A."},
    {"nombre": "Lavadora",               "potencia_w": 2200, "aplica_uso": ["lavanderia", "cocina", "logia"], "por_defecto": True,
     "descripcion": "Circuito 16A dedicado."},
    {"nombre": "Secadora",               "potencia_w": 3000, "aplica_uso": ["lavanderia", "logia"], "por_defecto": False,
     "descripcion": "Si hay secadora eléctrica. Circuito 16A."},
    {"nombre": "Lavavajillas",           "potencia_w": 1800, "aplica_uso": ["cocina"], "por_defecto": False,
     "descripcion": "Circuito 16A dedicado."},
    {"nombre": "Refrigerador",           "potencia_w": 300,  "aplica_uso": ["cocina"], "por_defecto": True,
     "descripcion": "Comparte circuito de enchufes cocina."},
    {"nombre": "Calefón / termo eléctrico", "potencia_w": 5500, "aplica_uso": ["bano", "cocina"], "por_defecto": False,
     "descripcion": "Solo si NO hay calefón a gas. Circuito 25A dedicado."},
    {"nombre": "Ducha eléctrica",        "potencia_w": 5500, "aplica_uso": ["bano"], "por_defecto": False,
     "descripcion": "Alternativa al calefón. Circuito 25A dedicado."},
    {"nombre": "Aire acondicionado split", "potencia_w": 2200, "aplica_uso": ["living", "dormitorio", "oficina"], "por_defecto": False,
     "descripcion": "Por cada equipo. Circuito 16A."},
    {"nombre": "Calefactor eléctrico", "potencia_w": 1800, "aplica_uso": ["living", "dormitorio"], "por_defecto": False,
     "descripcion": "Estufa eléctrica fija. Circuito 16A."},
]


# Factor de demanda según superficie total (vivienda BT1). Más superficie = más
# diversidad = menor factor.
def factor_demanda_vivienda(area_total_m2: float) -> float:
    if area_total_m2 < 50:   return 1.00   # Aplicar 100% por ser instalación chica
    if area_total_m2 < 100:  return 0.85
    if area_total_m2 < 200:  return 0.75
    return 0.65


# Factor de simultaneidad por tipo de proyecto (entre cargas simultáneas)
FACTOR_SIMULTANEIDAD = {
    "vivienda":             0.65,
    "edificio_residencial": 0.40,    # Entre departamentos
    "hotel":                0.55,
    "industria":            0.85,
    "comercial":            0.75,
    "oficina":              0.70,
    "manual":               0.70,
}


# Demanda kVA → corriente nominal según tensión y conexión
TENSIONES = {
    "monofasica_220":   {"V": 220,  "phases": 1},
    "bifasica_220":     {"V": 220,  "phases": 2},
    "trifasica_380":    {"V": 380,  "phases": 3},
}


def corriente_nominal(potencia_w: float, conexion: str = "monofasica_220",
                      factor_potencia: float = 0.93) -> float:
    """Corriente nominal del empalme en Amperes."""
    cfg = TENSIONES.get(conexion, TENSIONES["monofasica_220"])
    V = cfg["V"]
    if cfg["phases"] == 1:
        return potencia_w / (V * factor_potencia)
    elif cfg["phases"] == 2:
        return potencia_w / (V * factor_potencia)
    else:  # trifásica
        return potencia_w / (1.732 * V * factor_potencia)


def tipo_empalme_sugerido(corriente_a: float, conexion: str = "monofasica_220") -> str:
    """Sugiere tipo de empalme según corriente. Valores estándar SEC."""
    # Empalmes residenciales/comerciales típicos chilenos (CGE, Enel)
    escalera = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400]
    for nominal in escalera:
        if corriente_a <= nominal:
            phases = "monofásico" if "mono" in conexion else ("bifásico" if "bif" in conexion else "trifásico")
            return f"{nominal} A {phases}"
    return f">400 A {conexion} — evaluar AT"
