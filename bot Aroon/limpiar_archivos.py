#!/usr/bin/env python3
"""
Script para limpiar archivos innecesarios del proyecto
Elimina archivos de prueba, documentación temporal y código antiguo
"""

import os
import shutil
from pathlib import Path

# Directorio raíz del proyecto
ROOT_DIR = Path(__file__).parent

# Archivos de prueba a eliminar
archivos_prueba = [
    "test_import.py",
    "test_quotex_api.py",
    "test_connect_method.py",
    "test_bot_simple.py",
    "test_comparacion_payouts.py",
    "test_diagnostico_completo.py",
    "test_estrategia_pullback.py",
    "test_flujo_completo.py",
    "test_flujo_estrategias.py",
    "test_modo_forzado.py",
    "test_nueva_estrategia.py",
    "test_otc_after_4pm.py",
    "test_panel_mercados.py",
    "test_payout_real.py",
    "test_payouts.py",
    "test_senal_completa.py",
    "test_tendencia_multitimeframe.py",
]

# Archivos de documentación temporal
archivos_docs = [
    "FIX_CONEXION_PYQUOTEX.md",
    "FIX_FINAL_QUOTEX_API.md",
    "SOLUCION_PYTHON_312.md",
    "RESUMEN_FINAL.md",
]

# Scripts de instalación/verificación temporales
archivos_scripts = [
    "activar_venv312.ps1",
    "instalar_pyquotex.ps1",
    "verificar_pyquotex.py",
]

# Carpetas a eliminar (código antiguo)
carpetas_eliminar = [
    "quotexpy",  # Versión antigua con Chrome
    "backup_old_files",
]

def eliminar_archivos():
    """Elimina archivos innecesarios"""
    print("🧹 Limpiando archivos innecesarios...\n")
    
    eliminados = 0
    
    # Eliminar archivos de prueba
    print("📝 Eliminando archivos de prueba...")
    for archivo in archivos_prueba:
        ruta = ROOT_DIR / archivo
        if ruta.exists():
            try:
                ruta.unlink()
                print(f"  ✅ {archivo}")
                eliminados += 1
            except Exception as e:
                print(f"  ❌ Error eliminando {archivo}: {e}")
    
    # Eliminar documentación temporal
    print("\n📄 Eliminando documentación temporal...")
    for archivo in archivos_docs:
        ruta = ROOT_DIR / archivo
        if ruta.exists():
            try:
                ruta.unlink()
                print(f"  ✅ {archivo}")
                eliminados += 1
            except Exception as e:
                print(f"  ❌ Error eliminando {archivo}: {e}")
    
    # Eliminar scripts temporales
    print("\n🔧 Eliminando scripts temporales...")
    for archivo in archivos_scripts:
        ruta = ROOT_DIR / archivo
        if ruta.exists():
            try:
                ruta.unlink()
                print(f"  ✅ {archivo}")
                eliminados += 1
            except Exception as e:
                print(f"  ❌ Error eliminando {archivo}: {e}")
    
    # Eliminar carpetas
    print("\n📁 Eliminando carpetas antiguas...")
    for carpeta in carpetas_eliminar:
        ruta = ROOT_DIR / carpeta
        if ruta.exists() and ruta.is_dir():
            try:
                shutil.rmtree(ruta)
                print(f"  ✅ {carpeta}/")
                eliminados += 1
            except Exception as e:
                print(f"  ❌ Error eliminando {carpeta}: {e}")
    
    print(f"\n✅ Limpieza completada: {eliminados} elementos eliminados")
    print("\n⚠️  NOTA: Los entornos virtuales (venv, .venv312, etc.) NO fueron eliminados")

if __name__ == "__main__":
    print("="*60)
    print("LIMPIEZA DE ARCHIVOS INNECESARIOS")
    print("="*60)
    print()
    
    respuesta = input("¿Deseas continuar con la limpieza? (S/N): ")
    
    if respuesta.upper() == "S":
        eliminar_archivos()
    else:
        print("\n❌ Limpieza cancelada")
