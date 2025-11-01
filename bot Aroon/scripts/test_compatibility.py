#!/usr/bin/env python3
"""
Test de compatibilidad simple para validar que el nuevo sistema
funcione correctamente con la versión específica de quotexpy del proyecto
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
from src.core.market_manager_improved import MarketManagerImproved

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

async def test_quotex_instance():
    """Prueba básica de creación de instancia Quotex."""
    print("🧪 TEST 1: Creación de instancia Quotex")
    print("-" * 40)
    
    try:
        from quotexpy import Quotex
        
        # Crear instancia sin conectar
        quotex = Quotex(email="test@example.com", password="test123", headless=True)
        print("✅ Instancia Quotex creada exitosamente")
        
        # Verificar propiedades disponibles
        print(f"   📧 Email: {quotex.email}")
        print(f"   🔧 API disponible: {hasattr(quotex, 'api')}")
        
        if hasattr(quotex, 'api'):
            print(f"   🔌 API inicializada: {quotex.api is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando instancia Quotex: {e}")
        return False

async def test_connection_manager_creation():
    """Prueba creación del gestor de conexión."""
    print("\n🧪 TEST 2: Creación de QuotexConnectionManager")
    print("-" * 50)
    
    try:
        manager = QuotexConnectionManager("test@example.com", "test123")
        print("✅ QuotexConnectionManager creado exitosamente")
        
        # Verificar propiedades
        print(f"   📧 Email: {manager.email}")
        print(f"   🔐 Password: {'*' * len(manager.password)}")
        print(f"   📁 Data dir: {manager.data_dir}")
        print(f"   🔄 Max intentos: {manager.max_reconnect_attempts}")
        print(f"   ⏱️ Delay reconexión: {manager.reconnect_delay}s")
        
        # Verificar estado inicial
        status = manager.get_connection_status()
        print(f"   🔌 Estado inicial: {status['connected']}")
        print(f"   🚫 En cooldown 403: {status['in_403_cooldown']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando QuotexConnectionManager: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_market_manager_improved():
    """Prueba creación del MarketManager mejorado."""
    print("\n🧪 TEST 3: Creación de MarketManagerImproved")
    print("-" * 45)
    
    try:
        manager = MarketManagerImproved()
        print("✅ MarketManagerImproved creado exitosamente")
        
        # Verificar propiedades
        print(f"   📊 Mercados disponibles: {len(manager.mercados_disponibles)}")
        print(f"   🏪 Mercados OTC: {len(manager.mercados_otc)}")
        print(f"   💰 Payout mínimo: {manager.payout_minimo}%")
        print(f"   📁 Data dir: {manager.data_dir}")
        
        # Verificar estado inicial
        estado = manager.verificar_estado_conexion()
        print(f"   🔌 Conectado: {estado['conectado']}")
        print(f"   🏗️ Instancia Quotex: {estado['quotex_instance']}")
        print(f"   🎯 Listo para trading: {manager.is_ready_for_trading()}")
        
        # Verificar métodos de evaluación
        should_trade, reason = manager.should_attempt_trading()
        print(f"   📈 Debe hacer trading: {should_trade}")
        print(f"   📝 Razón: {reason}")
        
        # Verificar salud de conexión
        health = manager.get_connection_health_score()
        print(f"   💚 Salud conexión: {health:.2f}/1.0")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando MarketManagerImproved: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_connection_attempt():
    """Prueba intento de conexión real (solo si hay credenciales)."""
    print("\n🧪 TEST 4: Intento de conexión real")
    print("-" * 40)
    
    _load_dotenv_if_needed()
    email = os.environ.get("QUOTEX_EMAIL")
    password = os.environ.get("QUOTEX_PASSWORD")
    
    if not email or not password:
        print("⚠️ No hay credenciales disponibles - saltando test de conexión real")
        print("   Para probar conexión real, configura QUOTEX_EMAIL y QUOTEX_PASSWORD en .env")
        return True
    
    try:
        print(f"📧 Probando conexión con: {email}")
        
        # Crear gestor con timeout corto para prueba rápida
        manager = QuotexConnectionManager(email, password)
        manager.connection_timeout = 30  # 30 segundos para prueba rápida
        
        print("⏳ Intentando conexión (timeout: 30s)...")
        
        # Intentar conexión
        success = await manager.connect()
        
        if success:
            print("✅ Conexión exitosa!")
            
            # Obtener información básica
            status = manager.get_connection_status()
            print(f"   🕐 Conectado desde: {status.get('connection_timestamp', 'N/A')}")
            print(f"   🎯 Listo para trading: {manager.is_ready_for_trading()}")
            
            # Intentar obtener balance
            if manager.quotex:
                try:
                    balance = await manager.quotex.get_balance()
                    print(f"   💰 Balance: ${balance}")
                except Exception as e:
                    print(f"   ⚠️ Error obteniendo balance: {e}")
            
            # Desconectar
            await manager.disconnect()
            print("   🔌 Desconectado limpiamente")
            
        else:
            print("❌ Conexión falló")
            status = manager.get_connection_status()
            if status.get('last_error'):
                print(f"   💥 Error: {status['last_error']}")
            if status.get('in_403_cooldown'):
                print(f"   🚫 En cooldown 403")
        
        return success
        
    except Exception as e:
        print(f"❌ Error en test de conexión: {e}")
        return False

async def test_integration():
    """Prueba integración entre componentes."""
    print("\n🧪 TEST 5: Integración de componentes")
    print("-" * 40)
    
    try:
        # Crear MarketManager mejorado
        market_manager = MarketManagerImproved()
        
        # Verificar que los métodos auxiliares funcionen
        print("📊 Probando métodos auxiliares...")
        
        # Test métodos de verificación
        ws_connected = market_manager._check_websocket_connected()
        ws_thread = market_manager._check_websocket_thread_alive()
        
        print(f"   🌐 WebSocket conectado: {ws_connected}")
        print(f"   🧵 Thread WebSocket vivo: {ws_thread}")
        
        # Test evaluación de trading
        should_trade, reason = market_manager.should_attempt_trading()
        print(f"   📈 Evaluación trading: {should_trade} - {reason}")
        
        # Test horario permitido
        en_horario = market_manager.esta_en_horario_permitido()
        print(f"   🕐 En horario permitido: {en_horario}")
        
        # Test obtener mejor mercado
        mejor_mercado = market_manager.obtener_mejor_mercado()
        print(f"   🎯 Mejor mercado: {mejor_mercado}")
        
        print("✅ Integración de componentes exitosa")
        return True
        
    except Exception as e:
        print(f"❌ Error en test de integración: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Función principal de pruebas de compatibilidad."""
    print("🚀 SUITE DE PRUEBAS DE COMPATIBILIDAD")
    print("="*60)
    print(f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Directorio: {ROOT}")
    print("="*60)
    
    # Configurar logging básico
    logging.basicConfig(
        level=logging.WARNING,  # Solo mostrar warnings y errores
        format='%(levelname)s: %(message)s'
    )
    
    # Ejecutar tests
    tests = [
        ("Instancia Quotex", test_quotex_instance),
        ("Connection Manager", test_connection_manager_creation),
        ("Market Manager Improved", test_market_manager_improved),
        ("Conexión Real", test_connection_attempt),
        ("Integración", test_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n💥 Error inesperado en {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas de compatibilidad pasaron!")
        print("\n📝 Próximos pasos:")
        print("   1. El sistema mejorado está listo para usar")
        print("   2. Puedes integrar MarketManagerImproved en tu bot principal")
        print("   3. Ejecuta test_bot_integration.py para pruebas completas")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
    
    print("\n✅ Suite de pruebas completada")

if __name__ == "__main__":
    asyncio.run(main())
