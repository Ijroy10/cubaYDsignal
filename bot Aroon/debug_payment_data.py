"""
Script para debuggear la estructura real de get_payment()
"""
import asyncio
import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from pyquotex.stable_api import Quotex

async def debug_payment():
    """Debuggear estructura de payment data"""
    print("=" * 60)
    print("🔍 DEBUG: ESTRUCTURA DE get_payment()")
    print("=" * 60)
    
    load_dotenv()
    email = os.getenv("QUOTEX_EMAIL")
    password = os.getenv("QUOTEX_PASSWORD")
    
    if not email or not password:
        print("❌ Error: QUOTEX_EMAIL y QUOTEX_PASSWORD deben estar en .env")
        return
    
    print(f"\n📧 Email: {email}")
    print("🔐 Password: ********")
    
    # Crear cliente Quotex
    client = Quotex(email=email, password=password)
    
    print("\n🔌 Conectando...")
    connected = await client.connect()
    
    if not connected:
        print("❌ No se pudo conectar")
        return
    
    print("✅ Conectado")
    
    # Esperar a que se carguen los datos
    await asyncio.sleep(3)
    
    # Obtener payment data
    print("\n📊 Obteniendo payment data...")
    
    if hasattr(client, 'get_payment'):
        payment_data = client.get_payment()
        
        print(f"\n✅ Tipo de datos: {type(payment_data)}")
        print(f"✅ Cantidad de mercados: {len(payment_data) if payment_data else 0}")
        
        if payment_data:
            # Mostrar primeros 5 mercados con estructura completa
            print("\n📋 PRIMEROS 5 MERCADOS (estructura completa):")
            print("-" * 60)
            
            for i, (symbol, data) in enumerate(list(payment_data.items())[:5], 1):
                print(f"\n{i}. Symbol: {symbol}")
                print(f"   Tipo de data: {type(data)}")
                if isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())}")
                    for key, value in data.items():
                        print(f"   {key}: {value} (tipo: {type(value).__name__})")
                else:
                    print(f"   Valor directo: {data}")
            
            # Guardar estructura completa en JSON
            print("\n💾 Guardando estructura completa en debug_payment.json...")
            
            # Convertir a formato serializable
            serializable_data = {}
            for symbol, data in payment_data.items():
                if isinstance(data, dict):
                    serializable_data[symbol] = {k: str(v) for k, v in data.items()}
                else:
                    serializable_data[symbol] = str(data)
            
            with open("debug_payment.json", "w", encoding="utf-8") as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            
            print("✅ Archivo guardado: debug_payment.json")
            
            # Buscar mercados con diferentes payouts
            print("\n🔍 BUSCANDO VARIACIONES EN PAYOUTS...")
            payouts_unicos = set()
            
            for symbol, data in payment_data.items():
                if isinstance(data, dict):
                    if 'payment' in data:
                        payouts_unicos.add(data['payment'])
                    if 'turbo_payment' in data:
                        payouts_unicos.add(data['turbo_payment'])
            
            print(f"✅ Payouts únicos encontrados: {sorted(payouts_unicos)}")
            
            # Mostrar mercados con payout diferente a 90
            print("\n📊 MERCADOS CON PAYOUT ≠ 90:")
            print("-" * 60)
            count = 0
            for symbol, data in payment_data.items():
                if isinstance(data, dict) and 'payment' in data:
                    payout = data['payment']
                    # Convertir a porcentaje si es decimal
                    if isinstance(payout, (int, float)):
                        if payout < 1:
                            payout = payout * 100
                        if payout != 90:
                            print(f"   {symbol}: {payout}%")
                            count += 1
            
            if count == 0:
                print("   ⚠️ Todos los mercados tienen payout = 90%")
            
    else:
        print("❌ El cliente no tiene método get_payment()")
    
    # Verificar también api.instruments
    print("\n\n🔍 VERIFICANDO api.instruments...")
    if hasattr(client, 'api') and hasattr(client.api, 'instruments'):
        instruments = client.api.instruments
        print(f"✅ Tipo: {type(instruments)}")
        print(f"✅ Cantidad: {len(instruments) if instruments else 0}")
        
        if instruments and len(instruments) > 0:
            print("\n📋 PRIMER INSTRUMENTO (estructura completa):")
            print("-" * 60)
            primer = instruments[0]
            print(f"Tipo: {type(primer)}")
            if isinstance(primer, (list, tuple)):
                print(f"Longitud: {len(primer)}")
                for i, val in enumerate(primer):
                    print(f"  [{i}]: {val} (tipo: {type(val).__name__})")
            else:
                print(f"Valor: {primer}")
            
            # Guardar primeros 5 instrumentos
            print("\n💾 Guardando primeros 5 instrumentos en debug_instruments.json...")
            with open("debug_instruments.json", "w", encoding="utf-8") as f:
                json.dump([str(i) for i in instruments[:5]], f, indent=2, ensure_ascii=False)
            print("✅ Archivo guardado: debug_instruments.json")
    
    print("\n" + "=" * 60)
    print("✅ DEBUG COMPLETADO")
    print("=" * 60)
    print("\n📁 Archivos generados:")
    print("   • debug_payment.json")
    print("   • debug_instruments.json")

if __name__ == "__main__":
    asyncio.run(debug_payment())
