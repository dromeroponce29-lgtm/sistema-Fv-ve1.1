"""Comparativa de 3 escenarios de continuidad operacional (Lote E).

Escenario A — FV off-grid PURO:
  Sistema 100% solar + BESS dimensionado para N días de autonomía completa.
  CAPEX alto (BESS enorme). OPEX bajo (sólo mantención).
  Riesgo: si la autonomía cae bajo el consumo crítico → corte de operación.

Escenario B — FV off-grid + EMPALME MONOFÁSICO COMPLEMENTARIO (★ recomendado):
  Sistema solar + BESS chico (1-2 días) + empalme monofásico mínimo de respaldo.
  El empalme cubre el déficit residual cuando el BESS se agota.
  CAPEX moderado. OPEX = cargo fijo BT1 + cargo variable × kWh residuales.
  Es la arquitectura más resiliente y económica para clientes que no quieren
  depender 100% de la red pero tampoco gastar en un BESS sobredimensionado.

Escenario C — FV ON-GRID NETBILLING:
  Sistema solar + empalme tradicional + netbilling Ley 21.118.
  Sin BESS o BESS mínimo. Excedentes se inyectan a red y se descuentan en factura.
  CAPEX más bajo. OPEX depende de la cobertura solar y la facturación neta.

La comparativa devuelve, para cada escenario:
  - CAPEX inicial (CLP)
  - OPEX anual (CLP)
  - TCO 25 años descontado (CLP)
  - Recomendación: True / False
  - Texto explicativo

Y al final emite una recomendación: cuál escenario tiene el TCO menor.
"""
from app.services.tarifas_chile import (
    amperaje_para_potencia, kw_disponibles_empalme, categoria_recomendada,
    costo_anual_electricidad, costo_instalacion_empalme,
)


# Defaults editables
TASA_DESCUENTO = 0.08
HORIZONTE_ANIOS = 25
PRECIO_CLP_USD = 950
# Cargos referenciales para BESS adicional (USD/kWh nominal LFP entregado en obra)
COSTO_BESS_USD_KWH = 320
# Factor adicional CAPEX FV (inversor, paneles, estructura, instalación) — USD/kWp
COSTO_FV_USD_KWP = 850


def _valor_presente(flujo_anual: float, anos: int = HORIZONTE_ANIOS,
                     tasa: float = TASA_DESCUENTO) -> float:
    """Valor presente de una anualidad constante."""
    if tasa == 0:
        return flujo_anual * anos
    return flujo_anual * (1 - (1 + tasa) ** -anos) / tasa


def _capex_fv_base(P_kwp: float) -> int:
    """CAPEX base del sistema FV (paneles + inversor + estructura + BoS + instalación)."""
    return int(P_kwp * COSTO_FV_USD_KWP * PRECIO_CLP_USD)


def _capex_bess(kwh_nominales: float) -> int:
    """CAPEX del BESS (LFP, USD 320/kWh entregado)."""
    return int(kwh_nominales * COSTO_BESS_USD_KWH * PRECIO_CLP_USD)


