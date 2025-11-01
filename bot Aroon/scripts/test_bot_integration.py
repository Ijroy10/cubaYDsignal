#!/usr/bin/env python3
"""
Script de integración que demuestra cómo el nuevo sistema de conexión
se integra con el sistema de estrategias existente de CubaYDSignal
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta

# Configurar path para usar módulos locales
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "quotexpy"))

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

def mostrar_estado_bot(manager: MarketManagerImproved):
    """Muestra el estado completo del bot de manera organizada."""
    print("\n" + "="*70)
    print("🤖 ESTADO COMPLETO DEL BOT CUBAYDSIGNAL")
    print("="*70)
    
    # Estado de conexión
    estado = manager.verificar_estado_conexion()
    
    print("🔌 CONEXIÓN:")
    estado_emoji = "✅" if estado["conectado"] else "❌"
    print(f"   {estado_emoji} Estado: {'CONECTADO' if estado['conectado'] else 'DESCONECTADO'}")
    
    if estado.get("email"):
        print(f"   📧 Usuario: {estado['email']}")
    
    if estado.get("connection_timestamp"):
        print(f"   🕐 Conectado desde: {estado['connection_timestamp'].strftime('%H:%M:%S')}")
    
    # Salud de conexión
    health_score = manager.get_connection_health_score()
    health_emoji = "🟢" if health_score >= 0.8 else "🟡" if health_score >= 0.5 else "🔴"
    print(f"   {health_emoji} Salud: {health_score:.2f}/1.0")
    
    # Estado de trading
    print(f"\n🎯 TRADING:")
    ready_for_trading = manager.is_ready_for_trading()
    print(f"   {'✅' if ready_for_trading else '❌'} Listo para operar: {ready_for_trading}")
    
    should_trade, reason = manager.should_attempt_trading()
    print(f"   {'🟢' if should_trade else '🔴'} Debe operar: {should_trade}")
    print(f"   📝 Razón: {reason}")
    
    # Horario
    en_horario = manager.esta_en_horario_permitido()
    print(f"   {'🕐' if en_horario else '⏰'} Horario permitido: {en_horario}")
    
    # Mercados
    mercados = manager.mercados_disponibles
    print(f"   📊 Mercados disponibles: {len(mercados)}")
    if mercados:
        print(f"   🎯 Mejor mercado: {manager.obtener_mejor_mercado()}")
    
    # Errores o advertencias
    if estado.get("in_403_cooldown"):
        cooldown_min = estado.get("cooldown_remaining", 0) // 60
        print(f"\n🚫 ADVERTENCIA: En cooldown por bloqueo 403 ({cooldown_min} min restantes)")
    
    if estado.get("error_details"):
        print(f"\n❌ ÚLTIMO ERROR: {estado['error_details']}")
    
    print("="*70)

async def simular_ciclo_trading(manager: MarketManagerImproved):
    """Simula un ciclo completo de trading como lo haría el bot real."""
    print("\n🔄 SIMULANDO CICLO DE TRADING")
    print("-" * 50)
    
    # Paso 1: Verificar que estamos listos
    should_trade, reason = manager.should_attempt_trading()
    print(f"1️⃣ Evaluación inicial: {reason}")
    
    if not should_trade:
        print("   ❌ No se puede proceder con trading")
        return False
    
    # Paso 2: Obtener mercado
    mercado = manager.obtener_mejor_mercado()
    print(f"2️⃣ Mercado seleccionado: {mercado}")
    
    if not mercado:
        print("   ❌ No hay mercado disponible")
        return False
    
    # Paso 3: Verificar balance
    try:
        balance = await manager.get_balance_async()
        print(f"3️⃣ Balance disponible: ${balance}")
        
        if not balance or balance < 10:
            print("   ❌ Balance insuficiente para trading")
            return False
    except Exception as e:
        print(f"   ⚠️ Error obteniendo balance: {e}")
    
    # Paso 4: Simular análisis de estrategia
    print("4️⃣ Ejecutando análisis de estrategia...")
    await asyncio.sleep(2)  # Simular tiempo de análisis
    
    # Aquí es donde se integraría con el sistema de estrategias existente
    print("   📊 Analizando patrones de velas...")
    print("   📈 Calculando indicadores técnicos...")
    print("   🎯 Evaluando efectividad de señal...")
    
    # Simular resultado de análisis
    efectividad_simulada = 85.5  # En el bot real, esto vendría del análisis
    print(f"   ✅ Efectividad calculada: {efectividad_simulada}%")
    
    if efectividad_simulada >= 80:
        print("5️⃣ ✅ SEÑAL VÁLIDA - Se enviaría a Telegram")
        print(f"   📤 Señal: {mercado} CALL/PUT a las {datetime.now().strftime('%H:%M:%S')}")
        return True
    else:
        print("5️⃣ ❌ Efectividad insuficiente - No se envía señal")
        return False

async def test_reconnection_scenario(manager: MarketManagerImproved):
    """Prueba escenarios de reconexión."""
    print("\n🔄 PRUEBA DE ESCENARIOS DE RECONEXIÓN")
    print("-" * 50)
    
    # Escenario 1: Conexión normal
    print("📡 Escenario 1: Verificar conexión actual")
    health_before = manager.get_connection_health_score()
    print(f"   Salud antes: {health_before:.2f}")
    
    # Escenario 2: Forzar verificación de conexión
    print("📡 Escenario 2: Forzar ensure_connection()")
    try:
        ensured = await manager.ensure_connection()
        health_after = manager.get_connection_health_score()
        print(f"   Resultado: {'✅' if ensured else '❌'}")
        print(f"   Salud después: {health_after:.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Escenario 3: Simular pérdida de conexión
    print("📡 Escenario 3: Simular pérdida de conexión")
    original_connected = manager.conectado
    manager.conectado = False  # Simular desconexión
    
    print("   🔌 Conexión simulada como perdida")
    should_trade, reason = manager.should_attempt_trading()
    print(f"   Estado trading: {should_trade} - {reason}")
    
    # Intentar reconectar
    print("   🔄 Intentando reconexión automática...")
    try:
        reconnected = await manager.ensure_connection()
        print(f"   Resultado: {'✅ Reconectado' if reconnected else '❌ Fallo'}")
    except Exception as e:
        print(f"   ❌ Error en reconexión: {e}")
        manager.conectado = original_connected  # Restaurar estado

async def main():
    """Función principal de prueba de integración."""
    print("🚀 PRUEBA DE INTEGRACIÓN - CUBAYDSIGNAL BOT")
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
        return
    
    # Crear manager mejorado
    manager = MarketManagerImproved()
    
    try:
        print(f"📧 Iniciando con usuario: {email}")
        print("⏳ Conectando a Quotex...")
        
        # Conectar
        success = await manager.conectar_quotex(email, password)
        
        if success:
            print("✅ Conexión establecida exitosamente")
            
            # Mostrar estado inicial
            mostrar_estado_bot(manager)
            
            # Simular varios ciclos de trading
            print("\n🎯 SIMULANDO CICLOS DE TRADING")
            for i in range(3):
                print(f"\n--- Ciclo {i+1} ---")
                await simular_ciclo_trading(manager)
                
                if i < 2:  # No esperar en el último ciclo
                    print("⏳ Esperando 10 segundos para siguiente ciclo...")
                    await asyncio.sleep(10)
            
            # Probar escenarios de reconexión
            await test_reconnection_scenario(manager)
            
            # Estado final
            print("\n📊 ESTADO FINAL:")
            mostrar_estado_bot(manager)
            
        else:
            print("❌ No se pudo establecer conexión")
            estado = manager.verificar_estado_conexion()
            if estado.get("in_403_cooldown"):
                print("🚫 Bot en cooldown por bloqueo 403")
            if estado.get("error_details"):
                print(f"💥 Error: {estado['error_details']}")
    
    except KeyboardInterrupt:
        print("\n⚠️ Prueba interrumpida por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🧹 Limpiando recursos...")
        await manager.desconectar_quotex()
        print("✅ Limpieza completada")

if __name__ == "__main__":
    asyncio.run(main())
