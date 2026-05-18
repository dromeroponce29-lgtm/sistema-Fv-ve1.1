"""Motor de cálculo de cargas RIC.

Toma una lista de recintos (típicamente provenientes del módulo PLANOS) y
calcula la carga eléctrica instalada, la demanda diversificada y la demanda
máxima del proyecto según las tablas y factores RIC.
"""
from typing import List
from app.models.ric import (
    RicRequest, RicResult, RecintoCarga, CargaDedicadaCalculada
)
from app.services.ric_tables import (
    CARGAS_POR_USO, CARGAS_DEDICADAS_VIVIENDA,
    factor_demanda_vivienda, FACTOR_SIMULTANEIDAD,
    corriente_nominal, tipo_empalme_sugerido,
)


# Horas equivalentes de uso por mes para estimar consumo a partir de potencia.
# Valores conservadores: alumbrado 4 h/día, enchufes generales 6 h/día equivalente.
HORAS_MENSUALES_USO = {
    "alumbrado":      4 * 30,        # 120 h/mes
    "enchufes":       6 * 30,        # 180 h/mes
    "cocina":         1.5 * 30,      # cocción
    "calefon":        2 * 30,        # calefón eléctrico
    "ducha":          0.5 * 30,
    "microondas":     0.2 * 30,
    "lavadora":       0.5 * 30 * 4,  # 4 lavados/semana × 30 min
    "secadora":       0.7 * 30 * 3,
    "lavavajillas":   0.5 * 30 * 4,
    "refrigerador":   24 * 30,       # continuo (pero a 30% duty cycle dentro de la W)
    "aire":           4 * 30,        # 4 h/día verano + invierno equivalente
    "calefactor":     6 * 30,
    "default":        4 * 30,
}


def _horas_para_carga(nombre: str) -> float:
    nl = nombre.lower()
    if "cocina" in nl or "horno" in nl:   return HORAS_MENSUALES_USO["cocina"]
    if "calef" in nl and "elect" in nl:   return HORAS_MENSUALES_USO["calefon"]
    if "calefón" in nl or "termo" in nl:  return HORAS_MENSUALES_USO["calefon"]
    if "ducha" in nl:                     return HORAS_MENSUALES_USO["ducha"]
    if "microondas" in nl:                return HORAS_MENSUALES_USO["microondas"]
    if "lavadora" in nl:                  return HORAS_MENSUALES_USO["lavadora"]
    if "secadora" in nl:                  return HORAS_MENSUALES_USO["secadora"]
    if "lavavaj" in nl:                   return HORAS_MENSUALES_USO["lavavajillas"]
    if "refriger" in nl:                  return HORAS_MENSUALES_USO["refrigerador"] * 0.30  # duty cycle
    if "aire" in nl or "split" in nl:     return HORAS_MENSUALES_USO["aire"]
    if "calefactor" in nl or "estufa" in nl: return HORAS_MENSUALES_USO["calefactor"]
    return HORAS_MENSUALES_USO["default"]


