"""Catálogo de equipos FV — mercado chileno 2025/2026.

Valores compilados desde proveedores y distribuidores locales:
  • EMAT Chile          (ematchile.com)        — Jinko, JA, Pylontech, BYD
  • Tritec Center       (tritec-center.cl)     — Jinko, Trina, Sungrow
  • Natura Energy       (naturaenergy.cl)      — Victron, Huawei, Growatt, Dyness
  • Enertik             (enertik.com/cl)       — Growatt, multi-marca
  • TodoSolar           (todosolarchile.cl)    — multi-marca
  • Solarity            (solarity.cl)          — BESS empresarial
  • Rayssa              (rayssa.cl)            — instalador residencial

Precios referenciales: incluyen importación y margen de distribuidor, NO incluyen IVA
ni mano de obra. Conversión asumida CLP/USD = 950 (Mayo 2026).
Las cotizaciones reales deben actualizarse al inicio de cada proyecto.
"""
from typing import TypedDict, Literal


TipoUso = Literal["residencial", "comercial", "industrial", "universal"]


class Panel(TypedDict):
    marca: str
    modelo: str
    Pnom_w: float
    Vmp_v: float
    Imp_a: float
    Voc_v: float
    Isc_a: float
    eficiencia: float
    largo_mm: int
    ancho_mm: int
    area_m2: float
    peso_kg: float
    coef_temp_pmp: float
    NOCT: float
    garantia_anios: int
    precio_usd: float
    tier: int                   # 1 = Tier 1 Bloomberg, 2/3 = otras
    uso_recomendado: TipoUso


class Inversor(TypedDict):
    marca: str
    modelo: str
    P_AC_kw: float
    P_DC_max_kw: float
    n_mppt: int
    V_mppt_min: float
    V_mppt_max: float
    V_max_DC: float
    eficiencia_euro: float
    monofasico: bool
    bess_compatible: bool
    garantia_anios: int
    precio_usd: float
    uso_recomendado: TipoUso


class Bateria(TypedDict):
    marca: str
    modelo: str
    quimica: str
    capacidad_kwh: float
    capacidad_util_kwh: float
    potencia_kw: float
    voltaje_nominal: float
    profundidad_descarga: float
    eficiencia_round_trip: float
    ciclos_garantia: int
    modular: bool
    garantia_anios: int
    precio_usd: float
    uso_recomendado: TipoUso


