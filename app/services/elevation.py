"""Altitud sobre el nivel del mar usando Open-Elevation (SRTM).

La altitud afecta la temperatura de celda y la masa de aire, ambas
relevantes en pvlib para el cálculo de potencia."""
from typing import Optional
import httpx
from app.config import get_settings


async def get_elevation(latitude: float, longitude: float) -> Optional[float]:
    """Devuelve altitud en metros sobre el nivel del mar."""
    settings = get_settings()
    params = {"locations": f"{latitude},{longitude}"}

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            r = await client.get(settings.open_elevation_url, params=params)
            r.raise_for_status()
            data = r.json()
        return float(data["results"][0]["elevation"])
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        # Si Open-Elevation falla, retornamos None y el caller decide
        # (puede usar default de 500 msnm o pedir al usuario)
        return None
