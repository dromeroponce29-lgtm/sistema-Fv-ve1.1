"""Generador de SVG embeddable para visualizar el plano parseado.

Construye un SVG con:
  - Recintos como polígonos cerrados (con uso → color)
  - Etiqueta de cada recinto en su centroide
  - Zona técnica resaltada (si se indica)
  - Paneles FV superpuestos como rectángulos (si se entregan)
  - Grid de referencia métrica opcional

El SVG sale autocontenido y se puede inyectar directo en el HTML del frontend.
Las coordenadas del plano están en metros; el SVG usa un viewBox proporcional.

Convenciones de color por uso (consistentes con el frontend):
  living/comedor → beige claro
  cocina         → naranja claro
  dormitorio     → azul claro
  baño/cocina    → verde menta
  exterior/azotea/terraza → gris claro (típico target FV)
"""
from typing import Optional
from app.models.plans import PlanoParseado, Recinto
from app.models.layout import PanelPosicionado


COLOR_POR_USO = {
    "living":       "#FAF0E1",
    "comedor":      "#FAEFD8",
    "dormitorio":   "#E8EEF5",
    "cocina":       "#FBE3CC",
    "bano":         "#E0F0EA",
    "oficina":      "#F2EAE0",
    "hall":         "#F5F1E8",
    "pasillo":      "#F0ECE3",
    "exterior":     "#EDE9DB",
    "lavanderia":   "#E8EFE5",
    "logia":        "#E6E8DD",
    "bodega":       "#EAE6D9",
    "circulacion":  "#F0ECE3",
    "comun":        "#EFEBE0",
    "desconocido":  "#F5F2E8",
}

COLOR_BORDE = "#6B5340"
COLOR_TEXTO = "#4A3826"
COLOR_TEXTO_GRANDE = "#1F1D18"
COLOR_ZONA_TECNICA = "#E89923"   # naranja FV
COLOR_PANEL_FILL = "#1E4A7A"     # azul oscuro
COLOR_PANEL_BORDE = "#0F3158"


def _bbox_recintos(recintos: list[Recinto]) -> tuple[float, float, float, float]:
    """Devuelve (minx, miny, maxx, maxy) en metros que envuelve todos los recintos."""
    if not recintos:
        return 0, 0, 10, 10
    xs = [v[0] for r in recintos for v in r.vertices]
    ys = [v[1] for r in recintos for v in r.vertices]
    return min(xs), min(ys), max(xs), max(ys)


def _poligono_path(vertices: list[tuple[float, float]], y_flip: float) -> str:
    """Convierte vértices a un atributo `points` SVG, invirtiendo Y (CAD → pantalla)."""
    return " ".join(f"{x:.3f},{(y_flip - y):.3f}" for x, y in vertices)