# ==============================================================
#  PANELES — 20 modelos representativos del mercado chileno
# ==============================================================
PANELES: list[Panel] = [
    # --- Residencial / pequeño comercial (400-460 W, livianos para techo) ---
    {"marca": "JinkoSolar", "modelo": "Tiger Neo N-type 440W",
     "Pnom_w": 440, "Vmp_v": 33.7, "Imp_a": 13.1, "Voc_v": 40.6, "Isc_a": 13.9,
     "eficiencia": 22.0, "largo_mm": 1762, "ancho_mm": 1134, "area_m2": 2.00, "peso_kg": 21.5,
     "coef_temp_pmp": -0.29, "NOCT": 43, "garantia_anios": 25,
     "precio_usd": 110, "tier": 1, "uso_recomendado": "residencial"},
    {"marca": "Trina Solar", "modelo": "Vertex S+ 440W TOPCon",
     "Pnom_w": 440, "Vmp_v": 34.0, "Imp_a": 12.9, "Voc_v": 40.8, "Isc_a": 13.7,
     "eficiencia": 22.5, "largo_mm": 1762, "ancho_mm": 1134, "area_m2": 2.00, "peso_kg": 21.0,
     "coef_temp_pmp": -0.30, "NOCT": 43, "garantia_anios": 25,
     "precio_usd": 115, "tier": 1, "uso_recomendado": "residencial"},
    {"marca": "JA Solar", "modelo": "DeepBlue 4.0X 420W",
     "Pnom_w": 420, "Vmp_v": 32.8, "Imp_a": 12.8, "Voc_v": 39.3, "Isc_a": 13.6,
     "eficiencia": 21.5, "largo_mm": 1722, "ancho_mm": 1134, "area_m2": 1.95, "peso_kg": 21.2,
     "coef_temp_pmp": -0.32, "NOCT": 45, "garantia_anios": 25,
     "precio_usd": 100, "tier": 1, "uso_recomendado": "residencial"},
    {"marca": "Sunova",     "modelo": "Mono 450W (econ.)",
     "Pnom_w": 450, "Vmp_v": 34.5, "Imp_a": 13.0, "Voc_v": 41.5, "Isc_a": 13.8,
     "eficiencia": 21.0, "largo_mm": 1762, "ancho_mm": 1134, "area_m2": 2.00, "peso_kg": 22.0,
     "coef_temp_pmp": -0.35, "NOCT": 45, "garantia_anios": 12,
     "precio_usd": 95, "tier": 2, "uso_recomendado": "residencial"},

    # --- Comercial / mediana escala (500-580 W, el sweet spot del mercado) ---
    {"marca": "JinkoSolar", "modelo": "Tiger Neo N-type 550W",
     "Pnom_w": 550, "Vmp_v": 42.0, "Imp_a": 13.1, "Voc_v": 50.5, "Isc_a": 13.9,
     "eficiencia": 21.3, "largo_mm": 2278, "ancho_mm": 1134, "area_m2": 2.58, "peso_kg": 27.5,
     "coef_temp_pmp": -0.30, "NOCT": 45, "garantia_anios": 25,
     "precio_usd": 122, "tier": 1, "uso_recomendado": "comercial"},
    {"marca": "JinkoSolar", "modelo": "Tiger Neo N-type 580W",
     "Pnom_w": 580, "Vmp_v": 43.6, "Imp_a": 13.3, "Voc_v": 52.3, "Isc_a": 14.1,
     "eficiencia": 22.4, "largo_mm": 2278, "ancho_mm": 1134, "area_m2": 2.58, "peso_kg": 27.0,
     "coef_temp_pmp": -0.29, "NOCT": 44, "garantia_anios": 25,
     "precio_usd": 130, "tier": 1, "uso_recomendado": "comercial"},
    {"marca": "Trina Solar", "modelo": "Vertex S+ 550W",
     "Pnom_w": 550, "Vmp_v": 41.8, "Imp_a": 13.2, "Voc_v": 50.0, "Isc_a": 13.9,
     "eficiencia": 21.5, "largo_mm": 2278, "ancho_mm": 1134, "area_m2": 2.58, "peso_kg": 27.5,
     "coef_temp_pmp": -0.30, "NOCT": 44, "garantia_anios": 25,
     "precio_usd": 125, "tier": 1, "uso_recomendado": "comercial"},
    {"marca": "Canadian Solar", "modelo": "HiKu7 580W",
     "Pnom_w": 580, "Vmp_v": 41.6, "Imp_a": 13.9, "Voc_v": 50.0, "Isc_a": 14.7,
     "eficiencia": 21.8, "largo_mm": 2278, "ancho_mm": 1134, "area_m2": 2.58, "peso_kg": 28.0,
     "coef_temp_pmp": -0.34, "NOCT": 45, "garantia_anios": 25,
     "precio_usd": 128, "tier": 1, "uso_recomendado": "comercial"},
    {"marca": "LONGi",      "modelo": "Hi-MO 6 Explorer 580W",
     "Pnom_w": 580, "Vmp_v": 43.6, "Imp_a": 13.3, "Voc_v": 52.3, "Isc_a": 14.1,
     "eficiencia": 22.4, "largo_mm": 2278, "ancho_mm": 1134, "area_m2": 2.58, "peso_kg": 27.0,
     "coef_temp_pmp": -0.29, "NOCT": 44, "garantia_anios": 25,
     "precio_usd": 128, "tier": 1, "uso_recomendado": "comercial"},
    {"marca": "ZN Shine",   "modelo": "ZXM7-SHLDD144 550W",
     "Pnom_w": 550, "Vmp_v": 41.5, "Imp_a": 13.2, "Voc_v": 49.5, "Isc_a": 13.9,
     "eficiencia": 21.3, "largo_mm": 2278, "ancho_mm": 1134, "area_m2": 2.58, "peso_kg": 27.5,
     "coef_temp_pmp": -0.35, "NOCT": 45, "garantia_anios": 12,
     "precio_usd": 113, "tier": 2, "uso_recomendado": "comercial"},

    # --- Industrial / utility (600-700 W, módulos grandes para minimizar BoS) ---
    {"marca": "Canadian Solar", "modelo": "HiKu7 610W",
     "Pnom_w": 610, "Vmp_v": 41.4, "Imp_a": 14.7, "Voc_v": 49.8, "Isc_a": 15.7,
     "eficiencia": 21.6, "largo_mm": 2384, "ancho_mm": 1186, "area_m2": 2.83, "peso_kg": 32.0,
     "coef_temp_pmp": -0.34, "NOCT": 45, "garantia_anios": 25,
     "precio_usd": 138, "tier": 1, "uso_recomendado": "industrial"},
    {"marca": "JA Solar",   "modelo": "DeepBlue 4.0X 630W",
     "Pnom_w": 630, "Vmp_v": 41.6, "Imp_a": 15.1, "Voc_v": 50.0, "Isc_a": 16.2,
     "eficiencia": 22.0, "largo_mm": 2384, "ancho_mm": 1186, "area_m2": 2.83, "peso_kg": 32.5,
     "coef_temp_pmp": -0.32, "NOCT": 45, "garantia_anios": 25,
     "precio_usd": 145, "tier": 1, "uso_recomendado": "industrial"},
    {"marca": "JinkoSolar", "modelo": "Tiger Neo 78HL4-BDV 620W (bifacial)",
     "Pnom_w": 620, "Vmp_v": 41.0, "Imp_a": 15.1, "Voc_v": 49.5, "Isc_a": 16.2,
     "eficiencia": 22.6, "largo_mm": 2465, "ancho_mm": 1134, "area_m2": 2.80, "peso_kg": 32.5,
     "coef_temp_pmp": -0.29, "NOCT": 45, "garantia_anios": 30,
     "precio_usd": 158, "tier": 1, "uso_recomendado": "industrial"},
    {"marca": "Trina Solar", "modelo": "Vertex N TOPCon 700W (utility)",
     "Pnom_w": 700, "Vmp_v": 44.0, "Imp_a": 15.9, "Voc_v": 52.6, "Isc_a": 17.0,
     "eficiencia": 22.8, "largo_mm": 2384, "ancho_mm": 1303, "area_m2": 3.11, "peso_kg": 38.5,
     "coef_temp_pmp": -0.28, "NOCT": 43, "garantia_anios": 30,
     "precio_usd": 175, "tier": 1, "uso_recomendado": "industrial"},
]


