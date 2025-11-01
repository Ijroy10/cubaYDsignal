#!/usr/bin/env python3
"""
Script de diagnóstico de red y conexión a Quotex
Valida el entorno de red y proporciona recomendaciones específicas para resolver bloqueos Cloudflare
"""

import os
import sys
import asyncio
import logging
import requests
import socket
import subprocess
import platform
from datetime import datetime
from typing import Dict, List, Tuple

# Configurar path para usar la librería local
ROOT = os.path.dirname(os.path.dirname(__file__))
LOCAL_PKG_PARENT = os.path.join(ROOT, "quotexpy")
if LOCAL_PKG_PARENT not in sys.path:
    sys.path.insert(0, LOCAL_PKG_PARENT)

from quotexpy import Quotex

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

def get_public_ip() -> str:
    """Obtiene la IP pública actual."""
    try:
        response = requests.get("https://api.ipify.org", timeout=10)
        return response.text.strip()
    except Exception:
        try:
            response = requests.get("https://httpbin.org/ip", timeout=10)
            return response.json().get("origin", "Desconocida")
        except Exception:
            return "No disponible"

def check_ip_type(ip: str) -> Dict[str, any]:
    """Verifica el tipo de IP y proveedor."""
    result = {
        "ip": ip,
        "type": "Desconocido",
        "provider": "Desconocido",
        "is_residential": False,
        "is_datacenter": False,
        "is_vpn": False,
        "country": "Desconocido"
    }
    
    try:
        # Usar servicio gratuito para verificar tipo de IP
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=10)
        data = response.json()
        
        if data.get("status") == "success":
            result["country"] = data.get("country", "Desconocido")
            result["provider"] = data.get("isp", "Desconocido")
            
            # Detectar tipos de IP basado en el ISP
            isp_lower = data.get("isp", "").lower()
            org_lower = data.get("org", "").lower()
            
            datacenter_keywords = [
                "amazon", "aws", "google", "microsoft", "azure", "digitalocean",
                "linode", "vultr", "ovh", "hetzner", "cloudflare", "hosting",
                "server", "datacenter", "data center", "vps", "cloud"
            ]
            
            vpn_keywords = [
                "vpn", "proxy", "nordvpn", "expressvpn", "surfshark", "cyberghost",
                "private internet", "mullvad", "protonvpn", "tunnelbear"
            ]
            
            # Verificar si es datacenter
            for keyword in datacenter_keywords:
                if keyword in isp_lower or keyword in org_lower:
                    result["is_datacenter"] = True
                    result["type"] = "Datacenter/VPS"
                    break
            
            # Verificar si es VPN
            for keyword in vpn_keywords:
                if keyword in isp_lower or keyword in org_lower:
                    result["is_vpn"] = True
                    result["type"] = "VPN/Proxy"
                    break
            
            # Si no es datacenter ni VPN, probablemente es residencial
            if not result["is_datacenter"] and not result["is_vpn"]:
                result["is_residential"] = True
                result["type"] = "Residencial"
                
    except Exception as e:
        print(f"⚠️  Error verificando tipo de IP: {e}")
    
    return result

def check_dns_resolution() -> List[Dict[str, any]]:
    """Verifica la resolución DNS para dominios de Quotex."""
    domains = ["qxbroker.com", "quotex.io", "qxapi.com"]
    results = []
    
    for domain in domains:
        result = {"domain": domain, "resolved": False, "ip": None, "error": None}
        try:
            ip = socket.gethostbyname(domain)
            result["resolved"] = True
            result["ip"] = ip
        except Exception as e:
            result["error"] = str(e)
        results.append(result)
    
    return results

def check_connectivity() -> Dict[str, any]:
    """Verifica conectividad básica a internet y servicios."""
    tests = [
        ("Google DNS", "8.8.8.8", 53),
        ("Cloudflare DNS", "1.1.1.1", 53),
        ("Quotex HTTP", "qxbroker.com", 80),
        ("Quotex HTTPS", "qxbroker.com", 443)
    ]
    
    results = []
    for name, host, port in tests:
        result = {"name": name, "host": host, "port": port, "success": False, "error": None}
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        results.append(result)
    
    return {"tests": results, "internet_ok": any(r["success"] for r in results[:2])}

