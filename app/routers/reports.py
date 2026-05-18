"""Endpoints REST para generar reportes (XLSX / DOCX / PDF) por proyecto."""
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services.report_excel import generar_excel
from app.services.report_pdf import generar_pdf
from app.services.report_word import generar_word

router = APIRouter(prefix="/api/reports", tags=["reportes"])


@router.post("/excel")
async def excel(proyecto: dict):
    """Genera memoria de cálculo XLSX para un proyecto y la devuelve."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            path = Path(tmp.name)
        generar_excel(proyecto, path)
        return FileResponse(path, filename=f"memoria_calculo_{proyecto.get('id','proyecto')}.xlsx")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/pdf")
async def pdf(proyecto: dict):
    """Genera informe ejecutivo PDF para un proyecto."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = Path(tmp.name)
        generar_pdf(proyecto, path)
        return FileResponse(path, filename=f"informe_ejecutivo_{proyecto.get('id','proyecto')}.pdf")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/word")
async def word(proyecto: dict):
    """Genera memoria técnica DOCX firmable por instalador autorizado SEC."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            path = Path(tmp.name)
        generar_word(proyecto, path)
        return FileResponse(path, filename=f"memoria_tecnica_{proyecto.get('id','proyecto')}.docx")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/healthcheck", tags=["util"])
async def healthcheck() -> dict:
    return {"status": "ok", "module": "reports", "formatos": ["xlsx", "pdf", "docx"]}