# ==============================================================
#  INVERSORES — 15 modelos por escala y tipo
# ==============================================================
INVERSORES: list[Inversor] = [
    # --- Residencial monofásico ---
    {"marca": "Growatt", "modelo": "MIN 3000TL-X",
     "P_AC_kw": 3.0, "P_DC_max_kw": 3.6, "n_mppt": 2,
     "V_mppt_min": 80, "V_mppt_max": 500, "V_max_DC": 600,
     "eficiencia_euro": 97.0, "monofasico": True, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 380, "uso_recomendado": "residencial"},
    {"marca": "Huawei", "modelo": "SUN2000-3KTL-L1",
     "P_AC_kw": 3.0, "P_DC_max_kw": 3.9, "n_mppt": 2,
     "V_mppt_min": 100, "V_mppt_max": 500, "V_max_DC": 600,
     "eficiencia_euro": 97.5, "monofasico": True, "bess_compatible": True,
     "garantia_anios": 10, "precio_usd": 520, "uso_recomendado": "residencial"},
    {"marca": "Huawei", "modelo": "SUN2000-5KTL-L1",
     "P_AC_kw": 5.0, "P_DC_max_kw": 6.5, "n_mppt": 2,
     "V_mppt_min": 100, "V_mppt_max": 500, "V_max_DC": 600,
     "eficiencia_euro": 97.6, "monofasico": True, "bess_compatible": True,
     "garantia_anios": 10, "precio_usd": 750, "uso_recomendado": "residencial"},
    {"marca": "Growatt", "modelo": "MIN 6000TL-XH (híbrido)",
     "P_AC_kw": 6.0, "P_DC_max_kw": 7.8, "n_mppt": 2,
     "V_mppt_min": 80, "V_mppt_max": 550, "V_max_DC": 600,
     "eficiencia_euro": 97.5, "monofasico": True, "bess_compatible": True,
     "garantia_anios": 10, "precio_usd": 980, "uso_recomendado": "residencial"},
    {"marca": "Fronius", "modelo": "Primo 5.0-1",
     "P_AC_kw": 5.0, "P_DC_max_kw": 7.5, "n_mppt": 2,
     "V_mppt_min": 80, "V_mppt_max": 800, "V_max_DC": 1000,
     "eficiencia_euro": 97.8, "monofasico": True, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 1450, "uso_recomendado": "residencial"},

    # --- Comercial trifásico (10-50 kW) ---
    {"marca": "Sungrow", "modelo": "SG10RT",
     "P_AC_kw": 10.0, "P_DC_max_kw": 13.0, "n_mppt": 2,
     "V_mppt_min": 200, "V_mppt_max": 850, "V_max_DC": 1100,
     "eficiencia_euro": 98.0, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 1180, "uso_recomendado": "comercial"},
    {"marca": "Huawei", "modelo": "SUN2000-12KTL-M2",
     "P_AC_kw": 12.0, "P_DC_max_kw": 15.6, "n_mppt": 2,
     "V_mppt_min": 200, "V_mppt_max": 1000, "V_max_DC": 1100,
     "eficiencia_euro": 98.4, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 1450, "uso_recomendado": "comercial"},
    {"marca": "Sungrow", "modelo": "SG33CX",
     "P_AC_kw": 33.0, "P_DC_max_kw": 42.9, "n_mppt": 3,
     "V_mppt_min": 200, "V_mppt_max": 1000, "V_max_DC": 1100,
     "eficiencia_euro": 98.5, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 3200, "uso_recomendado": "comercial"},
    {"marca": "Huawei", "modelo": "SUN2000-36KTL-M3",
     "P_AC_kw": 36.0, "P_DC_max_kw": 46.8, "n_mppt": 4,
     "V_mppt_min": 200, "V_mppt_max": 1000, "V_max_DC": 1100,
     "eficiencia_euro": 98.6, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 3650, "uso_recomendado": "comercial"},
    {"marca": "SMA", "modelo": "Sunny Tripower CORE1 50",
     "P_AC_kw": 50.0, "P_DC_max_kw": 65.0, "n_mppt": 6,
     "V_mppt_min": 360, "V_mppt_max": 1000, "V_max_DC": 1000,
     "eficiencia_euro": 98.4, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 6200, "uso_recomendado": "comercial"},

    # --- Industrial / utility (≥60 kW) ---
    {"marca": "Sungrow", "modelo": "SG80KTL",
     "P_AC_kw": 80.0, "P_DC_max_kw": 104.0, "n_mppt": 8,
     "V_mppt_min": 200, "V_mppt_max": 1000, "V_max_DC": 1100,
     "eficiencia_euro": 98.6, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 7400, "uso_recomendado": "industrial"},
    {"marca": "Huawei", "modelo": "SUN2000-100KTL-M2",
     "P_AC_kw": 100.0, "P_DC_max_kw": 150.0, "n_mppt": 10,
     "V_mppt_min": 200, "V_mppt_max": 1100, "V_max_DC": 1100,
     "eficiencia_euro": 98.8, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 8900, "uso_recomendado": "industrial"},
    {"marca": "Growatt", "modelo": "MAX 100KTL3-LV",
     "P_AC_kw": 100.0, "P_DC_max_kw": 130.0, "n_mppt": 10,
     "V_mppt_min": 200, "V_mppt_max": 1000, "V_max_DC": 1100,
     "eficiencia_euro": 98.6, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 7100, "uso_recomendado": "industrial"},
    {"marca": "SMA", "modelo": "Sunny Tripower CORE2 110",
     "P_AC_kw": 110.0, "P_DC_max_kw": 150.0, "n_mppt": 12,
     "V_mppt_min": 200, "V_mppt_max": 1000, "V_max_DC": 1000,
     "eficiencia_euro": 98.8, "monofasico": False, "bess_compatible": False,
     "garantia_anios": 10, "precio_usd": 11500, "uso_recomendado": "industrial"},
]


