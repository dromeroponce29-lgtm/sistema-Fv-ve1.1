"""Motor de dimensionamiento FV.

Calcula tamaño del arreglo, pérdidas detalladas, Performance Ratio, generación
mensual y balance energético contra el consumo del proyecto.

Usa modelo simplificado de Sandia para temperatura de celda y aplica las pérdidas
como factores multiplicativos en cascada (modelo PVsyst-like).
"""
import math
from app.models.fv import FvRequest, FvResult, PerdidaItem
from app.services.fv_equipment import seleccionar_panel, seleccionar_inversor, seleccionar_bateria
from app.services.comparativa_escenarios import comparar_3_escenarios


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

    # 8. Dimensionar respaldo (generador / empalme) según conexion a red y tipo
    respaldo = _dimensionar_respaldo(req, demanda_max_kw=req.demanda_maxima_kw, P_kwp=P_kwp_real,
                                     bess_capacidad_util_kwh=bess_util,
                                     cons_critico_diario_kwh=cons_critico_diario,
                                     advertencias=advertencias)

    # 9. LOTE E — Comparativa de escenarios (A off-grid puro / B FV+empalme mono / C on-grid)
    try:
        comparativa = comparar_3_escenarios(
            consumo_anual_kwh=req.consumo_anual_kwh,
            cobertura_solar=cob_real,
            P_kwp=P_kwp_real,
            demanda_max_kw=req.demanda_maxima_kw,
            cons_critico_diario_kwh=cons_critico_diario,
            dias_autonomia_objetivo=max(req.dias_autonomia, 2.0),
            DoD=req.profundidad_descarga,
            eta_rt=req.eficiencia_round_trip,
            bess_capacidad_actual_kwh=bess_cap,
            tipo_proyecto=req.tipo_proyecto,
        )
        escenario_rec = comparativa["escenario_recomendado"]
    except Exception as e:
        comparativa = {"error": str(e)}
        escenario_rec = None
        advertencias.append(f"Comparativa de escenarios no disponible: {e}")

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
        conectado_red=req.conectado_red,
        tipo_respaldo=req.tipo_respaldo,
        respaldo_potencia_kw=respaldo["potencia_kw"],
        respaldo_descripcion=respaldo["descripcion"],
        respaldo_criterio=respaldo["criterio"],
        empalme_recomendado=respaldo["empalme"],
        respaldo_capex_usd=respaldo["capex_usd"],
        respaldo_opex_mensual_clp=respaldo["opex_clp_mes"],
        comparativa_escenarios=comparativa,
        escenario_recomendado=escenario_rec,
        cabe_en_superficie=cabe,
        advertencias=advertencias,
    )


