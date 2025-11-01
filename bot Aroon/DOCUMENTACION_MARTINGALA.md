# 🎲 Sistema de Martingala - Documentación Completa

## 📋 Índice
1. [¿Qué es Martingala?](#qué-es-martingala)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Flujo Completo](#flujo-completo)
4. [Sistema Predictivo](#sistema-predictivo)
5. [Notificaciones](#notificaciones)
6. [Configuración](#configuración)
7. [Ejemplos Prácticos](#ejemplos-prácticos)
8. [Casos de Uso](#casos-de-uso)

---

## 🎯 ¿Qué es Martingala?

### Definición
La **Martingala** es una estrategia de recuperación de pérdidas que consiste en **duplicar la inversión** después de una operación perdida, con el objetivo de recuperar la pérdida anterior y obtener ganancia.

### Ejemplo Básico
```
Operación 1: $5  → PIERDE → Pérdida: -$5
Operación 2: $10 → GANA   → Ganancia: +$9.40 (94% payout)
Resultado neto: +$4.40 (recuperó $5 + ganó $4.40)
```

### Fórmula
```
Monto Martingala = Monto Perdido × 2
```

---

## 🏗️ Arquitectura del Sistema

### Componentes Principales

#### 1. **SignalScheduler** (`signal_scheduler.py`)
- Gestiona la lógica de Martingala
- Analiza velas predictivamente
- Ejecuta operaciones automáticas
- Calcula efectividad

#### 2. **TelegramBot** (`telegram_bot.py`)
- Maneja callbacks de confirmación
- Envía notificaciones
- Gestiona interfaz de usuario

#### 3. **Variables de Estado**
```python
# Sistema de Martingala
self.martingala_activa = False              # ¿Hay Martingala en curso?
self.martingala_monto_base = 0              # Monto inicial perdido
self.martingala_monto_actual = 0            # Monto de la próxima operación
self.martingala_direccion = None            # CALL o PUT
self.martingala_symbol = None               # Par de mercado
self.martingala_intentos = 0                # Número de intento actual
self.martingala_max_intentos = 1            # Límite de intentos
self.martingala_pendiente = None            # Datos de Martingala esperando confirmación

# Sistema Predictivo
self.señal_martingala_pendiente = None      # Señal siendo analizada
self.martingala_confirmacion_anticipada = None  # True/False/None
```

---

## 🔄 Flujo Completo

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│                    SEÑAL SE EJECUTA                         │
│                    (Ejemplo: 12:00)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              ESPERA 3 MINUTOS (12:03)                       │
│         verificar_resultado_señal_automatico()              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           ANÁLISIS PREDICTIVO (12:03)                       │
│           analizar_vela_predictiva()                        │
│                                                             │
│  • Obtiene precio actual                                   │
│  • Compara con precio de entrada                           │
│  • Determina si probablemente se perderá                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ¿Probablemente se perderá?
                         │
        ┌────────────────┴────────────────┐
        │                                 │
       SÍ                                NO
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│ ENVÍA CONFIRMACIÓN│            │  NO HACE NADA   │
│   ANTICIPADA      │            │  Espera 2 min   │
│   AL ADMIN        │            └──────────────────┘
└────────┬──────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│         ADMIN RESPONDE (12:03-12:05)                        │
│                                                             │
│  ✅ Sí, pre-autorizar → martingala_confirmacion_anticipada = True  │
│  ❌ No, esperar      → martingala_confirmacion_anticipada = False  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              ESPERA 2 MINUTOS MÁS (12:05)                   │
│              Completa los 5 minutos totales                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           VERIFICA RESULTADO REAL (12:05)                   │
│                                                             │
│  • Obtiene precio final                                    │
│  • Calcula resultado: WIN o LOSS                           │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
      LOSS                               WIN
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│ procesar_        │            │ resetear_        │
│ martingala_      │            │ martingala()     │
│ perdida()        │            │                  │
└────────┬─────────┘            └────────┬─────────┘
         │                               │
         ▼                               ▼
¿Hay confirmación                 ¿Había confirmación
 anticipada?                       anticipada?
         │                               │
    ┌────┴────┐                     ┌────┴────┐
   SÍ        NO                    SÍ        NO
    │         │                     │         │
    ▼         ▼                     ▼         ▼
┌────────┐ ┌────────┐         ┌────────┐ ┌────────┐
│EJECUTA │ │SOLICITA│         │CANCELA │ │RESETEA │
│INMEDIA-│ │CONFIR- │         │MARTIN- │ │NORMAL  │
│TAMENTE│ │MACIÓN  │         │GALA    │ │        │
└───┬────┘ └───┬────┘         └───┬────┘ └───┬────┘
    │          │                  │          │
    │          ▼                  │          │
    │    ┌──────────┐             │          │
    │    │Admin     │             │          │
    │    │confirma? │             │          │
    │    └────┬─────┘             │          │
    │         │                   │          │
    │    ┌────┴────┐              │          │
    │   SÍ        NO              │          │
    │    │         │               │          │
    └────┘         ▼               │          │
         │    ┌────────┐           │          │
         │    │NO HACE │           │          │
         │    │NADA    │           │          │
         │    └────────┘           │          │
         ▼                         ▼          ▼
┌─────────────────────────────────────────────────┐
│     ESPERA APERTURA PRÓXIMA VELA (12:10)       │
│     ejecutar_martingala_confirmada()            │
│                                                 │
│  • Calcula próxima vela de 5 min               │
│  • Espera hasta apertura exacta                │
│  • Ejecuta operación con monto x2              │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         ESPERA 5 MINUTOS (12:15)                │
│         Verifica resultado de Martingala        │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
      GANA                      PIERDE
        │                         │
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│ resetear_        │    │ ¿Límite          │
│ martingala()     │    │ alcanzado?       │
│                  │    └────────┬─────────┘
│ • Notifica admin │             │
│ • Notifica users │    ┌────────┴────────┐
│ • Resetea sistema│   SÍ                NO
└──────────────────┘    │                 │
                        ▼                 ▼
                 ┌──────────────┐  ┌──────────────┐
                 │ DETIENE      │  │ SOLICITA     │
                 │ MARTINGALA   │  │ NUEVO        │
                 │              │  │ INTENTO      │
                 │ • Notifica   │  └──────────────┘
                 │   pérdida    │
                 │ • Resetea    │
                 └──────────────┘
```

---

## 🔮 Sistema Predictivo

### ¿Qué es?
El sistema predictivo analiza la vela **2 minutos antes** de que cierre para determinar si probablemente se perderá, permitiendo solicitar confirmación anticipada al admin.

### Ventajas
- ⚡ **Velocidad**: Martingala se ejecuta inmediatamente si se pierde
- 🎯 **Eficiencia**: No pierde tiempo esperando confirmación post-pérdida
- 🧠 **Inteligente**: Solo pregunta si probablemente se perderá
- ✅ **Seguro**: Cancela automáticamente si se gana

### Lógica de Predicción

```python
def analizar_vela_predictiva(señal):
    precio_actual = obtener_precio_actual()
    precio_entrada = señal['precio_entrada']
    direccion = señal['direccion']
    
    if direccion == 'CALL':
        # Para CALL, se pierde si precio está por debajo
        probablemente_perdida = precio_actual < precio_entrada
    else:  # PUT
        # Para PUT, se pierde si precio está por encima
        probablemente_perdida = precio_actual > precio_entrada
    
    if probablemente_perdida:
        solicitar_confirmacion_anticipada()
```

### Ejemplo Visual

```
CALL (Compra) - Precio de entrada: 1.08500

12:00 ──┬── Entrada: 1.08500
        │
12:01   │   Precio: 1.08520 ✅ (ganando)
        │
12:02   │   Precio: 1.08510 ✅ (ganando)
        │
12:03 ──┼── ANÁLISIS PREDICTIVO
        │   Precio: 1.08480 ❌ (perdiendo)
        │   → Solicita confirmación anticipada
        │
12:04   │   Admin confirma ✅
        │
12:05 ──┴── Cierre: 1.08470 ❌ PERDIDA
                    → Ejecuta Martingala INMEDIATAMENTE
```

---

## 📢 Notificaciones

### Tipos de Notificaciones

#### 1. **Confirmación Anticipada (Solo Admin)**
**Cuándo:** 2 minutos antes del cierre, si probablemente se perderá

**Mensaje:**
```
🔮 MARTINGALA PREDICTIVA - CONFIRMACIÓN ANTICIPADA

⚠️ La vela probablemente se perderá

📊 Análisis Actual (2 min antes del cierre):
• Symbol: EURUSD_otc
• Dirección: CALL
• Modo: DEMO
• Diferencia actual: 0.025% en contra

💰 Datos de Martingala:
• Intento: 1/1
• Monto actual: $5.00
• Monto Martingala: $10.00
• Efectividad estimada: 85%

⏰ Ventaja de confirmar ahora:
Si confirmas ahora y la vela se pierde, ejecutaré la Martingala 
inmediatamente en la próxima vela sin perder tiempo.

Si la vela se gana, cancelaré automáticamente la Martingala.

⚠️ ¿Deseas pre-autorizar la Martingala?

[✅ Sí, pre-autorizar Martingala] [❌ No, esperar resultado final]
```

#### 2. **Información de Martingala (Usuarios)**
**Cuándo:** Cuando una señal se pierde

**Mensaje:**
```
📊 SEÑAL #5 - PERDIDA
💱 EURUSD_otc | CALL | 82.5%
📊 Entrada: 1.08450 → Salida: 1.08420
📉 Diferencia: 0.028%

No te preocupes, es parte del trading. 
¡La próxima será mejor! 💪

🎲 OPORTUNIDAD DE MARTINGALA
Si deseas recuperar esta pérdida, puedes hacer Martingala:

💡 ¿Qué es Martingala?
Duplicar tu inversión en la próxima entrada del mismo mercado 
para recuperar la pérdida.

📊 Datos de Martingala:
• Efectividad estimada: 87.5%
• Monto recomendado: 2x tu inversión anterior
• Mercado: EURUSD_otc
• Dirección: CALL

⚠️ Importante:
• Espera la apertura de la próxima vela de 5 minutos
• Opera con responsabilidad
• Solo si te sientes cómodo con el riesgo

💪 ¡Tú decides si quieres recuperar!
```

#### 3. **Martingala Ganada (Admin + Usuarios)**

**Admin:**
```
✅ MARTINGALA EXITOSA

🎉 Recuperación completada en intento 1
💰 Ganancia: $4.70

Symbol: EURUSD_otc
Dirección: CALL
```

**Usuarios:**
```
🎉 MARTINGALA GANADA 🎉

✅ ¡Recuperación exitosa!

📊 Resultado:
• Symbol: EURUSD_otc
• Dirección: CALL
• Intento: 1
• Ganancia: $4.70

💪 ¡Felicidades!
La estrategia de Martingala funcionó perfectamente.
Has recuperado la pérdida anterior y obtenido ganancia.

🚀 ¡Seguimos adelante con más oportunidades!
```

#### 4. **Martingala Perdida (Admin + Usuarios)**

**Admin:**
```
⛔ MARTINGALA DETENIDA

Se alcanzó el límite de 1 intentos
Pérdida total acumulada: $15.00

Symbol: EURUSD_otc
Dirección: CALL
```

**Usuarios:**
```
❌ MARTINGALA PERDIDA

⛔ Se alcanzó el límite de intentos

📊 Resultado:
• Symbol: EURUSD_otc
• Dirección: CALL
• Intentos realizados: 1
• Pérdida total: $15.00

💡 Aprendizaje:
No todas las Martingalas funcionan. Es importante saber cuándo detenerse.

⚠️ Recomendación:
• Toma un descanso si es necesario
• Revisa tu estrategia
• No persigas las pérdidas
• Espera la próxima oportunidad

💪 Recuerda: El trading exitoso requiere disciplina y paciencia.
```

#### 5. **Martingala Cancelada (Admin)**
**Cuándo:** Cuando se pre-autorizó pero la vela se ganó

**Mensaje:**
```
✅ MARTINGALA CANCELADA

🎉 La vela se ganó!

La Martingala pre-autorizada fue cancelada automáticamente.
No fue necesaria la recuperación.

Symbol: EURUSD_otc
Dirección: CALL
Ganancia: $4.70
```

---

## ⚙️ Configuración

### Variables Configurables

```python
# En signal_scheduler.py - __init__()

self.martingala_max_intentos = 1  # Número máximo de intentos de Martingala
```

### Modificar Límite de Intentos

Para permitir múltiples intentos de Martingala:

```python
# Cambiar de:
self.martingala_max_intentos = 1

# A (por ejemplo, 3 intentos):
self.martingala_max_intentos = 3
```

**Ejemplo con 3 intentos:**
```
Operación 1: $5   → PIERDE → Pérdida: -$5
Martingala 1: $10  → PIERDE → Pérdida: -$15
Martingala 2: $20  → PIERDE → Pérdida: -$35
Martingala 3: $40  → GANA   → Ganancia: +$37.60
Resultado neto: +$2.60
```

### Cálculo de Efectividad

```python
efectividad_martingala = min(95, efectividad_original + (intento * 5))
```

**Tabla de Efectividad:**

| Intento | Efectividad Original | Efectividad Martingala |
|---------|---------------------|------------------------|
| 1       | 80%                 | 85%                    |
| 2       | 80%                 | 90%                    |
| 3       | 80%                 | 95%                    |
| 1       | 90%                 | 95% (máximo)           |

---

## 📚 Ejemplos Prácticos

### Ejemplo 1: Martingala Exitosa con Pre-autorización

**Timeline:**
```
12:00:00 → Señal EURUSD_otc CALL ejecutada ($5)
           Precio entrada: 1.08500

12:03:00 → Análisis predictivo
           Precio actual: 1.08480 (perdiendo)
           → Envía confirmación anticipada a admin

12:03:30 → Admin toca "✅ Sí, pre-autorizar Martingala"
           martingala_confirmacion_anticipada = True

12:05:00 → Vela cierra
           Precio final: 1.08470
           Resultado: LOSS ❌
           
           → Detecta pre-autorización
           → Ejecuta Martingala INMEDIATAMENTE

12:05:00 → Calcula próxima vela: 12:10:00
           Espera: 300 segundos

12:10:00 → Martingala ejecutada ($10)
           Precio entrada: 1.08470

12:15:00 → Vela cierra
           Precio final: 1.08520
           Resultado: WIN ✅
           
           → Notifica admin: "✅ MARTINGALA EXITOSA - $9.40"
           → Notifica usuarios: "🎉 MARTINGALA GANADA"
           → Resetea sistema
```

**Resultado:**
- Pérdida inicial: -$5.00
- Ganancia Martingala: +$9.40
- **Resultado neto: +$4.40** ✅

---

### Ejemplo 2: Martingala Rechazada por Admin

**Timeline:**
```
12:00:00 → Señal AUDUSD_otc PUT ejecutada ($5)

12:03:00 → Análisis predictivo detecta probable pérdida
           → Envía confirmación anticipada

12:03:45 → Admin toca "❌ No, esperar resultado final"
           martingala_confirmacion_anticipada = False

12:05:00 → Vela cierra
           Resultado: LOSS ❌
           
           → NO hay pre-autorización
           → Solicita confirmación NORMAL

12:05:05 → Admin recibe confirmación normal
           Admin toca "❌ No, cancelar"

12:05:10 → Martingala cancelada
           → Notifica señal perdida normal
           → NO ejecuta Martingala
```

**Resultado:**
- Pérdida: -$5.00
- **Sin recuperación** ❌

---

### Ejemplo 3: Predicción Incorrecta (Se Gana)

**Timeline:**
```
12:00:00 → Señal GBPUSD_otc CALL ejecutada ($5)
           Precio entrada: 1.27500

12:03:00 → Análisis predictivo
           Precio actual: 1.27480 (perdiendo)
           → Envía confirmación anticipada

12:03:20 → Admin toca "✅ Sí, pre-autorizar"
           martingala_confirmacion_anticipada = True

12:05:00 → Vela cierra
           Precio final: 1.27520 (¡REMONTÓ!)
           Resultado: WIN ✅
           
           → Detecta pre-autorización pero GANÓ
           → CANCELA Martingala automáticamente
           → Notifica admin: "✅ MARTINGALA CANCELADA - La vela se ganó!"
           → Resetea sistema
```

**Resultado:**
- Ganancia: +$4.70
- **Martingala no necesaria** ✅

---

### Ejemplo 4: Martingala Perdida

**Timeline:**
```
12:00:00 → Señal EURJPY_otc PUT ejecutada ($5)

12:03:00 → Admin pre-autoriza Martingala

12:05:00 → Vela cierra - LOSS ❌
           → Ejecuta Martingala inmediatamente

12:10:00 → Martingala ejecutada ($10)

12:15:00 → Vela cierra - LOSS ❌
           → Límite alcanzado (1 intento)
           
           → Notifica admin: "⛔ MARTINGALA DETENIDA - Pérdida: $15"
           → Notifica usuarios: "❌ MARTINGALA PERDIDA - Consejos"
           → Resetea sistema
```

**Resultado:**
- Pérdida inicial: -$5.00
- Pérdida Martingala: -$10.00
- **Pérdida total: -$15.00** ❌

---

## 🎯 Casos de Uso

### Caso 1: Trading Automático Normal
**Escenario:** Admin tiene trading automático activo en modo DEMO

**Flujo:**
1. Bot genera señal automáticamente
2. Ejecuta operación ($5)
3. Espera 3 minutos
4. Analiza vela predictivamente
5. Si probablemente se pierde → Solicita confirmación
6. Admin decide si pre-autorizar
7. Espera resultado final
8. Si se pierde y está pre-autorizado → Ejecuta Martingala
9. Notifica resultado

**Ventaja:** Máxima velocidad de recuperación

---

### Caso 2: Análisis Forzado con Trading
**Escenario:** Admin hace análisis forzado de EURUSD_otc con trading automático

**Flujo:**
1. Admin selecciona análisis forzado
2. Configura mercado, efectividad, duración
3. Activa trading automático
4. Bot analiza solo EURUSD_otc
5. Genera señal cuando cumple criterios
6. Sistema de Martingala funciona igual
7. Solo para señales de EURUSD_otc

**Ventaja:** Control total sobre mercado específico

---

### Caso 3: Usuario Manual
**Escenario:** Usuario recibe señales pero opera manualmente

**Flujo:**
1. Usuario recibe señal
2. Opera manualmente en Quotex
3. Señal se pierde
4. Usuario recibe información de Martingala
5. Usuario decide si hacer Martingala manualmente
6. Duplica su inversión en próxima vela
7. Recupera pérdida si gana

**Ventaja:** Usuario tiene control total, bot solo informa

---

## 📊 Estadísticas y Métricas

### Efectividad del Sistema

**Fórmula de Efectividad:**
```python
efectividad_base = 80%  # Efectividad de señal original
efectividad_martingala = efectividad_base + (intento × 5%)
efectividad_maxima = 95%
```

**Probabilidad de Recuperación:**
```
1 intento:  85% de éxito
2 intentos: 85% + (15% × 90%) = 98.5% de éxito
3 intentos: 85% + (15% × 90%) + (1.5% × 95%) = 99.93% de éxito
```

### Gestión de Riesgo

**Tabla de Riesgo:**

| Intentos | Inversión Total | Riesgo Máximo | Ganancia Potencial |
|----------|----------------|---------------|-------------------|
| 1        | $15            | -$15          | +$4.40            |
| 2        | $35            | -$35          | +$2.60            |
| 3        | $75            | -$75          | +$0.80            |

**Recomendación:** Limitar a 1-2 intentos para gestión de riesgo óptima.

---

## 🔧 Mantenimiento y Troubleshooting

### Logs Importantes

```
[Martingala Predictiva] 🔮 Analizando vela 2 minutos antes del cierre...
[Martingala Predictiva] 📊 Análisis: probablemente_perdida = True
[Martingala Predictiva] 📤 Confirmación anticipada enviada a admin
[Martingala] ✅ Admin confirmó Martingala
[Martingala] ✅ Confirmación anticipada encontrada - Ejecutando inmediatamente
[Martingala] ⏰ Esperando 300.0 segundos hasta apertura de vela (12:10:00)
[Martingala] ✅ Apertura de vela alcanzada - Ejecutando Martingala
[Martingala] ✅ VICTORIA - Recuperación exitosa!
```

### Problemas Comunes

#### 1. Martingala no se ejecuta
**Causa:** `martingala_confirmacion_anticipada` no está configurada
**Solución:** Verificar que admin confirmó o rechazó

#### 2. Doble ejecución
**Causa:** Callbacks duplicados
**Solución:** Verificar que no hay callbacks duplicados en telegram_bot.py

#### 3. Notificaciones no llegan
**Causa:** `bot_telegram.application` no está configurado
**Solución:** Verificar que `configurar_bot_telegram()` se llamó correctamente

---

## 📝 Checklist de Implementación

- [x] Sistema de Martingala básico
- [x] Análisis predictivo (3 minutos antes)
- [x] Confirmación anticipada para admin
- [x] Ejecución inmediata si pre-autorizado
- [x] Cancelación automática si se gana
- [x] Notificaciones a admin (ganada/perdida)
- [x] Notificaciones a usuarios (ganada/perdida)
- [x] Información educativa para usuarios
- [x] Cálculo de efectividad dinámico
- [x] Sincronización con apertura de vela
- [x] Límite de intentos configurable
- [x] Gestión de estado completa
- [x] Logs detallados

---

## 🚀 Próximas Mejoras (Futuras)

1. **Martingala Múltiple:** Permitir varios mercados simultáneamente
2. **Martingala Adaptativa:** Ajustar multiplicador según volatilidad
3. **Análisis de Tendencia:** Mejorar predicción con indicadores técnicos
4. **Historial de Martingalas:** Guardar estadísticas de éxito/fracaso
5. **Configuración por Usuario:** Permitir que cada usuario configure su Martingala
6. **Stop Loss Inteligente:** Detener Martingala si mercado muy volátil

---

## 📞 Soporte

Para dudas o problemas:
1. Revisar logs en consola
2. Verificar estado de variables
3. Comprobar callbacks en telegram_bot.py
4. Revisar flujo en signal_scheduler.py

---

**Última actualización:** 26 de Octubre, 2025
**Versión del sistema:** 2.0 (Con sistema predictivo)
