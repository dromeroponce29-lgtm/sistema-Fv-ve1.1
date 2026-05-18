"""Tarifas eléctricas chilenas (referenciales, editables).

Fuente: pliegos tarifarios SEC/CNE vigentes a 2024. Los valores se actualizan
trimestralmente — el motor permite override por proyecto.

Categorías cubiertas:
  BT1 — Residencial baja tensión, hasta 10 kW de potencia contratada.
        Cargo fijo + cargo por energía. Tarifa simple regulada.
  BT2 — Comercial/industrial baja tensión con potencia contratada (10-300 kW).
        Cargo fijo + cargo por potencia contratada + cargo por energía.
  BT4 — Comercial/industrial baja tensión con discriminación horaria
        (punta vs. valle). Se usa en empalmes ≥ 50 kW.

Empalmes monofásicos disponibles en Chile (escala IEC):
  10, 16, 20, 25, 32, 40 A → 2.2 a 8.8 kW @ 220 V × 0.93 FP

Empalmes trifásicos:
  10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400 A
  → 5.7 kW (10A) a 230 kW (400A) @ 380 V × 0.93 FP

Costos referenciales (CLP, ajustables):
  - Cargo fijo BT1: $1.800 CLP/mes
  - Cargo variable BT1: $165 CLP/kWh
  - Cargo fijo BT2: $4.500 CLP/mes
  - Cargo por potencia contratada BT2: $4.200 CLP/kW-mes
  - Cargo variable BT2: $145 CLP/kWh
  - Costo instalación empalme monofásico chico (≤25 A): ~$280.000 CLP inicial
  - Costo instalación empalme trifásico estándar: ~$650.000 CLP inicial
"""
from typing import Literal

CategoriaTarifa = Literal["BT1", "BT2", "BT4_punta"]


# ─── Valores referenciales por defecto (editables) ────────────────────────────
TARIFAS_DEFAULT = {
    "BT1": {
        "cargo_fijo_clp_mes":     1800,
        "cargo_variable_clp_kwh":  165,
        "potencia_max_kw":          10,
        "comentario": "Residencial. Cargo fijo + cargo por energía. Sin discriminación horaria.",
    },
    "BT2": {
        "cargo_fijo_clp_mes":     4500,
        "cargo_pot_clp_kwmes":    4200,
        "cargo_variable_clp_kwh":  145,
        "potencia_min_kw":          10,
        "potencia_max_kw":         300,
        "comentario": "Comercial/industrial con potencia contratada. Aplica cargo por kW contratado.",
    },
    "BT4_punta": {
        "cargo_fijo_clp_mes":     6500,
        "cargo_pot_clp_kwmes":    7800,
        "cargo_variable_clp_kwh_punta":  220,
        "cargo_variable_clp_kwh_valle":  120,
        "potencia_min_kw":          50,
        "comentario": "BT4 con discriminación horaria. Punta vs valle. Recomendado >50 kW industriales.",
    },
}

# Escalas IEC chilenas para amperaje de empalmes
ESCALA_AMP_MONOFASICO = [10, 16, 20, 25, 32, 40]                          # ≤ 8.8 kW
ESCALA_AMP_TRIFASICO  = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125,    # ≤ 230 kW
                        160, 200, 250, 315, 400]

# Costo aproximado de instalación del empalme (CLP, IVA incl.)
COSTO_EMPALME_CLP = {
    "monofasico_10A":   280_000,
    "monofasico_16A":   320_000,
    "monofasico_25A":   380_000,
    "monofasico_32A":   430_000,
    "monofasico_40A":   480_000,
    "trifasico_25A":    580_000,
    "trifasico_40A":    680_000,
    "trifasico_63A":    850_000,
    "trifasico_100A": 1_100_000,
    "trifasico_160A": 1_450_000,
}


def amperaje_para_potencia(P_kw: float, monofasico: bool, fp: float = 0.93) -> tuple[int, str]:
    """Devuelve (amperaje, etiqueta) del empalme mínimo que cubre P_kw.

    Aplica margen de seguridad del 15% sobre la corriente nominal.
    """
    V = 220 if monofasico else 380
    if monofasico:
        I = P_kw * 1000 / (V * fp)
    else:
        I = P_kw * 1000 / (1.732 * V * fp)
    I_req = I * 1.15
    escala = ESCALA_AMP_MONOFASICO if monofasico else ESCALA_AMP_TRIFASICO
    amp = next((a for a in escala if a >= I_req), escala[-1])
    label = f"{amp} A {'monofásico (BT1/BT2)' if monofasico else 'trifásico (BT2/BT4)'}"
    return amp, label


