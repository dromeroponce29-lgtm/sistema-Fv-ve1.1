# Protocolo de Auditoría del Motor FV

> **Cómo se activa:** cuando Daniel le diga al asistente "audita el motor FV",
> "revisa el análisis", "haz auditoría", o presente un proyecto pidiendo verificación.
>
> **Modo por defecto: PASIVO** — sólo entrega informe escrito con hallazgos y
> recomendaciones. Para aplicar cambios el usuario debe pedirlo explícitamente:
> "aplica las recomendaciones 2, 5 y 7" o "arregla el punto X".

---

## Paso 0 — Contexto antes de auditar

Antes de empezar:

1. Confirmar la **versión actual del motor** leyendo `git log --oneline -5`.
2. Identificar si la auditoría es:
   - **Sobre un proyecto específico** (Daniel pidió "audita este proyecto") → cargar
     el JSON del proyecto en `localStorage` (`fv-chile-proyectos-v1`) o pedirle al
     usuario que lo exporte y pegue.
   - **Sobre el motor en general** (Daniel pidió "audita el código") → revisar
     los servicios en `app/services/`.

---

## Paso 1 — Checklist por módulo

Recorrer en este orden, anotando hallazgos. Asignar severidad: 🔴 Bloqueante ·
🟠 Importante · 🟡 Mejora · 🟢 Observación.

### 1.1. Módulo RIC (`app/services/ric_loads.py`)

- [ ] **Factor de demanda**: ¿es coherente con tipo de proyecto y tamaño? Vivienda
      <60 m² debería tener fd ≈ 1.0; >300 m² fd ≈ 0.45. Hotel 0.65–0.75. Industria 0.85–0.95.
- [ ] **Factor de simultaneidad**: vivienda 0.6–0.7 · oficina 0.75 · industria 0.85–0.90.
- [ ] **Cargas dedicadas**: si `aplicar_dedicadas_por_defecto=True` y tipo vivienda,
      ¿están las cargas mínimas (cocina, calefón, ducha eléctrica, lavadora)?
- [ ] **Balance de fases (trifásico)**: ¿desbalance < 15%? Si no, advertencia presente.
- [ ] **Corriente nominal**: I = P / (V × fp) monofásico · I = P / (√3 × V × fp) trifásico.
- [ ] **Empalme sugerido**: ¿la escala IEC está respetada (10, 16, 20, 25, 32, 40, ...)?

### 1.2. Módulo FV (`app/services/pv_sizing.py`)

- [ ] **PR (Performance Ratio)**: producto de (1−L_i) de 8 pérdidas. PR ∈ [0.70, 0.86].
      Si PR < 0.70 → revisar pérdidas individuales (suciedad, sombras, mismatch).
- [ ] **Pérdida por temperatura**: L_temp = |coef × (T_celda − 25)|. Cap a 20%.
      T_celda = T_amb + (NOCT−20)/800 × G − corrección altitud.
- [ ] **Doble conteo PVGIS↔PR**: PVGIS aplica PR ≈ 0.86 interno → dividir antes de
      reaplicar PR detallado. ¿Está dividiendo por `PR_PVGIS_REF = 0.86`?
- [ ] **Potencia kWp**: `P = consumo_anual × cobertura_obj / (E_y × PR_efectivo)`.
- [ ] **Restricción de superficie**: si `superficie_disponible_m2` < calculada → ajustar
      paneles y advertir.
- [ ] **Cobertura real**: cobertura_real = autoconsumo / consumo_anual. ¿Recalculada
      tras ajuste por superficie?
- [ ] **Factor de planta**: FP = generación_anual / (P_kwp × 8760). Típicamente 0.18–0.22 en Chile.

### 1.3. Módulo BESS (`app/services/pv_sizing.py` sección BESS)

- [ ] **Capacidad útil**: `útil = nominal × DoD × η_RT`. DoD para LFP = 0.90–1.0;
      η_RT = 0.93–0.97.
