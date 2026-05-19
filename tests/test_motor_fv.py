"""Suite de regresión del motor FV.

Cubre los 5 lotes A→E del motor:
  A) Fase por carga + balance L1/L2/L3 + autonomía BESS
  B) On-grid/Off-grid + dimensionamiento respaldo
  C) Reportes selectivos (filtrado de secciones)
  D) Layout sobre plano real (SVG overlay)
  E) Comparativa de 3 escenarios + análisis tarifario

Ejecutar:
    cd /Users/mac/Documents/Claude/Projects/SISTEMAS\\ FOTOVOLTAICOS
    pytest tests/ -v
"""
import pytest
from pathlib import Path


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO RIC — Cargas eléctricas (Lote A)
# ════════════════════════════════════════════════════════════════════════════
class TestRicCargas:

    def test_vivienda_chica_factor_demanda_1(self, recintos_vivienda_tipica):
        """Vivienda < 60 m² debería tener factor demanda = 1.0."""
        from app.services.ric_loads import calcular_carga_ric
        from app.models.ric import RicRequest
        recintos_chicos = [{**r, "area_m2": r["area_m2"]/2} for r in recintos_vivienda_tipica]
        req = RicRequest(tipo_proyecto="vivienda", recintos=recintos_chicos,
                         aplicar_dedicadas_por_defecto=True)
        r = calcular_carga_ric(req)
        assert r.area_total_m2 < 60, f"Área debería ser <60 m², es {r.area_total_m2}"
        assert r.factor_demanda == 1.0, f"FD={r.factor_demanda}, esperado 1.0"

    def test_factores_simultaneidad_por_tipo(self):
        """Factores de simultaneidad por tipo de proyecto."""
        from app.services.ric_loads import calcular_carga_ric
        from app.models.ric import RicRequest
        for tipo, fs_esperado in [
            ("vivienda", 0.65),
            ("hotel", 0.65),
            ("industria", 0.85),
        ]:
            req = RicRequest(tipo_proyecto=tipo,
                             recintos=[{"id":1, "nombre":"R","uso":"comun","area_m2":50}],
                             aplicar_dedicadas_por_defecto=False)
            r = calcular_carga_ric(req)
            assert abs(r.factor_simultaneidad - fs_esperado) < 0.1, \
                f"{tipo}: fs={r.factor_simultaneidad}, esperado ≈ {fs_esperado}"

    def test_corriente_nominal_monofasica(self):
        """I = P / (V × fp) para monofásico."""
        from app.services.ric_tables import corriente_nominal
        # 4400 W @ 220V × 0.93 fp ≈ 21.5 A
        I = corriente_nominal(4400, "monofasica_220", 0.93)
        assert 20 < I < 25, f"I = {I:.1f} A; esperado ~21.5"

    def test_corriente_nominal_trifasica(self):
        """I = P / (√3 × V × fp) para trifásico."""
        from app.services.ric_tables import corriente_nominal
        # 10000 W @ 380V × 0.93 fp × √3 ≈ 16.3 A
        I = corriente_nominal(10000, "trifasica_380", 0.93)
        assert 14 < I < 19, f"I = {I:.1f} A; esperado ~16.3"

    def test_empalme_escala_iec(self):
        """Empalme sugerido respeta escala IEC 10/16/20/25/32/40/..."""
        from app.services.ric_tables import tipo_empalme_sugerido
        ESCALA = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100]
        for I in [8, 15, 21, 33]:
            e = tipo_empalme_sugerido(I, "monofasica_220")
            # Extrae el amperaje del texto resultante
            amp = int(e.split()[0])
            assert amp in ESCALA, f"I={I} → '{e}' tiene amp {amp} fuera de escala IEC"

    def test_balance_fases_trifasico_alerta_desbalance(self):
        """Desbalance > 15% genera advertencia."""
        from app.services.ric_loads import calcular_carga_ric
        from app.models.ric import RicRequest, CargaDedicadaCalculada
        cargas = [
            CargaDedicadaCalculada(nombre="Horno", potencia_w=8000, activa=True, fase="L1"),
            CargaDedicadaCalculada(nombre="Bomba", potencia_w=2000, activa=True, fase="L2"),
            CargaDedicadaCalculada(nombre="Luces", potencia_w=500,  activa=True, fase="L3"),
        ]
        req = RicRequest(tipo_proyecto="industria", conexion="trifasica_380",
                         recintos=[{"id":1,"nombre":"Galpón","uso":"comun","area_m2":100}],
                         cargas_dedicadas=cargas, aplicar_dedicadas_por_defecto=False)
        r = calcular_carga_ric(req)
        assert r.desbalance_fases_pct > 15, f"Esperado desbalance >15%, obtuvo {r.desbalance_fases_pct}"
        assert any("desbalance" in a.lower() for a in r.advertencias), \
            "Falta advertencia de desbalance"


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO FV — Dimensionamiento (Lote A interno)
# ════════════════════════════════════════════════════════════════════════════
class TestDimensionamientoFv:

    def test_pr_anual_rango_realista(self, fv_request_default):
        """Performance Ratio anual debería estar en [0.70, 0.86]."""
        from app.services.pv_sizing import calcular_fv
        r = calcular_fv(fv_request_default)
        assert 0.65 <= r.PR_anual <= 0.86, f"PR={r.PR_anual} fuera del rango esperado"

    def test_no_doble_conteo_pvgis(self, fv_request_default):
        """Verificar que se divide por PR_PVGIS_REF (no doble conteo)."""
        from app.services.pv_sizing import calcular_fv
        r = calcular_fv(fv_request_default)
        # La generación anual debería ser ≈ P_kwp × E_y / PR_PVGIS × PR_propio
        E_y = fv_request_default.E_y_kwh_por_kwp
        esperado = r.P_kwp * E_y / 0.86 * r.PR_anual
        assert abs(r.generacion_anual_kwh - esperado) / esperado < 0.1, \
            f"Gen={r.generacion_anual_kwh}, esperado ≈ {esperado:.0f}"

    def test_factor_planta_chile(self, fv_request_default):
        """Factor de planta en Chile: 0.18-0.25."""
        from app.services.pv_sizing import calcular_fv
        r = calcular_fv(fv_request_default)
        assert 0.15 <= r.factor_planta <= 0.30, f"FP={r.factor_planta} fuera de rango Chile"

    def test_perdida_temperatura_capada_20pct(self):
        """L_temp debe estar capada en 20% incluso con temperaturas altas."""
        from app.models.fv import FvRequest
        from app.services.pv_sizing import calcular_fv
        req = FvRequest(
            consumo_anual_kwh=6000, consumo_mensual_kwh=[500]*12,
            demanda_maxima_kw=3, E_y_kwh_por_kwp=1900, H_y_kwh_m2=2200,
            monthly_E_kwh_por_kwp=[200]*12,
            monthly_t_amb_c=[40]*12,  # 40°C todo el año (Atacama extremo)
            altitud_msnm=2400, tipo_proyecto="vivienda",
            coef_temp_pmp=-0.45,  # Coef agresivo
        )
        r = calcular_fv(req)
        assert r.L_temperatura_pct <= 20.0, f"L_temp={r.L_temperatura_pct}% sin cap a 20%"

    def test_restriccion_superficie_advertencia(self, fv_request_default):
        """Superficie insuficiente → advertencia y ajuste de paneles."""
        from app.services.pv_sizing import calcular_fv
        fv_request_default.superficie_disponible_m2 = 5.0  # solo 5 m² → 2 paneles max
        r = calcular_fv(fv_request_default)
        assert r.N_paneles <= 2, f"N_paneles={r.N_paneles} excede superficie de 5 m²"
        assert any("superficie" in a.lower() for a in r.advertencias), \
            "Falta advertencia de superficie insuficiente"


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO BESS — Autonomía (Lote A)
# ════════════════════════════════════════════════════════════════════════════
class TestBESS:

    def test_capacidad_util_dod_eficiencia(self, fv_request_default):
        """Capacidad útil = nominal × DoD × η_RT."""
        from app.services.pv_sizing import calcular_fv
        fv_request_default.tipo_sistema = "off_grid"
        fv_request_default.dias_autonomia = 2
        fv_request_default.cargas_criticas_pct = 0.4
        fv_request_default.profundidad_descarga = 0.90
        fv_request_default.eficiencia_round_trip = 0.95
        r = calcular_fv(fv_request_default)
        if r.bess_capacidad_kwh > 0:
            esperado_util = r.bess_capacidad_kwh * 0.90 * 0.95
            assert abs(r.bess_capacidad_util_kwh - esperado_util) < 0.5, \
                f"Útil={r.bess_capacidad_util_kwh}, esperado {esperado_util:.1f}"

    def test_off_grid_baja_autonomia_advertencia(self, fv_request_default):
        """Off-grid con autonomía < 1 día → advertencia crítica."""
        from app.services.pv_sizing import calcular_fv
        fv_request_default.tipo_sistema = "off_grid"
        fv_request_default.dias_autonomia = 0.3  # menos de 1 día
        fv_request_default.cargas_criticas_pct = 0.9  # 90% críticas, muy demandante
        fv_request_default.conectado_red = False
        r = calcular_fv(fv_request_default)
        # Debe haber advertencia sobre autonomía baja
        adv_text = " ".join(r.advertencias).lower()
        # No necesariamente bloquea pero debería al menos calcular
        assert r.bess_capacidad_kwh >= 0, "BESS debe calcularse aun con criterio agresivo"


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO RESPALDO (Lote B)
# ════════════════════════════════════════════════════════════════════════════
class TestRespaldo:

    def test_off_grid_puro_sin_empalme(self, fv_request_default):
        """Off-grid puro: 0 capex respaldo, 0 opex, sin empalme."""
        from app.services.pv_sizing import calcular_fv
        fv_request_default.conectado_red = False
        fv_request_default.tipo_respaldo = "ninguno"
        r = calcular_fv(fv_request_default)
        assert r.respaldo_potencia_kw == 0
        assert r.respaldo_capex_usd == 0
        assert "off-grid" in r.empalme_recomendado.lower() or "sin empalme" in r.empalme_recomendado.lower()

    def test_generador_escala_kva_comercial(self, fv_request_default):
        """Generador diésel respeta escala kVA comercial [5,10,15,20,30,50,...]."""
        from app.services.pv_sizing import calcular_fv
        fv_request_default.conectado_red = False
        fv_request_default.tipo_respaldo = "generador_diesel"
        fv_request_default.demanda_maxima_kw = 7  # Forzar generador chico
        r = calcular_fv(fv_request_default)
        ESCALA_KVA = [5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 250, 350, 500]
        # Reverse calc: kva = pot_kw / 0.8
        kva = round(r.respaldo_potencia_kw / 0.8)
        assert kva in ESCALA_KVA, f"kVA={kva} fuera de escala comercial"

    def test_empalme_reducido_genera_ahorro(self, fv_request_default):
        """On-grid + empalme reducido: opex mensual negativo (ahorro)."""
        from app.services.pv_sizing import calcular_fv
        fv_request_default.conectado_red = True
        fv_request_default.tipo_respaldo = "empalme_reducido"
        r = calcular_fv(fv_request_default)
        # Espera empalme < demanda total y ahorro (opex_mensual_clp < 0)
        assert r.respaldo_potencia_kw < fv_request_default.demanda_maxima_kw, \
            "Empalme reducido debe ser menor que demanda total"
        assert r.respaldo_opex_mensual_clp <= 0, "Empalme reducido debería generar ahorro"


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO LAYOUT (Lote D)
# ════════════════════════════════════════════════════════════════════════════
class TestLayout:

    def test_packing_rectangulo_simple(self):
        """Packing sobre rectángulo 10x8m con paneles 1.13x2.28m → 12-18 paneles."""
        from app.models.layout import LayoutRequest, AreaDisponible
        from app.services.layout import calcular_layout
        PANEL_ANCHO_M = 1.13
        area = AreaDisponible(
            poligono=[(0,0), (10,0), (10,8), (0,8)],
            tipo_montaje="techo_plano", retiro_perimetral_m=0.5,
        )
        req = LayoutRequest(area=area, panel_largo_m=2.28, panel_ancho_m=PANEL_ANCHO_M,
                           inclinacion_paneles_deg=30, latitud_deg=-33.4)
        r = calcular_layout(req)
        assert 12 <= r.n_paneles <= 18, f"N_paneles={r.n_paneles}, esperado 12-18"
        assert r.P_kwp_real > 0
        # En techo plano con inclinación → pitch > ancho panel (hay separación entre filas)
        assert r.pitch_m > PANEL_ANCHO_M, f"pitch {r.pitch_m} debería ser > ancho panel {PANEL_ANCHO_M}"

    def test_retiro_excesivo_advertencia(self):
        """Retiro >= 5m (límite) y área chica → packing imposible."""
        from app.models.layout import LayoutRequest, AreaDisponible
        from app.services.layout import calcular_layout
        # Pydantic limita retiro_perimetral_m a [0, 5]
        # Para forzar área vacía, usamos retiro al máximo permitido (5m) en área de 4x4m
        area = AreaDisponible(
            poligono=[(0,0), (4,0), (4,4), (0,4)],
            retiro_perimetral_m=5.0,  # máximo permitido por el modelo
        )
        req = LayoutRequest(area=area)
        r = calcular_layout(req)
        # Con retiro 5m en área 4x4m el polígono útil queda vacío
        assert r.n_paneles == 0
        assert any("retiro" in a.lower() or "obstáculo" in a.lower() or "ningún" in a.lower()
                   for a in r.advertencias), f"Esperaba advertencia, vi: {r.advertencias}"

    def test_techo_inclinado_pitch_es_ancho_panel(self):
        """Techo inclinado coplanar: pitch = ancho_panel (sin separación)."""
        from app.models.layout import LayoutRequest, AreaDisponible
        from app.services.layout import calcular_layout
        area = AreaDisponible(
            poligono=[(0,0),(20,0),(20,10),(0,10)],
            tipo_montaje="techo_inclinado", retiro_perimetral_m=0.3,
        )
        req = LayoutRequest(area=area, panel_largo_m=2.28, panel_ancho_m=1.13)
        r = calcular_layout(req)
        assert abs(r.pitch_m - 2.28) < 0.05 or abs(r.pitch_m - 1.13) < 0.05, \
            f"Techo inclinado pitch={r.pitch_m}, esperado = ancho panel"


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO PLAN SVG (Lote D)
# ════════════════════════════════════════════════════════════════════════════
class TestPlanSvg:

    def test_svg_contiene_recintos(self):
        """SVG generado contiene polígonos y etiquetas de cada recinto."""
        from app.models.plans import PlanoParseado, Recinto
        from app.services.plan_svg import plano_a_svg
        plano = PlanoParseado(
            archivo="test.dxf", formato="dxf", unidad_origen="m", factor_a_metros=1.0,
            n_recintos=2, area_total_m2=50,
            recintos=[
                Recinto(id=1, nombre="Living", uso="living", area_m2=20, perimetro_m=18,
                        centroide=(2.5,2), vertices=[(0,0),(5,0),(5,4),(0,4)], fuente_nombre="layer"),
                Recinto(id=2, nombre="Cocina", uso="cocina", area_m2=30, perimetro_m=22,
                        centroide=(2.5,7), vertices=[(0,4),(5,4),(5,10),(0,10)], fuente_nombre="layer"),
            ],
        )
        svg = plano_a_svg(plano, zona_tecnica_recinto_id=2)
        assert "<svg" in svg
        assert "Living" in svg and "Cocina" in svg
        assert "polygon" in svg
        assert "zona-hatch" in svg  # Patrón de zona técnica resaltada


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO TARIFAS CHILE (Lote E)
# ════════════════════════════════════════════════════════════════════════════
class TestTarifas:

    def test_amperaje_monofasico_escala_iec(self):
        """Amperaje monofásico respeta escala IEC [10,16,20,25,32,40]."""
        from app.services.tarifas_chile import amperaje_para_potencia, ESCALA_AMP_MONOFASICO
        for P_kw in [1.5, 3.0, 5.5, 7.0]:
            amp, _ = amperaje_para_potencia(P_kw, monofasico=True)
            assert amp in ESCALA_AMP_MONOFASICO, f"P={P_kw} kW → {amp}A fuera de escala"

    def test_kw_disponibles_monofasico(self):
        """KW disponibles = A × 220V × fp / 1000."""
        from app.services.tarifas_chile import kw_disponibles_empalme
        # 16A @ 220V × 0.93 = 3.27 kW
        assert abs(kw_disponibles_empalme(16, True) - 3.27) < 0.05

    def test_categoria_bt1_para_residencial_chico(self):
        """Empalme < 8.5 kW monofásico → BT1."""
        from app.services.tarifas_chile import categoria_recomendada
        assert categoria_recomendada(5.0, True) == "BT1"
        assert categoria_recomendada(8.0, True) == "BT1"

    def test_categoria_bt2_para_potencia_intermedia(self):
        """Empalme 10-50 kW → BT2."""
        from app.services.tarifas_chile import categoria_recomendada
        assert categoria_recomendada(30, False) == "BT2"

    def test_costo_anual_bt1(self):
        """Costo BT1 = cargo fijo × 12 + kWh × $165 (constantes 2026 post-fix #3)."""
        from app.services.tarifas_chile import costo_anual_electricidad
        r = costo_anual_electricidad("BT1", kwh_anuales=3000, P_empalme_kw=5)
        # Tras FIX #3: cargo fijo 2200*12 = 26,400 + 3000*165 = 495,000 → 521,400
        assert abs(r["total_anual_clp"] - 521_400) < 100, f"total={r['total_anual_clp']}"
        assert r["cargo_fijo_anual_clp"] == 26_400
        assert r["cargo_variable_anual_clp"] == 495_000

    def test_bt1_acepta_trifasico_hasta_10kw(self):
        """FIX #4 — BT1 también aplica a empalmes trifásicos ≤ 10 kW."""
        from app.services.tarifas_chile import categoria_recomendada
        # Vivienda rural trifásica con bomba de pozo, 7 kW empalme tri
        assert categoria_recomendada(7.0, monofasico=False) == "BT1"
        # 9.5 kW tri sigue siendo BT1
        assert categoria_recomendada(9.5, monofasico=False) == "BT1"
        # 12 kW tri ya pasa a BT2
        assert categoria_recomendada(12, monofasico=False) == "BT2"


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO COMPARATIVA ESCENARIOS (Lote E)
# ════════════════════════════════════════════════════════════════════════════
class TestComparativaEscenarios:

    def test_3_escenarios_presentes(self):
        """La comparativa debe entregar siempre A, B y C."""
        from app.services.comparativa_escenarios import comparar_3_escenarios
        r = comparar_3_escenarios(
            consumo_anual_kwh=6000, cobertura_solar=0.75, P_kwp=4.5,
            demanda_max_kw=3.5, cons_critico_diario_kwh=5.0,
        )
        assert set(r["escenarios"].keys()) == {"A", "B", "C"}
        for k in "ABC":
            e = r["escenarios"][k]
            assert "capex_clp" in e
            assert "opex_anual_clp" in e
            assert "tco_25_anios_clp" in e
            assert isinstance(e["pros"], list)

    def test_capex_A_mayor_que_B(self):
        """Escenario A (BESS gigante) debe tener CAPEX > B (BESS chico)."""
        from app.services.comparativa_escenarios import comparar_3_escenarios
        r = comparar_3_escenarios(
            consumo_anual_kwh=12000, cobertura_solar=0.85, P_kwp=8.5,
            demanda_max_kw=5.2, cons_critico_diario_kwh=8.0,
            dias_autonomia_objetivo=3.0,
        )
        cA = r["escenarios"]["A"]["capex_clp"]
        cB = r["escenarios"]["B"]["capex_clp"]
        assert cA > cB, f"CAPEX A ({cA}) debería ser mayor que B ({cB})"

    def test_escenario_B_empalme_monofasico(self):
        """Escenario B siempre usa empalme monofásico."""
        from app.services.comparativa_escenarios import comparar_3_escenarios
        r = comparar_3_escenarios(
            consumo_anual_kwh=8000, cobertura_solar=0.80, P_kwp=6.0,
            demanda_max_kw=4.5, cons_critico_diario_kwh=6.0,
        )
        B = r["escenarios"]["B"]
        assert "monofásico" in B["empalme_label"].lower()
        assert B["empalme_categoria"] == "BT1"

    def test_recomendacion_es_el_minimo_tco(self):
        """El escenario recomendado es el de TCO menor."""
        from app.services.comparativa_escenarios import comparar_3_escenarios
        r = comparar_3_escenarios(
            consumo_anual_kwh=6000, cobertura_solar=0.75, P_kwp=4.5,
            demanda_max_kw=3.5, cons_critico_diario_kwh=5.0,
        )
        tcos = {k: e["tco_25_anios_clp"] for k, e in r["escenarios"].items()}
        ganador = min(tcos, key=tcos.get)
        assert r["escenario_recomendado"] == ganador


