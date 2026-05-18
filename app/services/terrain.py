"""Orquestador del módulo TERRENO.

Coordina geocoding + elevación + PVGIS + NASA POWER y devuelve
un paquete unificado listo para el motor FV.
Las llamadas externas se ejecutan en paralelo donde es posible."""
import asyncio
from typing import Optional
from app.models.terrain import (
    GeoLocation,
    TerrainAnalysis,
    TerrainRequest,
)
from app.services import geocoding, elevation, pvgis, nasa_power


class TerrainOrchestrationError(Exception):
    pass


async def analyze_terrain(req: TerrainRequest) -> TerrainAnalysis:
    notes: list[str] = []

    # 1. Resolver coordenadas (geocoding o pasadas directas)
    if req.latitude is not None and req.longitude is not None:
        loc = await geocoding.reverse_geocode(req.latitude, req.longitude)
        if loc is None:
            loc = GeoLocation(latitude=req.latitude, longitude=req.longitude)
            notes.append("reverse_geocode falló — se usan coordenadas crudas")
    elif req.address:
        loc = await geocoding.geocode_address(req.address)
    else:
        raise TerrainOrchestrationError(
            "Debe proveer 'address' o 'latitude'+'longitude'"
        )

    # 2. En paralelo: elevación, PVGIS y NASA POWER
    elev_task = asyncio.create_task(
        elevation.get_elevation(loc.latitude, loc.longitude)
    )
    pvgis_task = asyncio.create_task(
        pvgis.get_pv_calculation(
            latitude=loc.latitude,
            longitude=loc.longitude,
            peakpower_kw=req.peakpower_kw,
            system_loss_pct=req.system_loss_pct,
            pv_tech=req.pv_tech,
            mounting=req.mounting,
            optimal_angles=True,
        )
    )
    nasa_task = asyncio.create_task(
        nasa_power.get_monthly_climate(loc.latitude, loc.longitude)
    )

    elev_val, pvgis_val, nasa_val = await asyncio.gather(
        elev_task, pvgis_task, nasa_task, return_exceptions=False
    )

    if elev_val is None:
        notes.append("Open-Elevation no respondió — altitud no disponible")

    # 3. Sanity check de azimut según hemisferio
    from app.config import get_settings
    expected_az = get_settings().optimal_azimuth
    az_diff = abs(abs(pvgis_val.optimal_azimuth_deg) - expected_az)
    if az_diff > 30 and pvgis_val.optimal_azimuth_deg != 0:
        notes.append(
            f"Azimut óptimo {pvgis_val.optimal_azimuth_deg}° no coincide con "
            f"hemisferio configurado ({expected_az}°) — revise ubicación"
        )

    return TerrainAnalysis(
        location=loc,
        elevation_masl=elev_val,
        pvgis=pvgis_val,
        nasa_power=nasa_val,
        notes=notes,
    )