- [ ] **Días autonomía real**: `dias_aut = útil / cons_critico_diario`.
- [ ] **Cargas críticas**: `cons_critico = consumo_anual × cargas_criticas_pct / 365`.
- [ ] **Advertencia crítica**: si off-grid y autonomía < 1 día → advertencia presente.

### 1.4. Módulo Respaldo (`app/services/pv_sizing.py:_dimensionar_respaldo`)

- [ ] **5 casos cubiertos**: off-grid+generador · off-grid puro · on-grid+empalme reducido
      · on-grid+generador · on-grid empalme completo.
- [ ] **Generador diésel**: escala kVA comercial respetada [5, 10, 15, 20, 30, 50, 75,
      100, 150, 200, 250, 350, 500]. Consumo 0.27 L/kWh · diésel 1280 CLP/L.
- [ ] **CAPEX generador**: ~$550 USD/kVA.
- [ ] **Empalme reducido**: `P_emp = max(demanda − P_FV×0.6, demanda×0.5)`.

### 1.5. Módulo Layout (`app/services/layout.py`)

- [ ] **Polígono útil**: `poly.buffer(-retiro)`. Si retiro > radio inscrito → vacío + advertencia.
- [ ] **Pitch entre filas**: `pitch = ancho × (cos β + sin β / tan α)` con α = altura solar
      crítica 21-jun. Cap inferior α = 15°.
- [ ] **Packing**: rectángulo del panel debe ser `poly_util.contains(rect)`, no `intersects`.
- [ ] **Aprovechamiento**: razonable 35–65%. Si > 80% → revisar si los retiros se aplican
      correctamente.

### 1.6. Módulo Tarifas Chile (`app/services/tarifas_chile.py`)

- [ ] **Categorías**: BT1 ≤ 10 kW · BT2 10–300 kW · BT4_punta industriales.
- [ ] **Cargo fijo BT1**: ~$1.800 CLP/mes (actualizable trimestralmente).
- [ ] **Cargo variable BT1**: ~$165 CLP/kWh.
- [ ] **Cargo por potencia BT2**: $4.200 CLP/kW-mes.
- [ ] **Escalas IEC**: mono [10,16,20,25,32,40], tri [10,16,20,...,400]. ¿Coinciden con
      pliego SEC vigente?

### 1.7. Módulo Comparativa Escenarios (`app/services/comparativa_escenarios.py`)

- [ ] **3 escenarios dimensionados**: A (BESS gigante 100% autonomía) · B (BESS chico
      1 día crítico + empalme mono) · C (on-grid netbilling).
- [ ] **TCO 25 años**: `TCO = CAPEX + VP(OPEX) + VP(reemplazo BESS año 12)`. Tasa 8%.
- [ ] **CAPEX FV**: ~$850 USD/kWp. BESS LFP: ~$320 USD/kWh nominal.
- [ ] **Empalme mono escenario B**: limitado a 8.5 kW (límite BT1).
- [ ] **Netbilling ingreso**: ~$75 CLP/kWh inyectado (precio energía).
- [ ] **Recomendación**: `min(TCO)`. ¿Explicación del ganador presente?

### 1.8. Módulo Reportes (`app/services/report_pdf.py`, `report_word.py`)

- [ ] **Filtro de secciones**: cada sección consulta `seccion_incluida(proyecto, key)`.
- [ ] **Catálogo sincronizado**: `report_sections.py:SECCIONES_DISPONIBLES` debe
      coincidir con `SECCIONES_REPORTE` del frontend.
- [ ] **Presets**: cliente_final · tecnico_sec · presupuesto_comercial. ¿Hay overlap
      en las claves?

### 1.9. Frontend `app_fv_chile.html`

- [ ] **Backend indicator**: ¿funciona en producción Render?
- [ ] **Persistencia localStorage**: proyectos, plano parseado, layout sobre plano,
      selección de secciones.