def calcular_carga_ric(req: RicRequest) -> RicResult:
    """Ejecuta el cálculo de carga RIC y retorna estructura tipada."""
    advertencias: list[str] = []

    # --- 1. Cargas por recinto (alumbrado + enchufes generales) ---
    recintos_carga: List[RecintoCarga] = []
    consumo_recintos_kwh_mes = 0.0
    for r in req.recintos:
        uso = r.get("uso", "desconocido")
        tabla = CARGAS_POR_USO.get(uso, CARGAS_POR_USO["desconocido"])
        if uso not in CARGAS_POR_USO:
            advertencias.append(
                f"Recinto '{r.get('nombre')}': uso '{uso}' no tabulado; aplicando defaults"
            )
        area = float(r.get("area_m2", 0))
        alum_w = round(area * tabla["alumbrado_w_m2"], 1)
        ench_w = round(area * tabla["enchufes_w_m2"], 1)
        subtotal = round(alum_w + ench_w, 1)
        recintos_carga.append(RecintoCarga(
            id=int(r.get("id", 0)),
            nombre=str(r.get("nombre", "")),
            uso=uso,
            area_m2=area,
            alumbrado_w=alum_w,
            enchufes_w=ench_w,
            subtotal_w=subtotal,
        ))
        consumo_recintos_kwh_mes += (
            alum_w * HORAS_MENSUALES_USO["alumbrado"] +
            ench_w * HORAS_MENSUALES_USO["enchufes"]
        ) / 1000

    subtotal_recintos = round(sum(r.subtotal_w for r in recintos_carga), 1)
    area_total = round(sum(r.area_m2 for r in recintos_carga), 2)

    # --- 2. Cargas dedicadas ---
    dedicadas = list(req.cargas_dedicadas)
    # Si el usuario pidió aplicar las default, las agregamos
    if req.aplicar_dedicadas_por_defecto and req.tipo_proyecto == "vivienda":
        usos_existentes = {r.uso for r in recintos_carga}
        for cd in CARGAS_DEDICADAS_VIVIENDA:
            if not cd["por_defecto"]:
                continue
            if not any(u in usos_existentes for u in cd["aplica_uso"]):
                continue
            dedicadas.append(CargaDedicadaCalculada(
                nombre=cd["nombre"],
                potencia_w=cd["potencia_w"],
                activa=True,
            ))

    subtotal_dedicadas = round(sum(d.potencia_w for d in dedicadas if d.activa), 1)
    consumo_dedicadas_kwh_mes = sum(
        d.potencia_w * _horas_para_carga(d.nombre) / 1000
        for d in dedicadas if d.activa
    )

    # --- 3. Carga total y aplicación de factores ---
    carga_total = round(subtotal_recintos + subtotal_dedicadas, 1)

    # Factor de demanda según tipo de proyecto y tamaño
    if req.tipo_proyecto == "vivienda":
        f_demanda = factor_demanda_vivienda(area_total)
    elif req.tipo_proyecto == "edificio_residencial":
        f_demanda = 0.55  # default razonable, debería refinarse con N° de deptos
    elif req.tipo_proyecto == "hotel":
        f_demanda = 0.70
    elif req.tipo_proyecto == "industria":
        f_demanda = 0.90
    elif req.tipo_proyecto in ("comercial", "oficina"):
        f_demanda = 0.80
    else:
        f_demanda = 0.75

    carga_diversificada = round(carga_total * f_demanda, 1)

    # Factor de simultaneidad
    f_sim = FACTOR_SIMULTANEIDAD.get(req.tipo_proyecto, 0.70)
    demanda_max = round(carga_diversificada * f_sim, 1)

    # --- 4. Corriente y empalme ---
    I_n = corriente_nominal(demanda_max, req.conexion, req.factor_potencia)
    empalme = tipo_empalme_sugerido(I_n, req.conexion)

    # --- 4.b Balance de fases (solo si trifásico) ---
    carga_L1 = carga_L2 = carga_L3 = 0.0
    desbalance = 0.0
    if req.conexion == "trifasica_380":
        # Distribuir cargas según campo "fase" de cada CargaDedicadaCalculada
        # Si fase=trifasica → reparte equitativamente entre L1, L2, L3
        # Si fase=monofasica/L1/L2/L3 → asigna a esa fase específica
        # Auto-balanceo: las "monofasicas" sin asignar van round-robin a L1/L2/L3
        fase_ptr = 0  # contador round-robin
        fases = ["L1", "L2", "L3"]
        cargas_por_fase = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
        for d in dedicadas:
            if not d.activa: continue
            p = d.potencia_w
            f = d.fase
            if f == "trifasica":
                cargas_por_fase["L1"] += p / 3
                cargas_por_fase["L2"] += p / 3
                cargas_por_fase["L3"] += p / 3
            elif f in ("L1", "L2", "L3"):
                cargas_por_fase[f] += p
            elif f == "bifasica":
                cargas_por_fase[fases[fase_ptr % 3]] += p / 2
                cargas_por_fase[fases[(fase_ptr + 1) % 3]] += p / 2
                fase_ptr += 1
            else:  # monofasica sin asignar → round-robin
                cargas_por_fase[fases[fase_ptr % 3]] += p
                fase_ptr += 1
        # Cargas por recinto: las repartimos equitativamente (asumimos balance arquitectónico)
        for rc in recintos_carga:
            for fase in fases:
                cargas_por_fase[fase] += rc.subtotal_w / 3
        carga_L1 = cargas_por_fase["L1"] * f_demanda * f_sim
        carga_L2 = cargas_por_fase["L2"] * f_demanda * f_sim
        carga_L3 = cargas_por_fase["L3"] * f_demanda * f_sim
        # Desbalance: pico vs valle
        L_max = max(carga_L1, carga_L2, carga_L3)
        L_min = min(carga_L1, carga_L2, carga_L3)
        desbalance = (L_max - L_min) / L_max * 100 if L_max > 0 else 0
        if desbalance > 15:
            advertencias.append(
                f"Desbalance entre fases: {desbalance:.1f}% (recomendado < 15%). "
                f"Reasignar cargas pesadas entre L1/L2/L3 para mejor balance."
            )
    elif req.conexion in ("monofasica_220", "bifasica_220"):
        # En monofásico todo va al único conductor
        carga_L1 = demanda_max

    # --- 5. Consumo estimado ---
    consumo_mes = round(consumo_recintos_kwh_mes + consumo_dedicadas_kwh_mes, 1)
    # Ajustar por factor de uso real (no todo está prendido siempre)
    consumo_mes_real = round(consumo_mes * 0.45, 1)  # uso típico ~45% del teórico
    consumo_anio_real = round(consumo_mes_real * 12, 0)

    return RicResult(
        tipo_proyecto=req.tipo_proyecto,
        area_total_m2=area_total,
        n_recintos=len(recintos_carga),
        recintos_carga=recintos_carga,
        subtotal_recintos_w=subtotal_recintos,
        cargas_dedicadas=dedicadas,
        subtotal_dedicadas_w=subtotal_dedicadas,
        carga_total_instalada_w=carga_total,
        factor_demanda=f_demanda,
        carga_diversificada_w=carga_diversificada,
        factor_simultaneidad=f_sim,
        demanda_maxima_w=demanda_max,
        corriente_nominal_a=round(I_n, 1),
        tipo_empalme_sugerido=empalme,
        conexion=req.conexion,
        factor_potencia=req.factor_potencia,
        consumo_mensual_estimado_kwh=consumo_mes_real,
        consumo_anual_estimado_kwh=consumo_anio_real,
        carga_L1_w=round(carga_L1, 1),
        carga_L2_w=round(carga_L2, 1),
        carga_L3_w=round(carga_L3, 1),
        corriente_L1_a=round(carga_L1 / (220 * req.factor_potencia), 1) if carga_L1 > 0 else 0,
        corriente_L2_a=round(carga_L2 / (220 * req.factor_potencia), 1) if carga_L2 > 0 else 0,
        corriente_L3_a=round(carga_L3 / (220 * req.factor_potencia), 1) if carga_L3 > 0 else 0,
        desbalance_fases_pct=round(desbalance, 1),
        advertencias=advertencias,
    )
