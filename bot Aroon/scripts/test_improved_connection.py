#!/usr/bin/env python3
"""
Script de prueba para el nuevo QuotexConnectionManager
Demuestra la lógica mejorada de conexión y reconexión
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Configurar path para usar módulos locales
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "quotexpy"))

from src.core.quotex_connection_manager import QuotexConnectionManager

def _load_dotenv_if_needed():
    """Carga variables desde .env si no están en el entorno."""
    env_path = os.path.join(ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if os.environ.get(k) is None:
                    os.environ[k] = v
    except Exception as e:
        print(f"⚠️ Error cargando .env: {e}")

def mostrar_estado_conexion(status):
    """Muestra el estado de conexión de manera organizada."""
    print("\n" + "="*60)
    print("🔌 ESTADO DE CONEXIÓN QUOTEX")
    print("="*60)
    
    # Estado principal
    estado_emoji = "✅" if status["connected"] else "❌"
    print(f"{estado_emoji} Conectado: {status['connected']}")
    print(f"📧 Email: {status['email']}")
    
    if status["connection_timestamp"]:
        print(f"🕐 Conectado desde: {status['connection_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Detalles técnicos
    print(f"\n📊 DETALLES TÉCNICOS:")
    print(f"   🏗️ Instancia Quotex: {'✅' if status['quotex_instance'] else '❌'}")
    
    if "quotex_check_connect" in status:
        print(f"   🔗 check_connect(): {'✅' if status['quotex_check_connect'] else '❌'}")
    
    if "has_ssid" in status:
        print(f"   🔑 SSID presente: {'✅' if status['has_ssid'] else '❌'}")
    
    if "websocket_error" in status:
        print(f"   🌐 WebSocket error: {'❌' if status['websocket_error'] else '✅'}")
    
    # Control de bloqueos
    if status["in_403_cooldown"]:
        remaining_min = status["cooldown_remaining"] // 60
        print(f"\n🚫 EN COOLDOWN 403: {remaining_min} minutos restantes")
    
    # Errores
    if status["last_error"]:
        print(f"\n❌ Último error: {status['last_error']}")
    
    print("="*60)

async def test_connection_manager():
    """Prueba el gestor de conexión mejorado."""
    print("🚀 INICIANDO PRUEBA DEL GESTOR DE CONEXIÓN MEJORADO")
    print("="*60)
    
    # Cargar credenciales
    _load_dotenv_if_needed()
    email = os.environ.get("QUOTEX_EMAIL")
    password = os.environ.get("QUOTEX_PASSWORD")
    
    if not email or not password:
        print("❌ Faltan credenciales QUOTEX_EMAIL y/o QUOTEX_PASSWORD en .env")
        return
    
    # Crear gestor de conexión
    connection_manager = QuotexConnectionManager(email, password)
    
    try:
        print(f"📧 Probando conexión para: {email}")
        print("⏳ Iniciando proceso de conexión...")
        
        # Intentar conexión
        success = await connection_manager.connect()
        
        # Mostrar estado después del intento
        status = connection_manager.get_connection_status()
        mostrar_estado_conexion(status)
        
        if success:
            print("\n✅ CONEXIÓN EXITOSA!")
            
            # Probar funcionalidades básicas
            print("\n🧪 PROBANDO FUNCIONALIDADES BÁSICAS:")
            
            try:
                # Verificar balance
                if connection_manager.quotex:
                    balance = await connection_manager.quotex.get_balance()
                    print(f"💰 Balance: ${balance}")
                
                # Verificar si está listo para trading
                ready = connection_manager.is_ready_for_trading()
                print(f"🎯 Listo para trading: {'✅' if ready else '❌'}")
                
                # Probar ensure_connected
                print("\n🔄 Probando ensure_connected()...")
                ensured = await connection_manager.ensure_connected()
                print(f"🔄 ensure_connected(): {'✅' if ensured else '❌'}")
                
            except Exception as e:
                print(f"❌ Error en pruebas básicas: {e}")
            
            # Mantener conexión por un momento para observar
            print("\n⏳ Manteniendo conexión por 30 segundos para observación...")
            await asyncio.sleep(30)
            
            # Verificar estado final
            final_status = connection_manager.get_connection_status()
            print("\n📊 ESTADO FINAL:")
            mostrar_estado_conexion(final_status)
            
        else:
            print("\n❌ CONEXIÓN FALLÓ")
            print("🔍 Revisa los logs arriba para más detalles")
            
            # Mostrar información de diagnóstico
            if status["in_403_cooldown"]:
                print(f"\n🚫 Bot en cooldown por bloqueo 403")
                print(f"⏰ Tiempo restante: {status['cooldown_remaining']//60} minutos")
            
    except Exception as e:
        print(f"\n💥 ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Limpiar recursos
        print("\n🧹 Limpiando recursos...")
        await connection_manager.disconnect()
        print("✅ Limpieza completada")

async def test_reconnection_logic():
    """Prueba específica de la lógica de reconexión."""
    print("\n" + "="*60)
    print("🔄 PRUEBA DE LÓGICA DE RECONEXIÓN")
    print("="*60)
    
    _load_dotenv_if_needed()
    email = os.environ.get("QUOTEX_EMAIL")
    password = os.environ.get("QUOTEX_PASSWORD")
    
    if not email or not password:
        print("❌ Faltan credenciales")
        return
    
    connection_manager = QuotexConnectionManager(email, password)
    
    try:
        # Primera conexión
        print("1️⃣ Primera conexión...")
        success1 = await connection_manager.connect()
        print(f"   Resultado: {'✅' if success1 else '❌'}")
        
        if success1:
            # Simular desconexión forzada
            print("\n2️⃣ Simulando desconexión forzada...")
            connection_manager.connected = False
            
            # Intentar ensure_connected (debería reconectar)
            print("3️⃣ Probando ensure_connected() tras desconexión...")
            success2 = await connection_manager.ensure_connected()
            print(f"   Resultado: {'✅' if success2 else '❌'}")
            
            # Estado final
            final_status = connection_manager.get_connection_status()
            mostrar_estado_conexion(final_status)
        
    except Exception as e:
        print(f"❌ Error en prueba de reconexión: {e}")
    
    finally:
        await connection_manager.disconnect()

async def main():
    """Función principal de prueba."""
    print("🎯 SUITE DE PRUEBAS - QUOTEX CONNECTION MANAGER")
    print("="*60)
    
    # Configurar logging para ver detalles
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    try:
        # Prueba principal
        await test_connection_manager()
        
        # Prueba de reconexión
        await test_reconnection_logic()
        
        print("\n🎉 TODAS LAS PRUEBAS COMPLETADAS")
        
    except KeyboardInterrupt:
        print("\n⚠️ Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n💥 Error en suite de pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