def get_network_interface_info() -> Dict[str, any]:
    """Obtiene información sobre las interfaces de red activas."""
    info = {"interfaces": [], "active_interface": None}
    
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["ipconfig"], capture_output=True, text=True, shell=True)
            output = result.stdout
            
            # Buscar adaptadores activos
            lines = output.split('\n')
            current_adapter = None
            for line in lines:
                line = line.strip()
                if "adaptador" in line.lower() or "adapter" in line.lower():
                    current_adapter = line
                elif "IPv4" in line and current_adapter:
                    ip = line.split(":")[-1].strip()
                    if not ip.startswith("169.254"):  # Evitar IPs APIPA
                        info["interfaces"].append({
                            "name": current_adapter,
                            "ip": ip,
                            "type": "WiFi" if "wi-fi" in current_adapter.lower() or "wireless" in current_adapter.lower() else "Ethernet"
                        })
        else:
            # Linux/Mac
            result = subprocess.run(["ip", "addr", "show"], capture_output=True, text=True)
            # Implementación básica para Linux/Mac
            pass
            
    except Exception as e:
        info["error"] = str(e)
    
    return info

def analyze_network_environment() -> Dict[str, any]:
    """Analiza el entorno de red completo."""
    print("🔍 Analizando entorno de red...")
    
    # Obtener IP pública
    public_ip = get_public_ip()
    print(f"📍 IP pública: {public_ip}")
    
    # Verificar tipo de IP
    ip_info = check_ip_type(public_ip)
    print(f"🏷️  Tipo de IP: {ip_info['type']}")
    print(f"🏢 Proveedor: {ip_info['provider']}")
    print(f"🌍 País: {ip_info['country']}")
    
    # Verificar conectividad
    connectivity = check_connectivity()
    print(f"🌐 Conectividad a internet: {'✅' if connectivity['internet_ok'] else '❌'}")
    
    # Verificar resolución DNS
    dns_results = check_dns_resolution()
    quotex_dns_ok = any(r["resolved"] for r in dns_results)
    print(f"🔍 Resolución DNS Quotex: {'✅' if quotex_dns_ok else '❌'}")
    
    # Obtener información de interfaces
    network_info = get_network_interface_info()
    
    return {
        "public_ip": public_ip,
        "ip_info": ip_info,
        "connectivity": connectivity,
        "dns_results": dns_results,
        "network_info": network_info,
        "recommendations": generate_recommendations(ip_info, connectivity, quotex_dns_ok)
    }

def generate_recommendations(ip_info: Dict, connectivity: Dict, dns_ok: bool) -> List[str]:
    """Genera recomendaciones específicas basadas en el análisis de red."""
    recommendations = []
    
    # Recomendaciones basadas en tipo de IP
    if ip_info.get("is_datacenter"):
        recommendations.extend([
            "🚨 CRÍTICO: Estás usando una IP de datacenter/VPS",
            "🔄 Cambia a una conexión residencial (WiFi doméstico o hotspot móvil)",
            "📱 Usa hotspot de tu teléfono móvil como alternativa inmediata",
            "🏠 Conecta desde tu red doméstica en lugar del servidor"
        ])
    
    if ip_info.get("is_vpn"):
        recommendations.extend([
            "🚨 CRÍTICO: Estás usando VPN/Proxy",
            "🔌 Desconecta la VPN completamente",
            "🌐 Usa tu conexión directa a internet",
            "⏰ Espera 30-60 minutos después de desconectar la VPN"
        ])
    
    if ip_info.get("is_residential"):
        recommendations.extend([
            "✅ Tipo de IP correcto (residencial)",
            "🕐 Si hay bloqueo, espera 30-60 minutos antes de reintentar",
            "🌐 Intenta navegar manualmente a qxbroker.com primero",
            "🔄 Reinicia tu router si persiste el problema"
        ])
    
    # Recomendaciones basadas en conectividad
    if not connectivity.get("internet_ok"):
        recommendations.extend([
            "🚨 CRÍTICO: Problemas de conectividad básica",
            "🔌 Verifica tu conexión a internet",
            "🔄 Reinicia tu router/módem",
            "📞 Contacta a tu proveedor de internet"
        ])
    
    if not dns_ok:
        recommendations.extend([
            "⚠️ Problemas de resolución DNS",
            "🔧 Cambia DNS a 8.8.8.8 y 8.8.4.4 (Google)",
            "🔧 O usa 1.1.1.1 y 1.0.0.1 (Cloudflare)",
            "🔄 Limpia caché DNS: ipconfig /flushdns (Windows)"
        ])
    
    # Recomendaciones generales anti-bloqueo
    recommendations.extend([
        "",
        "📋 RECOMENDACIONES GENERALES ANTI-BLOQUEO:",
        "1️⃣ Navega manualmente a qxbroker.com antes de usar el bot",
        "2️⃣ Completa cualquier verificación CAPTCHA manualmente",
        "3️⃣ Usa el bot en horarios de menor tráfico",
        "4️⃣ Evita múltiples intentos de conexión seguidos",
        "5️⃣ Mantén el navegador abierto durante las pruebas"
    ])
    
    return recommendations

