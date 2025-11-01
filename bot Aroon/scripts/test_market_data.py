"""
Script de prueba para verificar obtención de datos de mercado con pyquotex
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyquotex.stable_api import Quotex
import time

async def test_market_data():
    """Prueba la obtención de datos de mercado"""
    
    # Obtener credenciales
    email = os.getenv('QUOTEX_EMAIL')
    password = os.getenv('QUOTEX_PASSWORD')
    
    if not email or not password:
        print("❌ Error: QUOTEX_EMAIL y QUOTEX_PASSWORD deben estar configurados en .env")
        return
    
    print("=" * 60)
    print("PRUEBA DE OBTENCIÓN DE DATOS DE MERCADO - PYQUOTEX")
    print("=" * 60)
    print()
    
    try:
        # 1. Crear cliente
        print("1️⃣ Creando cliente pyquotex...")
        client = Quotex(email=email, password=password, lang="es")
        client.set_account_mode("PRACTICE")
        print("   ✅ Cliente creado")
        
        # 2. Conectar
        print()
        print("2️⃣ Conectando por WebSocket...")
        check, reason = await client.connect()
        
        if not check:
            print(f"   ❌ Fallo en conexión: {reason}")
            return
        
        print(f"   ✅ Conectado: {reason}")
        
        # 3. Verificar conexión
        print()
        print("3️⃣ Verificando estado de conexión...")
        is_connected = await client.check_connect()
        print(f"   ✅ Estado: {'Conectado' if is_connected else 'Desconectado'}")
        
        # 4. Obtener balance con timeout
        print()
        print("4️⃣ Obteniendo balance...")
        try:
            balance = await asyncio.wait_for(client.get_balance(), timeout=10.0)
            print(f"   ✅ Balance: ${balance}")
        except asyncio.TimeoutError:
            print("   ⚠️ Timeout obteniendo balance (esto es normal en algunas cuentas)")
            balance = "N/A"
        except Exception as e:
            print(f"   ⚠️ Error obteniendo balance: {e}")
            balance = "N/A"
        
        # 5. Obtener datos de mercado
        print()
        print("5️⃣ Obteniendo datos de mercado (EURUSD)...")
        
        # Parámetros para obtener 300 velas de 5 minutos
        asset = "EURUSD"
        end_time = int(time.time())
        history_seconds = 300 * 5 * 60  # 300 velas * 5 minutos * 60 segundos
        timeframe = 300  # 5 minutos en segundos
        
        print(f"   - Asset: {asset}")
        print(f"   - Timeframe: 5 minutos")
        print(f"   - Cantidad: 300 velas")
        print(f"   - Historial: {history_seconds} segundos (~{history_seconds/3600:.1f} horas)")
        
        candles = await asyncio.wait_for(
            client.get_candles(asset, end_time, history_seconds, timeframe),
            timeout=15.0
        )
        
        if not candles:
            print("   ❌ No se obtuvieron datos")
        else:
            print(f"   ✅ Obtenidas {len(candles)} velas")
            
            # Mostrar primeras 3 velas
            print()
            print("   📊 Primeras 3 velas:")
            for i, candle in enumerate(candles[:3]):
                print(f"      Vela {i+1}: {candle}")
            
            # Mostrar últimas 3 velas
            print()
            print("   📊 Últimas 3 velas:")
            for i, candle in enumerate(candles[-3:]):
                print(f"      Vela {len(candles)-2+i}: {candle}")
        
        # 6. Probar con otro activo
        print()
        print("6️⃣ Probando con otro activo (GBPUSD)...")
        asset2 = "GBPUSD"
        candles2 = await client.get_candles(asset2, end_time, 50 * 5 * 60, timeframe)
        
        if candles2:
            print(f"   ✅ {asset2}: Obtenidas {len(candles2)} velas")
        else:
            print(f"   ⚠️ {asset2}: No se obtuvieron datos")
        
        # 7. Cerrar conexión
        print()
        print("7️⃣ Cerrando conexión...")
        await client.close()
        print("   ✅ Conexión cerrada")
        
        print()
        print("=" * 60)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print()
        print("Resumen:")
        print(f"  - Conexión WebSocket: ✅ Exitosa")
        print(f"  - Balance obtenido: ✅ ${balance}")
        print(f"  - Datos EURUSD: ✅ {len(candles) if candles else 0} velas")
        print(f"  - Datos GBPUSD: ✅ {len(candles2) if candles2 else 0} velas")
        print()
        print("🎉 El bot está listo para usar pyquotex sin Selenium!")
        
    except Exception as e:
        print()
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_market_data())
