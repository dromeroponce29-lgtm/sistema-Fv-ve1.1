"""Informe ejecutivo en PDF con reportlab + matplotlib.

Documento de 3-4 páginas pensado para entregar al cliente final:
caratula, resumen del proyecto, métricas técnicas y económicas,
gráficos clave, y disclaimers normativos.
"""
import io
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image,
    KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from app.services.report_sections import seccion_incluida

ORANGE = colors.HexColor("#C56022")
ORANGE_DARK = colors.HexColor("#8C3F12")
GRAY = colors.HexColor("#595959")
LIGHT = colors.HexColor("#F5E6D8")
MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]


def _hex(c): return colors.HexColor(c)


def _chart_generacion(fv, consumo_mes):
    """Gráfico mensual generación vs consumo → BytesIO PNG."""
    fig, ax = plt.subplots(figsize=(7, 3))
    x = list(range(12))
    ax.bar(x, fv["generacion_mensual_kwh"], color="#e89923", label="Generación FV", width=0.7)
    ax.plot(x, [consumo_mes]*12, color="#1f1d18", linewidth=2, marker="o", markersize=4, label="Consumo")
    ax.set_xticks(x)
    ax.set_xticklabels(MESES, fontsize=9)
    ax.set_ylabel("kWh/mes", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#ece8dd", linewidth=0.5)
    ax.set_axisbelow(True)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _chart_flujo(eco):
    """Gráfico flujo de caja acumulado."""
    fig, ax = plt.subplots(figsize=(7, 3))
    y = list(range(len(eco["flujo_acumulado_clp"])))
    vals_m = [v/1e6 for v in eco["flujo_acumulado_clp"]]
    ax.fill_between(y, vals_m, 0, where=[v>=0 for v in vals_m], color="#3a8348", alpha=0.25, label="Flujo positivo")
    ax.fill_between(y, vals_m, 0, where=[v<0 for v in vals_m], color="#c56022", alpha=0.25, label="Flujo negativo")
    ax.plot(y, vals_m, color="#c56022", linewidth=2)
    ax.axhline(0, color="#1f1d18", linewidth=1, linestyle="--")
    ax.set_xlabel("Año", fontsize=9)
    ax.set_ylabel("CLP (millones)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#ece8dd", linewidth=0.5)
    ax.set_axisbelow(True)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="EYE", fontName="Helvetica-Bold", fontSize=8, textColor=ORANGE, alignment=TA_LEFT, spaceAfter=2))
    s.add(ParagraphStyle(name="TITLE2", fontName="Helvetica-Bold", fontSize=20, textColor=colors.black, spaceAfter=6, leading=22))
    s.add(ParagraphStyle(name="SUB", fontName="Helvetica-Oblique", fontSize=10, textColor=GRAY, spaceAfter=14))
    s.add(ParagraphStyle(name="H2X", fontName="Helvetica-Bold", fontSize=12, textColor=ORANGE_DARK, spaceBefore=10, spaceAfter=6))
    s.add(ParagraphStyle(name="BODY", fontName="Helvetica", fontSize=10, textColor=colors.black, leading=13, spaceAfter=6))
    s.add(ParagraphStyle(name="SMALL", fontName="Helvetica", fontSize=8, textColor=GRAY, leading=10))
    return s


