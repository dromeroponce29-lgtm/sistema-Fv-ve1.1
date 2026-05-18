"""Modelos Pydantic del módulo CARGAS RIC."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


TipoProyecto = Literal[
    "vivienda", "edificio_residencial", "hotel", "industria",
    "comercial", "oficina", "manual",
]


class RecintoCarga(BaseModel):
    """Recinto con su carga calculada (alumbrado + enchufes generales)."""
    id: int
    nombre: str
    uso: str
    area_m2: float
    alumbrado_w: float
    enchufes_w: float
    subtotal_w: float


class CargaDedicadaCalculada(BaseModel):
    nombre: str
    potencia_w: float
    recinto_id: Optional[int] = None
    recinto: Optional[str] = None
    activa: bool = True
    fase: Literal["monofasica", "bifasica", "trifasica", "L1", "L2", "L3"] = "monofasica"
    factor_potencia: float = 0.93


class RicRequest(BaseModel):
    """Petición para calcular carga RIC sobre una lista de recintos."""
    tipo_proyecto: TipoProyecto = "vivienda"
    recintos: List[dict] = Field(..., description="Lista de recintos con: id, nombre, uso, area_m2")
    cargas_dedicadas: List[CargaDedicadaCalculada] = []
    conexion: str = "monofasica_220"
    factor_potencia: float = 0.93
    aplicar_dedicadas_por_defecto: bool = True


class RicResult(BaseModel):
    """Resultado del cálculo RIC."""
    tipo_proyecto: TipoProyecto
    area_total_m2: float
    n_recintos: int

    # Cargas por recinto (alumbrado + enchufes generales)
    recintos_carga: List[RecintoCarga]
    subtotal_recintos_w: float

    # Cargas dedicadas (cocina, calefón, etc.)
    cargas_dedicadas: List[CargaDedicadaCalculada]
    subtotal_dedicadas_w: float

    # Cálculos consolidados
    carga_total_instalada_w: float       # Suma cruda de todo
    factor_demanda: float
    carga_diversificada_w: float          # Carga × factor de demanda
    factor_simultaneidad: float
    demanda_maxima_w: float               # Carga diversificada × simultaneidad

    # Sugerencias eléctricas
    corriente_nominal_a: float
    tipo_empalme_sugerido: str
    conexion: str
    factor_potencia: float

    # Para el módulo FV que sigue:
    consumo_mensual_estimado_kwh: float   # Estimación según perfil de uso
    consumo_anual_estimado_kwh: float

    # Balance de fases (solo aplica si conexion = trifasica_380)
    carga_L1_w: float = 0
    carga_L2_w: float = 0
    carga_L3_w: float = 0
    corriente_L1_a: float = 0
    corriente_L2_a: float = 0
    corriente_L3_a: float = 0
    desbalance_fases_pct: float = 0       # |L_max - L_min| / L_max × 100

    advertencias: List[str] = []
