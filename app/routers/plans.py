"""Endpoints REST del módulo PLANOS."""
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.models.plans import PlanoParseado
from app.services.plans import parse_plano, PlanosOrchestrationError
from app.services.dxf_parser import DxfParserError
from app.services.pdf_parser import PdfParserError


router = APIRouter(prefix="/api/plans", tags=["planos"])


@router.post("/parse", response_model=PlanoParseado)
async def parse(
    archivo: UploadFile = File(..., description="Archivo .dxf o .pdf"),
    escala_pdf: Optional[float] = Form(
        None,
        description="Solo para PDF: factor pt→m (ej. 100 * 0.0254 / 72 para escala 1:100). Si no se informa, asume 1:100.",
    ),
) -> PlanoParseado:
    """Sube un plano DXF o PDF y devuelve la estructura semántica de recintos."""
    ext = Path(archivo.filename).suffix.lower()
    if ext not in (".dxf", ".pdf"):
        raise HTTPException(400, f"Formato no soportado: {ext}. Use .dxf o .pdf")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        contenido = await archivo.read()
        tmp.write(contenido)
        tmp_path = Path(tmp.name)

    try:
        return parse_plano(tmp_path, escala_pdf=escala_pdf)
    except PlanosOrchestrationError as e:
        raise HTTPException(400, str(e))
    except DxfParserError as e:
        raise HTTPException(422, f"Error parseando DXF: {e}")
    except PdfParserError as e:
        raise HTTPException(422, f"Error parseando PDF: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/healthcheck", tags=["util"])
async def healthcheck() -> dict:
    return {"status": "ok", "module": "plans", "formatos_soportados": ["dxf", "pdf_vectorial"]}
