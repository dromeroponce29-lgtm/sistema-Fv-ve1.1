"""Orquestador del módulo PLANOS.

Detecta automáticamente el formato del archivo (DXF / PDF vectorial /
PDF escaneado) y delega al parser correspondiente."""
from pathlib import Path

from app.models.plans import PlanoParseado
from app.services import dxf_parser, pdf_parser


class PlanosOrchestrationError(Exception):
    pass


def parse_plano(ruta: Path | str, escala_pdf: float | None = None) -> PlanoParseado:
    """Parsea un plano y retorna su estructura semántica.

    Args:
        ruta: archivo del plano.
        escala_pdf: factor pt→m si el archivo es PDF vectorial (default 1:100).
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise PlanosOrchestrationError(f"Archivo no encontrado: {ruta}")

    ext = ruta.suffix.lower()
    if ext == ".dxf":
        return dxf_parser.parse_dxf(ruta)
    if ext == ".pdf":
        # El parser PDF detecta internamente si es vectorial o escaneado
        try:
            return pdf_parser.parse_pdf_vectorial(ruta, escala_pdf_a_metros=escala_pdf)
        except pdf_parser.PdfParserError as e:
            if "escaneado" in str(e).lower():
                return pdf_parser.parse_pdf_escaneado(ruta)
            raise
    raise PlanosOrchestrationError(
        f"Formato no soportado: {ext}. Formatos válidos: .dxf, .pdf"
    )