# ==============================================================
#  BATERÍAS — 10 modelos LFP disponibles en Chile
# ==============================================================
BATERIAS: list[Bateria] = [
    # Residencial pequeño (3-7 kWh modular)
    {"marca": "Pylontech", "modelo": "US3000C",
     "quimica": "LFP", "capacidad_kwh": 3.5, "capacidad_util_kwh": 3.3,
     "potencia_kw": 1.8, "voltaje_nominal": 48,
     "profundidad_descarga": 0.95, "eficiencia_round_trip": 0.95,
     "ciclos_garantia": 6000, "modular": True, "garantia_anios": 10,
     "precio_usd": 1750, "uso_recomendado": "residencial"},
    {"marca": "BYD", "modelo": "Battery-Box Premium LV Flex Lite 5.0",
     "quimica": "LFP", "capacidad_kwh": 5.0, "capacidad_util_kwh": 4.8,
     "potencia_kw": 3.7, "voltaje_nominal": 51.2,
     "profundidad_descarga": 0.96, "eficiencia_round_trip": 0.96,
     "ciclos_garantia": 6000, "modular": True, "garantia_anios": 10,
     "precio_usd": 2650, "uso_recomendado": "residencial"},
    {"marca": "Dyness", "modelo": "PowerBox Pro 5.12",
     "quimica": "LFP", "capacidad_kwh": 5.12, "capacidad_util_kwh": 4.8,
     "potencia_kw": 5.0, "voltaje_nominal": 51.2,
     "profundidad_descarga": 0.95, "eficiencia_round_trip": 0.95,
     "ciclos_garantia": 6000, "modular": True, "garantia_anios": 10,
     "precio_usd": 2200, "uso_recomendado": "residencial"},
    {"marca": "BYD", "modelo": "Battery-Box Premium HVS 7.7",
     "quimica": "LFP", "capacidad_kwh": 7.68, "capacidad_util_kwh": 7.4,
     "potencia_kw": 5.0, "voltaje_nominal": 256,
     "profundidad_descarga": 0.96, "eficiencia_round_trip": 0.96,
     "ciclos_garantia": 6000, "modular": True, "garantia_anios": 10,
     "precio_usd": 4200, "uso_recomendado": "residencial"},

    # Residencial mediano / comercial pequeño (10-15 kWh)
    {"marca": "Tesla", "modelo": "Powerwall 3",
     "quimica": "LFP", "capacidad_kwh": 13.5, "capacidad_util_kwh": 13.5,
     "potencia_kw": 11.5, "voltaje_nominal": 48,
     "profundidad_descarga": 1.00, "eficiencia_round_trip": 0.97,
     "ciclos_garantia": 6000, "modular": False, "garantia_anios": 10,
     "precio_usd": 7500, "uso_recomendado": "residencial"},
    {"marca": "Huawei", "modelo": "LUNA2000-15-S0",
     "quimica": "LFP", "capacidad_kwh": 15.0, "capacidad_util_kwh": 15.0,
     "potencia_kw": 7.0, "voltaje_nominal": 360,
     "profundidad_descarga": 1.00, "eficiencia_round_trip": 0.95,
     "ciclos_garantia": 6000, "modular": True, "garantia_anios": 10,
     "precio_usd": 6800, "uso_recomendado": "residencial"},
    {"marca": "BYD", "modelo": "Battery-Box Premium HVS 10.2",
     "quimica": "LFP", "capacidad_kwh": 10.24, "capacidad_util_kwh": 9.85,
     "potencia_kw": 5.0, "voltaje_nominal": 256,
     "profundidad_descarga": 0.96, "eficiencia_round_trip": 0.96,
     "ciclos_garantia": 6000, "modular": True, "garantia_anios": 10,
     "precio_usd": 5500, "uso_recomendado": "residencial"},

    # Comercial / industrial (≥ 25 kWh modular)
    {"marca": "Pylontech", "modelo": "Force-H2 7.1 (rack)",
     "quimica": "LFP", "capacidad_kwh": 7.1, "capacidad_util_kwh": 6.74,
     "potencia_kw": 5.0, "voltaje_nominal": 384,
     "profundidad_descarga": 0.95, "eficiencia_round_trip": 0.96,
     "ciclos_garantia": 6000, "modular": True, "garantia_anios": 10,
     "precio_usd": 3400, "uso_recomendado": "comercial"},
    {"marca": "BYD", "modelo": "Battery-Box Premium LVL 15.4 (rack)",
     "quimica": "LFP", "capacidad_kwh": 15.36, "capacidad_util_kwh": 14.7,
     "potencia_kw": 12.0, "voltaje_nominal": 51.2,
     "profundidad_descarga": 0.96, "eficiencia_round_trip": 0.96,
     "ciclos_garantia": 6000, "modular": True, "garantia_anios": 10,
     "precio_usd": 7800, "uso_recomendado": "comercial"},
    {"marca": "Sungrow", "modelo": "PowerStack 100kWh (industrial)",
     "quimica": "LFP", "capacidad_kwh": 100.0, "capacidad_util_kwh": 95.0,
     "potencia_kw": 50.0, "voltaje_nominal": 1500,
     "profundidad_descarga": 0.95, "eficiencia_round_trip": 0.95,
     "ciclos_garantia": 8000, "modular": False, "garantia_anios": 10,
     "precio_usd": 42000, "uso_recomendado": "industrial"},
]


