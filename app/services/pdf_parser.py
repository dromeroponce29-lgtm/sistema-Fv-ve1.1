"""Parser de planos en formato PDF.

Soporta dos modos:
  • PDF vectorial: planos exportados desde CAD (AutoCAD/Revit/SketchUp/QCAD).
    Las paredes y polilíneas vienen como líneas y rectángulos vectoriales que
    se reconstruyen con pdfplumber.
  • PDF escaneado / imagen: requiere OCR (ocrmypdf) + vectorización (OpenCV)
    + intervención manual del usuario para marcar las habitaciones (se delega
    al frontend en una etapa de revisión interactiva).

La calidad del parsing decrece en el orden:
    DXF nativo  >  PDF vectorial CAD  >  PDF escaneado

Si la calidad cae por debajo de un umbral, el sistema emite advertencia y
sugiere reingresar las habitaciones manualmente por formulario."""
from pathlib import Path
from typing import List, Tuple

from shapely.geometry import Polygon, Point

from app.models.plans import PlanoParseado, Recinto
from app.services.usos_recinto import inferir_uso


class PdfParserError(Exception):
    pass


# Conversión: PDF usa puntos (1 pt = 1/72 in = 0.3528 mm)
PT_A_METROS = 0.0254 / 72


def _esta_escaneado(pdf_path: Path) -> bool:
    """Heurística rápida: un PDF escaneado tiene casi puro contenido raster
    y muy pocos elementos vectoriales (líneas, paths)."""
    import pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pagina = pdf.pages[0]
            n_lineas = len(pagina.lines)
            n_rects = len(pagina.rects)
            n_curves = len(pagina.curves)
            n_imgs = len(pagina.images)
            vector_elements = n_lineas + n_rects + n_curves
            # Si tiene 1+ imagen grande y <10 vectoriales → casi seguro escaneado
            return vector_elements < 10 and n_imgs >= 1
    except Exception:
        return True  # ante duda, asumir lo peor


def parse_pdf_vectorial(
    ruta: Path | str,
    escala_pdf_a_metros: float | None = None,
) -> PlanoParseado:
    """Parsea un PDF vectorial (no escaneado).

    Args:
        ruta: archivo PDF.
        escala_pdf_a_metros: factor para convertir puntos PDF a metros.
            Si el plano se exportó a escala 1:50, el usuario lo informa
            (en CL los planos arquitectónicos suelen ser 1:50 o 1:100).
            Si None, se usa una heurística con el rectángulo más grande
            (cajetín del plano) o se asume 1:100.
    """
    import pdfplumber
    ruta = Path(ruta)
    if not ruta.exists():
        raise PdfParserError(f"Archivo no encontrado: {ruta}")

    advertencias: list[str] = []

    if _esta_escaneado(ruta):
        raise PdfParserError(
            "El PDF parece estar escaneado (sin elementos vectoriales). "
            "Usa el módulo de PDF escaneado (OCR + vectorización + marcado manual)."
        )

    with pdfplumber.open(ruta) as pdf:
        pagina = pdf.pages[0]  # plano arquitectónico típicamente en 1 página

        # Extraer rectángulos (cada habitación rectangular es un rect en el PDF)
        rects = pagina.rects
        if not rects:
            raise PdfParserError(
                "No se detectaron rectángulos vectoriales en el PDF. "
                "Verifica que el plano tenga las habitaciones dibujadas como "
                "rectángulos cerrados, no como segmentos sueltos."
            )

        # Determinar factor de escala
        if escala_pdf_a_metros is None:
            # Heurística: asumir escala 1:100 (1 pt = 1/72 in real → 100/72 in mundo)
            # 1:100 → factor = 100 * 0.0254 / 72 = 0.0353 m/pt
            escala_pdf_a_metros = 100 * PT_A_METROS
            advertencias.append(
                "Escala no informada; asumiendo 1:100. Ajustar parámetro "
                "'escala_pdf_a_metros' si los m² resultantes no coinciden con "
                "la cubicación esperada del plano."
            )

        # Extraer textos para nombrar recintos
        textos = []
        for w in pagina.extract_words():
            x = (w["x0"] + w["x1"]) / 2
            # En PDF Y crece hacia abajo; invertimos para coherencia con CAD
            y = pagina.height - (w["top"] + w["bottom"]) / 2
            textos.append((w["text"], (x * escala_pdf_a_metros, y * escala_pdf_a_metros)))

        # Construir recintos a partir de rectángulos
        recintos: List[Recinto] = []
        for idx, r in enumerate(rects, start=1):
            x0 = r["x0"] * escala_pdf_a_metros
            x1 = r["x1"] * escala_pdf_a_metros
            y0 = (pagina.height - r["bottom"]) * escala_pdf_a_metros
            y1 = (pagina.height - r["top"]) * escala_pdf_a_metros
            vertices = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            try:
                poly = Polygon(vertices)
            except Exception:
                continue
            if poly.area < 0.5:
                continue

            # Buscar texto dentro del polígono
            texto_interno = None
            for (texto, (tx, ty)) in textos:
                if poly.contains(Point(tx, ty)):
                    texto_interno = texto
                    break
            if texto_interno:
                nombre = texto_interno
                fuente = "texto_dentro"
                uso = inferir_uso(texto_interno)
            else:
                nombre = f"Recinto {idx}"
                fuente = "fallback"
                uso = "desconocido"

            if uso == "desconocido":
                advertencias.append(
                    f"Recinto #{idx}: uso no reconocido — requiere asignación manual"
                )

            cx, cy = poly.centroid.x, poly.centroid.y
            recintos.append(Recinto(
                id=idx,
                nombre=nombre,
                uso=uso,
                area_m2=round(poly.area, 2),
                perimetro_m=round(poly.length, 2),
                centroide=(round(cx, 2), round(cy, 2)),
                vertices=[(round(x, 3), round(y, 3)) for x, y in vertices],
                layer_origen=None,
                fuente_nombre=fuente,
            ))

    if not recintos:
        raise PdfParserError("No se pudieron reconstruir recintos válidos desde el PDF.")

    area_total = round(sum(r.area_m2 for r in recintos), 2)
    return PlanoParseado(
        archivo=ruta.name,
        formato="pdf_vectorial",
        unidad_origen="pt (1/72 in)",
        factor_a_metros=escala_pdf_a_metros,
        recintos=recintos,
        area_total_m2=area_total,
        n_recintos=len(recintos),
        advertencias=advertencias,
        metadatos={"n_rects_originales": len(rects), "escala_asumida_pdf_a_m": escala_pdf_a_metros},
    )


def parse_pdf_escaneado(ruta: Path | str) -> PlanoParseado:
    """Stub: PDF escaneado requiere pipeline OCR + vectorización + marcado manual.

    El flujo correcto en producción:
       1. ocrmypdf para OCR del texto (etiquetas de recinto).
       2. OpenCV para detectar líneas y contornos (paredes).
       3. UI del frontend muestra la imagen y el usuario marca cada recinto
          como polígono, asignándole nombre y uso.
       4. La herramienta calcula áreas con shapely.

    Esto NO se puede hacer 100% automático; siempre requiere supervisión.
    Por ahora retorna excepción guiando al usuario."""
    raise PdfParserError(
        "PDF escaneado detectado. Esta versión del parser requiere intervención "
        "manual. Próximamente: vista interactiva del frontend para marcar "
        "recintos sobre la imagen escaneada."
    )
