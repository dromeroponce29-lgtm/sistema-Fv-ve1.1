"""Motor de dimensionamiento FV.

Calcula tamaño del arreglo, pérdidas detalladas, Performance Ratio, generación
mensual y balance energético contra el consumo del proyecto.

Usa modelo simplificado de Sandia para temperatura de celda y aplica las pérdidas
como factores multiplicativos en cascada (modelo PVsyst-like).
"""
import math
from app.models.fv import FvRequest, FvResult, PerdidaItem
from app.services.fv_equipment import seleccionar_panel, seleccionar_inversor, seleccionar_bateria


def _t_celda_promedio(t_amb_promedio_c: float, NOCT: float, G: float = 800) -> float:
    """Modelo Sandia simplificado: T_celda = T_amb + (NOCT-20)/800 * G.
    Para promedio anual usamos G=800 W/m² (irradiancia operativa típica)."""
    return t_amb_promedio_c + (NOCT - 20) / 800 * G


def calcular_fv(req: FvRequest) -> FvResult:
    advertencias: list[str] = []

    # 1. Pérdidas por temperatura (mensual, promediada)
    t_amb_anual = sum(req.monthly_t_amb_c) / len(req.monthly_t_amb_c)
    t_celda = _t_celda_promedio(t_amb_anual, req.NOCT)
    # Aplicar corrección por altitud: cada 1000 msnm, T baja ~6,5°C
    t_celda -= (req.altitud_msnm / 1000) * 6.5 * 0.3  # 30% del efecto se mantiene en celda
    L_temp = abs(req.coef_temp_pmp / 100 * (t_celda - 25))
    L_temp = max(0, min(L_temp, 0.20))  # cap a 20%

    # 2. Performance Ratio (producto de 1 - cada pérdida)
    factores = {
        "Temperatura": L_temp,
        "Suciedad": req.perdida_suciedad,
        "Cableado DC": req.perdida_cableado_dc,
        "Cableado AC": req.perdida_cableado_ac,
        "Inversor": req.perdida_inversor,
        "Mismatch": req.perdida_mismatch,
        "Sombras": req.perdida_sombras,
        "Disponibilidad": req.perdida_disponibilidad,
    }
    PR = 1.0
    for L in factores.values():
        PR *= (1 - L)
    perdidas = [PerdidaItem(nombre=k, pct=round(v * 100, 2)) for k, v in factores.items()]

    # 3. Potencia FV requerida según consumo y cobertura
    # P_kWp tal que: E_anual = P_kWp * E_y * PR cubre cobertura_obj * consumo
    # OJO: PVGIS ya aplica un PR interno de ~0.86 (14% pérdidas sistema default).
    # Aquí re-aplicamos el PR detallado, así que para no doble-contar dividimos por PR_PVGIS.
    PR_PVGIS_REF = 0.86
    E_y_efectivo = req.E_y_kwh_por_kwp / PR_PVGIS_REF * PR

    P_kwp_teorica = req.consumo_anual_kwh * req.cobertura_objetivo / E_y_efectivo
    N_pan = math.ceil(P_kwp_teorica * 1000 / req.panel_Pnom_w)
    P_kwp_real = round(N_pan * req.panel_Pnom_w / 1000, 2)
    superficie = round(N_pan * req.panel_area_m2, 1)

    # Verificar restricción de superficie
    cabe = True
    if req.superficie_disponible_m2 is not None and superficie > req.superficie_disponible_m2:
        # Ajustar a la superficie disponible
        cabe = False
        N_pan_max = math.floor(req.superficie_disponible_m2 / req.panel_area_m2)
        if N_pan_max < N_pan:
            advertencias.append(
                f"Superficie {req.superficie_disponible_m2} m² insuficiente para {N_pan} paneles. "
                f"Limitado a {N_pan_max} paneles ({round(N_pan_max * req.panel_Pnom_w / 1000, 2)} kWp)."
            )
            N_pan = N_pan_max
            P_kwp_real = round(N_pan * req.panel_Pnom_w / 1000, 2)
            superficie = round(N_pan * req.panel_area_m2, 1)

    # 4. Inversor — selección automática considerando si requiere BESS
    requiere_bess = (req.tipo_sistema in ("on_grid_bess", "off_grid", "hibrido_red", "hibrido_generador") or req.capacidad_bess_kwh > 0)
    inv = seleccionar_inversor(P_kwp_real, monofasico_ok=(P_kwp_real <= 8), requiere_bess=requiere_bess)
    P_AC = inv["P_AC_kw"]
    inv_modelo = f"{inv['marca']} {inv['modelo']}"
    if P_kwp_real / req.DC_AC_ratio > P_AC * 1.1:
        advertencias.append(
            f"Inversor {inv_modelo} ({P_AC} kW AC) puede quedar subdimensionado para {P_kwp_real} kWp"
        )

    # 5. Generación mensual con el PR real
    monthly_gen = [round(e * P_kwp_real / PR_PVGIS_REF * PR, 1) for e in req.monthly_E_kwh_por_kwp]
    gen_anual = round(sum(monthly_gen), 0)
    cob_real = min(1.0, gen_anual / req.consumo_anual_kwh) if req.consumo_anual_kwh > 0 else 0
    fp = gen_anual / (P_kwp_real * 8760) if P_kwp_real > 0 else 0

    # 6. Balance energético mensual
    autoconsumo = 0
    inyeccion = 0
    compra = 0
    for m in range(12):
        cons_m = req.consumo_mensual_kwh[m] if m < len(req.consumo_mensual_kwh) else req.consumo_anual_kwh / 12
        gen_m = monthly_gen[m]
        ac = min(cons_m, gen_m)
        autoconsumo += ac
        inyeccion += max(0, gen_m - cons_m)
        compra += max(0, cons_m - gen_m)
    # Si tipo no permite inyección (off-grid, peak-shaving), el excedente se descarta
    if req.tipo_sistema in ("off_grid", "peak_shaving") and req.capacidad_bess_kwh == 0:
        inyeccion = 0

    # 7. BESS — dimensionamiento por criterios de autonomía operacional
    bess_modelo = None
    bess_cap = req.capacidad_bess_kwh
    bess_pot = 0
    bess_util = 0
    dias_aut_real = 0
    cons_critico_diario = 0
    criterio = ""
    aplica_bess = req.tipo_sistema in ("on_grid_bess", "off_grid", "hibrido_red", "hibrido_generador")
    if aplica_bess:
        cons_diario_total = req.consumo_anual_kwh / 365
        # Consumo crítico diario = total × % crítico (cargas que NO se pueden cortar)
        cons_critico_diario = round(cons_diario_total * req.cargas_criticas_pct, 2)
        if bess_cap == 0:
            # Auto-dimensionar: capacidad_nominal = (E_crítico_diario × días_autonomía) / (DoD × η_RT)
            dias = max(req.dias_autonomia, 1.0 if req.tipo_sistema == "off_grid" else 0.5)
            bess_cap_calc = cons_critico_diario * dias / (req.profundidad_descarga * req.eficiencia_round_trip)
            criterio = (
                f"Capacidad = (consumo crítico {cons_critico_diario:.1f} kWh/día × {dias} días autonomía) "
                f"/ (DoD {req.profundidad_descarga*100:.0f}% × η_RT {req.eficiencia_round_trip*100:.0f}%) "
                f"= {bess_cap_calc:.1f} kWh nominal"
            )
            bess_cap = bess_cap_calc
        else:
            criterio = f"Capacidad indicada manualmente: {bess_cap} kWh nominal"
        # Seleccionar batería del catálogo más cercana
        if bess_cap > 0:
            b = seleccionar_bateria(bess_cap)
            n_modulos = math.ceil(bess_cap / b['capacidad_kwh'])
            bess_modelo = f"{b['marca']} {b['modelo']}" + (f" × {n_modulos}" if n_modulos > 1 else "")
            bess_cap = round(n_modulos * b['capacidad_kwh'], 1)
            bess_util = round(bess_cap * req.profundidad_descarga * req.eficiencia_round_trip, 1)
            bess_pot = round(b['potencia_kw'] * n_modulos, 1)
            # Días de autonomía REAL con la capacidad redondeada al catálogo
            if cons_critico_diario > 0:
                dias_aut_real = round(bess_util / cons_critico_diario, 2)
            criterio += f". Catálogo: {n_modulos} × {b['marca']} {b['modelo']} ({b['capacidad_kwh']} kWh c/u). Útil real: {bess_util} kWh = {dias_aut_real} días de autonomía con cargas críticas."
            if req.tipo_sistema == "off_grid" and dias_aut_real < 1.0:
                advertencias.append(
                    f"OFF-GRID con autonomía solo {dias_aut_real} días — RIESGO de corte de operación. "
                    f"Aumentar capacidad BESS o reducir cargas críticas (actualmente {req.cargas_criticas_pct*100:.0f}% del consumo)."
                )

    return FvResult(
        P_kwp=P_kwp_real,
        N_paneles=N_pan,
        superficie_m2=superficie,
        inversor_P_AC_kw=P_AC,
        inversor_modelo=inv_modelo,
        PR_anual=round(PR, 3),
        perdidas=perdidas,
        L_temperatura_pct=round(L_temp * 100, 2),
        T_celda_promedio_c=round(t_celda, 1),
        generacion_anual_kwh=gen_anual,
        generacion_mensual_kwh=monthly_gen,
        factor_planta=round(fp, 3),
        cobertura_real=round(cob_real, 3),
        autoconsumo_kwh=round(autoconsumo, 0),
        inyeccion_kwh=round(inyeccion, 0),
        compra_red_kwh=round(compra, 0),
        bess_modelo=bess_modelo,
        bess_capacidad_kwh=bess_cap,
        bess_capacidad_util_kwh=bess_util,
        bess_potencia_kw=bess_pot,
        bess_dias_autonomia_real=dias_aut_real,
        bess_consumo_critico_diario_kwh=cons_critico_diario,
        bess_criterio_dimensionamiento=criterio,
        cabe_en_superficie=cabe,
        advertencias=advertencias,
    )
