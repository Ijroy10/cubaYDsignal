#!/usr/bin/env python3
"""Script para eliminar archivos run_bot_*.py innecesarios"""

import os

# Archivos a eliminar
archivos_eliminar = [
    "run_bot_complete_fixed.py",
    "run_bot_complete_safe.py",
    "run_bot_improved.py",
    "run_bot_notifications.py",
    "run_bot_robust.py",
    "run_bot_safe_test.py",
    "run_bot_simple.py",
    "run_bot_unified.py"
]

print("🗑️ Eliminando archivos run_bot_*.py innecesarios...\n")

eliminados = 0
for archivo in archivos_eliminar:
    if os.path.exists(archivo):
        try:
            os.remove(archivo)
            print(f"✅ Eliminado: {archivo}")
            eliminados += 1
        except Exception as e:
            print(f"❌ Error eliminando {archivo}: {e}")
    else:
        print(f"⚠️ No existe: {archivo}")

print(f"\n✅ Proceso completado: {eliminados} archivos eliminados")
print(f"✅ Archivo principal conservado: run_bot.py")
