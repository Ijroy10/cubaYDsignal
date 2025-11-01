#!/usr/bin/env python3
"""
Script para crear la estructura profesional del proyecto CubaYDSignal
"""

import os
import shutil

def create_professional_structure():
    """Crea la estructura profesional de carpetas"""
    
    # Estructura de carpetas profesional
    folders = [
        # Código fuente principal
        "src",
        "src/core",           # Lógica central del bot
        "src/bot",            # Bot de Telegram
        "src/strategies",     # Estrategias de trading
        "src/analysis",       # Análisis técnico
        "src/utils",          # Utilidades
        "src/config",         # Configuraciones
        
        # Documentación
        "docs",
        "docs/api",
        "docs/strategies",
        "docs/user_guide",
        
        # Tests
        "tests",
        "tests/unit",
        "tests/integration",
        
        # Assets y recursos
        "assets",
        "assets/images",
        "assets/templates",
        
        # Scripts de utilidad
        "scripts",
        
        # Datos y logs (ya existen)
        # "data",
        # "logs",
    ]
    
    print("🏗️ Creando estructura profesional de carpetas...")
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Creada: {folder}")
    
    print("🎯 Estructura de carpetas creada exitosamente!")

if __name__ == "__main__":
    create_professional_structure()
