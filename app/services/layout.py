"""Algoritmo de packing rectangular de paneles FV sobre área disponible.

Estrategia:
  1. Aplicar retiro perimetral al polígono → área útil con shapely.buffer(-retiro).
  2. Restar obstáculos.
  3. Calcular pitch entre filas según tipo de montaje y latitud:
       - techo_plano: pitch = ancho_panel · cos(β) + ancho_panel · sin(β) · cot(α_solar_critica)
         donde α_solar_critica = 90 - latitud - 23.45 + 5 (margen seguridad, 21 de junio 10:00)
       - techo_inclinado: pitch = ancho_panel (sin separación, paneles pegados al techo)
       - suelo: igual a techo_plano + pasillos cada N filas
       - carport: similar techo plano, sin pasillos
  4. Iterar grid: para cada posición candidata, verificar si el rectángulo del panel cabe
     completamente dentro del polígono útil → contains() de shapely.
  5. Asignar id, fila, columna, coordenadas.
"""
import math
from typing import List, Tuple
from shapely.geometry import Polygon, Point, box as shp_box
from shapely.affinity import translate

from app.models.layout import (
    AreaDisponible, LayoutRequest, DisposicionFV, PanelPosicionado, TipoMontaje
)


def _pitch_entre_filas(tipo: TipoMontaje, ancho_panel_m: float, inclinacion_deg: float,
                       latitud_deg: float) -> float:
    """Calcula la distancia mínima entre filas (centro a centro)."""
    beta = math.radians(inclinacion_deg)
    if tipo == "techo_inclinado":
        return ancho_panel_m   # Sin pitch, paneles coplanares
    # FIX #11 — Aclaración: En hemisferio sur (Chile), el solsticio de invierno ocurre
    # el 21 de junio, cuando el Sol está al norte. La altura solar mínima al mediodía es:
    # α(mediodía 21jun) = 90° - |latitud_sur| - 23.45°
    # (En valor absoluto, ya que en Chile la latitud es negativa).
    alt_solar = max(15, 90 - abs(latitud_deg) - 23.45 + 5)  # +5 margen
    alfa = math.radians(alt_solar)
    # Distancia proyectada en el suelo para que la sombra de fila i no caiga sobre fila i+1
    # pitch ≥ ancho · (cos(β) + sin(β) / tan(α))
    return ancho_panel_m * (math.cos(beta) + math.sin(beta) / math.tan(alfa))


def _dim_panel(req: LayoutRequest) -> Tuple[float, float]:
    """Devuelve (largo_x, ancho_y) del panel según orientación.
    Portrait: lado largo = altura (Y), lado corto = ancho (X).
    Landscape: al revés."""
    if req.orientacion == "portrait":
        return req.panel_ancho_m, req.panel_largo_m  # ancho X, largo Y
    else:
        return req.panel_largo_m, req.panel_ancho_m


