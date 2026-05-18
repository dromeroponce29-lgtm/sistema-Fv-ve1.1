"""Cliente PVGIS v5.3 (Joint Research Centre, Comisión Europea).

PVGIS provee radiación solar histórica, ángulo óptimo de inclinación
y estimación de generación FV. Es la referencia europea pero cubre
todo el mundo incluido Chile.

IMPORTANTE — convención de azimut PVGIS:
    azimuth=0   → Sur
    azimuth=180 → Norte
    azimuth=-90 → Este
    azimuth=90  → Oeste
Para Chile (hemisferio sur), el azimut óptimo es ~180° (paneles al norte).
"""
import httpx
from app.config import get_settings
from app.models.terrain import PvgisMonth, PvgisSummary


class PvgisError(Exception):
    pass


def _safe_float(value, default: float = 0.0) -> float:
    """PVGIS a veces devuelve '-' o cadena en pérdidas. Casteo defensivo."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def get_pv_calculation(
    latitude: float,
    longitude: float,
    peakpower_kw: float = 1.0,
    system_loss_pct: float = 14.0,
    pv_tech: str = "crystSi",
    mounting: str = "building",
    optimal_angles: bool = True,
    fixed_slope: float | None = None,
    fixed_azimuth: float | None = None,
) -> PvgisSummary:
    """Llama al endpoint PVcalc y retorna estructura tipada,
    **normalizada por kWp** (independiente de peakpower).

    PVGIS devuelve E_m, E_y como totales del sistema (no por kWp).
    Internamente siempre llamamos con peakpower=1 para obtener valores
    por kWp y luego el caller multiplica según su instalación real.

    Si `optimal_angles=True`, PVGIS calcula inclinación Y azimut óptimos
    enviando flags separados (optimalinclination + azimut según hemisferio).
    """
    settings = get_settings()
    params: dict[str, str | int | float] = {
        "lat": latitude,
        "lon": longitude,
        "peakpower": 1.0,  # SIEMPRE 1 → valores por kWp
        "loss": system_loss_pct,
        "outputformat": "json",
        "pvtechchoice": pv_tech,
        "mountingplace": mounting,
    }
    if optimal_angles:
        # PVGIS: optimalinclination=1 calcula inclinación óptima;
        # azimut debe ser fijado al óptimo conocido por hemisferio
        # (en hemisferio sur: aspect=0 que es Sur invertido = 180/-180 NORTE)
        params["optimalinclination"] = 1
        params["aspect"] = settings.optimal_azimuth  # 180 para Chile
    else:
        params["angle"] = fixed_slope if fixed_slope is not None else abs(latitude)
        params["aspect"] = (
            fixed_azimuth if fixed_azimuth is not None else settings.optimal_azimuth
        )

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        r = await client.get(f"{settings.pvgis_base_url}/PVcalc", params=params)
        if r.status_code != 200:
            raise PvgisError(f"PVGIS HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()

    try:
        fixed_mount = data["inputs"]["mounting_system"]["fixed"]
        slope = _safe_float(fixed_mount["slope"]["value"])
        azimuth = _safe_float(fixed_mount["azimuth"]["value"])

        totals = data["outputs"]["totals"]["fixed"]
        monthly_raw = data["outputs"]["monthly"]["fixed"]
    except KeyError as e:
        raise PvgisError(f"Estructura PVGIS inesperada, falta clave: {e}")

    monthly = [
        PvgisMonth(
            month=int(row["month"]),
            energy_kwh_per_kwp=_safe_float(row.get("E_m")),
            irradiation_kwh_per_m2=_safe_float(row.get("H(i)_m")),
            t2m_avg_c=_safe_float(row.get("T2m")) if row.get("T2m") is not None else None,
        )
        for row in monthly_raw
    ]

    # PVGIS reporta pérdidas con signo negativo (convención europea STC).
    # Para la UI chilena presentamos magnitudes positivas.
    return PvgisSummary(
        optimal_slope_deg=slope,
        optimal_azimuth_deg=azimuth,
        annual_energy_kwh_per_kwp=_safe_float(totals.get("E_y")),
        annual_irradiation_kwh_per_m2=_safe_float(totals.get("H(i)_y")),
        interannual_variability_kwh_per_kwp=_safe_float(totals.get("SD_y")),
        losses_pct_aoi=abs(_safe_float(totals.get("l_aoi"))),
        losses_pct_spectral=abs(_safe_float(totals.get("l_spec"))),
        losses_pct_temp_and_lowirr=abs(_safe_float(totals.get("l_tg"))),
        losses_pct_total=abs(_safe_float(totals.get("l_total"))),
        monthly=monthly,
    )
