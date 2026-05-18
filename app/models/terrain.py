"""Modelos Pydantic para datos del terreno (entrada y salida)."""
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------- ENTRADA ----------
class TerrainRequest(BaseModel):
    """Petición. Acepta dirección O coordenadas. Si vienen ambas, prevalecen coordenadas."""
    address: Optional[str] = Field(None, description="Dirección completa (ej: 'Av Apoquindo 5000, Las Condes, Chile')")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    peakpower_kw: float = Field(1.0, gt=0, description="Potencia pico hipotética para simulación PVGIS")
    system_loss_pct: float = Field(14.0, ge=0, le=50, description="Pérdidas del sistema (%)")
    pv_tech: str = Field("crystSi", description="crystSi | CIS | CdTe")
    mounting: str = Field("building", description="building | free")


# ---------- SUBSTRUCTURAS ----------
class GeoLocation(BaseModel):
    latitude: float
    longitude: float
    display_name: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class PvgisMonth(BaseModel):
    month: int
    energy_kwh_per_kwp: float       # E_m
    irradiation_kwh_per_m2: float   # H(i)_m
    t2m_avg_c: Optional[float] = None


class PvgisSummary(BaseModel):
    optimal_slope_deg: float
    optimal_azimuth_deg: float
    annual_energy_kwh_per_kwp: float
    annual_irradiation_kwh_per_m2: float
    interannual_variability_kwh_per_kwp: float
    losses_pct_aoi: float
    losses_pct_spectral: float
    losses_pct_temp_and_lowirr: float
    losses_pct_total: float
    monthly: List[PvgisMonth]


class NasaPowerMonth(BaseModel):
    month: int
    ghi_kwh_m2_day: float           # ALLSKY_SFC_SW_DWN
    t2m_avg_c: float                # T2M
    wind10m_avg_ms: float           # WS10M
    relative_humidity_pct: Optional[float] = None


class NasaPowerSummary(BaseModel):
    year: int
    annual_ghi_kwh_m2_day: float
    annual_t2m_avg_c: float
    annual_wind10m_avg_ms: float
    monthly: List[NasaPowerMonth]


# ---------- RESPUESTA AGREGADA ----------
class TerrainAnalysis(BaseModel):
    """Paquete completo de datos del terreno listos para el motor de diseño FV."""
    location: GeoLocation
    elevation_masl: Optional[float] = None
    pvgis: PvgisSummary
    nasa_power: NasaPowerSummary
    notes: List[str] = []
