"""Modelos Pydantic del módulo DIMENSIONAMIENTO FV + ECONÓMICO."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


TipoSistema = Literal[
    "on_grid",                  # Conectado a red sin baterías
    "on_grid_bess",             # Conectado a red con baterías
    "off_grid",                 # Aislado
    "hibrido_red",              # Solar + red + baterías
    "hibrido_generador",        # Solar + generador + baterías
    "autoconsumo_inyeccion",    # Con netbilling activo
    "peak_shaving",             # Reducción demanda punta
]


class FvRequest(BaseModel):
    # Inputs del proyecto (vienen del módulo RIC y del módulo TERRENO)
    consumo_anual_kwh: float
    consumo_mensual_kwh: List[float] = Field(..., description="12 valores")
    demanda_maxima_kw: float

    # Recurso solar (del módulo TERRENO)
    E_y_kwh_por_kwp: float                   # Generación anual PVGIS por kWp
    H_y_kwh_m2: float                         # Irradiación plano inclinado
    monthly_E_kwh_por_kwp: List[float]        # 12 valores PVGIS
    monthly_t_amb_c: List[float]              # 12 valores NASA
    altitud_msnm: float

    # Parámetros de diseño (editables)
    tipo_sistema: TipoSistema = "on_grid"
    cobertura_objetivo: float = Field(0.70, ge=0.05, le=1.0)
    DC_AC_ratio: float = Field(1.20, ge=1.0, le=1.5)
    panel_Pnom_w: float = 550
    panel_area_m2: float = 2.58
    coef_temp_pmp: float = -0.30
    NOCT: float = 45
    superficie_disponible_m2: Optional[float] = None
    capacidad_bess_kwh: float = 0
    dias_autonomia: float = 0
    tarifa_clp_kwh: float = 220
    tipo_proyecto: str = "vivienda"           # Para escoger defaults económicos
    # Criterios de continuidad operacional
    cargas_criticas_pct: float = Field(0.30, ge=0, le=1, description="Fracción del consumo total que es crítica y debe respaldarse con BESS")
    profundidad_descarga: float = Field(0.90, ge=0.5, le=1.0, description="DoD máxima de la batería (1.0 = 100%, típico LFP)")
    eficiencia_round_trip: float = Field(0.95, ge=0.7, le=1.0, description="Eficiencia carga-descarga de la batería")
    horas_consumo_critico_dia: float = Field(12, ge=1, le=24, description="Horas/día que las cargas críticas están activas")

    # Pérdidas editables (fracción 0..1)
    perdida_suciedad: float = 0.03
    perdida_cableado_dc: float = 0.015
    perdida_cableado_ac: float = 0.010
    perdida_inversor: float = 0.025
    perdida_mismatch: float = 0.02
    perdida_sombras: float = 0.03
    perdida_disponibilidad: float = 0.01


class PerdidaItem(BaseModel):
    nombre: str
    pct: float


class FvResult(BaseModel):
    # Dimensionamiento principal
    P_kwp: float
    N_paneles: int
    superficie_m2: float
    inversor_P_AC_kw: float
    inversor_modelo: str

    # Pérdidas detalladas
    PR_anual: float
    perdidas: List[PerdidaItem]
    L_temperatura_pct: float
    T_celda_promedio_c: float

    # Generación
    generacion_anual_kwh: float
    generacion_mensual_kwh: List[float]
    factor_planta: float
    cobertura_real: float

    # Balance energético
    autoconsumo_kwh: float
    inyeccion_kwh: float
    compra_red_kwh: float

    # BESS (si aplica) — dimensionado según criterios de autonomía
    bess_modelo: Optional[str] = None
    bess_capacidad_kwh: float = 0          # Nominal del banco completo
    bess_capacidad_util_kwh: float = 0     # Capacidad × DoD (energía realmente usable)
    bess_potencia_kw: float = 0
    bess_dias_autonomia_real: float = 0    # Días que cubre con cargas críticas
    bess_consumo_critico_diario_kwh: float = 0
    bess_criterio_dimensionamiento: str = ""  # Texto explicando cómo se calculó

    # Compatibilidad / advertencias
    cabe_en_superficie: bool
    advertencias: List[str] = []


class EconomicResult(BaseModel):
    # CAPEX
    capex_total_clp: float
    capex_desglose: dict                       # {paneles, inversor, estructura, ...}
    capex_unitario_usd_kwp: float
    tipo_cambio: float

    # Operación
    opex_anual_clp: float
    ahorro_anual_clp: float
    ingreso_inyeccion_clp: float
    ahorro_total_anual_clp: float

    # Métricas
    payback_simple_anios: float
    payback_descontado_anios: Optional[float]
    VAN_clp: float
    TIR_pct: Optional[float]
    LCOE_clp_kwh: float

    # Flujo de caja
    horizonte_anios: int
    tasa_descuento: float
    flujo_caja_anual_clp: List[float]
    flujo_acumulado_clp: List[float]

    # Ambiental
    CO2_evitado_anual_kg: float
    CO2_evitado_total_kg: float


class FvFullResult(BaseModel):
    fv: FvResult
    economic: EconomicResult
