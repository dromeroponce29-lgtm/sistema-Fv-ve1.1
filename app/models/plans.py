"""Modelos Pydantic del módulo PLANOS.

Representa un plano arquitectónico procesado: lista de recintos con
geometría (vértices, área, perímetro, centroide), uso inferido desde
nombre de layer/texto, y metadatos de la fuente."""
from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


# Usos reconocidos por la herramienta. Mapean directo a las tablas RIC del
# siguiente módulo (CARGAS), donde a cada uso se le asigna potencia mínima
# por m² según pliego.
UsoRecinto = Literal[
    "living", "cocina", "dormitorio", "bano", "comedor", "oficina",
    "pasillo", "hall", "exterior", "lavanderia", "bodega", "logia",
    "circulacion", "comun", "desconocido",
]


class Recinto(BaseModel):
    """Un recinto (habitación) detectado en el plano."""
    id: int
    nombre: str = Field(..., description="Nombre legible (desde texto cercano o nombre de layer)")
    uso: UsoRecinto = Field(..., description="Uso inferido a partir del nombre/layer")
    area_m2: float
    perimetro_m: float
    centroide: Tuple[float, float] = Field(..., description="(x, y) en metros")
    vertices: List[Tuple[float, float]] = Field(..., description="Polígono en metros")
    layer_origen: Optional[str] = None
    fuente_nombre: Literal["layer", "texto_dentro", "fallback"] = "fallback"


class PlanoParseado(BaseModel):
    """Resultado del parsing de un plano completo."""
    archivo: str
    formato: Literal["dxf", "pdf_vectorial", "pdf_escaneado"]
    unidad_origen: str = Field(..., description="mm, cm, m, in (lo que se leyó del archivo)")
    factor_a_metros: float = Field(..., description="Factor multiplicador para convertir a m")
    recintos: List[Recinto]
    area_total_m2: float
    n_recintos: int
    advertencias: List[str] = []
    metadatos: dict = Field(default_factory=dict)
