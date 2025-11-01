#!/usr/bin/env python3
"""
Script de inicio optimizado para CubaYDSignal Bot Unificado
===========================================================

🚀 CARACTERÍSTICAS:
✅ Verificación automática de dependencias
✅ Configuración automática del entorno
✅ Manejo robusto de errores
✅ Bypass Cloudflare integrado
✅ Logs detallados para debugging

🛡️ MODO PRACTICE (cuenta demo) - SIN RIESGO FINANCIERO
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
import asyncio
import traceback

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_startup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def print_banner():
    """Muestra banner de inicio."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║               🚀 CUBAYDSIGNAL BOT LAUNCHER 🚀                ║
║                    VERSIÓN UNIFICADA                         ║
╠══════════════════════════════════════════════════════════════╣
║  🔧 Verificando dependencias...                              ║
║  🔧 Configurando entorno...                                  ║
║  🚀 Iniciando bot con bypass Cloudflare...                   ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_python_version():
    """Verifica la versión de Python."""
    if sys.version_info < (3, 8):
        logger.error("❌ Se requiere Python 3.8 o superior")
        logger.error(f"📊 Versión actual: {sys.version}")
        return False
    
    logger.info(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def install_package(package_name):
    """Instala un paquete usando pip."""
    try:
        logger.info(f"📦 Instalando {package_name}...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", package_name
        ], capture_output=True, text=True, check=True)
        logger.info(f"✅ {package_name} instalado correctamente")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error instalando {package_name}: {e}")
        logger.error(f"📋 Output: {e.stdout}")
        logger.error(f"📋 Error: {e.stderr}")
        return False

def check_and_install_dependencies():
    """Verifica e instala las dependencias necesarias."""
    required_packages = [
        'cloudscraper',
        'python-telegram-bot',
        'python-dotenv',
        'requests',
        'asyncio'
    ]
    
    logger.info("🔍 Verificando dependencias...")
    
    for package in required_packages:
        try:
            if package == 'python-telegram-bot':
                import telegram
            elif package == 'python-dotenv':
                import dotenv
            elif package == 'cloudscraper':
                import cloudscraper
            elif package == 'requests':
                import requests
            elif package == 'asyncio':
                import asyncio
            
            logger.info(f"✅ {package} disponible")
            
        except ImportError:
            logger.warning(f"⚠️ {package} no encontrado, instalando...")
            if not install_package(package):
                return False
    
    return True

def check_quotexpy():
    """Verifica que quotexpy esté disponible."""
    project_root = Path(__file__).parent
    quotexpy_path = project_root / "quotexpy"
    
    if quotexpy_path.exists():
        logger.info("✅ quotexpy local encontrado")
        return True
    
    try:
        import quotexpy
        logger.info("✅ quotexpy instalado globalmente")
        return True
    except ImportError:
        logger.error("❌ quotexpy no encontrado")
        logger.error("💡 Asegúrate de que la carpeta 'quotexpy' esté en el directorio del proyecto")
        return False

def check_env_file():
    """Verifica que el archivo .env exista y tenga las variables necesarias."""
    env_path = Path(__file__).parent / ".env"
    
    if not env_path.exists():
        logger.error("❌ Archivo .env no encontrado")
        logger.error("💡 Crea un archivo .env con las siguientes variables:")
        logger.error("   QUOTEX_EMAIL=tu_email@ejemplo.com")
        logger.error("   QUOTEX_PASSWORD=tu_password")
        logger.error("   TELEGRAM_BOT_TOKEN=tu_bot_token")
        logger.error("   TELEGRAM_CHAT_ID=tu_chat_id")
        return False
    
    # Verificar variables requeridas
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['QUOTEX_EMAIL', 'QUOTEX_PASSWORD', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Variables faltantes en .env: {missing_vars}")
        return False
    
    logger.info("✅ Archivo .env configurado correctamente")
    return True

def check_system_requirements():
    """Verifica todos los requisitos del sistema."""
    logger.info("🔍 Verificando requisitos del sistema...")
    
    checks = [
        ("Versión de Python", check_python_version),
        ("Dependencias", check_and_install_dependencies),
        ("QuotexPy", check_quotexpy),
        ("Configuración .env", check_env_file)
    ]
    
    for check_name, check_func in checks:
        logger.info(f"🔄 Verificando {check_name}...")
        if not check_func():
            logger.error(f"❌ Error en verificación: {check_name}")
            return False
        logger.info(f"✅ {check_name} OK")
    
    return True

def run_unified_bot():
    """Ejecuta el bot unificado."""
    try:
        logger.info("🚀 Iniciando bot unificado...")
        
        # Importar y ejecutar el bot
        bot_path = Path(__file__).parent / "run_bot_unified.py"
        
        if not bot_path.exists():
            logger.error("❌ Archivo run_bot_unified.py no encontrado")
            return False
        
        # Ejecutar el bot
        result = subprocess.run([
            sys.executable, str(bot_path)
        ], cwd=str(Path(__file__).parent))
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando bot: {e}")
        traceback.print_exc()
        return False

def main():
    """Función principal del launcher."""
    print_banner()
    
    try:
        # Verificar requisitos del sistema
        if not check_system_requirements():
            logger.error("❌ Verificación de requisitos fallida")
            input("Presiona Enter para salir...")
            return 1
        
        logger.info("✅ Todos los requisitos verificados correctamente")
        logger.info("🚀 Iniciando CubaYDSignal Bot...")
        
        # Ejecutar el bot
        if run_unified_bot():
            logger.info("✅ Bot ejecutado correctamente")
            return 0
        else:
            logger.error("❌ Error ejecutando el bot")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Launcher detenido por el usuario")
        return 0
    except Exception as e:
        logger.error(f"❌ Error crítico en launcher: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    if exit_code != 0:
        input("Presiona Enter para salir...")
    sys.exit(exit_code)