- [ ] **JS válido**: probar con `node --check` después de cualquier edición.
- [ ] **Compatibilidad navegadores**: Chrome/Firefox/Safari última versión.

---

## Paso 2 — Completitud del estudio

Verificar que el análisis para un proyecto típico incluye:

- [ ] Caracterización del sitio (latitud, longitud, altitud, recurso solar PVGIS+NASA)
- [ ] Cargas RIC (recintos, dedicadas, factor demanda, simultaneidad, demanda máxima)
- [ ] Empalme sugerido y categoría tarifaria (BT1/BT2/BT4)
- [ ] Balance de fases (si trifásico)
- [ ] Dimensionamiento FV (P_kWp, paneles, inversor, pérdidas, PR, factor planta)
- [ ] Generación mensual y cobertura solar
- [ ] BESS si aplica (capacidad, autonomía, criterio)
- [ ] Respaldo si aplica (generador o empalme reducido/completo)
- [ ] Layout físico (con plano real si está disponible, sino rectángulo abstracto)
- [ ] Diagrama unifilar (protecciones DC, AC, puesta a tierra)
- [ ] CAPEX desglosado (8 partidas mínimo)
- [ ] OPEX anual (mantención + tarifa eléctrica residual)
- [ ] Flujo de caja 25 años con degradación y reposición de inversor
- [ ] Métricas: VAN, TIR, payback simple y descontado, LCOE
- [ ] Comparativa de escenarios A/B/C
- [ ] Análisis tarifario del empalme recomendado
- [ ] Impacto ambiental (CO₂ evitado)
- [ ] Cumplimiento normativo (Ley 21.118, RIC SEC, TE-1)
- [ ] Advertencias y disclaimers

---

## Paso 3 — Casos límite a probar manualmente

Si la auditoría es del motor en general (no de un proyecto), verificar:

1. **Vivienda chica (50 m²)**: ¿factor demanda → 1.0? ¿FV ≈ 2 kWp?
2. **Edificio 5000 m²**: ¿FV escalado correctamente sin error de memoria?
3. **Empalme monofásico al límite (8.5 kW)**: ¿se detecta y advierte cambio a trifásico?
4. **Off-grid con BESS < 1 día autonomía**: ¿advertencia crítica presente?
5. **Layout con polígono cóncavo (techo en L)**: ¿packing respeta la concavidad?
6. **Comparativa cuando A < B < C**: ¿recomienda A correctamente?
7. **Tarifa con consumo cero**: ¿manejo de división por cero?
8. **Plano sin recintos**: ¿manejo gracioso?

---

## Paso 4 — Formato del informe de auditoría

Cuando entregues los hallazgos a Daniel, usa este formato:

```
# Informe de Auditoría FV — [fecha]
## Resumen
[2-3 líneas: estado general, # hallazgos por severidad]

## Hallazgos por severidad

### 🔴 Bloqueantes
1. [Hallazgo] (módulo: archivo.py:línea)
   - Impacto: [qué se rompe o calcula mal]
   - Recomendación: [cómo arreglarlo]

### 🟠 Importantes
[ídem]

### 🟡 Mejoras
[ídem]

### 🟢 Observaciones
[ídem]

## Tests pytest ejecutados
[N pasados / M total — ver tests/test_motor_fv.py]

## Para aplicar arreglos
Dime "aplica las recomendaciones X, Y, Z" y los aplico en sesión.
```

---

## Paso 5 — Modo activo (aplicar correcciones)

Si Daniel autoriza explícitamente ("aplica X", "arregla el punto Y", "implementa
la recomendación 3"):

1. Editar el archivo correspondiente con `Edit`/`Write`.
2. Re-validar sintaxis (`python3 -c "import ast; ast.parse(...)"`, `node --check`).
3. Re-ejecutar el test correspondiente de la suite.
4. Reportar resultado: "✓ aplicado · tests pasan" o "✗ tests fallan, rollback".