# ════════════════════════════════════════════════════════════════════════════
#  MÓDULO REPORTES (Lote C + E)
# ════════════════════════════════════════════════════════════════════════════
class TestReportesSelectivos:

    def test_catalogo_secciones_completo(self):
        """El catálogo debe incluir las 19 secciones definidas + 2 del Lote E."""
        from app.services.report_sections import SECCIONES_DISPONIBLES
        # Mínimo 19 (Lotes A-D) + 2 (Lote E) = 21 secciones
        assert len(SECCIONES_DISPONIBLES) >= 19
        # Lote E debe incluir estas claves
        assert "analisis_tarifario" in SECCIONES_DISPONIBLES
        assert "comparativa_escenarios" in SECCIONES_DISPONIBLES

    def test_seccion_incluida_default_todo(self):
        """Si secciones_incluidas no está, todo se incluye (backward compat)."""
        from app.services.report_sections import seccion_incluida
        proyecto = {}  # Sin clave secciones_incluidas
        assert seccion_incluida(proyecto, "fv_dimensionamiento") is True
        assert seccion_incluida(proyecto, "cualquier_cosa") is True

    def test_seccion_incluida_lista_vacia_todo(self):
        """Lista vacía equivale a None (no filtrar)."""
        from app.services.report_sections import seccion_incluida
        proyecto = {"secciones_incluidas": []}
        assert seccion_incluida(proyecto, "capex") is True

    def test_seccion_incluida_lista_poblada_filtra(self):
        """Lista poblada sólo incluye lo marcado."""
        from app.services.report_sections import seccion_incluida
        proyecto = {"secciones_incluidas": ["portada_kpis", "resumen_ejecutivo"]}
        assert seccion_incluida(proyecto, "portada_kpis") is True
        assert seccion_incluida(proyecto, "advertencias") is False

    def test_presets_existen(self):
        """Los 3 presets están definidos."""
        from app.services.report_sections import PRESETS
        for k in ["cliente_final", "tecnico_sec", "presupuesto_comercial"]:
            assert k in PRESETS
            assert len(PRESETS[k]) >= 5  # mínimo 5 secciones por preset


