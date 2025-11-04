"""
Ejemplo de configuración de Proxy SOCKS5 para el bot

Este archivo muestra cómo configurar un proxy SOCKS5 directamente en el código.
Es la opción más simple si tienes acceso a un proxy SOCKS5.

IMPORTANTE: No subas este archivo con credenciales reales a GitHub.
"""

# ============================================================================
# CONFIGURACIÓN DE PROXY SOCKS5
# ============================================================================

# Ejemplo 1: Proxy sin autenticación
PROXY_CONFIG_SIMPLE = {
    'host': 'tu-proxy.com',
    'port': 1080,
    'username': None,
    'password': None
}

# Ejemplo 2: Proxy con autenticación
PROXY_CONFIG_AUTH = {
    'host': 'tu-proxy.com',
    'port': 1080,
    'username': 'tu_usuario',
    'password': 'tu_contraseña'
}

# Ejemplo 3: Proxy de servicio comercial (Bright Data, Smartproxy, etc.)
PROXY_CONFIG_COMERCIAL = {
    'host': 'brd.superproxy.io',  # Ejemplo de Bright Data
    'port': 22225,
    'username': 'brd-customer-hl_xxxxx-zone-residential',
    'password': 'tu_password_aqui'
}

# ============================================================================
# PROVEEDORES DE PROXY SOCKS5 RECOMENDADOS
# ============================================================================

"""
1. Bright Data (ex-Luminati)
   - Web: https://brightdata.com
   - Precio: Desde $500/mes (40GB)
   - IPs: Residenciales de 195+ países
   - Protocolo: SOCKS5, HTTP, HTTPS
   - Rotación: Automática
   
2. Smartproxy
   - Web: https://smartproxy.com
   - Precio: Desde $75/mes (5GB)
   - IPs: Residenciales de 195+ países
   - Protocolo: SOCKS5, HTTP, HTTPS
   - Rotación: Automática
   
3. Oxylabs
   - Web: https://oxylabs.io
   - Precio: Desde $300/mes
   - IPs: Residenciales y datacenter
   - Protocolo: SOCKS5, HTTP, HTTPS
   - Rotación: Automática
   
4. IPRoyal
   - Web: https://iproyal.com
   - Precio: Desde $1.75/GB
   - IPs: Residenciales y datacenter
   - Protocolo: SOCKS5, HTTP, HTTPS
   - Más económico
   
5. Proxy-Seller (Económico)
   - Web: https://proxy-seller.com
   - Precio: Desde $1.77/mes por proxy
   - IPs: Datacenter dedicadas
   - Protocolo: SOCKS5, HTTP
   - Ideal para uso personal
"""

# ============================================================================
# CÓMO USAR ESTE ARCHIVO
# ============================================================================

"""
Opción A: Modificar vpn_manager.py directamente
--------------------------------------------------
1. Abre: src/utils/vpn_manager.py
2. Busca el método: auto_conectar()
3. Agrega antes del return False:

    # Intentar proxy SOCKS5 como último recurso
    logger.info("[VPN] 🔌 Intentando proxy SOCKS5...")
    proxies = self.conectar_vpn_proxy_socks5(
        host='tu-proxy.com',
        port=1080,
        username='usuario',
        password='contraseña'
    )
    
    if proxies:
        # Configurar para toda la sesión
        import os
        os.environ['HTTP_PROXY'] = proxies['http']
        os.environ['HTTPS_PROXY'] = proxies['https']
        return True


Opción B: Usar variables de entorno
------------------------------------
1. Crea un archivo .env en la raíz del proyecto:

    PROXY_HOST=tu-proxy.com
    PROXY_PORT=1080
    PROXY_USER=usuario
    PROXY_PASS=contraseña

2. Modifica vpn_manager.py para leer estas variables:

    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    proxies = self.conectar_vpn_proxy_socks5(
        host=os.getenv('PROXY_HOST'),
        port=int(os.getenv('PROXY_PORT')),
        username=os.getenv('PROXY_USER'),
        password=os.getenv('PROXY_PASS')
    )


Opción C: Configurar en Render/VPS
-----------------------------------
1. En Render Dashboard:
   - Settings → Environment
   - Agregar variables:
     * PROXY_HOST = tu-proxy.com
     * PROXY_PORT = 1080
     * PROXY_USER = usuario
     * PROXY_PASS = contraseña

2. El bot las leerá automáticamente
"""

# ============================================================================
# EJEMPLO DE IMPLEMENTACIÓN COMPLETA
# ============================================================================

def configurar_proxy_automatico():
    """
    Función de ejemplo para configurar proxy automáticamente
    Copia esto en vpn_manager.py si lo prefieres
    """
    import os
    from dotenv import load_dotenv
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Obtener configuración
    proxy_host = os.getenv('PROXY_HOST')
    proxy_port = os.getenv('PROXY_PORT')
    proxy_user = os.getenv('PROXY_USER')
    proxy_pass = os.getenv('PROXY_PASS')
    
    if not proxy_host or not proxy_port:
        print("[Proxy] ⚠️ No hay configuración de proxy en variables de entorno")
        return None
    
    # Construir URL del proxy
    if proxy_user and proxy_pass:
        proxy_url = f"socks5://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
    else:
        proxy_url = f"socks5://{proxy_host}:{proxy_port}"
    
    # Configurar proxies
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    print(f"[Proxy] ✅ Configurado: {proxy_host}:{proxy_port}")
    return proxies


# ============================================================================
# VERIFICACIÓN DE PROXY
# ============================================================================

def verificar_proxy(proxies):
    """Verifica que el proxy funcione correctamente"""
    import requests
    
    try:
        print("[Proxy] 🔍 Verificando proxy...")
        
        # Verificar IP sin proxy
        response = requests.get('https://ipapi.co/json/', timeout=5)
        ip_original = response.json().get('ip')
        pais_original = response.json().get('country_name')
        print(f"[Proxy] 📍 IP Original: {ip_original} ({pais_original})")
        
        # Verificar IP con proxy
        response = requests.get('https://ipapi.co/json/', proxies=proxies, timeout=10)
        ip_proxy = response.json().get('ip')
        pais_proxy = response.json().get('country_name')
        print(f"[Proxy] 🌍 IP con Proxy: {ip_proxy} ({pais_proxy})")
        
        if ip_original != ip_proxy:
            print("[Proxy] ✅ Proxy funcionando correctamente")
            return True
        else:
            print("[Proxy] ❌ El proxy no está cambiando la IP")
            return False
            
    except Exception as e:
        print(f"[Proxy] ❌ Error verificando proxy: {e}")
        return False


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("EJEMPLO DE CONFIGURACIÓN DE PROXY SOCKS5")
    print("=" * 70)
    
    # Configurar proxy
    proxies = configurar_proxy_automatico()
    
    if proxies:
        # Verificar que funcione
        if verificar_proxy(proxies):
            print("\n✅ Proxy configurado y funcionando correctamente")
            print("💡 Ahora puedes usar este proxy en el bot")
        else:
            print("\n❌ El proxy no está funcionando correctamente")
            print("💡 Verifica las credenciales y la conectividad")
    else:
        print("\n⚠️ No se pudo configurar el proxy")
        print("💡 Configura las variables de entorno en .env")
