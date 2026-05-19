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
from app.services.fv_equipment import seleccionar_panel, seleccionar_inversor, seleccionar_bateria

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


def _chart_planos_layout(plano: dict, layout: dict | None = None):
    """Renderiza el plano arquitectónico + overlay de paneles FV como PNG.

    plano:  PlanoParseado dict (recintos con vertices, centroide, nombre)
    layout: dict opcional con paneles_xy [(x,y),...] y dimensiones panel
    """
    from matplotlib.patches import Polygon as MplPolygon, Rectangle as MplRect
    from matplotlib.collections import PatchCollection
    if not plano or not plano.get("recintos"):
        return None

    color_uso = {
        "living": "#FAF0E1", "comedor": "#FAEFD8", "dormitorio": "#E8EEF5",
        "cocina": "#FBE3CC", "bano": "#E0F0EA", "oficina": "#F2EAE0",
        "hall": "#F5F1E8", "pasillo": "#F0ECE3", "exterior": "#EDE9DB",
        "lavanderia": "#E8EFE5", "logia": "#E6E8DD", "bodega": "#EAE6D9",
        "circulacion": "#F0ECE3", "comun": "#EFEBE0", "desconocido": "#F5F2E8",
    }
    fig, ax = plt.subplots(figsize=(10, 7))

    # Dibujar recintos
    for r in plano["recintos"]:
        verts = r.get("vertices", [])
        if len(verts) < 3:
            continue
        color = color_uso.get(r.get("uso", "desconocido"), "#F5F2E8")
        poly = MplPolygon(verts, closed=True, facecolor=color, edgecolor="#6B5340",
                          linewidth=1.0)
        ax.add_patch(poly)
        cx, cy = r.get("centroide", (0, 0))
        ax.text(cx, cy, r.get("nombre", ""), ha="center", va="center",
                fontsize=8, fontweight="bold", color="#1F1D18")
        ax.text(cx, cy - 0.3, f"{r.get('area_m2', 0):.1f} m²", ha="center", va="center",
                fontsize=6, color="#4A3826")

    # Overlay paneles (si layout disponible)
    if layout and layout.get("paneles_xy") and layout.get("panel_largo_m"):
        L = layout["panel_largo_m"]
        A = layout["panel_ancho_m"]
        # Paneles_xy es [[x,y], ...] esquina inf-izq
        for (x, y) in layout["paneles_xy"]:
            rect = MplRect((x, y), L, A, facecolor="#1E4A7A", edgecolor="#0F3158",
                           linewidth=0.4, alpha=0.85)
            ax.add_patch(rect)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.grid(True, color="#E8E2D0", linewidth=0.4, linestyle=":")
    ax.set_xlabel("X (m)", fontsize=9)
    ax.set_ylabel("Y (m)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("Plano de implantación FV — recintos + paneles", fontsize=11, fontweight="bold", color="#8C3F12")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
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

    # ─── Sección EXPLICACIÓN SIMPLE (Importante #8) ───
    if inc("explicacion_simple") and eco:
        story.append(Paragraph("¿Qué significa todo esto en palabras simples?", sty["H2X"]))
        consumo_anual_kwh = ric.get("consumo_anual_estimado_kwh", 0)
        tarifa = 220  # CLP/kWh referencial residencial
        cuenta_mensual_actual = (consumo_anual_kwh * tarifa) / 12
        ahorro_anual = eco.get("ahorro_total_anual_clp", 0)
        meses_luz_gratis = ahorro_anual / cuenta_mensual_actual if cuenta_mensual_actual > 0 else 0
        capex = eco.get("capex_total_clp", 0)
        co2_anual_ton = eco.get("CO2_evitado_anual_kg", 0) / 1000

        story.append(Paragraph(
            f"Hoy probablemente gastas alrededor de <b>${cuenta_mensual_actual:,.0f} CLP al mes</b> en electricidad "
            f"(considerando una tarifa promedio de $220/kWh). Con este sistema solar:".replace(",", "."),
            sty["BODY"]))
        story.append(Spacer(1, 0.15*cm))

        bullets = [
            f"<b>Pagarás menos luz desde el día 1.</b> Te ahorrarás aproximadamente "
            f"<b>${ahorro_anual:,.0f} CLP cada año</b>, equivalente a <b>{meses_luz_gratis:.1f} meses de cuenta de luz gratis</b> al año.".replace(",", "."),

            f"<b>Recuperarás tu inversión.</b> Después de pagar <b>${capex:,.0f} CLP</b> ".replace(",", ".") +
            f"al instalar el sistema, los ahorros lo devuelven en <b>{pay:.1f} años</b>. "
            f"Después de ese plazo, todo lo que el sol genere es ganancia limpia.",

            f"<b>El sistema dura mucho más.</b> Los paneles tienen <b>25 años de garantía</b> de potencia. "
            f"Es decir, vas a recibir <b>al menos {25 - pay:.0f} años de ahorro neto</b> después de pagado.",

            f"<b>Ayudas al planeta.</b> Cada año dejarás de emitir <b>{co2_anual_ton:.1f} toneladas de CO₂</b>, "
            f"equivalente a <b>retirar {co2_anual_ton/2.3:.1f} autos</b> de circulación durante un año.",

            f"<b>Tu casa vale más.</b> Estudios inmobiliarios chilenos indican que una vivienda con FV se cotiza "
            f"entre <b>3% y 5% más</b> que una equivalente sin paneles.",
        ]
        for b in bullets:
            p = Paragraph(f"• {b}", sty["BODY"])
            story.append(p)
            story.append(Spacer(1, 0.1*cm))

        story.append(Spacer(1, 0.3*cm))
        # Glosario simple de términos técnicos
        story.append(Paragraph("Glosario breve (sin tecnicismos):", sty["H2X"]))
        glosario = [
            ["kWp", "Kilowatt-peak. Es el tamaño del sistema, cuántos paneles llevará. Más kWp = más generación."],
            ["kWh", "Kilowatt-hora. Es la unidad de energía que aparece en tu cuenta de luz."],
            ["Payback", "Cuántos años tarda en pagarse solo el sistema, con los ahorros."],
            ["VAN", "Valor Actual Neto. En palabras simples: cuánto dinero te queda al final de 25 años (después de pagar todo y considerar la inflación). Si es positivo → el proyecto te conviene."],
            ["TIR", "Tasa Interna de Retorno. Es como el 'interés anual' que te paga el sistema. Si supera al 8% de tasa de descuento → vale la pena."],
            ["LCOE", "Costo nivelado de energía. Es cuánto te termina costando cada kWh que el sol te entrega, sumando inversión y mantención. Si es menor que la tarifa que pagas hoy → ahorras."],
            ["Netbilling", "Ley 21.118. Te permite vender los excedentes de energía solar a la empresa eléctrica."],
            ["CO₂", "Dióxido de carbono. El gas que causa el cambio climático. Cada kWh solar evita ~0.2 kg de CO₂."],
        ]
        t = Table(glosario, colWidths=[2.5*cm, 15*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), ORANGE_DARK),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))

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

    # ─── Sección CONSUMO ─── cargas RIC del módulo cargas
    if inc("consumo") and ric:
        story.append(Paragraph("Cargas eléctricas y consumo (RIC)", sty["H2X"]))
        rows_ric = [
            ["Tipo de proyecto", ric.get("tipo_proyecto", "—").replace("_", " ").title()],
            ["Superficie total", f"{ric.get('area_total_m2', 0):.1f} m²"],
            ["N° recintos", str(ric.get("n_recintos", 0))],
            ["Carga total instalada", f"{ric.get('carga_total_instalada_w', 0):,.0f} W".replace(",", ".")],
            ["Factor de demanda", f"{ric.get('factor_demanda', 0):.2f}"],
            ["Factor de simultaneidad", f"{ric.get('factor_simultaneidad', 0):.2f}"],
            ["Demanda máxima del empalme", f"{ric.get('demanda_maxima_w', 0):,.0f} W = {ric.get('demanda_maxima_w', 0)/1000:.2f} kW".replace(",", ".")],
            ["Corriente nominal", f"{ric.get('corriente_nominal_a', 0):.1f} A"],
            ["Empalme sugerido (RIC)", ric.get("tipo_empalme_sugerido", "—")],
            ["Conexión", ric.get("conexion", "—").replace("_", " ")],
            ["Factor de potencia", f"{ric.get('factor_potencia', 0.93):.2f}"],
            ["Consumo anual estimado", f"{ric.get('consumo_anual_estimado_kwh', 0):,.0f} kWh/año".replace(",", ".")],
        ]
        t = Table(rows_ric, colWidths=[7*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), GRAY),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección BALANCE DE FASES ─── solo si es trifásico
    if inc("balance_fases") and ric and ric.get("conexion") == "trifasica_380":
        story.append(Paragraph("Balance de fases (L1/L2/L3)", sty["H2X"]))
        bal_rows = [
            ["", "Carga (W)", "Corriente (A)"],
            ["Fase L1", f"{ric.get('carga_L1_w', 0):,.0f}".replace(",","."), f"{ric.get('corriente_L1_a', 0):.1f}"],
            ["Fase L2", f"{ric.get('carga_L2_w', 0):,.0f}".replace(",","."), f"{ric.get('corriente_L2_a', 0):.1f}"],
            ["Fase L3", f"{ric.get('carga_L3_w', 0):,.0f}".replace(",","."), f"{ric.get('corriente_L3_a', 0):.1f}"],
            ["Desbalance", f"{ric.get('desbalance_fases_pct', 0):.1f} %", "(< 15 % aceptable)"],
        ]
        t = Table(bal_rows, colWidths=[5*cm, 6*cm, 6.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 9),
            ("BACKGROUND", (0,0), (-1,0), LIGHT),
            ("TEXTCOLOR", (0,0), (-1,0), ORANGE_DARK),
            ("FONT", (0,1), (-1,-1), "Helvetica", 9),
            ("FONT", (0,1), (0,-1), "Helvetica-Bold", 9),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
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

    # ─── Sección DIMENSIONAMIENTO FV ───
    if fv and inc("fv_dimensionamiento"):
        story.append(Paragraph("Dimensionamiento del sistema fotovoltaico", sty["H2X"]))
        fv_rows = [
            ["Potencia FV instalada (DC)",   f"{fv.get('P_kwp', 0):.2f} kWp"],
            ["N° de paneles",                f"{fv.get('N_paneles', 0)} unidades de {fv.get('panel_Pnom_w', 550) if False else 550} W"],
            ["Superficie ocupada",           f"{fv.get('superficie_m2', 0):.1f} m²"],
            ["Inversor",                     fv.get("inversor_modelo", "—")],
            ["Potencia AC del inversor",     f"{fv.get('inversor_P_AC_kw', 0):.1f} kW"],
            ["Ratio DC/AC",                  "1.20"],
            ["Performance Ratio (PR)",       f"{fv.get('PR_anual', 0)*100:.1f} %"],
            ["Factor de planta",             f"{fv.get('factor_planta', 0)*100:.1f} %"],
            ["Temperatura celda promedio",   f"{fv.get('T_celda_promedio_c', 0):.1f} °C"],
            ["Generación anual",             f"{fv.get('generacion_anual_kwh', 0):,.0f} kWh".replace(",", ".")],
            ["Cobertura solar del consumo",  f"{fv.get('cobertura_real', 0)*100:.1f} %"],
        ]
        t = Table(fv_rows, colWidths=[7*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), GRAY),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        # Tabla de pérdidas
        if fv.get("perdidas"):
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph("Pérdidas técnicas consideradas:", sty["BODY"]))
            perd_rows = [["Pérdida", "Magnitud"]]
            for pd in fv["perdidas"]:
                perd_rows.append([pd["nombre"], f"{pd['pct']:.2f} %"])
            t2 = Table(perd_rows, colWidths=[9*cm, 4*cm])
            t2.setStyle(TableStyle([
                ("FONT", (0,0), (-1,0), "Helvetica-Bold", 9),
                ("BACKGROUND", (0,0), (-1,0), LIGHT),
                ("FONT", (0,1), (-1,-1), "Helvetica", 9),
                ("ALIGN", (1,0), (-1,-1), "RIGHT"),
                ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4), ("TOPPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(t2)
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección BESS ───
    if fv and inc("bess") and fv.get("bess_capacidad_kwh", 0) > 0:
        story.append(Paragraph("Sistema de almacenamiento (BESS)", sty["H2X"]))
        bess_rows = [
            ["Capacidad nominal",              f"{fv.get('bess_capacidad_kwh', 0):.1f} kWh"],
            ["Capacidad útil (tras DoD × η)",  f"{fv.get('bess_capacidad_util_kwh', 0):.1f} kWh"],
            ["Potencia máxima de descarga",    f"{fv.get('bess_potencia_kw', 0):.1f} kW"],
            ["Días de autonomía real",         f"{fv.get('bess_dias_autonomia_real', 0):.2f} días"],
            ["Consumo crítico diario",         f"{fv.get('bess_consumo_critico_diario_kwh', 0):.1f} kWh/día"],
            ["Modelo de batería",              fv.get("bess_modelo", "—") or "—"],
        ]
        t = Table(bess_rows, colWidths=[7*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), GRAY),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        if fv.get("bess_criterio_dimensionamiento"):
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(f"<i>Criterio: {fv['bess_criterio_dimensionamiento']}</i>", sty["SMALL"]))
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección RESPALDO ───
    if fv and inc("respaldo"):
        story.append(Paragraph("Respaldo y conexión a red", sty["H2X"]))
        resp_rows = [
            ["Conectado a la red",          "Sí" if fv.get("conectado_red") else "No (off-grid)"],
            ["Tipo de respaldo",            fv.get("tipo_respaldo", "—").replace("_", " ").title()],
            ["Potencia de respaldo",        f"{fv.get('respaldo_potencia_kw', 0):.1f} kW"],
            ["Empalme recomendado",         fv.get("empalme_recomendado", "—") or "—"],
            ["Descripción",                 fv.get("respaldo_descripcion", "—") or "—"],
            ["CAPEX adicional respaldo",    f"USD {fv.get('respaldo_capex_usd', 0):,.0f}".replace(",", ".")],
            ["OPEX mensual respaldo",       _clp(fv.get("respaldo_opex_mensual_clp", 0))],
        ]
        t = Table(resp_rows, colWidths=[7*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), GRAY),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        if fv.get("respaldo_criterio"):
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(f"<i>{fv['respaldo_criterio']}</i>", sty["SMALL"]))
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección LAYOUT ───
    layout = proyecto.get("layout", {})
    if layout and inc("layout") and layout.get("n_paneles", 0) > 0:
        story.append(Paragraph("Layout y disposición de paneles", sty["H2X"]))
        lay_rows = [
            ["Tipo de montaje",           layout.get("tipo_montaje", "—").replace("_", " ").title()],
            ["N° paneles dispuestos",     f"{layout.get('n_paneles', 0)} unidades"],
            ["N° de filas",               f"{layout.get('n_filas', 0)}"],
            ["Pitch entre filas",         f"{layout.get('pitch_m', 0):.2f} m"],
            ["Potencia real instalable",  f"{layout.get('P_kwp_real', 0):.2f} kWp"],
            ["Área útil disponible",      f"{layout.get('area_util_m2', 0):.1f} m²"],
            ["Aprovechamiento",           f"{layout.get('aprovechamiento_pct', 0):.1f} %"],
        ]
        t = Table(lay_rows, colWidths=[7*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), GRAY),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección PLANOS TÉCNICOS (Bloqueante #5) ───
    plano_data = proyecto.get("plano", {})
    if plano_data and plano_data.get("recintos") and inc("planos_tecnicos"):
        story.append(PageBreak())
        story.append(Paragraph("Planos técnicos — implantación FV", sty["H2X"]))
        story.append(Paragraph(
            f"Plano arquitectónico del proyecto con superposición de los paneles fotovoltaicos. "
            f"Recintos detectados: {plano_data.get('n_recintos', len(plano_data['recintos']))} · "
            f"superficie total: {plano_data.get('area_total_m2', 0):.1f} m² · "
            f"unidad de origen: {plano_data.get('unidad_origen', 'm')}.", sty["BODY"]))
        story.append(Spacer(1, 0.3*cm))

        img_planos = _chart_planos_layout(plano_data, layout)
        if img_planos:
            story.append(Image(img_planos, width=17.5*cm, height=12*cm))
            story.append(Spacer(1, 0.2*cm))
            # Leyenda
            story.append(Paragraph(
                "<b>Leyenda:</b> "
                "<font color='#1E4A7A'>■</font> Paneles FV · "
                "<font color='#FAF0E1'>■</font> Living/Comedor · "
                "<font color='#E8EEF5'>■</font> Dormitorio · "
                "<font color='#FBE3CC'>■</font> Cocina · "
                "<font color='#E0F0EA'>■</font> Baño · "
                "<font color='#EDE9DB'>■</font> Exterior/Azotea (zona técnica) · "
                "Grid 1 m × 1 m", sty["SMALL"]))
            story.append(Spacer(1, 0.3*cm))
        else:
            story.append(Paragraph(
                "<i>El proyecto no tiene plano arquitectónico parseado todavía. "
                "Sube un DXF o PDF vectorial en el tab Layout para generar este plano.</i>",
                sty["BODY"]))

        # Tabla de información técnica del layout (si existe)
        if layout and layout.get("n_paneles", 0) > 0:
            story.append(Paragraph("Datos del layout:", sty["BODY"]))
            cuadro_rows = [
                ["Tipo de montaje",     layout.get("tipo_montaje", "—").replace("_", " ").title()],
                ["N° paneles dispuestos", f"{layout.get('n_paneles', 0)}"],
                ["N° de filas",         f"{layout.get('n_filas', 0)}"],
                ["Pitch entre filas",   f"{layout.get('pitch_m', 0):.2f} m"],
                ["Potencia FV real",    f"{layout.get('P_kwp_real', 0):.2f} kWp"],
                ["Aprovechamiento",     f"{layout.get('aprovechamiento_pct', 0):.1f} %"],
            ]
            t = Table(cuadro_rows, colWidths=[6*cm, 11.5*cm])
            t.setStyle(TableStyle([
                ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
                ("FONT", (1,0), (1,-1), "Helvetica", 9),
                ("TEXTCOLOR", (0,0), (0,-1), GRAY),
                ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4), ("TOPPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección UNIFILAR (simplificada — texto descriptivo) ───
    if inc("unifilar"):
        story.append(Paragraph("Diagrama unifilar — protecciones eléctricas", sty["H2X"]))
        story.append(Paragraph(
            "<b>Lado DC (paneles → inversor):</b> Fusibles tipo gPV en serie con cada string "
            "(Isc × 1.56), seccionador DC bipolar con capacidad de corte bajo carga, descargador "
            "de sobretensiones (SPD) tipo II clase II en el string box, conductor de protección (PE) "
            "continuo desde estructura hasta puesta a tierra.", sty["BODY"]))
        story.append(Paragraph(
            "<b>Lado AC (inversor → empalme):</b> Interruptor automático magnetotérmico dimensionado "
            "según corriente nominal del inversor, diferencial superinmunizado tipo A o B (30 mA), "
            "descargador de sobretensiones (SPD) tipo II clase II, medidor bidireccional aprobado por "
            "la empresa distribuidora para netbilling.", sty["BODY"]))
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección PUESTA A TIERRA ───
    if inc("puesta_tierra"):
        story.append(Paragraph("Sistema de puesta a tierra (PAT)", sty["H2X"]))
        story.append(Paragraph(
            "El sistema FV se conectará a la malla de tierra existente del inmueble. Si no existe "
            "malla adecuada, se construirá una nueva con resistencia objetivo <b>≤ 25 Ω</b>, medida "
            "con telurómetro calibrado al momento de la puesta en servicio. La estructura metálica "
            "de soporte de los paneles y todas las partes metálicas accesibles deben "
            "equipotencializarse con conductor de cobre desnudo de sección mínima según la corriente "
            "de cortocircuito esperada.", sty["BODY"]))
        story.append(Spacer(1, 0.4*cm))

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

    # ─── Sección PRESUPUESTO DE EQUIPOS (BOM con specs) ───
    if fv and inc("presupuesto_equipos"):
        story.append(Paragraph("Presupuesto detallado de equipos (BOM)", sty["H2X"]))
        story.append(Paragraph(
            "Bill of Materials con los equipos seleccionados desde el catálogo chileno 2026. "
            "Los precios son referenciales (sin IVA, sin instalación), tipo de cambio CLP/USD = 950. "
            "Ajustar al inicio del proyecto contra cotizaciones reales de proveedores.", sty["BODY"]))
        story.append(Spacer(1, 0.2*cm))

        # Seleccionar equipos según las características del proyecto
        try:
            panel = seleccionar_panel(fv.get("P_kwp", 5.0), proyecto.get("tipo_proyecto", "vivienda"))
            P_AC = fv.get("inversor_P_AC_kw", 5.0)
            monofasico = P_AC <= 10
            requiere_bess = fv.get("bess_capacidad_kwh", 0) > 0
            inversor = seleccionar_inversor(fv.get("P_kwp", 5.0), monofasico_ok=monofasico, requiere_bess=requiere_bess)
            bateria = seleccionar_bateria(fv.get("bess_capacidad_kwh", 0), proyecto.get("tipo_proyecto", "vivienda")) if requiere_bess else None
        except Exception:
            panel, inversor, bateria = None, None, None

        N_pan = fv.get("N_paneles", 0)
        P_kwp = fv.get("P_kwp", 0)

        # === Tabla principal BOM ===
        bom_header = ["Equipo", "Detalle", "Cant.", "P. unit. (USD)", "Total (USD)"]
        bom_rows = [bom_header]

        if panel:
            bom_rows.append([
                f"Panel FV\n{panel.get('marca','—')} {panel.get('modelo','—')}",
                f"{panel.get('Pnom_w', 550)} Wp · {panel.get('eficiencia', 0)}% · "
                f"{panel.get('largo_mm', 0)}×{panel.get('ancho_mm', 0)} mm · "
                f"{panel.get('peso_kg', 0)} kg · Tier {panel.get('tier', '—')} · "
                f"Gar. {panel.get('garantia_anios', 25)} años",
                f"{N_pan}",
                f"$ {panel.get('precio_usd', 0):,.0f}".replace(",", "."),
                f"$ {panel.get('precio_usd', 0) * N_pan:,.0f}".replace(",", "."),
            ])

        if inversor:
            bom_rows.append([
                f"Inversor\n{inversor.get('marca','—')} {inversor.get('modelo','—')}",
                f"{inversor.get('P_AC_kw', 0)} kW AC · {'monofásico' if inversor.get('monofasico') else 'trifásico'} · "
                f"{inversor.get('n_mppt', 0)} MPPTs · "
                f"Vmppt {inversor.get('V_mppt_min', 0)}–{inversor.get('V_mppt_max', 0)} V · "
                f"η euro {inversor.get('eficiencia_euro', 0)}% · "
                f"{'BESS compat.' if inversor.get('bess_compatible') else 'sin BESS'} · "
                f"Gar. {inversor.get('garantia_anios', 10)} años",
                "1",
                f"$ {inversor.get('precio_usd', 0):,.0f}".replace(",", "."),
                f"$ {inversor.get('precio_usd', 0):,.0f}".replace(",", "."),
            ])

        if bateria:
            n_bat = max(1, int(round(fv.get("bess_capacidad_kwh", 0) / bateria.get("capacidad_kwh", 5.0))))
            bom_rows.append([
                f"BESS\n{bateria.get('marca','—')} {bateria.get('modelo','—')}",
                f"{bateria.get('capacidad_kwh', 0)} kWh nominal · {bateria.get('quimica', 'LFP')} · "
                f"DoD {bateria.get('profundidad_descarga', 0.9)*100:.0f}% · "
                f"η RT {bateria.get('eficiencia_round_trip', 0.95)*100:.0f}% · "
                f"{bateria.get('ciclos_garantia', 6000)} ciclos · "
                f"{'modular' if bateria.get('modular') else 'monobloque'}",
                f"{n_bat}",
                f"$ {bateria.get('precio_usd', 0):,.0f}".replace(",", "."),
                f"$ {bateria.get('precio_usd', 0) * n_bat:,.0f}".replace(",", "."),
            ])

        # Estimaciones BoS (Balance of System) referenciales
        bos_estructura  = round(P_kwp * 90)    # USD/kWp para estructura aluminio
        bos_cableado    = round(P_kwp * 50)    # cableado DC + AC + conduits
        bos_protecciones= round(P_kwp * 60)    # SPD, fusibles, diferenciales, magnetotérmicos
        bos_pat         = round(P_kwp * 30)    # malla puesta a tierra + telurómetro

        bom_rows.extend([
            ["Estructura de montaje",
             "Aluminio anodizado clase A · clamps end/mid · garantía 20 años · resistencia 140 km/h",
             "1", f"$ {bos_estructura:,.0f}".replace(",", "."), f"$ {bos_estructura:,.0f}".replace(",", ".")],
            ["Cableado DC + AC",
             "Cable solar 4-6 mm² DC (UV resistente) · cable AC NYY-J · conduits y bandejas · conectores MC4",
             "1", f"$ {bos_cableado:,.0f}".replace(",", "."), f"$ {bos_cableado:,.0f}".replace(",", ".")],
            ["Protecciones eléctricas",
             "SPD tipo II DC y AC · fusibles gPV · seccionador DC · magnetotérmico AC · diferencial 30 mA tipo A",
             "1", f"$ {bos_protecciones:,.0f}".replace(",", "."), f"$ {bos_protecciones:,.0f}".replace(",", ".")],
            ["Puesta a tierra",
             "Malla cobre desnudo · barras Cu-acero 19 mm × 2.4 m · conexiones exotérmicas · resistencia ≤ 25 Ω",
             "1", f"$ {bos_pat:,.0f}".replace(",", "."), f"$ {bos_pat:,.0f}".replace(",", ".")],
        ])

        # Calcular total USD
        total_usd = 0
        if panel: total_usd += panel.get('precio_usd', 0) * N_pan
        if inversor: total_usd += inversor.get('precio_usd', 0)
        if bateria:
            n_bat = max(1, int(round(fv.get("bess_capacidad_kwh", 0) / bateria.get("capacidad_kwh", 5.0))))
            total_usd += bateria.get('precio_usd', 0) * n_bat
        total_usd += bos_estructura + bos_cableado + bos_protecciones + bos_pat

        bom_rows.append([
            "TOTAL EQUIPOS + BoS",
            "Sin IVA · sin mano de obra · sin trámites SEC/distribuidora",
            "",
            "",
            f"$ {total_usd:,.0f}".replace(",", "."),
        ])

        # Render tabla
        t = Table(bom_rows, colWidths=[3*cm, 7*cm, 1.3*cm, 2.5*cm, 2.5*cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("FONT", (0,0), (-1,0), "Helvetica-Bold", 8.5),
            ("BACKGROUND", (0,0), (-1,0), ORANGE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONT", (0,1), (-1,-2), "Helvetica", 8),
            ("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 9),
            ("BACKGROUND", (0,-1), (-1,-1), LIGHT),
            ("TEXTCOLOR", (0,-1), (-1,-1), ORANGE_DARK),
            ("ALIGN", (2,0), (-1,-1), "RIGHT"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))

        # Conversión a CLP
        eco = proyecto.get("eco", {})
        tc = eco.get("tipo_cambio", 950) if eco else 950
        total_clp = total_usd * tc
        story.append(Paragraph(
            f"<b>Equivalente en CLP:</b> ≈ ${total_clp:,.0f} CLP (tipo de cambio {tc:.0f} CLP/USD). "
            "Agregar IVA 19% y mano de obra (típicamente 25–35% del costo de equipos) para CAPEX total.".replace(",", "."),
            sty["BODY"]))
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección MÉTRICAS ECONÓMICAS ───
    if eco and inc("metricas_economicas"):
        story.append(Paragraph("Métricas económicas del proyecto", sty["H2X"]))
        met_rows = [
            ["Inversión total (CAPEX)",            _clp(eco.get("capex_total_clp", 0))],
            ["Costo unitario",                     f"USD {eco.get('capex_unitario_usd_kwp', 0):,.0f}/kWp".replace(",", ".")],
            ["Ahorro anual estimado",              _clp(eco.get("ahorro_total_anual_clp", 0))],
            ["Payback simple",                     f"{eco.get('payback_simple_anios', 0):.1f} años"],
            ["Payback descontado",                 f"{eco.get('payback_descontado_anios', 0) or '—'} años" if eco.get('payback_descontado_anios') else "—"],
            ["VAN (Valor Actual Neto)",            _clp(eco.get("VAN_clp", 0))],
            ["TIR (Tasa Interna de Retorno)",      f"{eco.get('TIR_pct', 0) or '—'} %"],
            ["LCOE (costo nivelado energía)",      f"{eco.get('LCOE_clp_kwh', 0):,.0f} CLP/kWh".replace(",", ".")],
            ["Tasa de descuento aplicada",         f"{eco.get('tasa_descuento', 0.08)*100:.1f} %"],
            ["Horizonte de evaluación",            f"{eco.get('horizonte_anios', 25)} años"],
        ]
        t = Table(met_rows, colWidths=[7*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), GRAY),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # ─── Sección CO2 AMBIENTAL ───
    if eco and inc("co2_ambiental"):
        story.append(Paragraph("Impacto ambiental — reducción de emisiones", sty["H2X"]))
        co2_anual = eco.get("CO2_evitado_anual_kg", 0)
        co2_total = eco.get("CO2_evitado_total_kg", 0)
        equiv_arboles = co2_total / 22   # aprox 22 kg CO2/año por árbol promedio
        equiv_autos = co2_anual / 2300   # aprox 2.3 ton CO2/año por auto promedio
        co2_rows = [
            ["Reducción anual de CO₂",          f"{co2_anual/1000:.2f} tCO₂/año"],
            ["Reducción total 25 años",         f"{co2_total/1000:.1f} tCO₂"],
            ["Equivalente — autos retirados",   f"≈ {equiv_autos:.1f} autos/año"],
            ["Equivalente — árboles plantados", f"≈ {equiv_arboles:,.0f} árboles".replace(",", ".")],
            ["Factor de emisión SEN (2024)",    "0.200 tCO₂/MWh"],
        ]
        t = Table(co2_rows, colWidths=[7*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ("FONT", (0,0), (0,-1), "Helvetica-Bold", 9),
            ("FONT", (1,0), (1,-1), "Helvetica", 9),
            ("TEXTCOLOR", (0,0), (0,-1), GRAY),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#E6E2D8")),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

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
