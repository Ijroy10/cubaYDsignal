#!/usr/bin/env python3
"""
Script de inicio automático para CubaYDSignal
============================================

Este script verifica la configuración y ejecuta el bot automáticamente.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_env_file():
    """Verifica si el archivo .env existe y está configurado."""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ Archivo .env no encontrado")
        return False
    
    required_vars = ['QUOTEX_EMAIL', 'QUOTEX_PASSWORD', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    found_vars = []
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
        for var in required_vars:
            if f"{var}=" in content:
                found_vars.append(var)
    
    missing_vars = set(required_vars) - set(found_vars)
    
    if missing_vars:
        print(f"❌ Variables faltantes en .env: {', '.join(missing_vars)}")
        return False
    
    print("✅ Archivo .env configurado correctamente")
    return True

def install_dependencies():
    """Instala las dependencias necesarias."""
    print("📦 Verificando e instalando dependencias...")
    
    try:
        # Verificar si pip está disponible
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      check=True, capture_output=True)
        
        # Instalar dependencias básicas
        packages = [
            "python-telegram-bot[job-queue]==20.7",
            "python-dotenv",
            "pandas",
            "numpy",
            "requests",
            "asyncio"
        ]
        
        for package in packages:
            print(f"📦 Instalando {package}...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", package], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {package} instalado")
            else:
                print(f"⚠️ {package} - {result.stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False

def main():
    """Función principal de inicio."""
    print("\n" + "="*60)
    print("🚀 CUBAYDSIGNAL - INICIO AUTOMÁTICO")
    print("="*60)
    
    # Paso 1: Verificar configuración
    print("\n📋 PASO 1: Verificando configuración...")
    
    if not check_env_file():
        print("\n🔧 Ejecutando configuración automática...")
        try:
            import setup_env
            setup_env.setup_environment()
        except Exception as e:
            print(f"❌ Error en configuración: {e}")
            print("\n📝 Configura manualmente el archivo .env con:")
            print("   QUOTEX_EMAIL=tu_email")
            print("   QUOTEX_PASSWORD=tu_password")
            print("   TELEGRAM_BOT_TOKEN=tu_token")
            print("   TELEGRAM_CHAT_ID=tu_chat_id")
            return
    
    # Paso 2: Instalar dependencias
    print("\n📦 PASO 2: Verificando dependencias...")
    
    if not install_dependencies():
        print("❌ Error instalando dependencias")
        return
    
    # Paso 3: Ejecutar bot
    print("\n🚀 PASO 3: Iniciando bot...")
    print("="*60)
    
    try:
        # Importar y ejecutar el bot
        import run_bot_complete_fixed
        print("✅ Bot iniciado correctamente")
        
    except KeyboardInterrupt:
        print("\n⚠️ Bot detenido por usuario")
    except Exception as e:
        print(f"\n💥 Error ejecutando bot: {e}")
        print("\n🔧 Soluciones posibles:")
        print("1. Verifica tu conexión a internet")
        print("2. Revisa las credenciales en .env")
        print("3. Asegúrate de que Quotex esté accesible")
        print("4. Verifica el token de Telegram")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Inicio cancelado por usuario")
    except Exception as e:
        print(f"\n💥 Error fatal: {e}")
