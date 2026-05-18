"""Endpoints REST para importar cuadros de carga desde Excel/CSV/JSON."""
import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse

from app.services.import_data import (
    parse_csv_recintos, parse_csv_cargas, parse_xlsx_bytes,
    plantilla_csv_recintos, plantilla_csv_cargas,
)

router = APIRouter(prefix="/api/import", tags=["importación"])


@router.post("/recintos")
async def importar_recintos(archivo: UploadFile = File(...)):
    """Recibe un Excel, CSV o JSON con cuadro de recintos y devuelve lista."""
    nombre = archivo.filename.lower()
    contenido = await archivo.read()
    try:
        if nombre.endswith(".xlsx") or nombre.endswith(".xls"):
            recintos = parse_xlsx_bytes(contenido, "recintos")
        elif nombre.endswith(".json"):
            data = json.loads(contenido.decode("utf-8"))
            # Aceptar formato {recintos: [...]} o lista directa
            recintos = data.get("recintos", data) if isinstance(data, dict) else data
        elif nombre.endswith(".csv") or nombre.endswith(".tsv") or nombre.endswith(".txt"):
            recintos = parse_csv_recintos(contenido.decode("utf-8", errors="replace"))
        else:
            raise HTTPException(400, f"Formato no soportado: {nombre}. Use .xlsx, .csv o .json")
        return {"n_recintos": len(recintos), "recintos": recintos}
    except ValueError as e:
        raise HTTPException(422, f"Error parseando archivo: {e}")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/cargas")
async def importar_cargas(archivo: UploadFile = File(...)):
    """Recibe un Excel, CSV o JSON con cargas dedicadas."""
    nombre = archivo.filename.lower()
    contenido = await archivo.read()
    try:
        if nombre.endswith(".xlsx") or nombre.endswith(".xls"):
            cargas = parse_xlsx_bytes(contenido, "cargas")
        elif nombre.endswith(".json"):
            data = json.loads(contenido.decode("utf-8"))
            cargas = data.get("cargas", data) if isinstance(data, dict) else data
        elif nombre.endswith(".csv") or nombre.endswith(".tsv") or nombre.endswith(".txt"):
            cargas = parse_csv_cargas(contenido.decode("utf-8", errors="replace"))
        else:
            raise HTTPException(400, f"Formato no soportado: {nombre}")
        return {"n_cargas": len(cargas), "cargas": cargas}
    except ValueError as e:
        raise HTTPException(422, f"Error parseando archivo: {e}")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/template/recintos.csv", response_class=PlainTextResponse)
async def template_recintos_csv():
    """Descarga la plantilla CSV de recintos."""
    return PlainTextResponse(plantilla_csv_recintos(),
        headers={"Content-Disposition": "attachment; filename=plantilla_recintos.csv"})


@router.get("/template/cargas.csv", response_class=PlainTextResponse)
async def template_cargas_csv():
    """Descarga la plantilla CSV de cargas dedicadas."""
    return PlainTextResponse(plantilla_csv_cargas(),
        headers={"Content-Disposition": "attachment; filename=plantilla_cargas.csv"})


@router.get("/template/cuadro-carga.xlsx")
async def template_xlsx():
    """Descarga la plantilla profesional XLSX (recintos + cargas con dropdowns)."""
    from fastapi.responses import Response
    from app.services.template_xlsx import generar_template_xlsx
    content = generar_template_xlsx()
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_cuadro_carga_FV.xlsx"},
    )


@router.get("/healthcheck")
async def healthcheck() -> dict:
    return {"status": "ok", "module": "imports", "formatos": ["xlsx", "csv", "json"]}
