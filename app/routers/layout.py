"""Endpoint REST del módulo LAYOUT FV."""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.models.layout import LayoutRequest, DisposicionFV, AreaDisponible
from app.models.plans import PlanoParseado
from app.services.layout import calcular_layout
from app.services.plan_svg import plano_a_svg

router = APIRouter(prefix="/api/layout", tags=["layout FV"])


class LayoutSobrePlanoRequest(BaseModel):
    """Calcula la disposición de paneles sobre un recinto específico de un plano parseado."""
    plano: PlanoParseado
    recinto_id: int = Field(..., description="ID del recinto del plano que actúa como zona técnica")
    panel_largo_m: float = 2.28
    panel_ancho_m: float = 1.13
    panel_Pnom_w: float = 550
    inclinacion_paneles_deg: float = 30
    latitud_deg: float = -33.4
    orientacion: str = "portrait"
    tipo_montaje: str = "techo_plano"
    retiro_perimetral_m: float = 0.5
    pasillo_cada_n_filas: int = 0
    ancho_pasillo_m: float = 0.8
    max_paneles: int = 0
    obstaculos: list[list[tuple[float, float]]] = []
    mostrar_grid: bool = True
    mostrar_etiquetas: bool = True


class LayoutSobrePlanoResponse(BaseModel):
    disposicion: DisposicionFV
    svg: str
    recinto_nombre: str
    recinto_area_m2: float


@router.post("/calc", response_model=DisposicionFV)
async def calc(req: LayoutRequest) -> DisposicionFV:
    """Calcula la disposición física de los paneles dentro del área disponible,
    considerando tipo de montaje, retiros perimetrales, obstáculos y pitch
    entre filas según latitud."""
    try:
        return calcular_layout(req)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/sobre_plano", response_model=LayoutSobrePlanoResponse)
async def calc_sobre_plano(req: LayoutSobrePlanoRequest) -> LayoutSobrePlanoResponse:
    """Calcula la disposición de paneles sobre un recinto específico del plano
    parseado del usuario y devuelve un SVG con el plano + los paneles overlay.

    Esto permite ver la disposición exactamente sobre la geometría real del
    techo/azotea/terraza que el usuario subió, en lugar de un rectángulo abstracto.
    """
    try:
        # 1. Localizar el recinto target
        recinto = next((r for r in req.plano.recintos if r.id == req.recinto_id), None)
        if recinto is None:
            raise HTTPException(404, f"Recinto id={req.recinto_id} no encontrado en el plano")

        # 2. Construir AreaDisponible a partir del recinto
        area = AreaDisponible(
            nombre=recinto.nombre,
            poligono=list(recinto.vertices),
            obstaculos=req.obstaculos,
            tipo_montaje=req.tipo_montaje,
            retiro_perimetral_m=req.retiro_perimetral_m,
            pasillo_cada_n_filas=req.pasillo_cada_n_filas,
            ancho_pasillo_m=req.ancho_pasillo_m,
        )

        # 3. Calcular packing
        lr = LayoutRequest(
            area=area,
            panel_largo_m=req.panel_largo_m,
            panel_ancho_m=req.panel_ancho_m,
            panel_Pnom_w=req.panel_Pnom_w,
            inclinacion_paneles_deg=req.inclinacion_paneles_deg,
            latitud_deg=req.latitud_deg,
            orientacion=req.orientacion,
            max_paneles=req.max_paneles,
        )
        disp = calcular_layout(lr)

        # 4. Generar SVG del plano completo con la zona destacada y los paneles
        svg = plano_a_svg(
            req.plano,
            zona_tecnica_recinto_id=req.recinto_id,
            paneles=disp.paneles,
            mostrar_grid=req.mostrar_grid,
            mostrar_etiquetas=req.mostrar_etiquetas,
        )

        return LayoutSobrePlanoResponse(
            disposicion=disp,
            svg=svg,
            recinto_nombre=recinto.nombre,
            recinto_area_m2=recinto.area_m2,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error calculando layout sobre plano: {e}")


@router.post("/svg")
async def svg_plano(plano: PlanoParseado, recinto_id: Optional[int] = None) -> dict:
    """Convierte un PlanoParseado a SVG sin calcular layout (útil para previsualizar)."""
    try:
        svg = plano_a_svg(plano, zona_tecnica_recinto_id=recinto_id, paneles=None)
        return {"svg": svg, "n_recintos": plano.n_recintos, "area_total_m2": plano.area_total_m2}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/healthcheck")
async def healthcheck() -> dict:
    return {"status": "ok", "module": "layout"}
