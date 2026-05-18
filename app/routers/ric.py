"""Endpoint REST del módulo CARGAS RIC."""
from fastapi import APIRouter, HTTPException
from app.models.ric import RicRequest, RicResult
from app.services.ric_loads import calcular_carga_ric

router = APIRouter(prefix="/api/ric", tags=["cargas RIC"])


@router.post("/calc", response_model=RicResult)
async def calcular(req: RicRequest) -> RicResult:
    """Calcula carga total instalada, demanda diversificada, demanda máxima
    y consumo estimado a partir de una lista de recintos."""
    try:
        return calcular_carga_ric(req)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/healthcheck", tags=["util"])
async def healthcheck() -> dict:
    from app.services.ric_tables import CARGAS_POR_USO, CARGAS_DEDICADAS_VIVIENDA
    return {
        "status": "ok", "module": "ric",
        "usos_tabulados": len(CARGAS_POR_USO),
        "cargas_dedicadas": len(CARGAS_DEDICADAS_VIVIENDA),
    }