# ==============================================================
#  COSTOS DE INSTALACIÓN (USD por kWp, mercado Chile)
# ==============================================================
COSTOS_REF = {
    "panel_usd_w":          0.22,   # Promedio Tier 1 importado a Chile (CIF)
    "inversor_usd_kw":      130,    # Solo equipo (residencial Huawei/Sungrow)
    "estructura_usd_kw":    90,     # Aluminio + zincado, techo plano
    "cableado_usd_kw":      55,     # DC + AC + canalización
    "tableros_proteccion_usd_kw": 60,
    "ingenieria_usd_kw":    75,     # Proyecto eléctrico + planos + TE-1
    "mano_obra_usd_kw":     220,    # Instalación, cuadrilla 2-3 personas
    "permisos_usd_proyecto": 850,   # SEC + distribuidora + ChileAtiende
    "bateria_usd_kwh":      560,    # LFP residencial instalada (Pylontech US3000)
    "opex_anual_pct":       0.012,  # 1,2% del CAPEX (lavado + mantención + monitoreo)
    "reposicion_inv_anio":  12,
    "reposicion_bess_anio": 10,
}


# ==============================================================
#  ALGORITMOS DE SELECCIÓN AUTOMÁTICA
# ==============================================================
def seleccionar_panel(P_kwp: float, tipo_proyecto: str = "comercial",
                      criterio: str = "balance") -> Panel:
    """Selecciona panel según escala y criterio (precio / eficiencia / balance)."""
    uso_target = {
        "vivienda": "residencial", "edificio_residencial": "comercial",
        "hotel": "comercial", "industria": "industrial",
        "comercial": "comercial", "oficina": "comercial", "manual": "comercial",
    }.get(tipo_proyecto, "comercial")

    # Filtrar candidatos del uso correcto
    candidatos = [p for p in PANELES if p["uso_recomendado"] == uso_target]
    if not candidatos: candidatos = PANELES

    if criterio == "precio":
        # Minimiza USD por watt
        return min(candidatos, key=lambda p: p["precio_usd"] / p["Pnom_w"])
    if criterio == "eficiencia":
        return max(candidatos, key=lambda p: p["eficiencia"])
    # Balance: tier 1 + buena eficiencia + precio razonable
    candidatos_t1 = [p for p in candidatos if p["tier"] == 1] or candidatos
    return max(candidatos_t1, key=lambda p: p["eficiencia"] - p["precio_usd"]/p["Pnom_w"]*5)


