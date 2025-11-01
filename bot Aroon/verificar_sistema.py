"""
Script de Verificación del Sistema - CubaYDSignal Bot
Verifica que todo esté listo antes de ejecutar el bot
"""
import sys
import os
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_check(text, status):
    emoji = "✅" if status else "❌"
    print(f"{emoji} {text}")
    return status

def verificar_python():
    """Verifica versión de Python"""
    print_header("1. VERIFICACIÓN DE PYTHON")
    version = sys.version_info
    print(f"Versión de Python: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 12:
        print_check("Python 3.12+ detectado", True)
        return True
    else:
        print_check(f"Python 3.12+ requerido (tienes {version.major}.{version.minor})", False)
        return False

def verificar_dependencias():
    """Verifica que las dependencias estén instaladas"""
    print_header("2. VERIFICACIÓN DE DEPENDENCIAS")
    
    dependencias = {
        'pyquotex': 'pyquotex',
        'pandas': 'pandas',
        'telegram': 'python-telegram-bot',
        'dotenv': 'python-dotenv',
        'loguru': 'loguru',
        'ta': 'ta'
    }
    
    todas_ok = True
    for modulo, nombre in dependencias.items():
        try:
            __import__(modulo)
            print_check(f"{nombre} instalado", True)
        except ImportError:
            print_check(f"{nombre} NO instalado", False)
            todas_ok = False
    
    return todas_ok

def verificar_env():
    """Verifica archivo .env"""
    print_header("3. VERIFICACIÓN DE CONFIGURACIÓN (.env)")
    
    if not os.path.exists('.env'):
        print_check("Archivo .env existe", False)
        return False
    
    print_check("Archivo .env existe", True)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    variables_requeridas = {
        'TELEGRAM_BOT_TOKEN': 'Token del bot de Telegram',
        'ADMIN_ID': 'ID del administrador',
        'QUOTEX_EMAIL': 'Email de Quotex',
        'QUOTEX_PASSWORD': 'Contraseña de Quotex'
    }
    
    todas_ok = True
    for var, desc in variables_requeridas.items():
        valor = os.getenv(var)
        if valor:
            # Ocultar valores sensibles
            if 'PASSWORD' in var or 'TOKEN' in var:
                valor_mostrar = valor[:4] + "..." + valor[-4:] if len(valor) > 8 else "***"
            else:
                valor_mostrar = valor
            print_check(f"{desc}: {valor_mostrar}", True)
        else:
            print_check(f"{desc}: NO configurado", False)
            todas_ok = False
    
    return todas_ok

def verificar_estructura():
    """Verifica estructura de directorios"""
    print_header("4. VERIFICACIÓN DE ESTRUCTURA")
    
    directorios = [
        'src/core',
        'src/strategies',
        'src/bot',
        'estrategias',
        'data'
    ]
    
    todas_ok = True
    for dir_path in directorios:
        existe = os.path.exists(dir_path)
        print_check(f"Directorio {dir_path}", existe)
        if not existe:
            todas_ok = False
    
    return todas_ok

def verificar_archivos_clave():
    """Verifica archivos clave del bot"""
    print_header("5. VERIFICACIÓN DE ARCHIVOS CLAVE")
    
    archivos = [
        'src/core/market_manager.py',
        'src/core/signal_scheduler.py',
        'src/core/main.py',
        'src/bot/telegram_bot.py',
        'src/strategies/evaluar_estrategia_completa.py',
        'estrategias/evaluar_estrategia_completa.py'
    ]
    
    todas_ok = True
    for archivo in archivos:
        existe = os.path.exists(archivo)
        print_check(f"{archivo}", existe)
        if not existe:
            todas_ok = False
    
    return todas_ok

def test_conexion_quotex():
    """Prueba conexión a Quotex"""
    print_header("6. PRUEBA DE CONEXIÓN A QUOTEX")
    
    try:
        import asyncio
        from dotenv import load_dotenv
        load_dotenv()
        
        from pyquotex.stable_api import Quotex
        
        email = os.getenv('QUOTEX_EMAIL')
        password = os.getenv('QUOTEX_PASSWORD')
        
        async def test():
            try:
                print("Conectando a Quotex...")
                client = Quotex(email=email, password=password, lang="es")
                client.set_account_mode("PRACTICE")
                
                check, reason = await client.connect()
                
                if check:
                    print_check(f"Conexión exitosa: {reason}", True)
                    
                    # Verificar conexión
                    is_connected = await client.check_connect()
                    print_check(f"Estado de conexión verificado", is_connected)
                    
                    # Cerrar
                    await client.close()
                    print_check("Desconexión exitosa", True)
                    return True
                else:
                    print_check(f"Conexión fallida: {reason}", False)
                    return False
            except Exception as e:
                print_check(f"Error: {str(e)}", False)
                return False
        
        resultado = asyncio.run(test())
        return resultado
        
    except Exception as e:
        print_check(f"Error en prueba: {str(e)}", False)
        return False

def generar_reporte():
    """Genera reporte final"""
    print_header("RESUMEN DE VERIFICACIÓN")
    
    checks = {
        'Python 3.12+': verificar_python(),
        'Dependencias': verificar_dependencias(),
        'Configuración (.env)': verificar_env(),
        'Estructura de directorios': verificar_estructura(),
        'Archivos clave': verificar_archivos_clave(),
        'Conexión a Quotex': test_conexion_quotex()
    }
    
    print("\n" + "="*60)
    print("  RESULTADO FINAL")
    print("="*60)
    
    total = len(checks)
    exitosos = sum(1 for v in checks.values() if v)
    
    for nombre, resultado in checks.items():
        emoji = "✅" if resultado else "❌"
        print(f"{emoji} {nombre}")
    
    print("\n" + "-"*60)
    print(f"Verificaciones exitosas: {exitosos}/{total}")
    print("-"*60)
    
    if exitosos == total:
        print("\n🎉 ¡TODO LISTO! El bot está preparado para ejecutarse.")
        print("\nPara iniciar el bot, ejecuta:")
        print("  python run_bot.py")
        return True
    else:
        print("\n⚠️ Hay problemas que resolver antes de ejecutar el bot.")
        print("\nRevisa los errores marcados con ❌ arriba.")
        return False

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║         VERIFICACIÓN DEL SISTEMA - CubaYDSignal         ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        sistema_ok = generar_reporte()
        sys.exit(0 if sistema_ok else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Verificación cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
