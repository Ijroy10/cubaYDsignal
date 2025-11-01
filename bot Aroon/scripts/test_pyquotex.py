import os
import asyncio

from dotenv import load_dotenv
from pyquotex.stable_api import Quotex


async def main():
    # Cargar variables desde .env si existen
    load_dotenv()

    email = os.getenv("QUOTEX_EMAIL")
    password = os.getenv("QUOTEX_PASSWORD")

    if not email or not password:
        print("Faltan variables de entorno QUOTEX_EMAIL y/o QUOTEX_PASSWORD.")
        print("Ejemplo en PowerShell:")
        print("$env:QUOTEX_EMAIL='tu_email'; $env:QUOTEX_PASSWORD='tu_password'")
        return

    client = Quotex(email=email, password=password, lang="en")

    # Modo práctica por defecto para evitar problemas de acceso
    client.set_account_mode("PRACTICE")

    print("Conectando a Quotex por WebSocket (pyquotex)...")
    check, reason = await client.connect()
    print(f"connect() => {check}, reason={reason}")

    # Verificación de conexión
    if not await client.check_connect():
        print("❌ WebSocket no aceptó la conexión aún (check_connect==False)")
        await client.close()
        return

    try:
        balance = await client.get_balance()
        print(f"✅ Balance: {balance}")
    except Exception as e:
        print(f"❌ Error obteniendo balance: {e}")
    finally:
        await client.close()
        print("Conexión cerrada.")


if __name__ == "__main__":
    asyncio.run(main())
