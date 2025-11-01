# 🔍 CÓMO EL BOT ANALIZA LOS MERCADOS

## 📊 PROCESO COMPLETO DE ANÁLISIS

### 1️⃣ OBTENCIÓN DE DATOS DEL MERCADO

```python
# El bot obtiene datos históricos desde Quotex
df = await market_manager.obtener_datos_mercado('EURUSD')

# Datos que obtiene (últimas 50+ velas):
{
    'open': [1.08500, 1.08520, ...],    # Precio de apertura
    'high': [1.08550, 1.08580, ...],    # Precio máximo
    'low': [1.08480, 1.08500, ...],     # Precio mínimo
    'close': [1.08520, 1.08560, ...],   # Precio de cierre
    'timestamp': [...]                   # Marca de tiempo
}
```

**Requisitos:**
- ✅ Mínimo 50 velas históricas
- ✅ Datos en tiempo real desde Quotex
- ✅ Timeframe: 1 minuto (M1)

---

### 2️⃣ CÁLCULO DE INDICADORES TÉCNICOS

El bot calcula 4 indicadores principales:

#### 📈 A. EMA 36 (Media Móvil Exponencial Rápida)

```python
def calcular_ema(df, periodo=36):
    return df['close'].ewm(span=36, adjust=False).mean()

# Ejemplo:
# Precio actual: 1.08520
# EMA36: 1.08530 (promedio ponderado de últimos 36 cierres)
```

**¿Qué indica?**
- Sigue el precio de cerca
- Reacciona rápido a cambios
- Muestra tendencia a corto plazo

---

#### 📉 B. EMA 50 (Media Móvil Exponencial Lenta)

```python
def calcular_ema(df, periodo=50):
    return df['close'].ewm(span=50, adjust=False).mean()

# Ejemplo:
# Precio actual: 1.08520
# EMA50: 1.08480 (promedio ponderado de últimos 50 cierres)
```

**¿Qué indica?**
- Sigue el precio más lento
- Filtra ruido del mercado
- Muestra tendencia a medio plazo

---

#### 🎯 C. AROON (Indicador de Tendencia)

```python
def calcular_aroon(df, periodo=14):
    # Para cada vela:
    # 1. Busca el máximo más reciente en últimas 14 velas
    # 2. Busca el mínimo más reciente en últimas 14 velas
    
    # Aroon UP = 100 * (14 - períodos desde último máximo) / 14
    # Aroon DOWN = 100 * (14 - períodos desde último mínimo) / 14
    
    return aroon_up, aroon_down

# Ejemplo:
# Último máximo fue hace 2 velas
# Aroon UP = 100 * (14 - 2) / 14 = 85.7%
# 
# Último mínimo fue hace 10 velas
# Aroon DOWN = 100 * (14 - 10) / 14 = 28.6%
```

**¿Qué indica?**
- **Aroon UP alto (>70%)**: Tendencia alcista fuerte
- **Aroon DOWN alto (>70%)**: Tendencia bajista fuerte
- **Ambos bajos (<50%)**: Mercado lateral/consolidación

---

#### 📊 D. ATR (Average True Range - Volatilidad)

```python
def calcular_atr(df, periodo=14):
    # Calcula el rango verdadero de cada vela:
    # TR = max(high - low, |high - close_anterior|, |low - close_anterior|)
    
    # ATR = promedio de TR de últimas 14 velas
    return atr

# Ejemplo:
# ATR = 0.00050 (50 pips)
# Indica volatilidad normal del mercado
```

**¿Qué indica?**
- ATR alto: Mercado volátil (movimientos grandes)
- ATR bajo: Mercado tranquilo (movimientos pequeños)
- Se usa para calcular distancia de rebote en EMAs

---

### 3️⃣ DETECCIÓN DE TENDENCIA

```python
# Análisis de posición de EMAs
precio_actual = 1.08520
ema36_actual = 1.08530
ema50_actual = 1.08480

# TENDENCIA ALCISTA
if ema36_actual > ema50_actual:
    tendencia = "ALCISTA"
    # EMA rápida está por encima de EMA lenta
    # Indica que el precio está subiendo

# TENDENCIA BAJISTA
elif ema36_actual < ema50_actual:
    tendencia = "BAJISTA"
    # EMA rápida está por debajo de EMA lenta
    # Indica que el precio está bajando

# LATERAL
else:
    tendencia = "LATERAL"
    # EMAs muy juntas o cruzándose
```

**Visualización:**
```
ALCISTA:
Precio: ━━━━━━━━━━━━━━━━━ 1.08520
EMA36:  ━━━━━━━━━━━━━━━━━ 1.08530 ⬆️
EMA50:  ━━━━━━━━━━━━━━━━━ 1.08480

BAJISTA:
Precio: ━━━━━━━━━━━━━━━━━ 1.08520
EMA36:  ━━━━━━━━━━━━━━━━━ 1.08470 ⬇️
EMA50:  ━━━━━━━━━━━━━━━━━ 1.08530
```