def kw_disponibles_empalme(amperaje: int, monofasico: bool, fp: float = 0.93) -> float:
    """Cuántos kW puede entregar un empalme de cierto amperaje."""
    V = 220 if monofasico else 380
    if monofasico:
        return round(amperaje * V * fp / 1000, 2)
    return round(amperaje * V * fp * 1.732 / 1000, 2)


def categoria_recomendada(P_empalme_kw: float, monofasico: bool) -> CategoriaTarifa:
    """Recomienda BT1/BT2/BT4 según potencia del empalme."""
    if monofasico and P_empalme_kw <= 8.5:
        return "BT1"
    if P_empalme_kw <= 50:
        return "BT2"
    return "BT4_punta"


def costo_anual_electricidad(
    categoria: CategoriaTarifa,
    kwh_anuales: float,
    P_empalme_kw: float,
    pct_consumo_punta: float = 0.30,
    tarifas: dict = None,
) -> dict:
    """Calcula el costo anual de electricidad para un escenario dado.

    Args:
        categoria: BT1, BT2 o BT4_punta
        kwh_anuales: kWh comprados a la red en el año (residual tras FV)
        P_empalme_kw: potencia contratada del empalme (kW)
        pct_consumo_punta: fracción del consumo en horario punta (sólo BT4)
        tarifas: override de los valores default

    Returns:
        {
          "cargo_fijo_anual_clp": ...,
          "cargo_potencia_anual_clp": ...,
          "cargo_variable_anual_clp": ...,
          "total_anual_clp": ...,
          "categoria": "BT1",
          "detalle": "..."
        }
    """
    t = (tarifas or TARIFAS_DEFAULT).get(categoria, TARIFAS_DEFAULT["BT1"])
    cf = t["cargo_fijo_clp_mes"] * 12

    if categoria == "BT1":
        cv = kwh_anuales * t["cargo_variable_clp_kwh"]
        cp = 0
        detalle = (f"BT1 residencial: cargo fijo ${t['cargo_fijo_clp_mes']:,}/mes × 12 = "
                   f"${cf:,} + {kwh_anuales:,.0f} kWh × ${t['cargo_variable_clp_kwh']}/kWh "
                   f"= ${int(cv):,}")
    elif categoria == "BT2":
        cv = kwh_anuales * t["cargo_variable_clp_kwh"]
        cp = P_empalme_kw * t["cargo_pot_clp_kwmes"] * 12
        detalle = (f"BT2 c/pot. contratada: fijo ${cf:,} + potencia ${P_empalme_kw:.1f} kW × "
                   f"${t['cargo_pot_clp_kwmes']:,}/kW-mes × 12 = ${int(cp):,} + energía "
                   f"{kwh_anuales:,.0f} kWh × ${t['cargo_variable_clp_kwh']} = ${int(cv):,}")
    else:  # BT4_punta
        kwh_punta = kwh_anuales * pct_consumo_punta
        kwh_valle = kwh_anuales * (1 - pct_consumo_punta)
        cv = (kwh_punta * t["cargo_variable_clp_kwh_punta"]
              + kwh_valle * t["cargo_variable_clp_kwh_valle"])
        cp = P_empalme_kw * t["cargo_pot_clp_kwmes"] * 12
        detalle = (f"BT4 punta: fijo + potencia + {kwh_punta:,.0f} kWh punta × "
                   f"${t['cargo_variable_clp_kwh_punta']} + {kwh_valle:,.0f} kWh valle × "
                   f"${t['cargo_variable_clp_kwh_valle']}")

    total = cf + cp + cv
    return {
        "categoria": categoria,
        "cargo_fijo_anual_clp":      round(cf),
        "cargo_potencia_anual_clp":  round(cp),
        "cargo_variable_anual_clp":  round(cv),
        "total_anual_clp":           round(total),
        "detalle":                   detalle,
    }


def costo_instalacion_empalme(amperaje: int, monofasico: bool) -> int:
    """CLP de inversión inicial para conectar el empalme (incluye trámites, medidor)."""
    tipo = "monofasico" if monofasico else "trifasico"
    key = f"{tipo}_{amperaje}A"
    if key in COSTO_EMPALME_CLP:
        return COSTO_EMPALME_CLP[key]
    # Interpolar
    base_mono = 280_000 + (amperaje - 10) * 7_000
    base_tri  = 580_000 + (amperaje - 25) * 8_500
    return int(base_mono if monofasico else base_tri)
