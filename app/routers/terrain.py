"""Endpoints REST del módulo TERRENO."""
from fastapi import APIRouter, HTTPException
from app.models.terrain import TerrainRequest, TerrainAnalysis
from app.services.terrain import analyze_terrain, TerrainOrchestrationError
from app.services.geocoding import GeocodingError
from app.services.pvgis import PvgisError
from app.services.nasa_power import NasaPowerError


router = APIRouter(prefix="/api/terrain", tags=["terreno"])


@router.post("/analyze", response_model=TerrainAnalysis)
async def analyze(req: TerrainRequest) -> TerrainAnalysis:
    """Devuelve el paquete completo de datos del terreno:
    ubicación, altitud, recurso solar (PVGIS) y clima histórico (NASA POWER)."""
    try:
        return await analyze_terrain(req)
    except TerrainOrchestrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeocodingError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (PvgisError, NasaPowerError) as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/healthcheck", tags=["util"])
async def healthcheck() -> dict:
    return {"status": "ok", "module": "terrain"}