def plano_a_svg(
    plano: PlanoParseado,
    zona_tecnica_recinto_id: Optional[int] = None,
    paneles: Optional[list[PanelPosicionado]] = None,
    ancho_max_px: int = 900,
    mostrar_grid: bool = True,
    mostrar_areas: bool = True,
    mostrar_etiquetas: bool = True,
) -> str:
    """Genera un string SVG con el plano + (opcional) recinto destacado + (opcional) paneles.

    Args:
        plano:        Plano parseado del módulo PLANOS.
        zona_tecnica_recinto_id: id del recinto marcado como "zona disponible para paneles".
        paneles:      Lista de PanelPosicionado del módulo LAYOUT (en coordenadas globales
                      del plano, mismo sistema que los recintos). Si están en coordenadas
                      relativas al recinto, hay que trasladarlas antes de pasarlas aquí.
        ancho_max_px: Ancho máximo del SVG en px (la altura se calcula para preservar aspecto).
        mostrar_grid: Dibuja una grilla de 1 m.
        mostrar_areas: Muestra el área del recinto en su centroide.
        mostrar_etiquetas: Muestra el nombre del recinto en su centroide.
    """
    if not plano.recintos:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><text x="50" y="25" text-anchor="middle" fill="#888">Sin recintos</text></svg>'

    minx, miny, maxx, maxy = _bbox_recintos(plano.recintos)
    pad = 0.5  # padding 50 cm
    minx -= pad; miny -= pad; maxx += pad; maxy += pad
    ancho_m = maxx - minx
    alto_m  = maxy - miny

    # SVG en escala 1:1 con metros (1 m = 1 unidad SVG). Mediante viewBox encajamos.
    # Y invertido: en CAD Y aumenta hacia arriba, en SVG hacia abajo.
    y_flip = miny + maxy

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{minx:.3f} {miny:.3f} {ancho_m:.3f} {alto_m:.3f}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="background:#fdfbf5; max-width:100%; height:auto; border:1px solid #d8d2c0; border-radius:6px;">'
    )

    # === Definiciones reutilizables ===
    parts.append(
        '<defs>'
        '<pattern id="grid-1m" width="1" height="1" patternUnits="userSpaceOnUse">'
        f'<path d="M 1 0 L 0 0 0 1" fill="none" stroke="#e8e2d0" stroke-width="0.015"/>'
        '</pattern>'
        '<pattern id="zona-hatch" patternUnits="userSpaceOnUse" width="0.4" height="0.4" '
        f'patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="0.4" stroke="{COLOR_ZONA_TECNICA}" stroke-width="0.06" opacity="0.35"/>'
        '</pattern>'
        '</defs>'
    )

    # === Grid de fondo ===
    if mostrar_grid:
        parts.append(
            f'<rect x="{minx:.3f}" y="{miny:.3f}" width="{ancho_m:.3f}" height="{alto_m:.3f}" fill="url(#grid-1m)"/>'
        )

    # === Recintos ===
    for r in plano.recintos:
        color = COLOR_POR_USO.get(r.uso, COLOR_POR_USO["desconocido"])
        es_zona = (zona_tecnica_recinto_id == r.id)
        stroke_w = 0.05 if not es_zona else 0.12
        stroke_color = COLOR_ZONA_TECNICA if es_zona else COLOR_BORDE
        pts = _poligono_path(r.vertices, y_flip)
        parts.append(
            f'<polygon points="{pts}" fill="{color}" stroke="{stroke_color}" '
            f'stroke-width="{stroke_w}" stroke-linejoin="round" data-recinto-id="{r.id}" '
            f'data-recinto-uso="{r.uso}" data-recinto-nombre="{r.nombre}">'
            f'<title>{r.nombre} · {r.uso} · {r.area_m2:.1f} m²</title></polygon>'
        )
        # Patrón "zona técnica" superpuesto
        if es_zona:
            parts.append(
                f'<polygon points="{pts}" fill="url(#zona-hatch)" stroke="none"/>'
            )

    # === Etiquetas de recintos ===
    if mostrar_etiquetas:
        for r in plano.recintos:
            cx, cy = r.centroide
            cy_svg = y_flip - cy
            font_size = max(0.20, min(0.45, (r.area_m2 ** 0.5) * 0.08))
            parts.append(
                f'<text x="{cx:.3f}" y="{cy_svg:.3f}" text-anchor="middle" '
                f'font-family="Helvetica,Arial,sans-serif" font-size="{font_size:.3f}" '
                f'fill="{COLOR_TEXTO_GRANDE}" font-weight="600">{r.nombre}</text>'
            )
            if mostrar_areas:
                parts.append(
                    f'<text x="{cx:.3f}" y="{(cy_svg + font_size*1.1):.3f}" text-anchor="middle" '
                    f'font-family="Helvetica,Arial,sans-serif" font-size="{(font_size*0.7):.3f}" '
                    f'fill="{COLOR_TEXTO}">{r.area_m2:.1f} m²</text>'
                )

    # === Paneles FV (overlay) ===
    if paneles:
        for p in paneles:
            # x,y en CAD (esquina inferior-izquierda); convertir a SVG (esquina superior-izq)
            x_svg = p.x
            y_svg = y_flip - p.y - p.ancho_m
            parts.append(
                f'<rect x="{x_svg:.3f}" y="{y_svg:.3f}" '
                f'width="{p.largo_m:.3f}" height="{p.ancho_m:.3f}" '
                f'fill="{COLOR_PANEL_FILL}" stroke="{COLOR_PANEL_BORDE}" stroke-width="0.025" '
                f'opacity="0.88" data-panel-id="{p.id}">'
                f'<title>Panel #{p.id} · fila {p.fila} col {p.columna}</title></rect>'
            )
            # Línea diagonal para indicar inclinación (estética)
            parts.append(
                f'<line x1="{x_svg:.3f}" y1="{y_svg:.3f}" '
                f'x2="{(x_svg + p.largo_m):.3f}" y2="{(y_svg + p.ancho_m):.3f}" '
                f'stroke="{COLOR_PANEL_BORDE}" stroke-width="0.015" opacity="0.5"/>'
            )

    # === Escala (regla de 1 m) ===
    rx = minx + 0.3; ry = maxy - 0.5
    parts.append(
        f'<g font-family="Helvetica,Arial,sans-serif">'
        f'<line x1="{rx:.3f}" y1="{(y_flip - ry):.3f}" x2="{(rx + 1):.3f}" y2="{(y_flip - ry):.3f}" '
        f'stroke="{COLOR_TEXTO_GRANDE}" stroke-width="0.05"/>'
        f'<line x1="{rx:.3f}" y1="{(y_flip - ry - 0.1):.3f}" x2="{rx:.3f}" y2="{(y_flip - ry + 0.1):.3f}" '
        f'stroke="{COLOR_TEXTO_GRANDE}" stroke-width="0.05"/>'
        f'<line x1="{(rx + 1):.3f}" y1="{(y_flip - ry - 0.1):.3f}" x2="{(rx + 1):.3f}" y2="{(y_flip - ry + 0.1):.3f}" '
        f'stroke="{COLOR_TEXTO_GRANDE}" stroke-width="0.05"/>'
        f'<text x="{(rx + 0.5):.3f}" y="{(y_flip - ry - 0.18):.3f}" text-anchor="middle" '
        f'font-size="0.22" fill="{COLOR_TEXTO_GRANDE}">1 m</text>'
        f'</g>'
    )

    parts.append('</svg>')
    return "".join(parts)


def trasladar_paneles_a_global(
    paneles: list[PanelPosicionado],
    offset_x: float,
    offset_y: float,
) -> list[PanelPosicionado]:
    """Si los paneles fueron calculados sobre un polígono trasladado al origen,
    los devuelve en coordenadas globales del plano."""
    return [
        PanelPosicionado(
            id=p.id, x=p.x + offset_x, y=p.y + offset_y,
            largo_m=p.largo_m, ancho_m=p.ancho_m,
            orientacion=p.orientacion, fila=p.fila, columna=p.columna,
        )
        for p in paneles
    ]
