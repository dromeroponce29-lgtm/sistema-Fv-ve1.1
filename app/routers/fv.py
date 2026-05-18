"""Endpoint REST del módulo DIMENSIONAMIENTO FV + ECONÓMICO."""
from fastapi import APIRouter, HTTPException
from app.models.fv import FvRequest, FvFullResult
from app.services.pv_sizing import calcular_fv
from app.services.economic import calcular_economico


router = APIRouter(prefix="/api/fv", tags=["dimensionamiento FV"])


@router.post("/design", response_model=FvFullResult)
async def design(req: FvRequest) -> FvFullResult:
    """Dimensiona el sistema FV y calcula análisis económico 25 años."""
    try:
        fv = calcular_fv(req)
        eco = calcular_economico(
            fv,
            tarifa_clp_kwh=req.tarifa_clp_kwh,
            tipo_proyecto=req.tipo_proyecto,
        )
        return FvFullResult(fv=fv, economic=eco)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/healthcheck", tags=["util"])
async def healthcheck() -> dict:
    return {"status": "ok", "module": "fv"}
