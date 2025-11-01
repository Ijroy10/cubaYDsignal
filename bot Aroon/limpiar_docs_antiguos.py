#!/usr/bin/env python3
"""
Script para eliminar documentación antigua del proyecto
Mantiene solo README.md y documentación esencial
"""

import os
from pathlib import Path

# Directorio raíz del proyecto
ROOT_DIR = Path(__file__).parent

# Documentos a MANTENER (lista blanca)
MANTENER = {
    "README.md",
    "LIMPIEZA_COMPLETADA.md",
    "limpiar_archivos.py",
    "limpiar_docs_antiguos.py",
}

# Patrones de archivos a eliminar
PATRONES_ELIMINAR = [
    "ANALISIS_*.md",
    "ACTUALIZACION_*.md",
    "ACTIVAR_*.md",
    "ANGULOS_*.md",
    "BOTON_*.md",
    "BOTONES_*.md",
    "CAMBIOS_*.md",
    "CANCELAR_*.md",
    "CHANGELOG_*.md",
    "COMO_*.md",
    "CORRECCION_*.md",
    "CORRECCIONES_*.md",
    "DATOS_*.md",
    "DEBUG_*.md",
    "DESCONEXION_*.md",
    "DIAGNOSTICO_*.md",
    "EFECTIVIDAD_*.md",
    "EJEMPLO_*.md",
    "ERRORES_*.md",
    "ESTADO_*.md",
    "ESTRATEGIA_*.md",
    "EXPLICACION_*.md",
    "FIRMA_*.md",
    "FIX_*.md",
    "GUIA_*.md",
    "IMPLEMENTACION_*.md",
    "INICIAR_*.md",
    "INTEGRACION_*.md",
    "MEJORA_*.md",
    "MEJORAS_*.md",
    "MIGRACION_*.md",
    "NUEVA_*.md",
    "NUEVO_*.md",
    "PANEL_*.md",
    "PARAMETROS_*.md",
    "PESO_*.md",
    "RECONEXION_*.md",
    "RESPUESTAS_*.md",
    "RESUMEN_*.md",
    "SEÑALES_*.md",
    "SOLUCION_*.md",
    "TRADING_*.md",
    "VERIFICACION_*.md",
]

def eliminar_docs_antiguos():
    """Elimina documentación antigua"""
    print("🧹 Limpiando documentación antigua...\n")
    
    eliminados = 0
    mantenidos = 0
    
    # Buscar todos los archivos .md en el directorio raíz
    for archivo in ROOT_DIR.glob("*.md"):
        nombre = archivo.name
        
        # Verificar si está en la lista de mantener
        if nombre in MANTENER:
            print(f"  ✅ Mantenido: {nombre}")
            mantenidos += 1
            continue
        
        # Verificar si coincide con algún patrón a eliminar
        debe_eliminar = False
        for patron in PATRONES_ELIMINAR:
            if archivo.match(patron):
                debe_eliminar = True
                break
        
        if debe_eliminar:
            try:
                archivo.unlink()
                print(f"  🗑️  Eliminado: {nombre}")
                eliminados += 1
            except Exception as e:
                print(f"  ❌ Error eliminando {nombre}: {e}")
        else:
            print(f"  ⚠️  No clasificado: {nombre}")
    
    print(f"\n✅ Limpieza completada:")
    print(f"   • Eliminados: {eliminados} archivos")
    print(f"   • Mantenidos: {mantenidos} archivos")

if __name__ == "__main__":
    print("="*60)
    print("LIMPIEZA DE DOCUMENTACIÓN ANTIGUA")
    print("="*60)
    print()
    print("Se eliminarán archivos de documentación antiguos.")
    print("Se mantendrán: README.md y documentos esenciales")
    print()
    
    respuesta = input("¿Deseas continuar? (S/N): ")
    
    if respuesta.upper() == "S":
        eliminar_docs_antiguos()
    else:
        print("\n❌ Limpieza cancelada")
