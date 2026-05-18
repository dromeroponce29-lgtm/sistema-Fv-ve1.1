"""Cliente NASA POWER (Prediction Of Worldwide Energy Resources).

Datos satelitales: irradiancia global, temperatura, viento, humedad.
Gratuito, sin API key, cobertura global desde 1984.

Parámetros usados (community=RE — Renewable Energy):
    ALLSKY_SFC_SW_DWN — Irradiancia global horizontal (kWh/m²/día)
    T2M               — Temperatura a 2 m sobre la superficie (°C)
    WS10M             — Velocidad del viento a 10 m (m/s)
    RH2M              — Humedad relativa a 2 m (%)
"""
import statistics
from typing import Optional
import httpx
from app.config import get_settings
from app.models.terrain import NasaPowerMonth, NasaPowerSummary


class NasaPowerError(Exception):
    pass


PARAMETERS = "ALLSKY_SFC_SW_DWN,T2M,WS10M,RH2M"


async def get_monthly_climate(
    latitude: float,
    longitude: float,
    year: Optional[int] = None,
) -> NasaPowerSummary:
    """Datos climáticos mensuales para un año.

    Por defecto usa año pasado (datos completos garantizados)."""
    settings = get_settings()
    if year is None:
        # Año anterior para garantizar dataset completo
        from datetime import datetime
        year = datetime.utcnow().year - 1

    params = {
        "parameters": PARAMETERS,
        "community": "RE",
        "longitude": longitude,
        "latitude": latitude,
        "start": year,
        "end": year,
        "format": "JSON",
    }

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        r = await client.get(
            f"{settings.nasa_power_base_url}/temporal/monthly/point", params=params
        )
        if r.status_code != 200:
            raise NasaPowerError(f"NASA POWER HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()

    try:
        p = data["properties"]["parameter"]
        ghi = p["ALLSKY_SFC_SW_DWN"]
        t2m = p["T2M"]
        ws = p["WS10M"]
        rh = p.get("RH2M", {})
    except KeyError as e:
        raise NasaPowerError(f"NASA POWER estructura inesperada, falta: {e}")

    SENTINEL = -999.0  # NASA POWER usa -999 cuando no hay dato

    def _clean(v) -> float | None:
        try:
            f = float(v)
            return None if f <= SENTINEL + 1 else f
        except (TypeError, ValueError):
            return None

    months_data: list[NasaPowerMonth] = []
    for m in range(1, 13):
        key = f"{year}{m:02d}"
        if key not in ghi:
            continue
        g = _clean(ghi[key])
        t = _clean(t2m[key])
        w = _clean(ws[key])
        # Si la variable principal (GHI) no tiene dato, descartamos el mes completo
        if g is None:
            continue
        months_data.append(
            NasaPowerMonth(
                month=m,
                ghi_kwh_m2_day=g,
                t2m_avg_c=t if t is not None else 0.0,
                wind10m_avg_ms=w if w is not None else 0.0,
                relative_humidity_pct=_clean(rh.get(key)) if key in rh else None,
            )
        )

    if not months_data:
        raise NasaPowerError("NASA POWER no devolvió datos mensuales útiles")

    return NasaPowerSummary(
        year=year,
        annual_ghi_kwh_m2_day=statistics.mean(m.ghi_kwh_m2_day for m in months_data),
        annual_t2m_avg_c=statistics.mean(m.t2m_avg_c for m in months_data),
        annual_wind10m_avg_ms=statistics.mean(m.wind10m_avg_ms for m in months_data),
        monthly=months_data,
    )
