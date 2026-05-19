"""Fixtures compartidos para los tests del motor FV."""
import sys
from pathlib import Path
import pytest

# Hacer importable el paquete `app` desde tests/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def recintos_vivienda_tipica():
    """3 recintos básicos de una casa de 80 m²."""
    return [
        {"id": 1, "nombre": "Living-comedor", "uso": "living",      "area_m2": 32},
        {"id": 2, "nombre": "Cocina",         "uso": "cocina",      "area_m2": 12},
        {"id": 3, "nombre": "Dormitorio 1",   "uso": "dormitorio",  "area_m2": 18},
        {"id": 4, "nombre": "Baño",           "uso": "bano",        "area_m2": 6},
        {"id": 5, "nombre": "Pasillo",        "uso": "pasillo",     "area_m2": 12},
    ]


@pytest.fixture
def sitio_santiago():
    """Datos solares de Santiago para pruebas FV."""
    return {
        "lat": -33.45, "lon": -70.65,
        "altitud_msnm": 520,
        "E_y": 1850, "H_y": 2100,
        "slope": 30, "azimuth": 0,
        "monthly_E": [180, 170, 160, 140, 120, 100, 110, 130, 150, 170, 180, 190],
        "monthly_t": [18, 17, 15, 12, 10, 8, 9, 11, 13, 15, 17, 19],
        "t2m_avg": 14.5, "wind_avg": 2.3,
    }


@pytest.fixture
def fv_request_default(sitio_santiago):
    """Petición FV mínima reproducible para casa típica en Santiago."""
    from app.models.fv import FvRequest
    return FvRequest(
        consumo_anual_kwh=6000,
        consumo_mensual_kwh=[500] * 12,
        demanda_maxima_kw=3.5,
        E_y_kwh_por_kwp=sitio_santiago["E_y"],
        H_y_kwh_m2=sitio_santiago["H_y"],
        monthly_E_kwh_por_kwp=sitio_santiago["monthly_E"],
        monthly_t_amb_c=sitio_santiago["monthly_t"],
        altitud_msnm=sitio_santiago["altitud_msnm"],
        tipo_proyecto="vivienda",
    )