---

### 4️⃣ DETECCIÓN DE SEÑALES DE ENTRADA

El bot busca **3 tipos de patrones**:

#### 🔄 TIPO 1: CRUCE DE EMAs

```python
# Compara posición actual vs anterior
ema36_anterior = 1.08470
ema50_anterior = 1.08480
ema36_actual = 1.08490
ema50_actual = 1.08480

# CRUCE ALCISTA (Golden Cross)
if ema36_anterior <= ema50_anterior and ema36_actual > ema50_actual:
    señal = "CALL"
    # EMA36 acaba de cruzar HACIA ARRIBA de EMA50
    
# CRUCE BAJISTA (Death Cross)
if ema36_anterior >= ema50_anterior and ema36_actual < ema50_actual:
    señal = "PUT"
    # EMA36 acaba de cruzar HACIA ABAJO de EMA50
```

**Confirmaciones adicionales:**
- ✅ Aroon confirma la dirección (>70%)
- ✅ Vela anterior es del mismo color que la señal

**Ejemplo Real:**
```
Vela -2:
  EMA36: 1.08470
  EMA50: 1.08480  (EMA36 por debajo)

Vela -1:
  EMA36: 1.08490
  EMA50: 1.08480  (¡CRUCE! EMA36 cruzó arriba)
  Vela: Verde ✅
  Aroon UP: 85% ✅

→ SEÑAL CALL (Compra)
```

---

#### 🎾 TIPO 2: REBOTE EN EMAs

```python
# El precio toca una EMA y rebota
precio_bajo_anterior = 1.08460
ema36_actual = 1.08470
atr_actual = 0.00050

# Calcular distancia de "toque"
touch_distance = atr_actual * 0.5  # 0.00025 (25 pips)

# REBOTE ALCISTA
if precio_bajo_anterior <= ema36_actual + touch_distance:
    # Precio tocó o se acercó mucho a EMA36
    if tendencia == "ALCISTA" and vela_anterior_verde:
        señal = "CALL"
        # Precio rebotó en soporte (EMA)

# REBOTE BAJISTA
if precio_alto_anterior >= ema36_actual - touch_distance:
    # Precio tocó o se acercó mucho a EMA36
    if tendencia == "BAJISTA" and vela_anterior_roja:
        señal = "PUT"
        # Precio rebotó en resistencia (EMA)
```

**Confirmaciones adicionales:**
- ✅ Tendencia confirmada (alcista o bajista)
- ✅ Aroon confirma (>70%)
- ✅ Vela rebota en dirección de la tendencia

**Ejemplo Real:**
```
Tendencia: ALCISTA
EMA36: 1.08470

Vela -1:
  Low: 1.08465 (tocó EMA36) ✅
  Close: 1.08490 (rebotó arriba) ✅
  Color: Verde ✅
  Aroon UP: 78% ✅

→ SEÑAL CALL (Compra)
```

---

#### 📊 TIPO 3: DOS VELAS CONSECUTIVAS

```python
# Busca momentum fuerte (2 velas del mismo color)

# MOMENTUM ALCISTA
vela_anterior2 = "Verde"
vela_anterior1 = "Verde"

if vela_anterior2 == "Verde" and vela_anterior1 == "Verde":
    if tendencia == "ALCISTA" and aroon_up > 70:
        señal = "CALL"
        # 2 velas verdes seguidas en tendencia alcista

# MOMENTUM BAJISTA
vela_anterior2 = "Roja"
vela_anterior1 = "Roja"

if vela_anterior2 == "Roja" and vela_anterior1 == "Roja":
    if tendencia == "BAJISTA" and aroon_down > 70:
        señal = "PUT"
        # 2 velas rojas seguidas en tendencia bajista
```

**Confirmaciones adicionales:**
- ✅ Tendencia confirmada
- ✅ Aroon fuerte (>70%)
- ✅ Ambas velas del mismo color

**Ejemplo Real:**
```
Tendencia: ALCISTA

Vela -2:
  Open: 1.08450
  Close: 1.08480 (Verde) ✅

Vela -1:
  Open: 1.08480
  Close: 1.08510 (Verde) ✅

Aroon UP: 82% ✅

→ SEÑAL CALL (Compra)
```

---

### 5️⃣ CÁLCULO DE EFECTIVIDAD

