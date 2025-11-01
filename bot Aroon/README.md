# 🇨🇺 CubaYDSignal Trading Bot v2.0 Professional

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://telegram.org)
[![Quotex](https://img.shields.io/badge/Quotex-API-green.svg)](https://quotex.io)
[![License](https://img.shields.io/badge/License-Private-red.svg)]()

**Bot de Trading Profesional para Quotex con Telegram integrado**

Desarrollado por: **Yorji Fonseca (@Ijroy10)**  
Admin ID: **5806367733**  
Master Key: **Yorji.010702.CubaYDsignal**

---

## 🎯 Características Principales

### 📊 **Análisis Técnico Avanzado**
- ✅ **6 Estrategias Integradas**: Tendencia, Soportes/Resistencias, Patrones de Velas, Volatilidad, Volumen, Pullback
- ✅ **53 Patrones de Velas Personalizados** en 5 categorías
- ✅ **Efectividad Garantizada ≥ 80%**
- ✅ **Aprendizaje Adaptativo Continuo**

### 🌍 **Gestión Multi-Mercado**
- ✅ **12+ Mercados Analizados** automáticamente
- ✅ **Filtrado Inteligente por Payout ≥ 80%**
- ✅ **Gestión de Noticias** con cambio automático a OTC
- ✅ **Selección Automática** del mejor mercado diario

### 🤖 **Bot de Telegram Profesional**
- ✅ **20-25 Señales Diarias** automáticas
- ✅ **Sistema de Usuarios** con autenticación
- ✅ **Bloqueo/Desbloqueo** de usuarios por admin
- ✅ **Historial Completo** de acciones
- ✅ **Mensajes Motivacionales** categorizados
- ✅ **Resúmenes Diarios** detallados

### 🧠 **Inteligencia Artificial**
- ✅ **Optimización Automática** de estrategias
- ✅ **Identificación de Patrones** exitosos
- ✅ **Mejora Continua** del rendimiento
- ✅ **Reportes de Aprendizaje** detallados

---

## 🏗️ Estructura del Proyecto

```
CubaYDSignal/
├── 📁 src/                    # Código fuente principal
│   ├── 📁 core/              # Lógica central del bot
│   │   ├── main.py           # Controlador principal
│   │   ├── market_manager.py # Gestión de mercados
│   │   ├── user_manager.py   # Gestión de usuarios
│   │   ├── signal_scheduler.py # Programador de señales
│   │   └── adaptive_learning.py # Aprendizaje adaptativo
│   ├── 📁 bot/               # Bot de Telegram
│   │   ├── telegram_bot.py   # Bot principal
│   │   ├── handlers/         # Manejadores de comandos
│   │   └── messages/         # Plantillas de mensajes
│   ├── 📁 strategies/        # Estrategias de trading
│   │   ├── tendencia/        # Análisis de tendencia
│   │   ├── soportes_resistencias/ # S/R
│   │   ├── calculo_velas_patrones/ # Patrones
│   │   ├── volatilidad/      # Volatilidad
│   │   ├── volumen/          # Volumen
│   │   └── estrategia_pullback/ # Pullback
│   ├── 📁 analysis/          # Análisis técnico
│   ├── 📁 utils/             # Utilidades
│   └── 📁 config/            # Configuraciones
│       ├── .env              # Variables de entorno
│       └── settings.py       # Configuraciones
├── 📁 docs/                  # Documentación
│   ├── api/                  # Documentación API
│   ├── strategies/           # Documentación estrategias
│   └── user_guide/           # Guía de usuario
├── 📁 tests/                 # Tests
│   ├── unit/                 # Tests unitarios
│   └── integration/          # Tests de integración
├── 📁 assets/                # Recursos
│   ├── images/               # Imágenes
│   └── templates/            # Plantillas
├── 📁 scripts/               # Scripts de utilidad
├── 📁 data/                  # Datos del bot
├── 📁 logs/                  # Logs del sistema
├── main.py                   # Punto de entrada principal
├── main_professional.py     # Entrada profesional
├── requirements.txt          # Dependencias
└── README.md                 # Este archivo
```

---

## 🚀 Instalación y Configuración

### 1. **Requisitos del Sistema**
```bash
Python 3.8+
pip (gestor de paquetes)
```

### 2. **Instalación de Dependencias**
```bash
pip install -r requirements.txt
```

### 3. **Configuración de Variables de Entorno**
Copia `src/config/.env.example` a `src/config/.env` y configura:

```env
# Bot de Telegram
BOT_TOKEN=8163922521:AAHv5IPZlLZnjEM77BH2fYPsIQznemVRG-Y
ADMIN_ID=5806367733

# Quotex API
QUOTEX_EMAIL=ijroyquotex@gmail.com
QUOTEX_PASSWORD=Yorji.050212

# Configuraciones del Bot
MASTER_KEY=Yorji.010702.CubaYDsignal
PAYOUT_MINIMO=80
SEÑALES_DIARIAS=25
HORARIO_INICIO=08:00
HORARIO_FIN=20:00
```

### 4. **Ejecutar el Bot**
```bash
# Versión profesional (recomendada)
python main_professional.py

# Versión legacy
python main.py
```

---

## 🎮 Comandos del Bot de Telegram

### 👑 **Comandos de Administrador** (ID: 5806367733)

| Comando | Descripción |
|---------|-------------|
| `/admin` | Panel completo de administración |
| `/bloquear ID_USUARIO` | Bloquear cualquier usuario |
| `/desbloquear ID_USUARIO` | Desbloquear cualquier usuario |
| `/historial` | Ver historial completo de bloqueos |
| `/estado` | Estado del sistema y estadísticas |
| `/ayuda` | Guía completa de comandos |

### 👥 **Comandos de Usuario**

| Comando | Descripción |
|---------|-------------|
| `/start` | Iniciar interacción con el bot |
| `/clave` | Ingresar clave de acceso |
| `/estado` | Ver tu estado y estadísticas |
| `/ayuda` | Ayuda básica |

---

## 🔧 Panel de Administrador

Accede con `/admin` para obtener:

```
⚙️ PANEL DE ADMINISTRADOR

🔑 Autenticación:
• Clave pública: CUBA20241205ABCD
• Fecha clave: 2024-12-05

👥 Usuarios:
• Activos: 15
• Bloqueados: 2
• Usuarios tardíos: 3

📊 Señales:
• Enviadas hoy: 18
• Efectividad promedio: 84.2%

🎯 Sistema:
• Estado: 🟢 ACTIVO
• Mercado: EURUSD

[🔑 Nueva Clave] [📊 Estadísticas]
[👥 Ver Usuarios] 
[🚫 Bloquear Usuario] [✅ Desbloquear Usuario]
[📋 Historial Bloqueos]
[🚀 Iniciar Día] [⏹️ Detener Bot]
```

---

## 📊 Estrategias de Trading

### 1. **Análisis de Tendencia**
- Tendencia principal (MA 50)
- Tendencia secundaria (MA 9)
- Fuerza de tendencia (ADX + MACD)
- Patrones chartistas

### 2. **Soportes y Resistencias**
- Detección automática de zonas
- Conteo de toques
- Análisis de recencia
- Filtrado por relevancia

### 3. **Patrones de Velas** (53 patrones)
- **Continuidad** (11): advance_block, deliberation, etc.
- **Reversión** (21): engulfing, harami, martillos, etc.
- **Indecisión** (6): dojis, spinning_top, etc.
- **Especiales** (10): marubozu, heiken_ashi, etc.
- **Rupturas** (5): breakout_bar, hikkake, etc.

### 4. **Análisis de Volatilidad**
- Bandas de Bollinger
- ATR (Average True Range)
- Detección de expansión/contracción

### 5. **Análisis de Volumen**
- OBV (On-Balance Volume)
- Relación precio-volumen
- Confirmación de movimientos

### 6. **Estrategia Pullback**
- Detección de retrocesos
- Puntos de entrada óptimos
- Gestión de riesgo

---

## 🤖 Flujo de Señales Automáticas

### **Horario de Operación**
- **Lunes a Viernes**: 8:00 AM - 8:00 PM
- **Objetivo**: 20-25 señales por día
- **Intervalos**: Aleatorios entre señales

### **Proceso de Análisis**
1. **Obtención de Datos**: Candles de 5 minutos
2. **Análisis Multi-Estrategia**: 6 estrategias simultáneas
3. **Cálculo de Efectividad**: Agregación de resultados
4. **Filtrado**: Solo señales ≥ 80% efectividad
5. **Envío**: Notificación 3 minutos antes
6. **Seguimiento**: Registro de resultados

### **Formato de Señal**
```
🎯 SEÑAL DE TRADING

💰 Mercado: EUR/USD
📈 Dirección: CALL (Subida)
⏰ Tiempo: 5 minutos
🎯 Efectividad: 87.5%

📊 ANÁLISIS TÉCNICO:
✅ Tendencia: Alcista fuerte
✅ S/R: Rebote en soporte clave
✅ Patrones: Martillo alcista
✅ Volatilidad: Expansión moderada
✅ Volumen: Confirmación alcista

🕐 Ejecutar en: 14:25:00
💡 Consejo: Entrada en ruptura de resistencia

#CubaYDSignal #Trading #Quotex
```

---

## 🔐 Sistema de Usuarios

### **Autenticación**
- **Admin**: Reconocimiento automático por ID (5806367733)
- **Usuarios**: Clave diaria generada automáticamente
- **Formato**: CUBA + FECHA + HASH (ej: CUBA2024120512AB)

### **Gestión de Acceso**
- **Bloqueo**: Admin puede bloquear cualquier usuario
- **Desbloqueo**: Admin puede desbloquear usuarios
- **Historial**: Registro completo de todas las acciones
- **Notificaciones**: Mensajes automáticos a usuarios afectados

### **Tipos de Usuario**
- **Admin**: Acceso completo, panel de control
- **Usuario Regular**: Recibe señales, acceso básico
- **Usuario Bloqueado**: Sin acceso, mensaje de bloqueo

---

## 🧠 Aprendizaje Adaptativo

### **Análisis de Resultados**
- Seguimiento de efectividad por estrategia
- Identificación de patrones exitosos
- Análisis de horarios óptimos
- Evaluación de mercados rentables

### **Optimización Automática**
- Ajuste de pesos de estrategias
- Selección de mejores patrones
- Optimización de horarios
- Mejora continua de parámetros

### **Reportes de Aprendizaje**
```
🧠 REPORTE DE APRENDIZAJE DIARIO

📊 RENDIMIENTO POR ESTRATEGIA:
• Tendencia: 89% (↑3%)
• Patrones: 85% (↓1%)
• S/R: 92% (↑5%)
• Volatilidad: 78% (↓2%)

🎯 MEJORES PATRONES:
1. Martillo Alcista: 94%
2. Engulfing Bajista: 91%
3. Doji Estrella: 88%

⏰ HORARIOS ÓPTIMOS:
• 09:00-11:00: 91%
• 14:00-16:00: 88%
• 19:00-20:00: 85%

💰 MEJORES MERCADOS:
1. EUR/USD: 89%
2. GBP/USD: 86%
3. Gold: 84%

🔧 AJUSTES REALIZADOS:
• ↑ Peso S/R: +5%
• ↓ Peso Volatilidad: -2%
• ⭐ Prioridad Martillo: +10%
```

---

## 📈 Estadísticas y Métricas

### **Métricas Diarias**
- Total de señales analizadas
- Señales enviadas (≥80%)
- Efectividad promedio
- Usuarios activos
- Mercados operados

### **Métricas Históricas**
- Rendimiento por semana/mes
- Evolución de estrategias
- Crecimiento de usuarios
- Mejoras del sistema

### **Alertas y Monitoreo**
- Notificaciones de baja efectividad
- Alertas de errores del sistema
- Monitoreo de conexión a Quotex
- Seguimiento de usuarios bloqueados

---

## 🛠️ Desarrollo y Mantenimiento

### **Estructura de Código**
- **Modular**: Cada funcionalidad en su módulo
- **Escalable**: Fácil agregar nuevas estrategias
- **Mantenible**: Código documentado y organizado
- **Testeable**: Tests unitarios e integración

### **Logging y Debugging**
- Logs detallados en `logs/`
- Diferentes niveles de logging
- Rotación automática de logs
- Debugging por módulos

### **Backup y Recuperación**
- Backup automático de datos de usuarios
- Persistencia de configuraciones
- Recuperación de historial
- Exportación de estadísticas

---

## 📞 Soporte y Contacto

**Desarrollador**: Yorji Fonseca  
**Telegram**: @Ijroy10  
**Admin ID**: 5806367733  

### **Reportar Problemas**
1. Revisa los logs en `logs/`
2. Verifica la configuración en `src/config/.env`
3. Contacta al desarrollador con detalles del error

### **Solicitar Funcionalidades**
- Contacta directamente al desarrollador
- Describe la funcionalidad deseada
- Proporciona casos de uso específicos

---

## 📄 Licencia

Este proyecto es **privado** y de uso exclusivo para el propietario.  
Todos los derechos reservados © 2024 Yorji Fonseca

---

## 🎯 Próximas Actualizaciones

- [ ] Integración con más brokers
- [ ] Análisis de noticias automático
- [ ] Dashboard web interactivo
- [ ] Alertas por email
- [ ] API REST para integraciones
- [ ] Modo paper trading
- [ ] Análisis de sentimiento de mercado

---

**¡Gracias por usar CubaYDSignal Trading Bot! 🇨🇺💰📈**
