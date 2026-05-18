# Sistemas Fotovoltaicos Chile

Aplicación web integral para dimensionamiento de sistemas solares fotovoltaicos bajo
norma RIC chilena (SEC) y marco regulatorio Ley 21.118 (Netbilling). Frontend HTML
autocontenido + backend FastAPI Python; todo opera en una sola URL al desplegar.

## Módulos

| Módulo | Estado | Descripción |
|---|---|---|
| `terrain`  | ✅ | Coordenadas, altitud, recurso solar PVGIS + clima NASA POWER (18 ciudades + custom) |
| `plans`    | ✅ | Parser DXF (ezdxf) + PDF vectorial (pdfplumber) + detector PDF escaneado |
| `ric`      | ✅ | Cargas por uso de recinto, factores demanda/simultaneidad, dimensión de empalme |
| `fv`       | ✅ | Dimensionamiento con 8 pérdidas, PR real, selección automática de equipos |
| `layout`   | ✅ | Packing de paneles sobre área (techo plano/inclinado/suelo/carport) con pitch latitud |
| `reports`  | ✅ | XLSX (6 hojas) + DOCX (memoria técnica SEC) + PDF (informe ejecutivo) |

## Arranque rápido — 3 opciones

### Opción A — Script bash (recomendado para Mac/Linux)
```bash
bash start.sh
```
Crea venv, instala deps, copia .env y arranca uvicorn. Luego abre <http://localhost:8000>.

### Opción B — Docker (recomendado para producción)
```bash
docker compose up -d
```
Imagen autocontenida con Python 3.11 + Tesseract OCR + todas las deps. Persiste reportes en host.

### Opción C — Python directo
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

En cualquiera de las 3, accede a:
- **App web**: <http://localhost:8000/>
- **API docs**: <http://localhost:8000/docs>
- **Health check**: <http://localhost:8000/api/health>

## Arquitectura

```
                  ┌──────────────────────────────────────────────────────┐
                  │           FastAPI (puerto 8000)                       │
                  │                                                       │
  Cliente ─HTTP─→ │  /                  → app_fv_chile.html (UI)         │
                  │  /api/terrain/...   → Recurso solar                  │
                  │  /api/plans/parse   → Parser DXF/PDF (multipart)     │
                  │  /api/ric/calc      → Cargas RIC                      │
                  │  /api/fv/design     → Diseño FV + Económico          │
                  │  /api/layout/calc   → Packing de paneles             │
                  │  /api/reports/...   → Genera y descarga XLSX/DOCX/PDF │
                  │  /reportes/...      → Archivos pre-generados          │
                  │                                                       │
                  └────────┬────────────────────────┬─────────────────────┘
                           │                        │
                  ┌────────▼────────┐      ┌────────▼────────┐
                  │  APIs externas  │      │  Cálculo local  │
                  │  PVGIS v5.3     │      │  pvlib, shapely │
                  │  NASA POWER     │      │  ezdxf, openpyxl│
                  │  Nominatim/OSM  │      │  reportlab      │
                  │  Open-Elevation │      │  python-docx    │
                  └─────────────────┘      └─────────────────┘
```

- **Backend**: FastAPI + Uvicorn (Python async)
- **Datos externos** (sin API key): PVGIS v5.3, NASA POWER, Nominatim/OSM, Open-Elevation
- **Cálculo**: pvlib (Sandia/NREL), numpy, pandas, scipy
- **Planos**: ezdxf, pdfplumber, ocrmypdf+OpenCV (futuro)
- **Persistencia**: localStorage del navegador (proyectos del usuario)
- **Reportes**: openpyxl, python-docx, reportlab + matplotlib

## Estructura del proyecto

```
SISTEMAS FOTOVOLTAICOS/
├── app/                        # Backend Python
│   ├── main.py                 # FastAPI + montaje estático + /api/health
│   ├── config.py               # Pydantic Settings desde .env
│   ├── models/                 # Pydantic: terrain, plans, ric, fv, layout
│   ├── services/               # Lógica: pvgis, parsers, ric_loads, pv_sizing, etc.
│   └── routers/                # Endpoints REST por módulo
├── app_fv_chile.html           # Frontend SPA autocontenido (UI + JS + CSS)
├── reportes/                   # XLSX/PDF/DOCX pre-generados de los 3 demos
├── 01_Resumen_Ejecutivo.docx   # Doc de especificación 1 pág
├── 02_Documento_Tecnico_Maestro.docx  # Spec técnica 27 secciones
├── plano-departamento-tipo.dxf # DXF de prueba (depto 2D-1B)
├── techo-*.dxf                 # DXFs de techos para layout (hotel/industria/vivienda)
├── start.sh                    # Script bash de arranque
├── Dockerfile                  # Imagen Docker
├── docker-compose.yml          # Orquestación Docker
├── requirements.txt            # Deps Python
└── .env.example                # Plantilla de variables
```