def seleccionar_inversor(P_kwp: float, monofasico_ok: bool = True,
                         requiere_bess: bool = False) -> Inversor:
    """Elige inversor por escala. Si P > 8 kWp fuerza trifásico."""
    P_AC_objetivo = P_kwp / 1.20
    candidatos = [i for i in INVERSORES
                  if i["P_AC_kw"] >= P_AC_objetivo * 0.90
                  and i["P_AC_kw"] <= P_AC_objetivo * 1.40]
    if not candidatos:
        candidatos = sorted(INVERSORES, key=lambda i: abs(i["P_AC_kw"] - P_AC_objetivo))[:5]
    if not monofasico_ok or P_AC_objetivo > 8:
        candidatos_tri = [i for i in candidatos if not i["monofasico"]]
        if candidatos_tri: candidatos = candidatos_tri
    if requiere_bess:
        cb = [i for i in candidatos if i["bess_compatible"]]
        if cb: candidatos = cb
    # Mejor: eficiencia alta + precio razonable
    return min(candidatos, key=lambda i: i["precio_usd"] / i["P_AC_kw"] - i["eficiencia_euro"]/2)


def seleccionar_bateria(capacidad_kwh: float, tipo_proyecto: str = "vivienda") -> Bateria:
    """Elige batería que cubra la capacidad solicitada, preferiendo modulares."""
    uso = "residencial" if tipo_proyecto in ("vivienda", "edificio_residencial") else \
          ("industrial" if tipo_proyecto == "industria" else "comercial")
    candidatos = [b for b in BATERIAS if b["uso_recomendado"] == uso] or BATERIAS
    # Ordenar por capacidad ascendente, escoger la primera que cubre
    candidatos_sorted = sorted(candidatos, key=lambda b: b["capacidad_kwh"])
    for b in candidatos_sorted:
        if b["capacidad_kwh"] >= capacidad_kwh:
            return b
    return candidatos_sorted[-1]


def info_catalogo() -> dict:
    return {
        "paneles": len(PANELES),
        "inversores": len(INVERSORES),
        "baterias": len(BATERIAS),
        "marcas_paneles": sorted(set(p["marca"] for p in PANELES)),
        "marcas_inversores": sorted(set(i["marca"] for i in INVERSORES)),
        "marcas_baterias": sorted(set(b["marca"] for b in BATERIAS)),
        "fuentes": [
            "EMAT Chile (ematchile.com)",
            "Tritec Center (tritec-center.cl)",
            "Natura Energy (naturaenergy.cl)",
            "Enertik (enertik.com/cl)",
            "TodoSolar (todosolarchile.cl)",
            "Solarity (solarity.cl)",
            "Rayssa (rayssa.cl)",
        ],
    }
