#!/usr/bin/env python3
"""
Ejemplo completo del flujo del bot CubaYDSignal con el nuevo sistema de conexión
Demuestra la integración con el sistema de estrategias y notificaciones de Telegram
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
import json

# Configurar path para usar módulos locales
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "quotexpy"))

from src.core.market_manager_improved import MarketManagerImproved

class MockTelegramBot:
    """Mock del bot de Telegram para pruebas."""
    
    def __init__(self):
        self.messages_sent = []
    
    async def notificar_admin_telegram(self, mensaje: str):
        """Simula envío de notificación al admin."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n📱 [TELEGRAM {timestamp}] {mensaje}")
        self.messages_sent.append({"timestamp": timestamp, "message": mensaje})
    
    async def enviar_señal_trading(self, señal: dict):
        """Simula envío de señal de trading."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = "🟢" if señal["direccion"] == "CALL" else "🔴"
        mensaje = (
            f"{emoji} SEÑAL DE TRADING\n"
            f"💱 Par: {señal['par']}\n"
            f"📊 Dirección: {señal['direccion']}\n"
            f"⏰ Tiempo: {señal['tiempo']}\n"
            f"🎯 Efectividad: {señal['efectividad']}%\n"
            f"💰 Monto sugerido: ${señal['monto']}"
        )
        print(f"\n📱 [SEÑAL {timestamp}] {mensaje}")
        self.messages_sent.append({"timestamp": timestamp, "message": mensaje, "type": "signal"})

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

async def simular_analisis_estrategia(market_manager: MarketManagerImproved, par: str) -> dict:
    """
    Simula el análisis de estrategia completo que haría el bot real.
    En el bot real, esto integraría con el sistema de estrategias existente.
    """
    print(f"🔍 Analizando estrategia para {par}...")
    
    # Simular tiempo de análisis
    await asyncio.sleep(2)
    
    # Simular análisis técnico (en el bot real, esto vendría del sistema de estrategias)
    analisis = {
        "par": par,
        "timestamp": datetime.now(),
        "indicadores": {
            "rsi": 65.5,
            "macd": "bullish",
            "sma_20": 1.0845,
            "sma_50": 1.0820,
            "bollinger_position": "middle"
        },
        "patrones_velas": {
            "hammer": False,
            "doji": False,
            "engulfing": True,
            "shooting_star": False
        },
        "tendencia": "alcista",
        "soporte": 1.0820,
        "resistencia": 1.0870,
        "volatilidad": "media",
        "efectividad_calculada": 87.5,  # Simulado - en el bot real vendría del análisis
        "direccion_recomendada": "CALL",
        "confianza": 0.875
    }
    
    print(f"   📊 RSI: {analisis['indicadores']['rsi']}")
    print(f"   📈 MACD: {analisis['indicadores']['macd']}")
    print(f"   🕯️ Patrón engulfing: {analisis['patrones_velas']['engulfing']}")
    print(f"   📊 Tendencia: {analisis['tendencia']}")
    print(f"   🎯 Efectividad: {analisis['efectividad_calculada']}%")
    print(f"   🔮 Dirección: {analisis['direccion_recomendada']}")
    
    return analisis

async def procesar_señal_trading(analisis: dict, telegram_bot: MockTelegramBot) -> bool:
    """Procesa y envía una señal de trading si cumple los criterios."""
    
    efectividad_minima = 80.0
    
    if analisis["efectividad_calculada"] >= efectividad_minima:
        # Crear señal
        señal = {
            "par": analisis["par"],
            "direccion": analisis["direccion_recomendada"],
            "tiempo": analisis["timestamp"].strftime("%H:%M:%S"),
            "efectividad": analisis["efectividad_calculada"],
            "monto": 50,  # Monto base
            "expiracion": "5 min",
            "confianza": analisis["confianza"]
        }
        
        # Enviar señal
        await telegram_bot.enviar_señal_trading(señal)
        
        print(f"✅ Señal enviada: {señal['par']} {señal['direccion']} ({señal['efectividad']}%)")
        return True
    else:
        print(f"❌ Efectividad insuficiente: {analisis['efectividad_calculada']}% < {efectividad_minima}%")
        return False

async def ciclo_principal_bot(market_manager: MarketManagerImproved, telegram_bot: MockTelegramBot):
    """Simula el ciclo principal del bot de trading."""
    
    print("\n🔄 INICIANDO CICLO PRINCIPAL DEL BOT")
    print("="*60)
    
    ciclo = 0
    señales_enviadas = 0
    
    try:
        while ciclo < 5:  # Limitar a 5 ciclos para la demo
            ciclo += 1
            print(f"\n--- CICLO {ciclo} ---")
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"🕐 Hora: {timestamp}")
            
            # Paso 1: Verificar estado de conexión
            print("1️⃣ Verificando conexión...")
            connected = await market_manager.ensure_connection(telegram_bot)
            
            if not connected:
                print("❌ Sin conexión - Saltando ciclo")
                await asyncio.sleep(30)
                continue
            
            # Paso 2: Evaluar si debe hacer trading
            should_trade, reason = market_manager.should_attempt_trading()
            print(f"2️⃣ Evaluación trading: {should_trade} - {reason}")
            
            if not should_trade:
                print("⏸️ No se puede hacer trading en este momento")
                await asyncio.sleep(60)
                continue
            
            # Paso 3: Obtener mercado
            mercado = market_manager.obtener_mejor_mercado()
            print(f"3️⃣ Mercado seleccionado: {mercado}")
            
            if not mercado:
                print("❌ No hay mercado disponible")
                await asyncio.sleep(60)
                continue
            
            # Paso 4: Verificar balance
            try:
                balance = await market_manager.get_balance_async()
                print(f"4️⃣ Balance: ${balance}")
                
                if not balance or balance < 50:
                    print("❌ Balance insuficiente")
                    await asyncio.sleep(60)
                    continue
            except Exception as e:
                print(f"⚠️ Error obteniendo balance: {e}")
            
            # Paso 5: Análisis de estrategia
            print("5️⃣ Ejecutando análisis de estrategia...")
            analisis = await simular_analisis_estrategia(market_manager, mercado)
            
            # Paso 6: Procesar señal
            print("6️⃣ Procesando señal...")
            señal_enviada = await procesar_señal_trading(analisis, telegram_bot)
            
            if señal_enviada:
                señales_enviadas += 1
            
            # Paso 7: Estadísticas del ciclo
            health_score = market_manager.get_connection_health_score()
            print(f"7️⃣ Salud conexión: {health_score:.2f}/1.0")
            print(f"📊 Señales enviadas: {señales_enviadas}")
            
            # Esperar antes del siguiente ciclo
            if ciclo < 5:
                print("⏳ Esperando 30 segundos para siguiente ciclo...")
                await asyncio.sleep(30)
    
    except KeyboardInterrupt:
        print("\n⚠️ Ciclo interrumpido por el usuario")
    except Exception as e:
        print(f"\n💥 Error en ciclo principal: {e}")
        import traceback
        traceback.print_exc()
    
    # Resumen final
    print(f"\n📊 RESUMEN FINAL:")
    print(f"   🔄 Ciclos completados: {ciclo}")
    print(f"   📤 Señales enviadas: {señales_enviadas}")
    print(f"   📱 Mensajes Telegram: {len(telegram_bot.messages_sent)}")

async def test_error_scenarios(market_manager: MarketManagerImproved, telegram_bot: MockTelegramBot):
    """Prueba escenarios de error y recuperación."""
    
    print("\n🧪 PRUEBA DE ESCENARIOS DE ERROR")
    print("="*50)
    
    # Escenario 1: Simular pérdida de conexión
    print("🔌 Escenario 1: Simulando pérdida de conexión")
    original_connected = market_manager.conectado
    market_manager.conectado = False
    
    should_trade, reason = market_manager.should_attempt_trading()
    print(f"   Estado: {should_trade} - {reason}")
    
    # Intentar reconexión
    print("   🔄 Intentando reconexión automática...")
    reconnected = await market_manager.ensure_connection(telegram_bot)
    print(f"   Resultado: {'✅' if reconnected else '❌'}")
    
    # Escenario 2: Verificar cooldown 403 (simulado)
    print("\n🚫 Escenario 2: Simulando cooldown 403")
    if market_manager.connection_manager:
        # Simular bloqueo 403 reciente
        market_manager.connection_manager.last_403_block = datetime.now()
        
        should_trade, reason = market_manager.should_attempt_trading()
        print(f"   Estado: {should_trade} - {reason}")
        
        # Limpiar simulación
        market_manager.connection_manager.last_403_block = None
    
    # Escenario 3: Verificar salud de conexión baja
    print("\n📊 Escenario 3: Evaluando salud de conexión")
    health_score = market_manager.get_connection_health_score()
    print(f"   Salud actual: {health_score:.2f}")
    
    if health_score < 0.7:
        print("   ⚠️ Salud baja detectada")
    else:
        print("   ✅ Salud de conexión buena")

async def main():
    """Función principal del ejemplo completo."""
    
    print("🚀 EJEMPLO COMPLETO - FLUJO DEL BOT CUBAYDSIGNAL")
    print("="*70)
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Cargar credenciales
    _load_dotenv_if_needed()
    email = os.environ.get("QUOTEX_EMAIL")
    password = os.environ.get("QUOTEX_PASSWORD")
    
    if not email or not password:
        print("❌ Faltan credenciales QUOTEX_EMAIL y/o QUOTEX_PASSWORD en .env")
        print("\nConfigura las credenciales en el archivo .env:")
        print("QUOTEX_EMAIL=tu_email@ejemplo.com")
        print("QUOTEX_PASSWORD=tu_password")
        return
    
    # Crear instancias
    market_manager = MarketManagerImproved()
    telegram_bot = MockTelegramBot()
    
    try:
        print(f"📧 Usuario: {email}")
        print("⏳ Estableciendo conexión inicial...")
        
        # Conectar
        success = await market_manager.conectar_quotex(email, password, telegram_bot)
        
        if success:
            print("✅ Conexión establecida - Iniciando operación del bot")
            
            # Mostrar estado inicial
            estado = market_manager.verificar_estado_conexion()
            health_score = market_manager.get_connection_health_score()
            
            print(f"\n📊 ESTADO INICIAL:")
            print(f"   🔌 Conectado: {estado['conectado']}")
            print(f"   📧 Usuario: {estado.get('email', 'N/A')}")
            print(f"   💚 Salud: {health_score:.2f}/1.0")
            print(f"   🎯 Listo para trading: {market_manager.is_ready_for_trading()}")
            
            # Ejecutar ciclo principal
            await ciclo_principal_bot(market_manager, telegram_bot)
            
            # Probar escenarios de error
            await test_error_scenarios(market_manager, telegram_bot)
            
            # Resumen de mensajes de Telegram
            print(f"\n📱 RESUMEN TELEGRAM:")
            for i, msg in enumerate(telegram_bot.messages_sent, 1):
                msg_type = msg.get("type", "notification")
                print(f"   {i}. [{msg['timestamp']}] {msg_type.upper()}")
            
        else:
            print("❌ No se pudo establecer conexión inicial")
            estado = market_manager.verificar_estado_conexion()
            
            if estado.get("in_403_cooldown"):
                cooldown_min = estado.get("cooldown_remaining", 0) // 60
                print(f"🚫 En cooldown 403: {cooldown_min} minutos restantes")
            
            if estado.get("error_details"):
                print(f"💥 Error: {estado['error_details']}")
    
    except KeyboardInterrupt:
        print("\n⚠️ Ejemplo interrumpido por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Finalizando y limpiando recursos...")
        await market_manager.desconectar_quotex()
        print("✅ Ejemplo completado")

if __name__ == "__main__":
    print("🎯 Para ejecutar este ejemplo, asegúrate de tener configurado el archivo .env")
    print("📝 Este script simula el flujo completo del bot sin hacer operaciones reales")
    print("🔄 Presiona Ctrl+C para interrumpir en cualquier momento\n")
    
    asyncio.run(main())