```python
efectividad = 50  # Base inicial

# BONUS 1: Tendencia Clara (+15%)
diferencia_emas = abs(ema36 - ema50) / ema50 * 100
if diferencia_emas > 0.1:  # EMAs separadas
    efectividad += min(diferencia_emas * 10, 15)
    # Máximo +15%

# BONUS 2: Aroon Fuerte (+15%)
diferencia_aroon = abs(aroon_up - aroon_down)
if diferencia_aroon > 40:  # Aroon claro
    efectividad += min(diferencia_aroon / 5, 15)
    # Máximo +15%

# BONUS 3: Tipo de Señal
if es_cruce_emas:
    efectividad += 10  # +10% por cruce
elif es_rebote:
    efectividad += 8   # +8% por rebote
elif es_velas_consecutivas:
    efectividad += 5   # +5% por velas

# LÍMITE
efectividad = min(efectividad, 100)  # Máximo 100%
```

**Ejemplo de Cálculo:**
```
Base: 50%

Tendencia clara:
  EMA36: 1.08530
  EMA50: 1.08480
  Diferencia: 0.046%
  Bonus: +4.6% → +5%

Aroon fuerte:
  Aroon UP: 85%
  Aroon DOWN: 15%
  Diferencia: 70%
  Bonus: 70/5 = 14%

Cruce de EMAs:
  Bonus: +10%

TOTAL: 50 + 5 + 14 + 10 = 79%
```

---

### 6️⃣ DECISIÓN FINAL

```python
# Solo envía señal si efectividad ≥ 75%
umbral_minimo = 75

if efectividad >= umbral_minimo:
    if señal_alcista and not señal_bajista:
        decision = "CALL"
        enviar_señal()
    elif señal_bajista and not señal_alcista:
        decision = "PUT"
        enviar_señal()
else:
    # Efectividad insuficiente
    descartar_señal()
    esperar_siguiente_analisis()
```

---

## 📊 EJEMPLO COMPLETO DE ANÁLISIS

### Datos del Mercado: EURUSD

```
Últimas 3 velas (M1):

Vela -3:
  Open: 1.08450
  High: 1.08470
  Low: 1.08440
  Close: 1.08460
  Color: Verde

Vela -2:
  Open: 1.08460
  High: 1.08490
  Low: 1.08455
  Close: 1.08480
  Color: Verde

Vela -1:
  Open: 1.08480
  High: 1.08520
  Low: 1.08475
  Close: 1.08510
  Color: Verde

Precio Actual: 1.08520
```

### Indicadores Calculados

```
EMA36: 1.08530
EMA50: 1.08480
Diferencia: +0.046% (EMA36 > EMA50)

Aroon UP: 85.7%
Aroon DOWN: 14.3%
Diferencia: 71.4%

ATR: 0.00050 (50 pips)
```

### Análisis de Tendencia

```
✅ TENDENCIA: ALCISTA
   (EMA36 > EMA50)

✅ AROON CONFIRMA: Alcista
   (Aroon UP > 70%)

✅ MOMENTUM: Fuerte
   (2 velas verdes consecutivas)
```

### Detección de Señales

```
❌ Cruce de EMAs: NO
   (No hubo cruce reciente)

❌ Rebote en EMA: NO
   (Precio no tocó EMAs)

✅ 2 Velas Consecutivas: SÍ
   Vela -2: Verde ✅
   Vela -1: Verde ✅
   Tendencia: Alcista ✅
   Aroon UP: 85.7% ✅
```

### Cálculo de Efectividad

```
Base: 50%

Tendencia clara:
  Diferencia EMAs: 0.046%
  Bonus: +5%

Aroon fuerte:
  Diferencia: 71.4%
  Bonus: +14%

Velas consecutivas:
  Bonus: +5%

TOTAL: 50 + 5 + 14 + 5 = 74%
```

### Decisión

```
❌ Efectividad: 74%
❌ Umbral mínimo: 75%
❌ SEÑAL DESCARTADA

Motivo: Efectividad insuficiente (74% < 75%)
Acción: Esperar siguiente análisis
```

---

## 🔄 FRECUENCIA DE ANÁLISIS

```
El bot analiza el mercado:
• Cada 20-40 minutos (variable)
• Entre 8:00 AM - 8:00 PM
• Lunes a Sábado
• Objetivo: 20-25 señales por día
```

---

## 📈 RESUMEN DEL PROCESO

```
1. Obtener datos (50+ velas)
   ↓
2. Calcular indicadores (EMA36, EMA50, Aroon, ATR)
   ↓
3. Detectar tendencia (Alcista/Bajista/Lateral)
   ↓
4. Buscar patrones:
   • Cruce de EMAs
   • Rebote en EMAs
   • 2 velas consecutivas
   ↓
5. Calcular efectividad (50-100%)
   ↓
6. ¿Efectividad ≥ 75%?
   ├─ SÍ → Generar señal CALL/PUT
   └─ NO → Descartar y esperar
```

---

**✅ El bot analiza el mercado de forma sistemática usando múltiples indicadores y confirmaciones para generar señales de alta calidad**
