"""Aplicación FastAPI — Sistemas Fotovoltaicos Chile.

Punto de entrada. Levantar con:
    uvicorn app.main:app --reload --port 8000

Al levantar, sirve:
  http://localhost:8000/         → app web (HTML + JS + CSS, todo en uno)
  http://localhost:8000/docs     → documentación interactiva OpenAPI
  http://localhost:8000/api/...  → endpoints REST de cada módulo
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import terrain as terrain_router
from app.routers import plans as plans_router
from app.routers import ric as ric_router
from app.routers import fv as fv_router
from app.routers import reports as reports_router
from app.routers import layout as layout_router
from app.routers import imports as imports_router

settings = get_settings()

app = FastAPI(
    title="Sistemas Fotovoltaicos Chile",
    version=settings.app_version,
    description=(
        "Dimensionamiento integral de sistemas FV bajo norma RIC chilena. "
        "Procesa planos DXF/PDF, calcula carga por habitación, recurso solar "
        "del sitio y dimensiona el arreglo."
    ),
)

# CORS — permisivo en desarrollo. En producción restringir a tu dominio.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Routers -----
app.include_router(terrain_router.router)
app.include_router(plans_router.router)
app.include_router(ric_router.router)
app.include_router(fv_router.router)
app.include_router(reports_router.router)
app.include_router(layout_router.router)
app.include_router(imports_router.router)


# ----- Endpoint de health para que la UI detecte el backend -----
@app.get("/api/health", tags=["util"])
async def health() -> dict:
    """Health check público — devuelve estado y módulos disponibles."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "hemisphere": settings.hemisphere,
        "modules": ["terrain", "plans", "ric", "fv", "layout", "reports"],
        "endpoints": {
            "terrain":  "/api/terrain/analyze",
            "plans":    "/api/plans/parse",
            "ric":      "/api/ric/calc",
            "fv":       "/api/fv/design",
            "layout":   "/api/layout/calc",
            "reports":  "/api/reports/{excel,pdf,word}",
        },
    }


# ----- Servir la app web (HTML SPA) desde la raíz -----
# El HTML está al lado del proyecto, como `app_fv_chile.html`.
# Buscar primero en la raíz del proyecto, luego en /static/.
ROOT_DIR = Path(__file__).resolve().parent.parent
INDEX_CANDIDATES = [
    ROOT_DIR / "app_fv_chile.html",
    ROOT_DIR / "static" / "index.html",
]
INDEX_HTML = next((p for p in INDEX_CANDIDATES if p.exists()), None)

# Si hay carpeta /static/ con assets adicionales, montarla
STATIC_DIR = ROOT_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Carpeta de reportes pre-generados (los de los demos)
REPORTES_DIR = ROOT_DIR / "reportes"
if REPORTES_DIR.exists():
    app.mount("/reportes", StaticFiles(directory=REPORTES_DIR), name="reportes")


@app.get("/", response_class=HTMLResponse, tags=["util"])
async def root():
    """Sirve la app web autocontenida o redirige a la docs si no existe."""
    if INDEX_HTML and INDEX_HTML.exists():
        return FileResponse(INDEX_HTML, media_type="text/html")
    return HTMLResponse(
        f"<!DOCTYPE html><html><body style='font-family:system-ui;padding:40px;max-width:600px;margin:auto;'>"
        f"<h1>{settings.app_name} v{settings.app_version}</h1>"
        f"<p>Backend FastAPI corriendo correctamente.</p>"
        f"<p>El HTML de la app no se encontró en <code>{ROOT_DIR}/app_fv_chile.html</code>.</p>"
        f"<ul>"
        f"<li><a href='/api/health'>API health</a></li>"
        f"<li><a href='/docs'>Documentación OpenAPI</a></li>"
        f"<li>Para servir la app web, copia <code>app_fv_chile.html</code> a la raíz del proyecto</li>"
        f"</ul></body></html>"
    )
