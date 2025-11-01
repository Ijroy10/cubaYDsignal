# 📊 CÓMO FUNCIONA EL BOT DE SEÑALES AROON

## 🎯 1. ANÁLISIS DEL MERCADO

### **Estrategia: EMA 50/36 + AROON**

El bot analiza el mercado usando una estrategia técnica que combina:

#### **Indicadores Principales:**

1. **EMA 36 y EMA 50** (Medias Móviles Exponenciales)
   - EMA 36: Media rápida
   - EMA 50: Media lenta
   - Detecta tendencias y cruces

2. **Indicador AROON** (período 14)
   - **Aroon Up**: Mide la fuerza alcista (0-100%)
   - **Aroon Down**: Mide la fuerza bajista (0-100%)
   - Umbral: 70% para confirmar tendencia

3. **ATR** (Average True Range)
   - Mide la volatilidad del mercado
   - Ayuda a detectar rebotes en EMAs

#### **Tipos de Señales que Detecta:**

**A) CRUCE DE EMAs** (Efectividad +10%)
```
SEÑAL CALL (Alcista):
- EMA 36 cruza por encima de EMA 50
- Aroon Up > 70% y Aroon Up > Aroon Down
- Vela anterior alcista (cierre > apertura)

SEÑAL PUT (Bajista):
- EMA 36 cruza por debajo de EMA 50
- Aroon Down > 70% y Aroon Down > Aroon Up
- Vela anterior bajista (cierre < apertura)
```

**B) REBOTE EN EMAs** (Efectividad +8%)
```
SEÑAL CALL:
- Precio toca EMA 36 o EMA 50 desde abajo
- Tendencia alcista confirmada (EMA 36 > EMA 50)
- Aroon Up > 70%
- Vela anterior alcista

SEÑAL PUT:
- Precio toca EMA 36 o EMA 50 desde arriba
- Tendencia bajista confirmada (EMA 36 < EMA 50)
- Aroon Down > 70%
- Vela anterior bajista
```

**C) 2 VELAS CONSECUTIVAS** (Efectividad +5%)
```
SEÑAL CALL:
- 2 velas alcistas consecutivas
- Tendencia alcista confirmada
- Aroon Up > 70%

SEÑAL PUT:
- 2 velas bajistas consecutivas
- Tendencia bajista confirmada
- Aroon Down > 70%
```

#### **Cálculo de Efectividad:**

```python
Efectividad Base = 50%

Bonus por tendencia clara:
+ Hasta 15% (según diferencia entre EMAs)

Bonus por Aroon fuerte:
+ Hasta 15% (según diferencia Aroon Up vs Down)

Bonus por tipo de señal:
+ 10% si es cruce de EMAs
+ 8% si es rebote en EMA
+ 5% si son 2 velas consecutivas

Efectividad Máxima = 100%
Efectividad Mínima para señal = 75%
```

#### **Proceso de Análisis:**

```
1. Obtener datos históricos (mínimo 50 velas)
2. Calcular EMA 36, EMA 50, Aroon Up/Down, ATR
3. Analizar últimas 3 velas
4. Detectar tendencia actual
5. Buscar patrones de entrada (cruce, rebote, velas)
6. Calcular efectividad
7. Si efectividad >= 75% → Generar señal
8. Si efectividad < 75% → Descartar
```

---

## 📤 2. ENVÍO DE SEÑALES POR TELEGRAM

### **Flujo de Envío:**

