#!/usr/bin/env python3
"""
Script para probar la detección de estado "listo para operar" del bot CubaYDSignal
Valida todos los criterios necesarios para que el bot pueda ejecutar estrategias
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime

# Configurar path para usar módulos locales
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "quotexpy"))

from src.core.market_manager import MarketManager

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

def mostrar_estado_detallado(estado):
    """Muestra el estado de manera legible y organizada."""
    print("\n" + "="*60)
    print("📊 ESTADO DETALLADO DEL BOT")
    print("="*60)
    
    # Estado general
    if estado["listo"]:
        print(f"🎯 ESTADO: ✅ {estado['mensaje']}")
    else:
        print(f"🎯 ESTADO: ⚠️ {estado['mensaje']}")
    
    print(f"⏰ Timestamp: {estado['timestamp']}")
    
    # Criterios individuales
    print("\n📋 CRITERIOS DE VERIFICACIÓN:")
    print("-" * 40)
    
    for criterio, cumplido in estado["criterios"].items():
        emoji = "✅" if cumplido else "❌"
        nombre = criterio.replace('_', ' ').title()
        print(f"{emoji} {nombre}")
    
    # Detalles técnicos
    if estado["detalles"]:
        print("\n🔍 DETALLES TÉCNICOS:")
        print("-" * 40)
        for categoria, detalle in estado["detalles"].items():
            print(f"• {categoria}: {detalle}")
    
    # Recomendaciones
    if estado["recomendaciones"]:
        print("\n💡 RECOMENDACIONES:")
        print("-" * 40)
        for i, rec in enumerate(estado["recomendaciones"], 1):
            print(f"{i}. {rec}")
    
    # Errores si los hay
    if "error" in estado:
        print(f"\n❌ ERROR: {estado['error']}")

async def test_conexion_y_estado():
    """Prueba la conexión y verifica el estado completo del bot."""
    print("🚀 Iniciando prueba de estado del bot...")
    
    # Cargar variables de entorno
    _load_dotenv_if_needed()
    
    # Verificar credenciales
    email = os.getenv("QUOTEX_EMAIL")
    password = os.getenv("QUOTEX_PASSWORD")
    
    if not email or not password:
        print("❌ Faltan credenciales de Quotex")
        print("📝 Configura QUOTEX_EMAIL y QUOTEX_PASSWORD en .env")
        return False
    
    print(f"👤 Usuario: {email}")
    
    # Crear instancia del MarketManager
    market_manager = MarketManager()
    
    try:
        print("\n🔗 Paso 1: Verificando estado inicial...")
        estado_inicial = await market_manager.esta_listo_para_operar()
        mostrar_estado_detallado(estado_inicial)
        
        if estado_inicial["listo"]:
            print("\n🎉 ¡El bot ya está listo para operar!")
            return True
        
        print("\n🔌 Paso 2: Intentando conectar a Quotex...")
        conectado = await market_manager.conectar_quotex()
        
        if conectado:
            print("✅ Conexión establecida")
        else:
            print("❌ Fallo en la conexión")
            estado_post_conexion = await market_manager.esta_listo_para_operar()
            mostrar_estado_detallado(estado_post_conexion)
            return False
        
        print("\n🔍 Paso 3: Verificando estado después de la conexión...")
        estado_post_conexion = await market_manager.esta_listo_para_operar()
        mostrar_estado_detallado(estado_post_conexion)
        
        if estado_post_conexion["listo"]:
            print("\n🎉 ¡Bot completamente listo para operar!")
            return True
        else:
            print("\n⏳ Paso 4: Esperando hasta estar completamente listo...")
            listo = await market_manager.esperar_hasta_estar_listo(timeout=180)  # 3 minutos
            
            if listo:
                print("\n🎉 ¡Bot finalmente listo para operar!")
                return True
            else:
                print("\n⏰ Timeout: El bot no estuvo listo en el tiempo esperado")
                estado_final = await market_manager.esta_listo_para_operar()
                mostrar_estado_detallado(estado_final)
                return False
    
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        return False
    
    finally:
        # Limpiar recursos
        try:
            await market_manager.desconectar_quotex()
        except Exception:
            pass

async def test_criterios_individuales():
    """Prueba cada criterio individualmente para diagnóstico detallado."""
    print("\n" + "="*60)
    print("🔬 PRUEBA DE CRITERIOS INDIVIDUALES")
    print("="*60)
    
    market_manager = MarketManager()
    
    print("\n1️⃣ Probando conexión básica...")
    try:
        conectado = await market_manager.conectar_quotex()
        print(f"   Resultado: {'✅ Conectado' if conectado else '❌ No conectado'}")
    except Exception as e:
        print(f"   Resultado: ❌ Error: {e}")
    
    print("\n2️⃣ Verificando estado de conexión detallado...")
    try:
        estado_conexion = market_manager.verificar_estado_conexion()
        print(f"   WebSocket conectado: {'✅' if estado_conexion.get('websocket_connected') else '❌'}")
        print(f"   SSID presente: {'✅' if estado_conexion.get('ssid_present') else '❌'}")
        print(f"   Sin errores WS: {'✅' if estado_conexion.get('no_websocket_errors') else '❌'}")
        print(f"   Thread activo: {'✅' if estado_conexion.get('thread_alive') else '❌'}")
        print(f"   Balance disponible: {'✅' if estado_conexion.get('balance_available') else '❌'}")
    except Exception as e:
        print(f"   Error verificando conexión: {e}")
    
    print("\n3️⃣ Probando obtención de mercados...")
    try:
        mercados = market_manager.obtener_mercados_disponibles()
        print(f"   Mercados obtenidos: {len(mercados)} mercados")
        if mercados:
            print(f"   Ejemplo: {mercados[0]['name']} (Payout: {mercados[0]['payout']}%)")
    except Exception as e:
        print(f"   Error obteniendo mercados: {e}")
    
    print("\n4️⃣ Verificando horario operativo...")
    ahora = datetime.now()
    es_fin_semana = ahora.weekday() >= 5
    hora_actual = ahora.hour
    en_horario = not es_fin_semana and 6 <= hora_actual <= 22
    
    print(f"   Día actual: {ahora.strftime('%A')}")
    print(f"   Hora actual: {ahora.strftime('%H:%M')}")
    print(f"   Es fin de semana: {'Sí' if es_fin_semana else 'No'}")
    print(f"   En horario operativo: {'✅ Sí' if en_horario else '❌ No'}")
    
    print("\n5️⃣ Verificando bloqueos 403...")
    tiene_bloqueo = market_manager._debe_esperar_por_bloqueo_403()
    if tiene_bloqueo:
        tiempo_restante = market_manager._tiempo_restante_bloqueo_403()
        print(f"   Bloqueo 403 activo: ❌ Sí ({tiempo_restante//60} min restantes)")
    else:
        print(f"   Bloqueo 403 activo: ✅ No")
    
    # Limpiar
    try:
        await market_manager.desconectar_quotex()
    except Exception:
        pass

async def main():
    """Función principal de prueba."""
    print("="*60)
    print("🧪 PRUEBA DE DETECCIÓN DE ESTADO 'LISTO PARA OPERAR'")
    print("="*60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Prueba principal
    exito = await test_conexion_y_estado()
    
    # Prueba de criterios individuales
    await test_criterios_individuales()
    
    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL")
    print("="*60)
    
    if exito:
        print("🎉 ✅ PRUEBA EXITOSA: El bot puede detectar correctamente cuando está listo para operar")
        print("💡 El bot debería funcionar correctamente en producción")
    else:
        print("⚠️ ❌ PRUEBA FALLIDA: El bot no pudo estar completamente listo")
        print("💡 Revisa los detalles arriba para identificar problemas")
    
    print("\n🔄 Ejecuta este script regularmente para monitorear el estado del bot")

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Ejecutar prueba
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Prueba interrumpida por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
