"""Análisis económico del sistema FV: CAPEX, OPEX, flujo de caja, VAN, TIR, LCOE.

Asume horizonte 25 años (vida útil garantizada de paneles), degradación lineal
0,5%/año, reposición de inversor en año 12, reposición de baterías en año 10.
"""
import math
from app.models.fv import FvResult, EconomicResult
from app.services.fv_equipment import COSTOS_REF


def _irr(flows: list[float], guess: float = 0.10) -> float | None:
    """TIR por Newton-Raphson. Retorna None si no converge."""
    rate = guess
    for _ in range(200):
        npv = sum(f / (1 + rate) ** t for t, f in enumerate(flows))
        d_npv = sum(-t * f / (1 + rate) ** (t + 1) for t, f in enumerate(flows))
        if abs(d_npv) < 1e-12:
            return None
        new_rate = rate - npv / d_npv
        if abs(new_rate - rate) < 1e-7:
            return new_rate
        rate = new_rate
        if rate < -0.99:
            return None
    return None


def calcular_economico(
    fv: FvResult,
    tarifa_clp_kwh: float,
    tipo_proyecto: str = "vivienda",
    horizonte_anios: int = 25,
    tasa_descuento: float = 0.08,
    tipo_cambio: float = 950,
    precio_inyeccion_clp_kwh: float | None = None,
    crecimiento_tarifa_anual: float = 0.02,
    degradacion_anual: float = 0.005,
) -> EconomicResult:
    """Calcula flujo de caja y métricas económicas."""

    # CAPEX desglosado
    P = fv.P_kwp
    capex_paneles = P * 1000 * COSTOS_REF["panel_usd_w"]
    capex_inversor = P * COSTOS_REF["inversor_usd_kw"]
    capex_estructura = P * COSTOS_REF["estructura_usd_kw"]
    capex_cableado = P * COSTOS_REF["cableado_usd_kw"]
    capex_tableros = P * COSTOS_REF["tableros_proteccion_usd_kw"]
    capex_ingenieria = P * COSTOS_REF["ingenieria_usd_kw"]
    capex_mano_obra = P * COSTOS_REF["mano_obra_usd_kw"]
    capex_permisos = COSTOS_REF["permisos_usd_proyecto"]
    capex_bess = fv.bess_capacidad_kwh * COSTOS_REF["bateria_usd_kwh"]

    capex_total_usd = (
        capex_paneles + capex_inversor + capex_estructura + capex_cableado +
        capex_tableros + capex_ingenieria + capex_mano_obra + capex_permisos + capex_bess
    )
    capex_clp = capex_total_usd * tipo_cambio
    capex_unitario = capex_total_usd / P if P > 0 else 0

    capex_desglose = {
        "Paneles":     round(capex_paneles * tipo_cambio),
        "Inversor":    round(capex_inversor * tipo_cambio),
        "Estructura":  round(capex_estructura * tipo_cambio),
        "Cableado":    round(capex_cableado * tipo_cambio),
        "Protecciones":round(capex_tableros * tipo_cambio),
        "Ingeniería":  round(capex_ingenieria * tipo_cambio),
        "Mano de obra":round(capex_mano_obra * tipo_cambio),
        "Permisos":    round(capex_permisos * tipo_cambio),
        "Baterías":    round(capex_bess * tipo_cambio),
    }

    # OPEX anual
    opex_anual = capex_clp * COSTOS_REF["opex_anual_pct"]

    # Precio de inyección (netbilling): usualmente ~50% del precio de retiro
    if precio_inyeccion_clp_kwh is None:
        precio_inyeccion_clp_kwh = tarifa_clp_kwh * 0.50

    # Ahorro año 1
    ahorro_autoconsumo = fv.autoconsumo_kwh * tarifa_clp_kwh
    ingreso_inyeccion = fv.inyeccion_kwh * precio_inyeccion_clp_kwh
    ahorro_total_y1 = ahorro_autoconsumo + ingreso_inyeccion

    # Flujo de caja 25 años con degradación + crecimiento tarifa
    flujos = [-capex_clp]  # Año 0
    acumulado = [-capex_clp]
    for y in range(1, horizonte_anios + 1):
        deg = (1 - degradacion_anual) ** y
        cre = (1 + crecimiento_tarifa_anual) ** y
        ahorro_y = ahorro_total_y1 * deg * cre
        opex_y = opex_anual * (1 + 0.02) ** y  # OPEX también sube con inflación
        # Reposiciones
        repos = 0
        if y == COSTOS_REF["reposicion_inv_anio"]:
            repos += capex_inversor * tipo_cambio * 0.6  # 60% del inversor original
        if fv.bess_capacidad_kwh > 0 and y == COSTOS_REF["reposicion_bess_anio"]:
            repos += capex_bess * tipo_cambio * 0.7
        flujo = ahorro_y - opex_y - repos
        flujos.append(flujo)
        acumulado.append(acumulado[-1] + flujo)

    # Métricas
    payback_simple = capex_clp / ahorro_total_y1 if ahorro_total_y1 > 0 else float("inf")
    # Payback descontado
    payback_desc = None
    acum_desc = -capex_clp
    for y in range(1, horizonte_anios + 1):
        acum_desc += flujos[y] / (1 + tasa_descuento) ** y
        if acum_desc >= 0 and payback_desc is None:
            payback_desc = y - acum_desc / (flujos[y] / (1 + tasa_descuento) ** y)
            break

    VAN = sum(f / (1 + tasa_descuento) ** t for t, f in enumerate(flujos))
    TIR = _irr(flujos)
    TIR_pct = round(TIR * 100, 2) if TIR is not None else None

    # LCOE: (CAPEX + Σ OPEX descontado) / Σ E_gen descontada
    e_gen_desc = sum(
        fv.generacion_anual_kwh * (1 - degradacion_anual) ** y / (1 + tasa_descuento) ** y
        for y in range(1, horizonte_anios + 1)
    )
    opex_desc = sum(opex_anual * (1.02) ** y / (1 + tasa_descuento) ** y for y in range(1, horizonte_anios + 1))
    LCOE = (capex_clp + opex_desc) / e_gen_desc if e_gen_desc > 0 else float("inf")

    # CO2
    co2_anual = fv.generacion_anual_kwh * 0.2  # 0.2 kg/kWh = 0.2 tCO2/MWh
    co2_total = sum(fv.generacion_anual_kwh * (1 - degradacion_anual) ** y * 0.2 for y in range(1, horizonte_anios + 1))

    return EconomicResult(
        capex_total_clp=round(capex_clp),
        capex_desglose=capex_desglose,
        capex_unitario_usd_kwp=round(capex_unitario, 1),
        tipo_cambio=tipo_cambio,
        opex_anual_clp=round(opex_anual),
        ahorro_anual_clp=round(ahorro_autoconsumo),
        ingreso_inyeccion_clp=round(ingreso_inyeccion),
        ahorro_total_anual_clp=round(ahorro_total_y1),
        payback_simple_anios=round(payback_simple, 2),
        payback_descontado_anios=round(payback_desc, 2) if payback_desc else None,
        VAN_clp=round(VAN),
        TIR_pct=TIR_pct,
        LCOE_clp_kwh=round(LCOE, 1),
        horizonte_anios=horizonte_anios,
        tasa_descuento=tasa_descuento,
        flujo_caja_anual_clp=[round(f) for f in flujos],
        flujo_acumulado_clp=[round(a) for a in acumulado],
        CO2_evitado_anual_kg=round(co2_anual),
        CO2_evitado_total_kg=round(co2_total),
    )