```
┌─────────────────────────────────────┐
│  1. Análisis detecta señal válida   │
│     (Efectividad >= 75%)             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. Generar mensaje formateado      │
│     - Número de señal                │
│     - Mercado y dirección            │
│     - Efectividad                    │
│     - Detalles técnicos              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. Enviar a TODOS los usuarios     │
│     activos (no bloqueados)          │
│                                      │
│     Mensaje: "¿Deseas recibir       │
│              esta señal?"            │
│                                      │
│     Botones: [✅ Aceptar] [❌ Rechazar]│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. Usuario presiona botón          │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
   ✅ ACEPTAR      ❌ RECHAZAR
       │               │
       │               └──> Mensaje: "Señal rechazada"
       │
       ▼
┌─────────────────────────────────────┐
│  5. Mostrar SEÑAL COMPLETA          │
│                                      │
│  🎯 SEÑAL #X - CALL/PUT             │
│  💱 Mercado: EURUSD_OTC             │
│  ⏰ Hora: 14:35:20                  │
│  📊 Efectividad: 85.3%              │
│  ⏱️ Temporalidad: 5M                │
│                                      │
│  📈 ANÁLISIS TÉCNICO:               │
│  • EMA 36: 1.08523                  │
│  • EMA 50: 1.08456                  │
│  • Aroon Up: 85.7%                  │
│  • Aroon Down: 21.4%                │
│  • Tendencia: ALCISTA               │
│  • Tipo: Cruce de EMAs              │
│                                      │
│  ⏰ VÁLIDA POR 5 MINUTOS            │
└─────────────────────────────────────┘
```

### **Características del Sistema de Señales:**

1. **Sin Pre-Señales**: Las señales se envían directamente (antes había pre-avisos)

2. **Confirmación Obligatoria**: El usuario debe aceptar para ver los detalles

3. **Caducidad**: Las señales expiran después de 5 minutos

4. **Registro**: Todas las señales se guardan en el historial del día

5. **Verificación Automática**: Después de 5 minutos, el bot verifica el resultado

---

## 🤖 3. TRADING AUTOMÁTICO EN QUOTEX

### **Configuración del Trading Automático:**

El admin puede activar el trading automático con estos parámetros:

```
/trading
├─ Modo: DEMO o REAL
├─ Monto: $1 - $10,000
└─ Límite diario: 1-50 operaciones
```

### **Flujo de Ejecución Automática:**

```
┌─────────────────────────────────────┐
│  1. Señal generada y enviada        │
│     a usuarios                       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. ¿Trading automático activo?     │
└──────────────┬──────────────────────┘
               │
               ▼ SÍ
┌─────────────────────────────────────┐
│  3. Validar condiciones:             │
│     ✓ Conexión a Quotex activa      │
│     ✓ Efectividad >= umbral (80%)   │
│     ✓ Límite diario no alcanzado    │
│     ✓ Monto configurado válido      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. Cambiar cuenta (DEMO/REAL)      │
│     await quotex.change_account()    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  5. Ejecutar operación:              │
│                                      │
│     await quotex.buy(                │
│         amount = monto,              │
│         asset = "EURUSD_otc",        │
│         direction = "call",          │
│         duration = 300  # 5 min     │
│     )                                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  6. ¿Operación exitosa?             │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼ SÍ            ▼ NO
   ✅ ÉXITO        ❌ ERROR
       │               │
       │               └──> Notificar admin
       │
       ▼
┌─────────────────────────────────────┐
│  7. Guardar información:             │
│     - Order ID                       │
│     - Monto                          │
│     - Símbolo                        │
│     - Dirección                      │
│     - Modo (DEMO/REAL)               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  8. Notificar admin:                 │
│                                      │
│     ✅ Operación Ejecutada           │
│     • Modo: REAL                     │
│     • Symbol: EURUSD_OTC             │
│     • Dirección: CALL                │
│     • Monto: $10.00                  │
│     • Efectividad: 85.3%             │
│     • Order ID: 123456789            │
│     • Duración: 5 minutos            │
│                                      │
│     ⏰ Resultado en 5 minutos        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  9. Esperar 5 minutos                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  10. Verificar resultado:            │
│      - Ganancia → Resetear Martingala│
│      - Pérdida → Activar Martingala  │
└─────────────────────────────────────┘
```

### **Sistema de Martingala:**

Cuando una operación pierde, el bot puede ejecutar **1 Martingala** automática:

```
Operación 1: $10 → PIERDE
    ↓
Martingala: $20 (doble) → Recuperar pérdida
    ↓
Si GANA → Recupera pérdida + ganancia
Si PIERDE → Detiene Martingala (máximo 1 intento)
```

### **Protecciones del Trading Automático:**

1. **Límite Diario**: Máximo de operaciones por día
2. **Umbral de Efectividad**: Solo opera señales >= 80%
3. **Verificación de Saldo**: Valida que haya fondos suficientes
4. **Control de Conexión**: Solo opera si Quotex está conectado
5. **Modo DEMO/REAL**: Separación clara de cuentas
6. **Martingala Limitada**: Máximo 1 intento de recuperación

