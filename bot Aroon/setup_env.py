#!/usr/bin/env python3
"""
Script de configuración automática para CubaYDSignal
==================================================

Este script ayuda a configurar correctamente el archivo .env
con todas las variables necesarias para el bot.
"""

import os
from pathlib import Path

def setup_environment():
    """Configura el archivo .env con las variables necesarias."""
    
    print("🔧 CONFIGURACIÓN DE CUBAYDSIGNAL")
    print("=" * 50)
    
    env_path = Path(".env")
    
    # Leer archivo .env existente si existe
    existing_vars = {}
    if env_path.exists():
        print("📄 Archivo .env existente encontrado")
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    existing_vars[key.strip()] = value.strip().strip('"').strip("'")
    
    # Variables requeridas
    required_vars = {
        'QUOTEX_EMAIL': 'Email de tu cuenta Quotex',
        'QUOTEX_PASSWORD': 'Contraseña de tu cuenta Quotex',
        'TELEGRAM_BOT_TOKEN': 'Token del bot de Telegram (obtener de @BotFather)',
        'TELEGRAM_CHAT_ID': 'ID del chat de Telegram (tu ID de usuario)'
    }
    
    # Recopilar valores
    new_vars = {}
    
    for var_name, description in required_vars.items():
        current_value = existing_vars.get(var_name, '')
        
        if current_value:
            print(f"\n✅ {var_name}: {current_value[:20]}{'...' if len(current_value) > 20 else ''}")
            use_existing = input(f"¿Mantener este valor? (s/n): ").lower().strip()
            
            if use_existing in ['s', 'si', 'y', 'yes', '']:
                new_vars[var_name] = current_value
                continue
        
        print(f"\n📝 {description}")
        while True:
            value = input(f"Ingresa {var_name}: ").strip()
            if value:
                new_vars[var_name] = value
                break
            print("❌ Este campo es obligatorio")
    
    # Escribir archivo .env
    print(f"\n💾 Guardando configuración en {env_path}...")
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write("# Configuración CubaYDSignal\n")
        f.write("# ===========================\n\n")
        
        f.write("# Credenciales Quotex\n")
        f.write(f'QUOTEX_EMAIL={new_vars["QUOTEX_EMAIL"]}\n')
        f.write(f'QUOTEX_PASSWORD={new_vars["QUOTEX_PASSWORD"]}\n\n')
        
        f.write("# Configuración Telegram\n")
        f.write(f'TELEGRAM_BOT_TOKEN={new_vars["TELEGRAM_BOT_TOKEN"]}\n')
        f.write(f'TELEGRAM_CHAT_ID={new_vars["TELEGRAM_CHAT_ID"]}\n\n')
        
        f.write("# Configuración adicional\n")
        f.write("# QUOTEX_HEADLESS=false\n")
        f.write("# DEBUG_MODE=false\n")
    
    print("✅ Archivo .env configurado correctamente")
    
    # Verificar configuración
    print("\n🔍 VERIFICANDO CONFIGURACIÓN:")
    print("-" * 30)
    
    for var_name in required_vars:
        value = new_vars[var_name]
        if var_name == 'QUOTEX_PASSWORD':
            display_value = '*' * len(value)
        elif var_name == 'TELEGRAM_BOT_TOKEN':
            display_value = value[:10] + '...' + value[-10:] if len(value) > 20 else value
        else:
            display_value = value
        
        print(f"✅ {var_name}: {display_value}")
    
    print("\n🎉 CONFIGURACIÓN COMPLETADA")
    print("=" * 50)
    print("🚀 Ahora puedes ejecutar el bot con:")
    print("   python run_bot_complete_fixed.py")
    print("\n📱 Para obtener tu TELEGRAM_CHAT_ID:")
    print("   1. Envía un mensaje a tu bot")
    print("   2. Visita: https://api.telegram.org/bot<TOKEN>/getUpdates")
    print("   3. Busca el campo 'id' en 'from' o 'chat'")

def verify_dependencies():
    """Verifica que las dependencias estén instaladas."""
    
    print("\n🔍 VERIFICANDO DEPENDENCIAS:")
    print("-" * 30)
    
    required_packages = [
        'python-telegram-bot',
        'quotexpy',
        'python-dotenv',
        'asyncio',
        'pandas',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'python-telegram-bot':
                import telegram
            elif package == 'quotexpy':
                # Verificar si existe la carpeta local
                if os.path.exists('quotexpy'):
                    print(f"✅ {package}: Librería local encontrada")
                    continue
                else:
                    import quotexpy
            elif package == 'python-dotenv':
                import dotenv
            elif package == 'asyncio':
                import asyncio
            elif package == 'pandas':
                import pandas
            elif package == 'numpy':
                import numpy
            
            print(f"✅ {package}: Instalado")
            
        except ImportError:
            print(f"❌ {package}: NO instalado")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ DEPENDENCIAS FALTANTES:")
        print("Ejecuta el siguiente comando para instalarlas:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    else:
        print("\n✅ Todas las dependencias están instaladas")
        return True

if __name__ == "__main__":
    try:
        # Verificar dependencias
        deps_ok = verify_dependencies()
        
        if deps_ok:
            # Configurar entorno
            setup_environment()
        else:
            print("\n❌ Instala las dependencias faltantes antes de continuar")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Configuración cancelada por usuario")
    except Exception as e:
        print(f"\n💥 Error durante la configuración: {e}")
