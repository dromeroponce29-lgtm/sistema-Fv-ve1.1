"""Script reproducible de validación del módulo TERRENO.

Ejecuta el orquestador para tres ciudades chilenas y compara con el atlas
solar oficial. Sirve como smoke test y de ejemplo de uso programático.

    python3 scripts/probar_terreno.py
"""
import asyncio
import sys
from pathlib import Path

# Agregar raíz del proyecto al path para que `from app...` funcione
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.terrain import analyze_terrain  # noqa: E402
from app.models.terrain import TerrainRequest  # noqa: E402


CASOS = [
    ("Antofagasta (desierto)", "Avenida Argentina 1962, Antofagasta, Chile"),
    ("Santiago (RM)", "Avenida Apoquindo 5000, Las Condes, Chile"),
    ("Punta Arenas (austral)", "Avenida Bulnes 01855, Punta Arenas, Chile"),
]


async def main() -> None:
    print(f"{'CIUDAD':<28} {'LAT':>7} {'msnm':>6} {'°incl':>6} "
          f"{'°azim':>6} {'kWh/kWp/año':>12} {'GHI':>6} {'T°C':>6}")
    print("-" * 92)
    for nombre, addr in CASOS:
        try:
            r = await analyze_terrain(TerrainRequest(address=addr))
            print(
                f"{nombre:<28} {r.location.latitude:>7.2f} {(r.elevation_masl or 0):>6.0f} "
                f"{r.pvgis.optimal_slope_deg:>6.1f} {r.pvgis.optimal_azimuth_deg:>6.0f} "
                f"{r.pvgis.annual_energy_kwh_per_kwp:>12.0f} "
                f"{r.nasa_power.annual_ghi_kwh_m2_day:>6.2f} "
                f"{r.nasa_power.annual_t2m_avg_c:>6.1f}"
            )
        except Exception as e:
            print(f"{nombre:<28}  ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
