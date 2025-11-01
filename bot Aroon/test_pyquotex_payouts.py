#!/usr/bin/env python3
"""
Test para verificar si pyquotex puede obtener payouts
"""

import asyncio
from pyquotex.api import QuotexAPI
import os
from dotenv import load_dotenv

load_dotenv()

async def test_payouts():
    print("="*60)
    print("TEST: Obtención de Payouts con pyquotex")
    print("="*60)
    print()
    
    # Credenciales
    email = os.getenv('QUOTEX_EMAIL')
    password = os.getenv('QUOTEX_PASSWORD')
    
    if not email or not password:
        print("❌ Error: Faltan credenciales en .env")
        return
    
    try:
        # Conectar
        print("1. Conectando a Quotex...")
        quotex = QuotexAPI(
            host="qxbroker.com",
            username=email,
            password=password,
            lang="es"
        )
        
        check, reason = await quotex.connect(is_demo=False)
        
        if not check:
            print(f"❌ Error de conexión: {reason}")
            return
        
        print(f"✅ Conectado: {reason}")
        print()
        
        # Esperar un momento para que se carguen datos
        print("2. Esperando datos...")
        await asyncio.sleep(5)
        print()
        
        # Verificar métodos disponibles
        print("3. Verificando métodos disponibles:")
        print()
        
        # Método 1: get_payment()
        if hasattr(quotex, 'get_payment'):
            print("✅ quotex.get_payment() - EXISTE")
            try:
                payment_data = quotex.get_payment()
                print(f"   Tipo: {type(payment_data)}")
                if payment_data:
                    print(f"   Cantidad de mercados: {len(payment_data) if isinstance(payment_data, (dict, list)) else 'N/A'}")
                    if isinstance(payment_data, dict) and len(payment_data) > 0:
                        # Mostrar ejemplo
                        ejemplo = list(payment_data.items())[0]
                        print(f"   Ejemplo: {ejemplo[0]}")
                        print(f"   Datos: {ejemplo[1]}")
                else:
                    print("   ⚠️ payment_data está vacío")
            except Exception as e:
                print(f"   ❌ Error al llamar: {e}")
        else:
            print("❌ quotex.get_payment() - NO EXISTE")
        print()
        
        # Método 2: payment_data attribute
        if hasattr(quotex, 'payment_data'):
            print("✅ quotex.payment_data - EXISTE")
            try:
                payment_data = quotex.payment_data
                print(f"   Tipo: {type(payment_data)}")
                if payment_data:
                    print(f"   Cantidad: {len(payment_data) if isinstance(payment_data, (dict, list)) else 'N/A'}")
                else:
                    print("   ⚠️ payment_data está vacío")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print("❌ quotex.payment_data - NO EXISTE")
        print()
        
        # Método 3: instruments
        if hasattr(quotex, 'instruments'):
            print("✅ quotex.instruments - EXISTE")
            try:
                instruments = quotex.instruments
                print(f"   Tipo: {type(instruments)}")
                if instruments:
                    print(f"   Cantidad: {len(instruments) if isinstance(instruments, (dict, list)) else 'N/A'}")
                    if isinstance(instruments, dict) and len(instruments) > 0:
                        ejemplo = list(instruments.items())[0]
                        print(f"   Ejemplo: {ejemplo[0]}")
                        print(f"   Datos: {ejemplo[1]}")
                else:
                    print("   ⚠️ instruments está vacío")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print("❌ quotex.instruments - NO EXISTE")
        print()
        
        # Listar todos los atributos
        print("4. Atributos disponibles en quotex:")
        atributos = [attr for attr in dir(quotex) if not attr.startswith('_')]
        print(f"   Total: {len(atributos)}")
        print("   Relacionados con payment/payout:")
        payment_attrs = [attr for attr in atributos if 'payment' in attr.lower() or 'payout' in attr.lower() or 'profit' in attr.lower()]
        if payment_attrs:
            for attr in payment_attrs:
                print(f"   • {attr}")
        else:
            print("   (ninguno encontrado)")
        print()
        
        # Cerrar conexión
        await quotex.close()
        print("✅ Conexión cerrada")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_payouts())