## 13 endpoints REST disponibles

```
GET   /                            → App web HTML
GET   /docs                        → Documentación interactiva OpenAPI
GET   /api/health                  → Health + módulos disponibles
POST  /api/terrain/analyze         → Análisis del sitio (dirección o lat/lon)
GET   /api/terrain/healthcheck
POST  /api/plans/parse             → Upload DXF/PDF, devuelve recintos con m²
GET   /api/plans/healthcheck
POST  /api/ric/calc                → Calcula carga RIC desde recintos
GET   /api/ric/healthcheck
POST  /api/fv/design               → Dimensionamiento FV + análisis económico
GET   /api/fv/healthcheck
POST  /api/layout/calc             → Packing de paneles sobre polígono
GET   /api/layout/healthcheck
POST  /api/reports/excel           → Genera y descarga XLSX
POST  /api/reports/word            → Genera y descarga DOCX (memoria SEC)
POST  /api/reports/pdf             → Genera y descarga PDF ejecutivo
GET   /api/reports/healthcheck
```

## Cómo se conectan UI y backend

La UI HTML detecta automáticamente si está siendo servida por el backend (mismo host)
o si está abierta como archivo standalone. Indicador en la barra superior:

- 🟢 **Backend conectado** — botones generan XLSX/DOCX/PDF en vivo, plano se parsea al subir
- 🟡 **Backend no responde** — URL configurada pero servidor caído; modo local activo
- ⚫ **Modo local** — sin URL configurada; cálculos en JS dentro del navegador

Para configurar URL custom (ej. backend remoto), entrar a **Configuración** en la app
y poner la URL completa (`https://fv.midominio.cl`).

## Validación regional (resultados reales contra atlas solar chileno)

| Ciudad | Lat | Slope óptimo | E_y (kWh/kWp/año) | GHI (kWh/m²/día) |
|---|---|---|---|---|
| Antofagasta | -23° | 24° | 1.888 | 6,06 |
| Calama      | -22° | 25° | 2.085 | 6,94 |
| Santiago    | -33° | 32° | 1.743 | 5,45 |
| Puerto Montt| -41° | 36° | 1.274 | 3,65 |
| Punta Arenas| -53° | 47° | 1.136 | 2,58 |

Patrón consistente con el Explorador Solar oficial: inclinación crece con latitud
austral, generación decrece, Atacama lidera el recurso.

## Notas técnicas relevantes

- **Convención PVGIS azimut**: `aspect=0` apunta al **sur**, `aspect=180` al **norte**.
  Para Chile (hemisferio sur) → `aspect=180`. Configurado vía `HEMISPHERE=SOUTH` en `.env`.
- **PVGIS pérdidas**: PVGIS reporta `l_total` con signo negativo (convención STC europea);
  el servicio lo normaliza a positivo para presentación al usuario chileno.
- **NASA POWER sentinel**: la API usa `-999` para meses sin dato; el servicio los filtra.
- **Nominatim rate limit**: máx. 1 req/s, exige `User-Agent` identificable. Para
  producción → cachear o migrar a Mapbox/Google.
- **CORS**: configurado como `allow_origins=["*"]` para desarrollo. En producción
  restringir a tu dominio en `app/main.py`.
- **localStorage**: los proyectos del usuario se guardan en el navegador. Para
  persistencia multi-usuario migrar a PostgreSQL + auth (próximo paso).

## Próximos pasos pendientes

1. **Autenticación multi-usuario** (login + JWT + DB)
2. **Persistencia en PostgreSQL** (reemplazar localStorage)
3. **Pipeline OCR completo** para PDFs escaneados (UI interactiva de marcado)
4. **Integración con API SEC** para auto-cargar TE-1 cuando esté operativa
5. **Catálogos en vivo** desde proveedores chilenos (precios al día)

## Soporte y contacto

Daniel Romero · dromeroponce29@gmail.com
# proy-fv-ver1.0
# sistema-Fv-ve1.1
