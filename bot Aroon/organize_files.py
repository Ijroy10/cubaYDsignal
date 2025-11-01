#!/usr/bin/env python3
"""
Script para organizar archivos en la estructura profesional del proyecto CubaYDSignal
"""

import os
import shutil
from pathlib import Path

def organize_files():
    """Organiza todos los archivos en la estructura profesional"""
    
    print("📁 Organizando archivos en estructura profesional...")
    
    # Mapeo de archivos a sus nuevas ubicaciones
    file_moves = {
        # Archivos principales del core
        "main_enhanced.py": "src/core/main.py",
        "market_manager.py": "src/core/market_manager.py",
        "user_manager.py": "src/core/user_manager.py",
        "signal_scheduler.py": "src/core/signal_scheduler.py",
        "adaptive_learning.py": "src/core/adaptive_learning.py",
        
        # Bot de Telegram
        "telegram_bot.py": "src/bot/telegram_bot.py",
        
        # Configuración
        "config.py": "src/config/settings.py",
        ".env": "src/config/.env",
        ".env.example": "src/config/.env.example",
        
        # Utilidades
        "send_telegram.py": "src/utils/telegram_utils.py",
        
        # Scripts
        "test_quotex.py": "scripts/test_quotex.py",
        "iniciar_bot.bat": "scripts/start_bot.bat",
        
        # Archivos de proyecto
        "requirements.txt": "requirements.txt",  # Se queda en raíz
        "main.py": "main.py",  # Archivo principal en raíz
    }
    
    # Mover archivos individuales
    for source, destination in file_moves.items():
        if os.path.exists(source):
            # Crear directorio de destino si no existe
            dest_dir = os.path.dirname(destination)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
            
            try:
                shutil.move(source, destination)
                print(f"✅ Movido: {source} → {destination}")
            except Exception as e:
                print(f"⚠️  Error moviendo {source}: {e}")
        else:
            print(f"⚠️  Archivo no encontrado: {source}")
    
    # Mover carpetas completas
    folder_moves = {
        "strategy": "src/strategies",
        "handlers": "src/bot/handlers",
        "messages": "src/bot/messages",
        "utils": "src/utils/legacy",  # Mover utils existente como legacy
    }
    
    for source, destination in folder_moves.items():
        if os.path.exists(source) and os.path.isdir(source):
            try:
                if os.path.exists(destination):
                    # Si el destino existe, mover contenido
                    for item in os.listdir(source):
                        src_item = os.path.join(source, item)
                        dst_item = os.path.join(destination, item)
                        if os.path.isdir(src_item):
                            shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src_item, dst_item)
                    shutil.rmtree(source)
                else:
                    shutil.move(source, destination)
                print(f"✅ Carpeta movida: {source} → {destination}")
            except Exception as e:
                print(f"⚠️  Error moviendo carpeta {source}: {e}")
    
    print("🎯 Organización de archivos completada!")

def create_init_files():
    """Crea archivos __init__.py para hacer los directorios paquetes Python"""
    
    print("📦 Creando archivos __init__.py...")
    
    init_dirs = [
        "src",
        "src/core",
        "src/bot",
        "src/strategies",
        "src/analysis",
        "src/utils",
        "src/config",
    ]
    
    for directory in init_dirs:
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(f'"""\\n{directory.replace("/", ".").replace("src.", "")} module\\n"""\\n')
            print(f"✅ Creado: {init_file}")

if __name__ == "__main__":
    organize_files()
    create_init_files()
