"""Parser de planos DXF usando ezdxf + shapely.

Estrategia:
  1. Abrir el archivo (modo recover para tolerancia a DXFs imperfectos).
  2. Identificar polilíneas cerradas (LWPOLYLINE, POLYLINE) y rectángulos
     compuestos por 4 LINE conectadas → cada uno representa un recinto.
  3. Para cada recinto, calcular área y perímetro con shapely.
  4. Inferir el nombre/uso desde:
       a) layer en que está dibujado (preferente),
       b) texto contenido dentro del polígono (TEXT/MTEXT),
       c) fallback al índice numérico.
  5. Convertir todas las unidades a metros (DXF guarda mm, cm, in, ft, ...).
"""
from pathlib import Path
from typing import List, Tuple

import ezdxf
from ezdxf import recover
from shapely.geometry import Polygon, Point

from app.models.plans import PlanoParseado, Recinto
from app.services.usos_recinto import inferir_uso


class DxfParserError(Exception):
    pass


# Tabla $INSUNITS de DXF → factor para convertir a metros
INSUNITS_A_METROS = {
    0: 1.0,        # unidades sin asignar → asumimos metros
    1: 0.0254,     # pulgadas
    2: 0.3048,     # pies
    3: 1609.344,   # millas
    4: 0.001,      # milímetros (estándar arquitectónico CL)
    5: 0.01,       # centímetros
    6: 1.0,        # metros
    7: 1000.0,     # kilómetros
}


def _abrir_dxf(ruta: Path) -> tuple[ezdxf.document.Drawing, list[str]]:
    """Abre intentando primero modo estándar, luego recover."""
    advertencias: list[str] = []
    try:
        doc = ezdxf.readfile(str(ruta))
        return doc, advertencias
    except (ezdxf.DXFStructureError, ezdxf.DXFError) as e:
        advertencias.append(f"DXF mal formado, usando modo recovery: {e}")
        try:
            doc, auditor = recover.readfile(str(ruta))
            if auditor.fixes:
                advertencias.append(f"Auditor aplicó {len(auditor.fixes)} correcciones")
            return doc, advertencias
        except Exception as e2:
            raise DxfParserError(f"No se pudo leer el DXF ni en modo recovery: {e2}")


def _extraer_polilineas_cerradas(modelspace) -> List[tuple[str, List[Tuple[float, float]]]]:
    """Devuelve lista de (layer, vertices) para cada polilínea cerrada."""
    out = []
    # LWPOLYLINE (polilínea liviana, formato moderno)
    for p in modelspace.query("LWPOLYLINE"):
        pts = [(pt[0], pt[1]) for pt in p.get_points("xy")]
        if len(pts) >= 3:
            # Cerrar si el flag dice cerrado o si visualmente cierra
            if p.closed or (pts[0] != pts[-1] and len(pts) >= 3):
                out.append((p.dxf.layer, pts))
    # POLYLINE clásica
    for p in modelspace.query("POLYLINE"):
        if p.is_2d_polyline and p.is_closed:
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in p.vertices]
            if len(pts) >= 3:
                out.append((p.dxf.layer, pts))
    return out


def _textos_en_modelspace(modelspace) -> List[tuple[str, Tuple[float, float], str]]:
    """Devuelve (texto, posición, layer) para TEXT y MTEXT."""
    out = []
    for t in modelspace.query("TEXT"):
        pos = t.dxf.insert
        out.append((t.dxf.text, (pos.x, pos.y), t.dxf.layer))
    for t in modelspace.query("MTEXT"):
        pos = t.dxf.insert
        out.append((t.text, (pos.x, pos.y), t.dxf.layer))
    return out


def _texto_dentro(poligono: Polygon, textos) -> str | None:
    """Busca un texto cuya posición caiga dentro del polígono."""
    for texto, (x, y), _layer in textos:
        if poligono.contains(Point(x, y)) or poligono.touches(Point(x, y)):
            return texto.strip()
    return None


def parse_dxf(ruta: Path | str) -> PlanoParseado:
    """Parsea un archivo DXF y retorna su estructura semántica."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise DxfParserError(f"Archivo no encontrado: {ruta}")

    doc, advertencias = _abrir_dxf(ruta)
    ms = doc.modelspace()

    # Determinar unidad y factor a metros
    insunits = int(doc.header.get("$INSUNITS", 0))
    factor = INSUNITS_A_METROS.get(insunits, 1.0)
    unidad_str = {1: "in", 2: "ft", 4: "mm", 5: "cm", 6: "m"}.get(insunits, "desconocida")
    if insunits == 0:
        advertencias.append(
            "DXF sin $INSUNITS declarado; asumiendo metros. "
            "Verificar visualmente antes de usar las áreas."
        )

    # Extraer polilíneas cerradas y textos
    poligonos_crudos = _extraer_polilineas_cerradas(ms)
    textos = _textos_en_modelspace(ms)

    if not poligonos_crudos:
        raise DxfParserError(
            "No se encontraron polilíneas cerradas en el plano. "
            "Verifica que las habitaciones estén dibujadas como polilíneas "
            "cerradas y no como segmentos sueltos."
        )

    # Convertir a metros y construir Recintos
    recintos: List[Recinto] = []
    for idx, (layer, pts) in enumerate(poligonos_crudos, start=1):
        pts_m = [(x * factor, y * factor) for x, y in pts]
        try:
            poly = Polygon(pts_m)
            if not poly.is_valid:
                poly = poly.buffer(0)  # repara auto-intersecciones leves
        except Exception as e:
            advertencias.append(f"Polígono #{idx} en layer '{layer}' inválido: {e}")
            continue
        if poly.area < 0.5:  # < 0.5 m² → probablemente no es un recinto real
            advertencias.append(
                f"Polígono en layer '{layer}' descartado: área {poly.area:.2f} m² < 0,5 m²"
            )
            continue

        # Determinar nombre y uso
        # Prioridad 1: texto que esté dentro del polígono
        texto_interno = _texto_dentro(poly, [(t, (x*factor, y*factor), l) for t,(x,y),l in textos])
        if texto_interno:
            nombre = texto_interno
            fuente = "texto_dentro"
            uso = inferir_uso(texto_interno) or inferir_uso(layer)
        else:
            # Prioridad 2: nombre del layer
            nombre = layer
            fuente = "layer"
            uso = inferir_uso(layer)

        if uso == "desconocido":
            advertencias.append(
                f"Recinto '{nombre}' (layer '{layer}'): uso no reconocido — "
                f"requiere asignación manual para el módulo CARGAS RIC"
            )

        cx, cy = poly.centroid.x, poly.centroid.y
        recintos.append(Recinto(
            id=idx,
            nombre=nombre,
            uso=uso,
            area_m2=round(poly.area, 2),
            perimetro_m=round(poly.length, 2),
            centroide=(round(cx, 2), round(cy, 2)),
            vertices=[(round(x, 3), round(y, 3)) for x, y in pts_m],
            layer_origen=layer,
            fuente_nombre=fuente,
        ))

    area_total = round(sum(r.area_m2 for r in recintos), 2)

    return PlanoParseado(
        archivo=ruta.name,
        formato="dxf",
        unidad_origen=unidad_str,
        factor_a_metros=factor,
        recintos=recintos,
        area_total_m2=area_total,
        n_recintos=len(recintos),
        advertencias=advertencias,
        metadatos={
            "dxf_version": doc.dxfversion,
            "n_layers": len(list(doc.layers)),
            "insunits_codigo": insunits,
        },
    )