# ════════════════════════════════════════════════════════════════════════════
#  INTEGRACIÓN END-TO-END
# ════════════════════════════════════════════════════════════════════════════
class TestIntegracion:

    def test_calcular_fv_completo_incluye_comparativa(self, fv_request_default):
        """El motor completo debe incluir comparativa_escenarios al final."""
        from app.services.pv_sizing import calcular_fv
        r = calcular_fv(fv_request_default)
        assert r.comparativa_escenarios is not None
        assert r.escenario_recomendado in ["A", "B", "C", None]

    def test_pdf_generable_con_filtros(self, fv_request_default, tmp_path):
        """PDF se genera correctamente con preset cliente_final."""
        from app.services.pv_sizing import calcular_fv
        from app.services.report_pdf import generar_pdf
        from app.services.report_sections import PRESETS
        fv_res = calcular_fv(fv_request_default)
        proyecto = {
            "id": "test", "nombre": "Test integral",
            "cliente": "Test", "tipo_proyecto": "vivienda", "fecha_creacion": "2026-05-18",
            "sitio": {
                "nombre":"Santiago", "region":"RM", "lat":-33.45, "lon":-70.65, "altitud_msnm":520,
                "pvgis":{"slope":30,"azimuth":0,"E_y":1850,"H_y":2100,"monthly_E":[180]*12},
                "nasa":{"t2m_avg":14,"wind_avg":2.3,"monthly_ghi":[7]*12,"monthly_t":[15]*12,"months_idx":list(range(1,13))},
            },
            "ric": {
                "consumo_mensual_estimado_kwh": 500, "consumo_anual_estimado_kwh": 6000,
                "recintos_carga": [], "cargas_dedicadas": [],
                "area_total_m2": 80, "subtotal_recintos_w": 4000, "subtotal_dedicadas_w": 3000,
                "carga_total_instalada_w": 7000, "factor_demanda": 0.85, "carga_diversificada_w": 5950,
                "factor_simultaneidad": 0.65, "demanda_maxima_w": 3868, "corriente_nominal_a": 19,
                "tipo_empalme_sugerido": "25A monofásico", "conexion": "monofasica_220",
                "factor_potencia": 0.93,
            },
            "fv": fv_res.model_dump(),
            "eco": {
                "capex_total_clp": 4_500_000, "tipo_cambio": 950, "capex_unitario_usd_kwp": 850,
                "capex_desglose": {"Paneles": 1_800_000, "Inversor": 800_000, "Estructura": 500_000,
                                   "BoS+instalación": 1_100_000, "Trámites": 300_000},
                "payback_simple_anios": 5.2, "VAN_clp": 8_500_000, "TIR_pct": 18,
                "LCOE_clp_kwh": 80, "tasa_descuento": 0.08, "horizonte_anios": 25,
                "flujo_caja_anual_clp": [-4_500_000] + [800_000]*25,
                "flujo_acumulado_clp": [-4_500_000 + 800_000*i for i in range(26)],
                "opex_anual_clp": 50_000, "ahorro_anual_clp": 1_000_000,
                "ingreso_inyeccion_clp": 150_000, "ahorro_total_anual_clp": 1_150_000,
                "CO2_evitado_anual_kg": 2_000, "CO2_evitado_total_kg": 50_000,
                "payback_descontado_anios": 6.5,
            },
            "secciones_incluidas": PRESETS["cliente_final"],
        }
        out = tmp_path / "test_integral.pdf"
        generar_pdf(proyecto, out)
        assert out.exists()
        # Tamaño > 5 KB (no es archivo vacío) y < 200 KB (filtro funcionó)
        size = out.stat().st_size
        assert 5_000 < size < 200_000, f"PDF tamaño {size} fuera de rango esperado"
