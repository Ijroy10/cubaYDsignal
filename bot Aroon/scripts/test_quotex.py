import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Forzar a usar la librería local modificada: paquete local 'quotexpy'
ROOT = os.path.dirname(os.path.dirname(__file__))
LOCAL_PKG_PARENT = os.path.join(ROOT, "quotexpy")  # padre de la carpeta de paquete
if LOCAL_PKG_PARENT not in sys.path:
    sys.path.insert(0, LOCAL_PKG_PARENT)

from quotexpy import Quotex  # noqa: E402

def _load_dotenv_if_needed():
    """Carga variables QUOTEX_EMAIL y QUOTEX_PASSWORD desde .env si no están en el entorno."""
    env_path = os.path.join(ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    need_email = os.environ.get("QUOTEX_EMAIL") is None
    need_pass = os.environ.get("QUOTEX_PASSWORD") is None
    if not (need_email or need_pass):
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
                if k in ("QUOTEX_EMAIL", "QUOTEX_PASSWORD") and os.environ.get(k) is None:
                    os.environ[k] = v
    except Exception as e:
        logging.getLogger(__name__).warning(f"No se pudo cargar .env automáticamente: {e}")

async def test_connection():
    """Prueba la conexión a Quotex con diagnósticos detallados"""
    _load_dotenv_if_needed()
    email = os.environ.get("QUOTEX_EMAIL")
    password = os.environ.get("QUOTEX_PASSWORD")
    
    if not email or not password:
        print("❌ Faltan variables de entorno QUOTEX_EMAIL y/o QUOTEX_PASSWORD.")
        print("Revisa tu archivo .env")
        return False

    print(f"🔍 Intentando conectar con: {email}")
    print("📊 Iniciando conexión a Quotex...")
    
    try:
        # Crear instancia con modo visible (no headless)
        q = Quotex(email=email, password=password, headless=False)
        q.trace_ws = True  # habilitar trazas de WebSocket para depuración
        
        print("🌐 Estableciendo conexión...")
        ok = await q.connect()
        
        if not ok:
            print("❌ No se pudo establecer conexión WebSocket.")
            return False
        
        print("✅ Conexión WebSocket establecida")
        
        # Verificar si está realmente conectado
        if q.is_connected:
            print("✅ Estado de conexión: CONECTADO")
        else:
            print("⚠️ Estado de conexión: DESCONECTADO")
            return False
        
        # Intentar obtener balance como prueba final
        print("💰 Obteniendo balance...")
        try:
            balance = await q.get_balance()
            print(f"✅ Balance obtenido: {balance}")
            
            # Intentar obtener instrumentos/activos
            print("📈 Obteniendo lista de activos...")
            instruments = await q.get_instruments()
            if instruments:
                print(f"✅ Activos disponibles: {len(instruments)}")
                # Mostrar algunos activos como ejemplo
                for i, instrument in enumerate(instruments[:5]):
                    print(f"   - {instrument}")
            else:
                print("⚠️ No se pudieron obtener activos")
                
        except Exception as e:
            print(f"❌ Error obteniendo datos: {e}")
            return False
            
        print("🎉 ¡Conexión exitosa! El bot puede conectarse a Quotex.")
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"❌ Error de conexión: {e}")
        
        # Diagnósticos específicos
        if '403' in error_msg or 'cloudflare' in error_msg:
            print("\n🚨 DIAGNÓSTICO: Error Cloudflare 403")
            print("   Soluciones:")
            print("   • Cambia a una red residencial (hotspot móvil)")
            print("   • Evita VPNs de datacenter")
            print("   • Espera 20-40 minutos y reintenta")
            
        elif 'unable to extract ssid token' in error_msg:
            print("\n🚨 DIAGNÓSTICO: Error de token SSID")
            print("   Soluciones:")
            print("   • Verifica credenciales en .env")
            print("   • Inicia sesión manualmente en Quotex para descartar CAPTCHA")
            print("   • Verifica que la cuenta no esté bloqueada")
            
        elif 'timeout' in error_msg:
            print("\n🚨 DIAGNÓSTICO: Timeout de conexión")
            print("   Soluciones:")
            print("   • Verifica tu conexión a internet")
            print("   • Reintenta en unos minutos")
            
        return False

async def main():
    # Configurar logging para ver más detalles
    root_logger = logging.getLogger()
    has_stream = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    if not has_stream:
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%H:%M:%S"))
        root_logger.addHandler(sh)
    root_logger.setLevel(logging.INFO)
    
    print("🤖 CubaYDSignal - Test de Conexión a Quotex")
    print("=" * 50)
    
    success = await test_connection()
    
    print("=" * 50)
    if success:
        print("✅ RESULTADO: Conexión exitosa")
    else:
        print("❌ RESULTADO: Fallo de conexión")
        print("\n📋 Pasos siguientes:")
        print("1. Revisa las credenciales en .env")
        print("2. Verifica tu conexión de red")
        print("3. Intenta desde una IP residencial")
        print("4. Inicia sesión manualmente en quotex.io")

if __name__ == "__main__":
    asyncio.run(main())