---

## 🔄 CICLO COMPLETO DEL BOT

```
08:00 AM - Inicio del día
    ↓
Conectar a Quotex
    ↓
Cargar mercados disponibles (OTC y Normal)
    ↓
┌─────────────────────────────────────┐
│  CICLO CONTINUO (cada 5 minutos)    │
│                                      │
│  1. Analizar todos los mercados     │
│     - Obtener datos históricos      │
│     - Calcular indicadores          │
│     - Buscar patrones               │
│                                      │
│  2. Filtrar señales válidas         │
│     - Efectividad >= 75%            │
│     - Sin señales duplicadas        │
│                                      │
│  3. Ordenar por efectividad         │
│     - Mejor señal primero           │
│                                      │
│  4. Enviar señal a usuarios         │
│     - Confirmación obligatoria      │
│                                      │
│  5. Ejecutar trading automático     │
│     - Si está activado              │
│                                      │
│  6. Esperar 5 minutos               │
│     - Verificar resultado           │
│     - Procesar Martingala           │
│                                      │
│  7. Repetir ciclo                   │
└─────────────────────────────────────┘
    ↓
20:00 PM - Fin del día
    ↓
Desconectar de Quotex
    ↓
Generar reporte diario
```

---

## 📊 ARCHIVOS CLAVE DEL CÓDIGO

### **1. Análisis de Mercado:**
- `src/strategies/ema_aroon_strategy.py` - Estrategia EMA + Aroon
- `src/strategies/evaluar_estrategia_completa.py` - Punto de entrada

### **2. Gestión de Señales:**
- `src/core/signal_scheduler.py` - Scheduler de señales
  - `analizar_mercado()` - Analiza un mercado
  - `enviar_señal()` - Envía señal a usuarios
  - `ejecutar_operacion_automatica()` - Trading automático
  - `procesar_martingala_perdida()` - Sistema Martingala

### **3. Bot de Telegram:**
- `src/bot/telegram_bot.py` - Bot de Telegram
  - `enviar_confirmacion_senal_a_usuarios()` - Envía confirmación
  - `handle_callback_signal_accept()` - Procesa aceptación
  - `handle_callback_signal_reject()` - Procesa rechazo

### **4. Conexión a Quotex:**
- `src/core/market_manager.py` - Gestión de mercados
  - `conectar_quotex()` - Conecta a Quotex
  - `obtener_mercados_disponibles()` - Lista mercados
  - `obtener_datos_mercado()` - Obtiene velas históricas

### **5. Ejecución Principal:**
- `run_bot.py` - Punto de entrada principal
- `src/core/main.py` - Orquestador del sistema

---

## 🎯 RESUMEN EJECUTIVO

**El bot funciona en 3 pasos simples:**

1. **ANALIZA** → Usa EMA 50/36 + Aroon para detectar oportunidades
2. **ENVÍA** → Notifica a usuarios por Telegram con confirmación
3. **EJECUTA** → Opera automáticamente en Quotex (si está activado)

**Ventajas:**
- ✅ Análisis técnico profesional automatizado
- ✅ Señales con efectividad calculada (75-100%)
- ✅ Sistema de confirmación para usuarios
- ✅ Trading automático con protecciones
- ✅ Sistema Martingala inteligente (1 intento)
- ✅ Operación 24/5 en horario configurado

**Protecciones:**
- 🛡️ Umbral de efectividad mínima
- 🛡️ Límite diario de operaciones
- 🛡️ Separación DEMO/REAL
- 🛡️ Verificación de conexión constante
- 🛡️ Martingala limitada a 1 intento

---

## 📝 EJEMPLO PRÁCTICO COMPLETO

### Escenario: Señal CALL en EURUSD_OTC