async def test_quotex_connection():
    """Prueba la conexión a Quotex con diagnósticos detallados."""
    print("\n🔗 Probando conexión a Quotex...")
    
    _load_dotenv_if_needed()
    email = os.environ.get("QUOTEX_EMAIL")
    password = os.environ.get("QUOTEX_PASSWORD")
    
    if not email or not password:
        print("❌ Faltan credenciales de Quotex")
        print("📝 Configura QUOTEX_EMAIL y QUOTEX_PASSWORD en .env")
        return False
    
    try:
        print(f"👤 Usuario: {email}")
        print("🚀 Iniciando conexión...")
        
        q = Quotex(email=email, password=password, headless=False)
        q.trace_ws = True
        
        print("🔌 Estableciendo conexión WebSocket...")
        start_time = datetime.now()
        
        connected = await q.connect()
        
        connection_time = (datetime.now() - start_time).total_seconds()
        print(f"⏱️  Tiempo de conexión: {connection_time:.2f} segundos")
        
        if connected:
            print("✅ Conexión WebSocket establecida")
            
            # Verificar estado detallado
            print("🔍 Verificando estado de conexión...")
            
            # Verificar SSID
            ssid_ok = bool(q.api.SSID) if hasattr(q, 'api') else False
            print(f"🎫 SSID presente: {'✅' if ssid_ok else '❌'}")
            
            # Verificar WebSocket
            ws_ok = not q.api.check_websocket_if_error if hasattr(q, 'api') else False
            print(f"🌐 WebSocket sin errores: {'✅' if ws_ok else '❌'}")
            
            # Verificar balance
            try:
                balance = await q.get_balance()
                balance_ok = balance is not None
                print(f"💰 Balance disponible: {'✅' if balance_ok else '❌'} ({balance if balance_ok else 'N/A'})")
            except Exception as e:
                balance_ok = False
                print(f"💰 Balance disponible: ❌ (Error: {e})")
            
            # Estado general
            all_ok = ssid_ok and ws_ok and balance_ok
            print(f"\n🎯 Estado general: {'✅ CONECTADO' if all_ok else '⚠️ CONEXIÓN PARCIAL'}")
            
            if all_ok:
                print("🎉 ¡Conexión exitosa! El bot debería funcionar correctamente.")
                return True
            else:
                print("⚠️ Conexión establecida pero con problemas. Revisa los detalles arriba.")
                return False
                
        else:
            print("❌ No se pudo establecer conexión WebSocket")
            
            # Verificar errores específicos
            if hasattr(q, 'api') and hasattr(q.api, 'check_websocket_if_error'):
                if q.api.check_websocket_if_error:
                    print("🚨 Error WebSocket detectado - posible bloqueo 403")
            
            return False
            
    except Exception as e:
        error_msg = str(e).lower()
        print(f"❌ Error de conexión: {e}")
        
        # Análisis específico de errores
        if '403' in error_msg or 'forbidden' in error_msg:
            print("🚨 BLOQUEO CLOUDFLARE DETECTADO (403 Forbidden)")
            print("📋 Sigue las recomendaciones de red mostradas arriba")
        elif 'timeout' in error_msg:
            print("⏰ Timeout de conexión - verifica tu red")
        elif 'ssl' in error_msg or 'certificate' in error_msg:
            print("🔒 Problema de certificado SSL")
        
        return False

async def main():
    """Función principal del diagnóstico."""
    print("=" * 60)
    print("🔧 DIAGNÓSTICO DE RED Y CONEXIÓN A QUOTEX")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Análisis de red
    network_analysis = analyze_network_environment()
    
    print("\n" + "=" * 60)
    print("📋 RECOMENDACIONES")
    print("=" * 60)
    
    for rec in network_analysis["recommendations"]:
        if rec:  # Evitar líneas vacías
            print(rec)
    
    print("\n" + "=" * 60)
    print("🔗 PRUEBA DE CONEXIÓN A QUOTEX")
    print("=" * 60)
    
    # Prueba de conexión
    success = await test_quotex_connection()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN FINAL")
    print("=" * 60)
    
    ip_info = network_analysis["ip_info"]
    
    print(f"🌐 Tipo de red: {ip_info['type']}")
    print(f"🎯 Conexión Quotex: {'✅ EXITOSA' if success else '❌ FALLIDA'}")
    
    if ip_info.get("is_datacenter") or ip_info.get("is_vpn"):
        print("🚨 ACCIÓN REQUERIDA: Cambia tu tipo de conexión")
    elif success:
        print("🎉 ¡Todo listo! El bot debería funcionar correctamente")
    else:
        print("⚠️ Revisa las recomendaciones y vuelve a intentar")
    
    print("\n💡 TIP: Ejecuta este script periódicamente para monitorear tu red")

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Ejecutar diagnóstico
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Diagnóstico interrumpido por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
