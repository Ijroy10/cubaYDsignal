#!/usr/bin/env python3
"""
🚀 CubaYDSignal - INICIO RÁPIDO DEL BOT
======================================

✅ Incluye nueva estrategia de tendencia multi-timeframe
✅ Análisis en 4 niveles temporales (MA 200, 50, 20, 9)
✅ Sistema de alineación con bonus/penalización
✅ Integración inteligente entre estrategias

🛡️ MODO PRACTICE (cuenta demo) - SIN RIESGO FINANCIERO

EJECUTAR: python INICIAR_BOT.py
"""

import os
import sys
from pathlib import Path

# Configurar path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("🚀 CUBAYDSIGNAL - BOT DE TRADING INICIANDO")
print("=" * 70)
print()
print("✅ NUEVA ESTRATEGIA EMA 50/36 + AROON ACTIVADA")
print("📊 Cruces de EMAs con confirmación Aroon")
print("🎯 Rebotes en EMAs + Velas consecutivas")
print("📈 Efectividad mínima: 75%")
print()
print("=" * 70)
print()

# Verificar que existe run_bot.py
run_bot_file = project_root / "run_bot.py"
if not run_bot_file.exists():
    print("❌ ERROR: run_bot.py no encontrado")
    print("📝 Verifica que el archivo run_bot.py existe en el directorio")
    sys.exit(1)

print("🔄 Iniciando bot con estrategia EMA + Aroon...")
print()

# Ejecutar el bot
os.system(f"python {run_bot_file}")
