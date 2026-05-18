"""Geocoding usando Nominatim (OpenStreetMap).

Nominatim exige User-Agent identificable y ≤1 req/s. Para uso intensivo
recomendamos cachear o migrar a un proveedor pago (Mapbox/Google)."""
from typing import Optional
import httpx
from app.config import get_settings
from app.models.terrain import GeoLocation


class GeocodingError(Exception):
    pass


async def geocode_address(address: str) -> GeoLocation:
    """Convierte una dirección a coordenadas y metadatos administrativos."""
    settings = get_settings()
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "countrycodes": "cl" if settings.default_country.lower() == "chile" else None,
    }
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"User-Agent": settings.user_agent, "Accept-Language": "es"}

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        r = await client.get(
            f"{settings.nominatim_base_url}/search", params=params, headers=headers
        )
        r.raise_for_status()
        data = r.json()

    if not data:
        raise GeocodingError(f"No se encontró la dirección: {address!r}")

    item = data[0]
    addr = item.get("address", {})
    return GeoLocation(
        latitude=float(item["lat"]),
        longitude=float(item["lon"]),
        display_name=item.get("display_name"),
        city=addr.get("city") or addr.get("town") or addr.get("municipality"),
        region=addr.get("state"),
        country=addr.get("country"),
    )


async def reverse_geocode(latitude: float, longitude: float) -> Optional[GeoLocation]:
    """Coordenadas → dirección. Útil cuando el usuario marca punto en un mapa."""
    settings = get_settings()
    params = {"lat": latitude, "lon": longitude, "format": "json", "addressdetails": 1}
    headers = {"User-Agent": settings.user_agent, "Accept-Language": "es"}

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        r = await client.get(
            f"{settings.nominatim_base_url}/reverse", params=params, headers=headers
        )
        r.raise_for_status()
        item = r.json()

    if not item or "lat" not in item:
        return GeoLocation(latitude=latitude, longitude=longitude)

    addr = item.get("address", {})
    return GeoLocation(
        latitude=float(item["lat"]),
        longitude=float(item["lon"]),
        display_name=item.get("display_name"),
        city=addr.get("city") or addr.get("town") or addr.get("municipality"),
        region=addr.get("state"),
        country=addr.get("country"),
    )