def _clp(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def _kpi_table(rows):
    t = Table(rows, colWidths=[5.5*cm, 4*cm, 5.5*cm, 4*cm])
    t.setStyle(TableStyle([
        ("FONT", (0,0), (-1,-1), "Helvetica", 9),
        ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
        ("FONT", (2,0), (2,-1), "Helvetica-Bold", 9),
        ("FONT", (1,0), (1,-1), "Helvetica-Bold", 11),
        ("FONT", (3,0), (3,-1), "Helvetica-Bold", 11),
        ("TEXTCOLOR", (0,0), (0,-1), GRAY),
        ("TEXTCOLOR", (2,0), (2,-1), GRAY),
        ("TEXTCOLOR", (1,0), (1,-1), ORANGE_DARK),
        ("TEXTCOLOR", (3,0), (3,-1), ORANGE_DARK),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("ALIGN", (3,0), (3,-1), "RIGHT"),
        ("LINEBELOW", (0,0), (-1,-1), 0.4, colors.HexColor("#E6E2D8")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 7),
    ]))
    return t


def generar_pdf(proyecto: dict, salida: Path | str) -> Path:
    salida = Path(salida)
    fv = proyecto.get("fv", {})
    eco = proyecto.get("eco", {})
    ric = proyecto["ric"]
    s = proyecto["sitio"]
    inc = lambda k: seccion_incluida(proyecto, k)

    doc = SimpleDocTemplate(
        str(salida), pagesize=letter,
        leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.5*cm, bottomMargin=1.5*cm,
        title=f"Informe FV — {proyecto['nombre']}", author="FV Chile",
    )
    sty = _styles()
    story = []

    # === PORTADA === (siempre incluida, es identificación básica)
    story.append(Paragraph("INFORME EJECUTIVO", sty["EYE"]))
    story.append(Paragraph("Sistema Solar Fotovoltaico", sty["TITLE2"]))
    story.append(Paragraph(proyecto["nombre"], sty["H2X"]))
    story.append(Paragraph(
        f"{proyecto.get('cliente','')} · {s['nombre']}, {s['region']} · {proyecto.get('fecha_creacion','')}",
        sty["SUB"]))

    # Big numbers — KPIs principales
    cob_pct = (fv.get("cobertura_real", 0) * 100)
    pay = eco.get("payback_simple_anios", 0)
    capex = eco.get("capex_total_clp", 0)
    ahorro = eco.get("ahorro_total_anual_clp", 0)

    rows = [
        ["Potencia FV", f"{fv.get('P_kwp','—')} kWp", "Cobertura solar", f"{cob_pct:.0f}%"],
        ["Generación anual", f"{fv.get('generacion_anual_kwh',0):,.0f} kWh".replace(",", "."),
         "Ahorro anual", _clp(ahorro)],
        ["CAPEX estimado", _clp(capex), "Payback", f"{pay:.1f} años"],
        ["TIR (25 años)", f"{eco.get('TIR_pct','—')}%" if eco.get('TIR_pct') is not None else "—",
         "LCOE", f"{eco.get('LCOE_clp_kwh',0):,.0f} CLP/kWh".replace(",", ".")],
        ["Reducción CO2", f"{eco.get('CO2_evitado_anual_kg',0)/1000:.1f} tCO2/año",
         "Total 25 años", f"{eco.get('CO2_evitado_total_kg',0)/1000:.0f} tCO2"],
    ]
    if inc("portada_kpis"):
        story.append(_kpi_table(rows))
        story.append(Spacer(1, 0.4*cm))

    # Resumen narrativo
    if inc("resumen_ejecutivo"):
        story.append(Paragraph("Resumen", sty["H2X"]))
        inv = fv.get("inversor_modelo", "—")
        story.append(Paragraph(
            f"Se propone un sistema fotovoltaico de <b>{fv.get('P_kwp','—')} kWp</b> compuesto por "
            f"<b>{fv.get('N_paneles','—')} paneles de 550 W</b> sobre una superficie de "
            f"<b>{fv.get('superficie_m2','—')} m²</b>, con inversor <b>{inv}</b>. "
            f"El sistema cubrirá aproximadamente el <b>{cob_pct:.0f}%</b> del consumo anual estimado "
            f"({ric['consumo_anual_estimado_kwh']:,.0f} kWh/año).".replace(",", "."), sty["BODY"]))
        if eco:
            van_clp = eco.get("VAN_clp", 0)
            signo = "viable" if van_clp > 0 else "no recupera la inversión"
            story.append(Paragraph(
                f"El análisis económico a 25 años entrega un VAN de <b>{_clp(van_clp)}</b> a tasa "
                f"{eco['tasa_descuento']*100:.0f}%, lo que indica que el proyecto es <b>{signo}</b>. "
                f"El payback simple es de <b>{pay:.1f} años</b>, equivalente a una TIR de "
                f"<b>{eco.get('TIR_pct','—')}%</b>. La energía generada tiene un costo nivelado (LCOE) "
                f"de <b>{eco['LCOE_clp_kwh']:,.0f} CLP/kWh</b>.".replace(",", "."), sty["BODY"]))

    story.append(PageBreak())

    # === PÁGINA 2 — Detalles técnicos + gráficos ===
    if inc("sitio"):
        story.append(Paragraph("Sitio y recurso solar", sty["H2X"]))
        sitio_data = [
            ["Ubicación", f"{s['nombre']}, {s['region']}"],
            ["Coordenadas", f"{s['lat']:.4f}, {s['lon']:.4f}"],
            ["Altitud", f"{s.get('altitud_msnm','—')} msnm"],
            ["Inclinación óptima", f"{s['pvgis']['slope']}°"],
            ["Azimut óptimo", f"{s['pvgis']['azimuth']}° (norte)"],
            ["Generación por kWp (PVGIS)", f"{s['pvgis']['E_y']:,.0f} kWh/kWp/año".replace(",", ".")],
            ["Temperatura ambiente promedio", f"{s['nasa']['t2m_avg']:.1f} °C"],
        ]
        t = Table(sitio_data, colWidths=[6*cm, 11.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), GRAY),
            ("LINEBELOW", (0,0), (-1,-1), 0.4, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    if fv and inc("generacion_grafica"):
        story.append(Paragraph("Generación esperada (kWh/mes)", sty["H2X"]))
        img_gen = _chart_generacion(fv, ric["consumo_mensual_estimado_kwh"])
        story.append(Image(img_gen, width=17.5*cm, height=7*cm))
        story.append(Spacer(1, 0.3*cm))

    if eco and inc("flujo_caja"):
        story.append(Paragraph("Flujo de caja acumulado (25 años)", sty["H2X"]))
        img_flujo = _chart_flujo(eco)
        story.append(Image(img_flujo, width=17.5*cm, height=7*cm))

    story.append(PageBreak())

    # === PÁGINA 3 — Desglose CAPEX + Normativo ===
    if eco and inc("capex"):
        story.append(Paragraph("Desglose de inversión (CAPEX)", sty["H2X"]))
        rows = [["Partida", "CLP", "% del total"]]
        for k, v in eco["capex_desglose"].items():
            if v:
                rows.append([k, _clp(v), f"{v/eco['capex_total_clp']*100:.1f}%"])
        rows.append(["Total", _clp(eco["capex_total_clp"]), "100%"])
        t = Table(rows, colWidths=[9*cm, 5*cm, 3.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 9),
            ("BACKGROUND", (0,0), (-1,0), LIGHT),
            ("TEXTCOLOR", (0,0), (-1,0), ORANGE_DARK),
            ("FONT", (0,1), (-1,-2), "Helvetica", 9),
            ("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 10),
            ("BACKGROUND", (0,-1), (-1,-1), LIGHT),
            ("LINEBELOW", (0,0), (-1,-1), 0.4, colors.HexColor("#E6E2D8")),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

    # LOTE E — Comparativa de escenarios (si está disponible)
    comp = fv.get("comparativa_escenarios") if fv else None
    if comp and inc("comparativa_escenarios") and "escenarios" in comp:
        story.append(Paragraph("Comparativa de escenarios de continuidad operacional", sty["H2X"]))
        story.append(Paragraph(
            f"Análisis de 3 arquitecturas posibles sobre un horizonte de "
            f"{comp.get('horizonte_anios',25)} años, tasa de descuento "
            f"{comp.get('tasa_descuento',0.08)*100:.0f}%. El escenario óptimo según TCO es "
            f"<b>{comp.get('escenario_recomendado','—')}</b>.", sty["BODY"]))

        rows = [["Escenario", "CAPEX (CLP)", "OPEX/año (CLP)", "TCO 25y (CLP)"]]
        for k in ["A", "B", "C"]:
            e = comp["escenarios"].get(k, {})
            if not e:
                continue
            marca = "★ " if e.get("es_recomendado") else ""
            nombre = f"{marca}{k}: {e.get('nombre','—')[:55]}"
            rows.append([
                nombre,
                _clp(e.get("capex_clp", 0)),
                _clp(e.get("opex_anual_clp", 0)),
                _clp(e.get("tco_25_anios_clp", 0)),
            ])
        t = Table(rows, colWidths=[8.5*cm, 3*cm, 3*cm, 3*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 9),
            ("BACKGROUND", (0,0), (-1,0), LIGHT),
            ("TEXTCOLOR", (0,0), (-1,0), ORANGE_DARK),
            ("FONT", (0,1), (-1,-1), "Helvetica", 8.5),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            f"<i>Recomendación:</i> {comp.get('explicacion_recomendacion','')}", sty["BODY"]))
        story.append(Spacer(1, 0.4*cm))

    # LOTE E — Detalle tarifario del empalme recomendado
    if comp and inc("analisis_tarifario") and "escenarios" in comp:
        rec = comp.get("escenario_recomendado")
        if rec in comp["escenarios"]:
            e = comp["escenarios"][rec]
            if e.get("empalme_label"):
                story.append(Paragraph("Análisis tarifario del empalme recomendado", sty["H2X"]))
                detalles_filas = [
                    ["Empalme",          e.get("empalme_label", "—")],
                    ["Categoría tarifaria", e.get("empalme_categoria", "—")],
                ]
                if "consumo_red_anual_kwh" in e:
                    detalles_filas.append(["Consumo desde red", f"{e['consumo_red_anual_kwh']:,.0f} kWh/año".replace(",", ".")])
                if "compra_red_anual_kwh" in e:
                    detalles_filas.append(["Compra desde red", f"{e['compra_red_anual_kwh']:,.0f} kWh/año".replace(",", ".")])
                if "inyeccion_red_anual_kwh" in e:
                    detalles_filas.append(["Inyección a red (netbilling)", f"{e['inyeccion_red_anual_kwh']:,.0f} kWh/año".replace(",", ".")])
                if "ingreso_netbilling_clp" in e:
                    detalles_filas.append(["Ingreso netbilling", _clp(e['ingreso_netbilling_clp'])])
                detalles_filas.append(["OPEX anual eléctrico", _clp(e.get("opex_anual_clp", 0))])
                t = Table(detalles_filas, colWidths=[7*cm, 10.5*cm])
                t.setStyle(TableStyle([
                    ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
                    ("FONT", (1,0), (1,-1), "Helvetica", 9),
                    ("TEXTCOLOR", (0,0), (0,-1), GRAY),
                    ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                    ("TOPPADDING", (0,0), (-1,-1), 5),
                ]))
                story.append(t)
                if e.get("costo_red_detalle", {}).get("detalle"):
                    story.append(Spacer(1, 0.2*cm))
                    story.append(Paragraph(f"<i>{e['costo_red_detalle']['detalle']}</i>", sty["SMALL"]))
                story.append(Spacer(1, 0.4*cm))

    if inc("normativa"):
        story.append(Paragraph("Cumplimiento normativo", sty["H2X"]))
        P_kwp = fv.get("P_kwp", 0)
        categoria_nb = "BT1 ≤ 20 kW — Netbilling con compra obligatoria" if P_kwp <= 20 else \
                       ("Netbilling estándar (20-300 kW)" if P_kwp <= 300 else "PMGD (> 300 kW)")
        story.append(Paragraph(
            f"<b>Categoría:</b> {categoria_nb}.<br/>"
            "<b>Marco legal:</b> Ley 21.118 de Generación Distribuida (Netbilling) — "
            "permite inyectar excedentes a la red al precio del componente de energía.<br/>"
            "<b>Norma técnica:</b> Pliegos RIC vigentes de la SEC para el dimensionamiento "
            "de circuitos interiores, protecciones y conductores.<br/>"
            "<b>Declaración:</b> requiere TE-1 firmada por instalador eléctrico autorizado "
            "(clase A/B/C/D según potencia) y aprobación de la empresa distribuidora.", sty["BODY"]))
        story.append(Spacer(1, 0.5*cm))

    if inc("advertencias"):
        story.append(Paragraph("Advertencias", sty["H2X"]))
        story.append(Paragraph(
            "Este informe constituye un <b>predimensionamiento técnico-comercial</b>; no reemplaza "
            "el proyecto eléctrico de detalle ni los planos as-built requeridos por la SEC. Los datos "
            "de recurso solar provienen de PVGIS v5.3 (Joint Research Centre) y NASA POWER, con "
            "incertidumbre típica de ±5% anual. Los costos referenciales deben actualizarse por "
            "cotización al inicio del proyecto. El factor de emisión SEN utilizado para el cálculo "
            "de CO2 evitado es 0,200 tCO2/MWh (Coordinador Eléctrico Nacional, 2024).", sty["BODY"]))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Documento generado por <b>FV Chile</b> · {proyecto.get('fecha_creacion','')}", sty["SMALL"]))

    doc.build(story)
    return salida
