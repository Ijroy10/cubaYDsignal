#!/usr/bin/env python3
"""
Test para ver la estructura de instruments en pyquotex
"""

import asyncio
from pyquotex.api import QuotexAPI
import os
from dotenv import load_dotenv
import json

load_dotenv()

async def test_instruments():
    print("="*60)
    print("TEST: Estructura de Instruments en pyquotex")
    print("="*60)
    print()
    
    email = os.getenv('QUOTEX_EMAIL')
    password = os.getenv('QUOTEX_PASSWORD')
    
    try:
        # Conectar
        print("Conectando a Quotex...")
        quotex = QuotexAPI(
            host="qxbroker.com",
            username=email,
            password=password,
            lang="es"
        )
        
        check, reason = await quotex.connect(is_demo=False)
        
        if not check:
            print(f"❌ Error: {reason}")
            return
        
        print(f"✅ Conectado")
        print()
        
        # Esperar datos
        print("Esperando datos...")
        await asyncio.sleep(5)
        print()
        
        # Obtener instruments
        if hasattr(quotex, 'instruments'):
            instruments = quotex.instruments
            print(f"📊 Total de instruments: {len(instruments)}")
            print()
            
            if instruments and len(instruments) > 0:
                # Mostrar estructura del primer instrumento
                print("📋 Estructura del primer instrumento:")
                print(json.dumps(instruments[0], indent=2, default=str))
                print()
                
                # Mostrar primeros 5 instrumentos
                print("📋 Primeros 5 instrumentos:")
                for i, inst in enumerate(instruments[:5], 1):
                    print(f"\n{i}. Instrumento:")
                    # Mostrar campos clave
                    for key, value in inst.items():
                        print(f"   • {key}: {value}")
                print()
                
                # Buscar campos relacionados con payout/payment/profit
                print("🔍 Buscando campos de payout/payment/profit:")
                primer_inst = instruments[0]
                campos_payout = [k for k in primer_inst.keys() if any(word in k.lower() for word in ['payout', 'payment', 'profit', 'percent'])]
                
                if campos_payout:
                    print(f"✅ Campos encontrados: {campos_payout}")
                    for campo in campos_payout:
                        print(f"   • {campo}: {primer_inst[campo]}")
                else:
                    print("❌ No se encontraron campos de payout")
                    print("   Campos disponibles:")
                    for key in primer_inst.keys():
                        print(f"   • {key}")
                print()
                
                # Verificar si hay algún atributo global de payouts
                print("🔍 Buscando payouts en otros atributos:")
                attrs_to_check = ['payment', 'payments', 'payouts', 'profit', 'profits', 'asset_info', 'assets_data']
                for attr in attrs_to_check:
                    if hasattr(quotex, attr):
                        value = getattr(quotex, attr)
                        print(f"✅ quotex.{attr} existe")
                        print(f"   Tipo: {type(value)}")
                        if value:
                            print(f"   Contenido: {str(value)[:200]}...")
                    else:
                        print(f"❌ quotex.{attr} no existe")
                print()
        
        await quotex.close()
        print("✅ Test completado")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_instruments())
