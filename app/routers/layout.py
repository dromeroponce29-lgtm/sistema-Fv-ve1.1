"""Endpoint REST del módulo LAYOUT FV."""
from fastapi import APIRouter, HTTPException
from app.models.layout import LayoutRequest, DisposicionFV
from app.services.layout import calcular_layout

router = APIRouter(prefix="/api/layout", tags=["layout FV"])


@router.post("/calc", response_model=DisposicionFV)
async def calc(req: LayoutRequest) -> DisposicionFV:
    """Calcula la disposición física de los paneles dentro del área disponible,
    considerando tipo de montaje, retiros perimetrales, obstáculos y pitch
    entre filas según latitud."""
    try:
        return calcular_layout(req)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/healthcheck")
async def healthcheck() -> dict:
    return {"status": "ok", "module": "layout"}