def comparar_3_escenarios(
    consumo_anual_kwh: float,
    cobertura_solar: float,           # fracción del consumo cubierto por FV (0..1)
    P_kwp: float,
    demanda_max_kw: float,
    cons_critico_diario_kwh: float,
    dias_autonomia_objetivo: float = 2.0,
    DoD: float = 0.90,
    eta_rt: float = 0.95,
    bess_capacidad_actual_kwh: float = 0,
    tipo_proyecto: str = "vivienda",
) -> dict:
    """Compara los 3 escenarios y emite recomendación.

    Args:
        consumo_anual_kwh: consumo anual total estimado (kWh)
        cobertura_solar: fracción del consumo que cubre el FV (0..1)
        P_kwp: potencia FV instalada (kWp)
        demanda_max_kw: demanda máxima del sistema (RIC, kW)
        cons_critico_diario_kwh: consumo de cargas críticas por día (kWh/día)
        dias_autonomia_objetivo: días que se quiere cubrir con BESS en escenario A
        DoD: profundidad de descarga del BESS (0..1)
        eta_rt: eficiencia round-trip del BESS (0..1)
        bess_capacidad_actual_kwh: BESS ya dimensionado (escenario base)
        tipo_proyecto: para ajustar contrato BT1/BT2

    Returns:
        dict con escenarios A/B/C + recomendación + datos auxiliares
    """
    capex_fv = _capex_fv_base(P_kwp)
    consumo_residual_anual = consumo_anual_kwh * (1 - cobertura_solar)
    es_residencial = tipo_proyecto in ("vivienda", "edificio_residencial")

    # ───── Escenario A: OFF-GRID PURO ──────────────────────────────────────
    # BESS dimensionado para N días de consumo completo (no sólo crítico)
    bess_A_nominal = consumo_anual_kwh / 365 * dias_autonomia_objetivo / (DoD * eta_rt)
    capex_bess_A   = _capex_bess(bess_A_nominal)
    # Generador como backup obligatorio en off-grid puro? Asumimos NO (puro = sin gen)
    # OPEX: sólo mantención FV + reemplazo BESS a los 12 años
    mantencion_anual_A = capex_fv * 0.01 + capex_bess_A * 0.015  # 1% FV + 1.5% BESS
    reemplazo_bess_vp  = capex_bess_A * 0.5 / (1 + TASA_DESCUENTO) ** 12  # 50% reemplazo en año 12
    opex_anual_A = round(mantencion_anual_A)
    capex_A = capex_fv + capex_bess_A
    tco_A = capex_A + _valor_presente(opex_anual_A) + reemplazo_bess_vp

    # ───── Escenario B (★): FV + BESS chico + EMPALME MONOFÁSICO ──────────
    # BESS dimensionado para sólo 1 día de cargas críticas (no consumo total)
    bess_B_nominal = cons_critico_diario_kwh * 1.0 / (DoD * eta_rt)  # 1 día crítico
    capex_bess_B   = _capex_bess(bess_B_nominal)
    # Empalme monofásico mínimo que cubra demanda residual (cargas no críticas + picos)
    # Estimamos demanda del empalme = max(demanda_max × 0.4, cargas críticas en kW)
    P_empalme_B = max(demanda_max_kw * 0.4, cons_critico_diario_kwh / 12)
    P_empalme_B = min(P_empalme_B, 8.5)  # cap a 8.5 kW (límite BT1 monofásico)
    amp_B, lbl_B = amperaje_para_potencia(P_empalme_B, monofasico=True)
    # En off-grid + empalme complementario, asumimos que ~15% del consumo se compra a red
    # (el residual real cuando BESS está agotado y FV no genera, ej. invierno noche)
    pct_red_B = 0.15
    kwh_red_B = consumo_anual_kwh * pct_red_B
    categoria_B = "BT1" if es_residencial else "BT2"
    costo_red_B = costo_anual_electricidad(categoria_B, kwh_red_B, P_empalme_B)
    capex_empalme_B = costo_instalacion_empalme(amp_B, monofasico=True)
    opex_anual_B = costo_red_B["total_anual_clp"] + round(capex_fv * 0.01 + capex_bess_B * 0.015)
    capex_B = capex_fv + capex_bess_B + capex_empalme_B
    reemplazo_bess_vp_B = capex_bess_B * 0.5 / (1 + TASA_DESCUENTO) ** 12
    tco_B = capex_B + _valor_presente(opex_anual_B) + reemplazo_bess_vp_B

    # ───── Escenario C: ON-GRID NETBILLING ────────────────────────────────
    # Sin BESS (o BESS mínimo opcional, dejamos en 0)
    bess_C_nominal = 0
    capex_bess_C   = 0
    # Empalme estándar dimensionado para 100% demanda
    monofasico_C = demanda_max_kw <= 8.5 and es_residencial
    amp_C, lbl_C = amperaje_para_potencia(demanda_max_kw, monofasico=monofasico_C)
    capex_empalme_C = costo_instalacion_empalme(amp_C, monofasico=monofasico_C)
    categoria_C = categoria_recomendada(demanda_max_kw, monofasico_C)
    # Consumo desde red = consumo total - autoconsumo FV (cobertura efectiva instantánea ~70%)
    autoconsumo_C = consumo_anual_kwh * cobertura_solar * 0.7
    compra_red_C  = consumo_anual_kwh - autoconsumo_C
    # Inyección = excedentes FV no consumidos (30% de la generación FV)
    gen_total = consumo_anual_kwh * cobertura_solar
    inyeccion_C = gen_total * 0.3
    # Ingreso netbilling: ~$70-90 CLP/kWh (precio energía)
    PRECIO_NETBILLING_CLP_KWH = 75
    ingreso_netbilling = inyeccion_C * PRECIO_NETBILLING_CLP_KWH
    costo_red_C = costo_anual_electricidad(categoria_C, compra_red_C, demanda_max_kw)
    opex_anual_C = round(costo_red_C["total_anual_clp"] - ingreso_netbilling + capex_fv * 0.01)
    capex_C = capex_fv + capex_empalme_C
    tco_C = capex_C + _valor_presente(opex_anual_C)

    # ───── Recomendación: menor TCO ────────────────────────────────────────
    tcos = {"A": tco_A, "B": tco_B, "C": tco_C}
    escenario_ganador = min(tcos, key=tcos.get)

    # ───── Empaquetar resultado ────────────────────────────────────────────
    return {
        "horizonte_anios": HORIZONTE_ANIOS,
        "tasa_descuento":  TASA_DESCUENTO,
        "escenario_recomendado": escenario_ganador,
        "ahorro_recomendado_vs_peor_clp": int(max(tcos.values()) - min(tcos.values())),
        "escenarios": {
            "A": {
                "nombre": "FV off-grid puro (BESS gigante, sin red)",
                "icono": "🔋",
                "capex_clp": int(capex_A),
                "capex_desglose": {
                    "FV (paneles+inversor+estructura+instalación)": capex_fv,
                    f"BESS {bess_A_nominal:.0f} kWh nominales":    capex_bess_A,
                },
                "bess_kwh_nominales": round(bess_A_nominal, 1),
                "empalme": "Sin empalme — 100% autónomo",
                "opex_anual_clp": opex_anual_A,
                "tco_25_anios_clp": int(tco_A),
                "es_recomendado": escenario_ganador == "A",
                "pros": ["Independencia total de la red",
                         "Sin cargo fijo eléctrico",
                         "Ideal para zonas remotas sin acceso a empalme"],
                "contras": ["CAPEX BESS muy alto",
                            "Reemplazo BESS a los ~12 años",
                            "Riesgo de corte si autonomía insuficiente",
                            "Sin respaldo ante fallas FV/BESS"],
                "comentario": f"Autonomía objetivo: {dias_autonomia_objetivo} días completos × consumo total. BESS = {bess_A_nominal:.0f} kWh nominales (≈ {round(bess_A_nominal*DoD,0):.0f} kWh útiles).",
            },
            "B": {
                "nombre": "FV off-grid + empalme monofásico complementario ★",
                "icono": "🔌",
                "capex_clp": int(capex_B),
                "capex_desglose": {
                    "FV (paneles+inversor+estructura+instalación)":  capex_fv,
                    f"BESS {bess_B_nominal:.1f} kWh (1 día crítico)": capex_bess_B,
                    f"Empalme {amp_B} A monofásico (instalación)":   capex_empalme_B,
                },
                "bess_kwh_nominales":      round(bess_B_nominal, 1),
                "empalme_amperaje":         amp_B,
                "empalme_label":            lbl_B,
                "empalme_kw_disponibles":   kw_disponibles_empalme(amp_B, True),
                "empalme_categoria":        categoria_B,
                "consumo_red_anual_kwh":    round(kwh_red_B, 0),
                "pct_consumo_de_red":       pct_red_B * 100,
                "costo_red_detalle":        costo_red_B,
                "opex_anual_clp":           opex_anual_B,
                "tco_25_anios_clp":         int(tco_B),
                "es_recomendado":           escenario_ganador == "B",
                "pros": ["Continuidad operacional garantizada",
                         "BESS dimensionado eficiente (1 día crítico, no consumo total)",
                         f"Cargo fijo mínimo (~${costo_red_B['cargo_fijo_anual_clp']/12:,.0f} CLP/mes BT1)",
                         "Empalme chico, bajo trámite SEC"],
                "contras": ["Depende parcialmente de la red para residual (~15% consumo)",
                            "Requiere contrato eléctrico BT1"],
                "comentario": (f"BESS para 1 día de cargas críticas ({cons_critico_diario_kwh:.1f} kWh/día). "
                              f"Empalme {lbl_B} cubre el residual cuando BESS se agota o FV no genera. "
                              f"Consumo estimado desde red: {kwh_red_B:.0f} kWh/año (~{pct_red_B*100:.0f}% del total)."),
            },
            "C": {
                "nombre": "FV on-grid completo + netbilling",
                "icono": "⚡",
                "capex_clp": int(capex_C),
                "capex_desglose": {
                    "FV (paneles+inversor+estructura+instalación)":  capex_fv,
                    f"Empalme {lbl_C} (instalación)":                 capex_empalme_C,
                },
                "bess_kwh_nominales":     0,
                "empalme_amperaje":       amp_C,
                "empalme_label":          lbl_C,
                "empalme_categoria":      categoria_C,
                "compra_red_anual_kwh":   round(compra_red_C, 0),
                "inyeccion_red_anual_kwh": round(inyeccion_C, 0),
                "ingreso_netbilling_clp": int(ingreso_netbilling),
                "costo_red_detalle":      costo_red_C,
                "opex_anual_clp":         opex_anual_C,
                "tco_25_anios_clp":       int(tco_C),
                "es_recomendado":         escenario_ganador == "C",
                "pros": ["CAPEX más bajo (sin BESS)",
                         "Netbilling: ingresos por inyección Ley 21.118",
                         "Mantenimiento mínimo"],
                "contras": ["Cargo fijo mensual del empalme completo",
                            "Sin respaldo ante corte de red",
                            "Si la red cae, el inversor se desconecta por seguridad (anti-isla)"],
                "comentario": (f"Netbilling activo. Inyección estimada {inyeccion_C:.0f} kWh/año a "
                              f"${PRECIO_NETBILLING_CLP_KWH}/kWh = ${ingreso_netbilling:,.0f} CLP/año de ingreso. "
                              f"Empalme {lbl_C} contrato {categoria_C}."),
            },
        },
        "explicacion_recomendacion": _explicar_recomendacion(escenario_ganador, tcos),
    }


def _explicar_recomendacion(ganador: str, tcos: dict) -> str:
    diferencias = {k: v - min(tcos.values()) for k, v in tcos.items() if k != ganador}
    detalles = " y ".join(f"${diferencias[k]/1e6:.1f}M menos que escenario {k}" for k in diferencias)
    motivo = {
        "A": ("escenario 100% autónomo es óptimo cuando no hay empalme disponible o el "
              "cliente exige cero dependencia de la red — pero financieramente raras veces gana"),
        "B": ("la combinación FV + BESS chico + empalme monofásico complementario logra el "
              "mejor balance CAPEX/OPEX. El empalme monofásico cubre el residual con cargo fijo "
              "mínimo y el BESS sólo se dimensiona para 1 día de cargas críticas en lugar de "
              "varios días de consumo total"),
        "C": ("on-grid con netbilling tiene el CAPEX más bajo porque no requiere BESS, y los "
              "excedentes generan ingresos. Recomendado cuando la red es estable y el cliente "
              "no requiere autonomía"),
    }[ganador]
    return (f"Escenario {ganador} es el de menor TCO 25 años: {detalles}. "
            f"Recomendado porque {motivo}.")