def _dimensionar_respaldo(req, demanda_max_kw: float, P_kwp: float,
                          bess_capacidad_util_kwh: float, cons_critico_diario_kwh: float,
                          advertencias: list[str]) -> dict:
    """Dimensiona la potencia del respaldo (generador diesel, empalme normal o reducido).

    Reglas:
      • OFF-GRID puro (sin respaldo): la generación FV + BESS debe cubrir todo el consumo.
        Si autonomía < 1 día → advertencia crítica.
      • GENERADOR DIESEL: P_gen = max(demanda_max × 1.25, P_críticas × 1.5)
        para arrancar motores y cubrir picos. CAPEX ~600 USD/kW. Combustible 0.27 L/kWh.
      • EMPALME REDUCIDO (con FV, ahorra capacidad): P_empalme = demanda_max − P_FV × 0.6
        (asumiendo que el FV contribuye al menos 60% en horario pico).
      • EMPALME COMPLETO: P_empalme = demanda_max (netbilling estándar).
    """
    factor = req.factor_seguridad_respaldo
    fs = factor if factor >= 1.0 else 1.25
    P_kwp_contrib = P_kwp * 0.6  # contribución FV en horario pico (estimación)

    if not req.conectado_red:  # Off-grid
        if req.tipo_respaldo == "generador_diesel":
            # Generador para cubrir demanda crítica cuando BESS no alcanza
            # FIX #2 — guard división por cero si horas_consumo_critico_dia = 0
            cons_critico_horario_kw = (
                cons_critico_diario_kwh / req.horas_consumo_critico_dia
                if req.horas_consumo_critico_dia and req.horas_consumo_critico_dia > 0
                else cons_critico_diario_kwh / 12  # fallback: 12 hrs default
            )
            P_gen = max(demanda_max_kw * fs, cons_critico_horario_kw * 1.5)
            # Escala a tamaños comerciales: 5, 10, 15, 20, 30, 50, 75, 100, 150 kVA (factor 0.8 → kW)
            escala_kva = [5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 250, 350, 500]
            P_kva = next((k for k in escala_kva if k * 0.8 >= P_gen), 500)
            P_kw_gen = round(P_kva * 0.8, 1)
            capex_usd = round(P_kva * 550)  # ~$550 USD/kVA
            # OPEX: combustible × horas/mes × consumo_específico × precio diesel
            l_por_kwh = 0.27
            kwh_mes_gen = P_kw_gen * 0.7 * req.horas_uso_generador_mes  # 70% de carga típica
            litros_mes = kwh_mes_gen * l_por_kwh
            precio_diesel_clp = 1280
            opex_clp = round(litros_mes * precio_diesel_clp + capex_usd * 0.02 * 950 / 12)
            if cons_critico_diario_kwh > 0 and bess_capacidad_util_kwh < cons_critico_diario_kwh * 0.5:
                advertencias.append(
                    f"OFF-GRID + generador: BESS ({bess_capacidad_util_kwh:.1f} kWh útil) cubre menos del "
                    f"50% del consumo crítico diario. El generador se usará frecuentemente."
                )
            return {
                "potencia_kw": P_kw_gen,
                "descripcion": f"Generador diesel {P_kva} kVA ({P_kw_gen} kW), uso estimado {req.horas_uso_generador_mes:.0f} hrs/mes",
                "criterio": (f"P_gen = max(demanda_máx {demanda_max_kw:.1f} × FS {fs}, "
                             f"P_crítica/h {cons_critico_horario_kw:.1f} × 1.5) = {P_gen:.1f} kW. "
                             f"Escalado al tamaño comercial siguiente: {P_kva} kVA."),
                "empalme": "Sin empalme (off-grid puro + generador)",
                "capex_usd": capex_usd,
                "opex_clp_mes": opex_clp,
            }
        else:  # off-grid puro sin generador
            return {
                "potencia_kw": 0, "descripcion": "Sin respaldo eléctrico — operación 100% solar + BESS",
                "criterio": "Off-grid sin respaldo. Toda la demanda crítica debe cubrirse con BESS.",
                "empalme": "Sin empalme (off-grid puro)", "capex_usd": 0, "opex_clp_mes": 0,
            }

    # ON-GRID: empalme + posibilidad de respaldo extra
    if req.tipo_respaldo == "empalme_reducido":
        # FV contribuye en horario pico → empalme puede ser menor
        P_empalme_kw = max(demanda_max_kw - P_kwp_contrib, demanda_max_kw * 0.5)
        # Ahorro vs empalme completo (cargo fijo distribuidora)
        ahorro_cargo_fijo_clp = round((demanda_max_kw - P_empalme_kw) * 12 * 1100)  # ~$1100/kW-mes
        empalme = _texto_empalme(P_empalme_kw, demanda_max_kw)
        return {
            "potencia_kw": round(P_empalme_kw, 2),
            "descripcion": f"Empalme reducido {empalme}, ahorra ~${ahorro_cargo_fijo_clp:,} CLP/año en cargo fijo",
            "criterio": (f"P_empalme = max(demanda_máx {demanda_max_kw:.1f} − P_FV×0.6 ({P_kwp_contrib:.1f}), "
                         f"demanda_máx×0.5) = {P_empalme_kw:.1f} kW. El FV cubre el pico de demanda."),
            "empalme": empalme,
            "capex_usd": round(P_empalme_kw * 80),  # ahorro ~$80/kW vs empalme completo
            "opex_clp_mes": -round(ahorro_cargo_fijo_clp / 12),  # negativo = ahorro
        }
    elif req.tipo_respaldo == "generador_diesel":
        # On-grid + generador de respaldo (raro, solo industria crítica)
        cons_critico_horario_kw = cons_critico_diario_kwh / req.horas_consumo_critico_dia if req.horas_consumo_critico_dia else 0
        P_gen = max(cons_critico_horario_kw * 1.5, 10)
        escala_kva = [10, 15, 20, 30, 50, 75, 100, 150, 200]
        P_kva = next((k for k in escala_kva if k * 0.8 >= P_gen), 200)
        return {
            "potencia_kw": round(P_kva * 0.8, 1),
            "descripcion": f"On-grid con generador de emergencia {P_kva} kVA (solo cargas críticas si cae la red)",
            "criterio": f"Generador para cargas críticas {cons_critico_horario_kw:.1f} kW × 1.5 = {P_gen:.1f} kW",
            "empalme": _texto_empalme(demanda_max_kw, demanda_max_kw),
            "capex_usd": round(P_kva * 600),
            "opex_clp_mes": 50000,  # mantención
        }
    else:  # empalme_completo (default)
        return {
            "potencia_kw": demanda_max_kw,
            "descripcion": f"Empalme estándar a red ({_texto_empalme(demanda_max_kw, demanda_max_kw)}), netbilling activo",
            "criterio": f"Empalme dimensionado para la demanda máxima total ({demanda_max_kw:.1f} kW). FV inyecta excedentes (Ley 21.118 Netbilling).",
            "empalme": _texto_empalme(demanda_max_kw, demanda_max_kw),
            "capex_usd": 0,  # ya incluido en costos normales
            "opex_clp_mes": 0,
        }


def _texto_empalme(P_kw: float, demanda_total_kw: float) -> str:
    """Devuelve el texto del empalme estándar según corriente."""
    monofasico = demanda_total_kw <= 8
    V = 220 if monofasico else 380
    fp = 0.93
    I = P_kw * 1000 / (V * fp) if monofasico else P_kw * 1000 / (1.732 * V * fp)
    escala = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400]
    I_n = next((v for v in escala if v >= I * 1.15), 400)
    return f"{I_n} A {'monofásico' if monofasico else 'trifásico'}"