**1. Análisis (08:15:00)**
```
Mercado: EURUSD_OTC
Datos: Últimas 50 velas de 5 minutos

Indicadores calculados:
- EMA 36: 1.08523
- EMA 50: 1.08456
- Aroon Up: 85.7%
- Aroon Down: 21.4%

Detección:
✓ EMA 36 > EMA 50 (tendencia alcista)
✓ Aroon Up > 70% (fuerza alcista confirmada)
✓ 2 velas alcistas consecutivas

Efectividad calculada:
- Base: 50%
- Tendencia clara: +12%
- Aroon fuerte: +13%
- Velas consecutivas: +5%
- TOTAL: 80%

Decisión: GENERAR SEÑAL CALL
```

**2. Envío (08:15:05)**
```
Telegram → Todos los usuarios activos:

"🔔 Nueva señal disponible

¿Deseas recibir esta señal?

✅ Aceptar: Recibirás todos los detalles
❌ Rechazar: No recibirás la señal"

[Botones: ✅ Aceptar | ❌ Rechazar]
```

**3. Usuario Acepta (08:15:10)**
```
Telegram → Usuario:

"🎯 SEÑAL #1 - CALL

💱 Mercado: EURUSD_OTC
⏰ Hora: 08:15:10
📊 Efectividad: 80.0%
⏱️ Temporalidad: 5M

📈 ANÁLISIS TÉCNICO:
• EMA 36: 1.08523
• EMA 50: 1.08456
• Aroon Up: 85.7%
• Aroon Down: 21.4%
• Tendencia: ALCISTA
• Tipo: 2 Velas Consecutivas

⏰ VÁLIDA POR 5 MINUTOS"
```

**4. Trading Automático (08:15:15)**
```
Sistema verifica:
✓ Trading automático: ACTIVO
✓ Modo: REAL
✓ Monto: $10
✓ Efectividad: 80% >= 80%
✓ Límite diario: 5/20 operaciones
✓ Conexión Quotex: ACTIVA

Ejecutando operación:
→ Cambiar a cuenta REAL
→ quotex.buy(
    amount=10,
    asset="EURUSD_otc",
    direction="call",
    duration=300
  )

Resultado: ✅ ÉXITO
Order ID: 987654321

Notificación al admin:
"✅ Operación Ejecutada

🎯 Detalles:
• Modo: REAL
• Symbol: EURUSD_OTC
• Dirección: CALL
• Monto: $10.00
• Efectividad: 80.0%
• Order ID: 987654321
• Duración: 5 minutos

⏰ Resultado en 5 minutos"
```

**5. Verificación de Resultado (08:20:15)**
```
Sistema verifica resultado:
→ Consultar estado de Order ID: 987654321

Resultado: ✅ GANANCIA ($8.50)

Acciones:
- Resetear Martingala
- Incrementar contador de ganancias
- Registrar en historial

Notificación al admin:
"✅ OPERACIÓN GANADA

💰 Ganancia: $8.50
📊 Balance: +$8.50
🎯 Efectividad real: 80%
📈 Racha: 3 ganancias consecutivas"
```

---

## 🔧 CONFIGURACIÓN RECOMENDADA

### Para Principiantes:
```
Modo: DEMO
Monto: $1
Límite diario: 5 operaciones
Efectividad mínima: 85%
```

### Para Usuarios Intermedios:
```
Modo: REAL
Monto: $5
Límite diario: 10 operaciones
Efectividad mínima: 80%
```

### Para Usuarios Avanzados:
```
Modo: REAL
Monto: $10-20
Límite diario: 20 operaciones
Efectividad mínima: 75%
Martingala: Activada (1 intento)
```

---

## ⚠️ ADVERTENCIAS IMPORTANTES

1. **Riesgo de Pérdida**: El trading de opciones binarias conlleva riesgo de pérdida de capital

2. **No es Garantía**: La efectividad calculada es una estimación, no una garantía

3. **Gestión de Riesgo**: Nunca operes más del 2-5% de tu capital por operación

4. **Martingala**: Usar con precaución, puede aumentar pérdidas

5. **Modo DEMO**: Siempre prueba primero en DEMO antes de usar REAL

6. **Supervisión**: Revisa regularmente el desempeño del bot

7. **Horarios**: El bot opera mejor en horarios de alta liquidez (8:00-20:00)

---

**Documento creado:** 25 de Octubre, 2025
**Versión del Bot:** EMA 50/36 + Aroon Strategy
**Autor:** Sistema de Trading Automático CubaYD
