"""Modelos del módulo LAYOUT FV (disposición física a estaca)."""
from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


TipoMontaje = Literal[
    "techo_plano",        # Estructura inclinada sobre techo plano
    "techo_inclinado",    # Coplanar al techo inclinado
    "suelo",              # Montaje en terreno con pasillos
    "carport",            # Pérgola sobre estacionamiento
]

OrientacionPanel = Literal["portrait", "landscape"]


class AreaDisponible(BaseModel):
    """Área útil donde se pueden instalar paneles."""
    nombre: str = "Área disponible"
    poligono: List[Tuple[float, float]] = Field(..., description="Polígono cerrado del área (m)")
    obstaculos: List[List[Tuple[float, float]]] = Field(
        default_factory=list,
        description="Lista de polígonos de obstáculos a evitar (m)"
    )
    tipo_montaje: TipoMontaje = "techo_plano"
    inclinacion_techo_deg: float = Field(0, ge=0, le=60, description="Solo si techo_inclinado")
    azimut_techo_deg: float = Field(0, description="Solo si techo_inclinado (0=norte, 90=este, etc)")
    retiro_perimetral_m: float = Field(0.5, ge=0, le=5, description="Margen libre del borde")
    pasillo_cada_n_filas: int = Field(0, ge=0, description="Pasillo de mantención cada N filas (0 = sin pasillos)")
    ancho_pasillo_m: float = Field(0.8, ge=0)


class PanelPosicionado(BaseModel):
    """Un panel con su posición y orientación en el área."""
    id: int
    x: float            # Esquina inferior izquierda (m)
    y: float
    largo_m: float
    ancho_m: float
    orientacion: OrientacionPanel
    fila: int
    columna: int


class LayoutRequest(BaseModel):
    area: AreaDisponible
    panel_largo_m: float = 2.28      # Default Jinko 550W
    panel_ancho_m: float = 1.13
    panel_Pnom_w: float = 550
    inclinacion_paneles_deg: float = Field(30, ge=0, le=60, description="Inclinación de la estructura (techo plano)")
    latitud_deg: float = Field(-33.4, description="Para calcular pitch entre filas")
    orientacion: OrientacionPanel = "portrait"   # portrait = lado largo vertical
    max_paneles: int = Field(0, ge=0, description="0 = sin límite, llenar todo el área")


class DisposicionFV(BaseModel):
    """Resultado del cálculo de disposición."""
    n_paneles: int
    n_filas: int
    paneles_por_fila: List[int]              # Cuántos paneles tiene cada fila
    pitch_m: float                            # Distancia entre filas (centro a centro)
    P_kwp_real: float                         # Potencia real instalable
    area_paneles_m2: float
    area_disponible_m2: float
    area_util_m2: float                       # Tras aplicar retiro perimetral
    aprovechamiento_pct: float                # área paneles / área útil
    paneles: List[PanelPosicionado]
    advertencias: List[str] = []
