"""Configuración global cargada desde variables de entorno o .env."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Identificación
    app_name: str = "SistemasFV-Chile"
    app_version: str = "0.1.0"
    contact_email: str = "dromeroponce29@gmail.com"

    # Endpoints externos
    pvgis_base_url: str = "https://re.jrc.ec.europa.eu/api/v5_3"
    nasa_power_base_url: str = "https://power.larc.nasa.gov/api"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    open_elevation_url: str = "https://api.open-elevation.com/api/v1/lookup"

    # Comportamiento HTTP
    http_timeout: int = 30

    # Regional
    default_country: str = "Chile"
    default_timezone: str = "America/Santiago"
    hemisphere: str = "SOUTH"  # SOUTH para Chile → paneles al norte (PVGIS azimuth=180)

    # Persistencia
    database_url: str = "sqlite+aiosqlite:///./sistemas_fv.db"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def user_agent(self) -> str:
        """User-Agent obligatorio para Nominatim/OSM (incluye contacto)."""
        return f"{self.app_name}/{self.app_version} ({self.contact_email})"

    @property
    def optimal_azimuth(self) -> int:
        """Azimut óptimo según hemisferio. PVGIS: 0=sur, 180=norte."""
        return 180 if self.hemisphere.upper() == "SOUTH" else 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