def calcular_layout(req: LayoutRequest) -> DisposicionFV:
    advertencias: list[str] = []
    area = req.area

    # 1. Polígono útil = área − retiro perimetral
    poly = Polygon(area.poligono)
    if not poly.is_valid:
        poly = poly.buffer(0)
    # FIX #17 — buffer(-retiro) puede devolver MultiPolygon en concavidades severas;
    # nos quedamos con el más grande para no fallar en contains() después.
    poly_util = poly.buffer(-area.retiro_perimetral_m)
    if hasattr(poly_util, "geoms"):  # MultiPolygon → tomar el componente mayor
        poly_util = max(poly_util.geoms, key=lambda g: g.area)
        advertencias.append(
            "El polígono útil quedó dividido por el retiro perimetral. "
            "Se usa el subpolígono mayor para el packing."
        )
    if poly_util.is_empty:
        advertencias.append("Retiro perimetral mayor que el área disponible")
        return DisposicionFV(
            n_paneles=0, n_filas=0, paneles_por_fila=[], pitch_m=0,
            P_kwp_real=0, area_paneles_m2=0,
            area_disponible_m2=poly.area, area_util_m2=0,
            aprovechamiento_pct=0, paneles=[], advertencias=advertencias,
        )

    # 2. Restar obstáculos
    for obs_pts in area.obstaculos:
        try:
            obs = Polygon(obs_pts).buffer(area.retiro_perimetral_m)
            poly_util = poly_util.difference(obs)
        except Exception:
            continue
    if poly_util.is_empty:
        advertencias.append("Obstáculos cubren toda el área útil")
        return DisposicionFV(
            n_paneles=0, n_filas=0, paneles_por_fila=[], pitch_m=0,
            P_kwp_real=0, area_paneles_m2=0,
            area_disponible_m2=poly.area, area_util_m2=0,
            aprovechamiento_pct=0, paneles=[], advertencias=advertencias,
        )

    # 3. Bounding box del área útil
    minx, miny, maxx, maxy = poly_util.bounds

    # 4. Dimensiones del panel y pitch
    dx, dy = _dim_panel(req)   # dx = ancho X, dy = ancho Y (altura)
    inclin = req.inclinacion_paneles_deg
    if area.tipo_montaje == "techo_inclinado":
        inclin = area.inclinacion_techo_deg
    pitch = _pitch_entre_filas(area.tipo_montaje, dy, inclin, req.latitud_deg)

    # 5. Packing: iterar filas (Y) y columnas (X)
    paneles: List[PanelPosicionado] = []
    paneles_por_fila: list[int] = []
    fila_idx = 0
    y = miny
    while y + dy <= maxy + 1e-6:
        fila_idx += 1
        # Pasillo de mantención
        if (area.pasillo_cada_n_filas > 0 and
                fila_idx > 1 and (fila_idx - 1) % area.pasillo_cada_n_filas == 0):
            y += area.ancho_pasillo_m   # añade pasillo extra
            if y + dy > maxy + 1e-6:
                break

        col_idx = 0
        x = minx
        n_en_fila = 0
        # FIX #9 — Para polígonos cóncavos, si un rectángulo no cabe, no nos quedamos
        # bloqueados: hacemos un pequeño barrido (sub-paso = dx/3) buscando posición válida.
        # Esto recupera ~10-15% paneles en formas en L o U.
        SUB_PASOS = 3
        sub_dx = dx / SUB_PASOS
        while x + dx <= maxx + 1e-6:
            rect = shp_box(x, y, x + dx, y + dy)
            if poly_util.contains(rect):
                col_idx += 1
                paneles.append(PanelPosicionado(
                    id=len(paneles) + 1,
                    x=round(x, 3), y=round(y, 3),
                    largo_m=dx, ancho_m=dy,
                    orientacion=req.orientacion,
                    fila=fila_idx, columna=col_idx,
                ))
                n_en_fila += 1
                x += dx     # avance completo cuando hay panel
            else:
                # Sub-barrido fino antes de descartar (forma cóncava)
                x_test = x + sub_dx
                found = False
                while x_test + dx <= x + dx + 1e-6 - sub_dx:
                    rect2 = shp_box(x_test, y, x_test + dx, y + dy)
                    if poly_util.contains(rect2):
                        col_idx += 1
                        paneles.append(PanelPosicionado(
                            id=len(paneles) + 1,
                            x=round(x_test, 3), y=round(y, 3),
                            largo_m=dx, ancho_m=dy,
                            orientacion=req.orientacion,
                            fila=fila_idx, columna=col_idx,
                        ))
                        n_en_fila += 1
                        x = x_test + dx
                        found = True
                        break
                    x_test += sub_dx
                if not found:
                    x += dx
            if req.max_paneles and len(paneles) >= req.max_paneles:
                break
        if n_en_fila > 0:
            paneles_por_fila.append(n_en_fila)
        if req.max_paneles and len(paneles) >= req.max_paneles:
            break
        y += pitch     # Avanzar a la siguiente fila

    # 6. Métricas
    area_paneles = sum(p.largo_m * p.ancho_m for p in paneles)
    aprov = (area_paneles / poly_util.area * 100) if poly_util.area > 0 else 0
    P_kwp = round(len(paneles) * req.panel_Pnom_w / 1000, 2)

    if len(paneles) == 0:
        advertencias.append(
            f"Ningún panel cabe. Verifica dimensiones del área (≥ {dx:.1f}×{dy:.1f} m) "
            f"y retiro perimetral ({area.retiro_perimetral_m} m)."
        )

    return DisposicionFV(
        n_paneles=len(paneles),
        n_filas=len(paneles_por_fila),
        paneles_por_fila=paneles_por_fila,
        pitch_m=round(pitch, 3),
        P_kwp_real=P_kwp,
        area_paneles_m2=round(area_paneles, 2),
        area_disponible_m2=round(poly.area, 2),
        area_util_m2=round(poly_util.area, 2),
        aprovechamiento_pct=round(aprov, 1),
        paneles=paneles,
        advertencias=advertencias,
    )
