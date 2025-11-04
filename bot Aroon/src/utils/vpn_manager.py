"""
VPN Manager - Detección geográfica y conexión automática a VPN
Evita bloqueos geográficos de Quotex cuando el servidor está en Estados Unidos
"""

import requests
import subprocess
import platform
import os
import time
from typing import Dict, Optional, Tuple
from loguru import logger


class VPNManager:
    """Gestiona la detección de ubicación y conexión VPN automática"""
    
    # Países permitidos donde Quotex funciona sin restricciones
    # Incluye: Latinoamérica, Caribe, Canadá y Europa
    PAISES_PERMITIDOS = [
        # Caribe (Antillas y Región Caribeña)
        'CU',  # Cuba
        'DO',  # República Dominicana
        'HT',  # Haití
        'JM',  # Jamaica
        'TT',  # Trinidad y Tobago
        'BS',  # Bahamas
        'BB',  # Barbados
        'GD',  # Granada
        'LC',  # Santa Lucía
        'VC',  # San Vicente y las Granadinas
        'AG',  # Antigua y Barbuda
        'DM',  # Dominica
        'KN',  # San Cristóbal y Nieves
        'PR',  # Puerto Rico
        'VI',  # Islas Vírgenes (US)
        'VG',  # Islas Vírgenes (UK)
        'KY',  # Islas Caimán
        'TC',  # Islas Turcas y Caicos
        'BM',  # Bermudas
        'AW',  # Aruba
        'CW',  # Curazao
        'SX',  # Sint Maarten
        'BQ',  # Bonaire
        'MF',  # San Martín (Francia)
        'GP',  # Guadalupe
        'MQ',  # Martinica
        'GF',  # Guayana Francesa
        'SR',  # Surinam
        'GY',  # Guyana
        
        # Centroamérica
        'MX',  # México
        'GT',  # Guatemala
        'HN',  # Honduras
        'SV',  # El Salvador
        'NI',  # Nicaragua
        'CR',  # Costa Rica
        'PA',  # Panamá
        'BZ',  # Belice
        
        # Sudamérica
        'CO',  # Colombia
        'VE',  # Venezuela
        'EC',  # Ecuador
        'PE',  # Perú
        'BR',  # Brasil
        'BO',  # Bolivia
        'PY',  # Paraguay
        'UY',  # Uruguay
        'AR',  # Argentina
        'CL',  # Chile
        
        # Norteamérica (excepto USA)
        'CA',  # Canadá
        
        # Europa (principales)
        'ES',  # España
        'PT',  # Portugal
        'FR',  # Francia
        'IT',  # Italia
        'DE',  # Alemania
        'UK',  # Reino Unido
        'GB',  # Gran Bretaña
        'NL',  # Países Bajos
        'BE',  # Bélgica
        'CH',  # Suiza
        'AT',  # Austria
        'SE',  # Suecia
        'NO',  # Noruega
        'DK',  # Dinamarca
        'FI',  # Finlandia
        'IE',  # Irlanda
        'PL',  # Polonia
        'CZ',  # República Checa
        'RO',  # Rumania
        'GR',  # Grecia
    ]
    
    # Países bloqueados (principalmente USA)
    PAISES_BLOQUEADOS = ['US']
    
    # Servidores VPN recomendados por país (priorizados para Latinoamérica)
    # Orden de preferencia: Cuba > Argentina > México > Canadá
    VPN_SERVERS = {
        # Prioridad 1: Cuba (ideal para latencia desde Cuba)
        'CU': ['cu.prod.surfshark.com', 'cu.prod.nordvpn.com'],
        
        # Prioridad 2: Argentina (excelente para Latinoamérica)
        'AR': ['ar.prod.surfshark.com', 'ar-bue.prod.nordvpn.com', 'ar.prod.protonvpn.com'],
        
        # Prioridad 3: México (muy cercano a Cuba, baja latencia)
        'MX': ['mx.prod.surfshark.com', 'mx.prod.nordvpn.com', 'mx.prod.protonvpn.com'],
        
        # Alternativas Latinoamericanas
        'BR': ['br.prod.surfshark.com', 'br-sao.prod.nordvpn.com'],  # Brasil
        'CL': ['cl.prod.surfshark.com', 'cl.prod.nordvpn.com'],      # Chile
        'CO': ['co.prod.surfshark.com', 'co.prod.nordvpn.com'],      # Colombia
        
        # Canadá (backup, más lejano pero confiable)
        'CA': ['ca-montreal.prod.surfshark.com', 'ca-toronto.prod.surfshark.com', 'ca.prod.protonvpn.com'],
    }
    
    # Orden de preferencia para auto-conexión VPN
    PAISES_VPN_PREFERIDOS = ['CU', 'AR', 'MX', 'BR', 'CL', 'CO', 'CA']
    
    def __init__(self):
        self.ubicacion_actual: Optional[Dict] = None
        self.vpn_activa: bool = False
        self.vpn_proceso: Optional[subprocess.Popen] = None
        self.pais_vpn: Optional[str] = None
        
    def detectar_ubicacion(self) -> Tuple[str, Dict]:
        """
        Detecta la ubicación actual del servidor mediante APIs públicas
        
        Returns:
            Tuple[str, Dict]: (código_país, info_completa)
        """
        try:
            # Intentar múltiples servicios de geolocalización
            servicios = [
                'https://ipapi.co/json/',
                'http://ip-api.com/json/',
                'https://ipinfo.io/json',
            ]
            
            for servicio in servicios:
                try:
                    response = requests.get(servicio, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Normalizar respuesta según el servicio
                        if 'country_code' in data:
                            pais = data['country_code']
                        elif 'countryCode' in data:
                            pais = data['countryCode']
                        elif 'country' in data and len(data['country']) == 2:
                            pais = data['country']
                        else:
                            continue
                        
                        self.ubicacion_actual = data
                        logger.info(f"[VPN] 🌍 Ubicación detectada: {pais} - {data.get('city', 'N/A')}, {data.get('region', 'N/A')}")
                        return pais, data
                        
                except Exception as e:
                    logger.warning(f"[VPN] ⚠️ Error con servicio {servicio}: {e}")
                    continue
            
            # Si todos los servicios fallan
            logger.error("[VPN] ❌ No se pudo detectar la ubicación")
            return 'UNKNOWN', {}
            
        except Exception as e:
            logger.error(f"[VPN] ❌ Error detectando ubicación: {e}")
            return 'UNKNOWN', {}
    
    def necesita_vpn(self) -> bool:
        """
        Determina si se necesita VPN basado en la ubicación actual
        
        Returns:
            bool: True si está en país bloqueado (USA)
        """
        pais, info = self.detectar_ubicacion()
        
        if pais in self.PAISES_BLOQUEADOS:
            logger.warning(f"[VPN] 🚫 País bloqueado detectado: {pais}")
            logger.warning(f"[VPN] 🔒 Quotex está restringido en Estados Unidos")
            return True
        elif pais in self.PAISES_PERMITIDOS:
            logger.success(f"[VPN] ✅ País permitido: {pais} - No se necesita VPN")
            return False
        elif pais == 'UNKNOWN':
            logger.warning("[VPN] ⚠️ Ubicación desconocida - Se recomienda usar VPN por seguridad")
            return True
        else:
            logger.info(f"[VPN] ℹ️ País: {pais} - Verificando acceso a Quotex...")
            return False
    
    def conectar_vpn_wireguard(self, config_path: str) -> bool:
        """
        Conecta a VPN usando WireGuard
        
        Args:
            config_path: Ruta al archivo de configuración .conf de WireGuard
            
        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            sistema = platform.system()
            
            if not os.path.exists(config_path):
                logger.error(f"[VPN] ❌ Archivo de configuración no encontrado: {config_path}")
                return False
            
            logger.info(f"[VPN] 🔌 Conectando a WireGuard...")
            
            if sistema == "Linux":
                # Activar interfaz WireGuard en Linux
                cmd = ['sudo', 'wg-quick', 'up', config_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.success("[VPN] ✅ WireGuard conectado exitosamente")
                    self.vpn_activa = True
                    return True
                else:
                    logger.error(f"[VPN] ❌ Error conectando WireGuard: {result.stderr}")
                    return False
                    
            elif sistema == "Windows":
                # En Windows, usar el cliente de WireGuard
                cmd = ['wireguard', '/installtunnelservice', config_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.success("[VPN] ✅ WireGuard conectado exitosamente")
                    self.vpn_activa = True
                    return True
                else:
                    logger.error(f"[VPN] ❌ Error conectando WireGuard: {result.stderr}")
                    return False
            else:
                logger.error(f"[VPN] ❌ Sistema operativo no soportado: {sistema}")
                return False
                
        except Exception as e:
            logger.error(f"[VPN] ❌ Error conectando WireGuard: {e}")
            return False
    
    def conectar_vpn_openvpn(self, config_path: str, auth_file: Optional[str] = None) -> bool:
        """
        Conecta a VPN usando OpenVPN
        
        Args:
            config_path: Ruta al archivo .ovpn
            auth_file: Ruta al archivo con usuario/contraseña (opcional)
            
        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            if not os.path.exists(config_path):
                logger.error(f"[VPN] ❌ Archivo de configuración no encontrado: {config_path}")
                return False
            
            logger.info(f"[VPN] 🔌 Conectando a OpenVPN...")
            
            cmd = ['openvpn', '--config', config_path, '--daemon']
            
            if auth_file and os.path.exists(auth_file):
                cmd.extend(['--auth-user-pass', auth_file])
            
            self.vpn_proceso = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Esperar a que se establezca la conexión
            time.sleep(5)
            
            # Verificar si el proceso sigue corriendo
            if self.vpn_proceso.poll() is None:
                logger.success("[VPN] ✅ OpenVPN conectado exitosamente")
                self.vpn_activa = True
                return True
            else:
                logger.error("[VPN] ❌ OpenVPN falló al conectar")
                return False
                
        except Exception as e:
            logger.error(f"[VPN] ❌ Error conectando OpenVPN: {e}")
            return False
    
    def conectar_vpn_proxy_socks5(self, host: str, port: int, username: str = None, password: str = None) -> Dict:
        """
        Configura proxy SOCKS5 para usar con requests
        
        Args:
            host: Host del proxy
            port: Puerto del proxy
            username: Usuario (opcional)
            password: Contraseña (opcional)
            
        Returns:
            Dict: Configuración de proxies para requests
        """
        try:
            if username and password:
                proxy_url = f"socks5://{username}:{password}@{host}:{port}"
            else:
                proxy_url = f"socks5://{host}:{port}"
            
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            logger.info(f"[VPN] 🔌 Configurando proxy SOCKS5: {host}:{port}")
            
            # Verificar que el proxy funciona
            try:
                response = requests.get('https://ipapi.co/json/', proxies=proxies, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    logger.success(f"[VPN] ✅ Proxy SOCKS5 funcionando - Nueva IP: {data.get('ip', 'N/A')}")
                    logger.success(f"[VPN] 🌍 Nueva ubicación: {data.get('country_name', 'N/A')}")
                    self.vpn_activa = True
                    return proxies
            except Exception as e:
                logger.error(f"[VPN] ❌ Proxy no responde: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"[VPN] ❌ Error configurando proxy: {e}")
            return {}
    
    def conectar_cloudflare_warp(self) -> bool:
        """
        Conecta usando Cloudflare WARP (VPN gratis e ilimitado)
        
        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            logger.info("[VPN] 🔌 Conectando a Cloudflare WARP...")
            
            # Verificar si WARP está instalado
            result = subprocess.run(['which', 'warp-cli'], capture_output=True)
            if result.returncode != 0:
                logger.warning("[VPN] ⚠️ Cloudflare WARP no está instalado")
                logger.info("[VPN] 💡 Instalar con: sudo apt install cloudflare-warp")
                return False
            
            # Registrar si es necesario (no falla si ya está registrado)
            subprocess.run(['warp-cli', 'register'], capture_output=True, stderr=subprocess.DEVNULL)
            
            # Conectar
            result = subprocess.run(['warp-cli', 'connect'], capture_output=True, text=True)
            
            if result.returncode == 0 or 'Success' in result.stdout:
                logger.success("[VPN] ✅ Cloudflare WARP conectado exitosamente")
                self.vpn_activa = True
                self.pais_vpn = 'Cloudflare Network'
                
                # Verificar nueva IP
                try:
                    time.sleep(2)
                    pais, info = self.detectar_ubicacion()
                    logger.success(f"[VPN] 🌍 Nueva ubicación: {pais} - {info.get('city', 'N/A')}")
                except:
                    pass
                
                return True
            else:
                logger.error(f"[VPN] ❌ Error conectando WARP: {result.stderr}")
                return False
                
        except FileNotFoundError:
            logger.warning("[VPN] ⚠️ Comando warp-cli no encontrado")
            logger.info("[VPN] 💡 Instalar Cloudflare WARP:")
            logger.info("[VPN]    curl https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg")
            logger.info("[VPN]    echo 'deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ jammy main' | sudo tee /etc/apt/sources.list.d/cloudflare-client.list")
            logger.info("[VPN]    sudo apt update && sudo apt install cloudflare-warp")
            return False
        except Exception as e:
            logger.error(f"[VPN] ❌ Error con Cloudflare WARP: {e}")
            return False
    
    def desconectar_vpn(self) -> bool:
        """Desconecta la VPN activa"""
        try:
            if not self.vpn_activa:
                logger.info("[VPN] ℹ️ No hay VPN activa para desconectar")
                return True
            
            logger.info("[VPN] 🔌 Desconectando VPN...")
            
            # Si hay proceso de OpenVPN activo
            if self.vpn_proceso and self.vpn_proceso.poll() is None:
                self.vpn_proceso.terminate()
                self.vpn_proceso.wait(timeout=5)
                logger.success("[VPN] ✅ OpenVPN desconectado")
            
            self.vpn_activa = False
            self.vpn_proceso = None
            return True
            
        except Exception as e:
            logger.error(f"[VPN] ❌ Error desconectando VPN: {e}")
            return False
    
    def verificar_conexion_quotex(self) -> bool:
        """
        Verifica si se puede acceder a Quotex desde la ubicación actual
        
        Returns:
            bool: True si Quotex es accesible
        """
        try:
            logger.info("[VPN] 🔍 Verificando acceso a Quotex...")
            
            # Intentar acceder a Quotex
            response = requests.get('https://qxbroker.com', timeout=10)
            
            if response.status_code == 200:
                logger.success("[VPN] ✅ Quotex es accesible desde esta ubicación")
                return True
            else:
                logger.warning(f"[VPN] ⚠️ Quotex respondió con código: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error("[VPN] ❌ No se puede conectar a Quotex - Posible bloqueo geográfico")
            return False
        except Exception as e:
            logger.error(f"[VPN] ❌ Error verificando acceso a Quotex: {e}")
            return False
    
    def auto_conectar(self, config_dir: str = None) -> bool:
        """
        Detecta ubicación y conecta VPN automáticamente si es necesario
        
        Args:
            config_dir: Directorio con archivos de configuración VPN
            
        Returns:
            bool: True si está listo para usar Quotex (con o sin VPN)
        """
        try:
            logger.info("[VPN] 🚀 Iniciando verificación automática...")
            
            # 1. Detectar ubicación
            if not self.necesita_vpn():
                logger.success("[VPN] ✅ No se necesita VPN - Ubicación permitida")
                return True
            
            # 2. Si está en USA, intentar conectar VPN
            logger.warning("[VPN] 🔒 Se requiere VPN para acceder a Quotex")
            
            if not config_dir:
                config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'vpn_configs')
            
            # Buscar archivos de configuración
            if os.path.exists(config_dir):
                # Intentar WireGuard primero
                wg_configs = [f for f in os.listdir(config_dir) if f.endswith('.conf')]
                if wg_configs:
                    config_path = os.path.join(config_dir, wg_configs[0])
                    logger.info(f"[VPN] 📁 Usando configuración WireGuard: {wg_configs[0]}")
                    if self.conectar_vpn_wireguard(config_path):
                        time.sleep(3)
                        if self.verificar_conexion_quotex():
                            return True
                
                # Intentar OpenVPN
                ovpn_configs = [f for f in os.listdir(config_dir) if f.endswith('.ovpn')]
                if ovpn_configs:
                    config_path = os.path.join(config_dir, ovpn_configs[0])
                    logger.info(f"[VPN] 📁 Usando configuración OpenVPN: {ovpn_configs[0]}")
                    if self.conectar_vpn_openvpn(config_path):
                        time.sleep(3)
                        if self.verificar_conexion_quotex():
                            return True
            
            # Intentar Cloudflare WARP (gratis e ilimitado)
            logger.info("[VPN] 🔌 Intentando Cloudflare WARP (gratis)...")
            if self.conectar_cloudflare_warp():
                time.sleep(3)
                if self.verificar_conexion_quotex():
                    return True
            
            # Intentar proxy SOCKS5 desde variables de entorno
            logger.info("[VPN] 🔌 Buscando configuración de proxy SOCKS5...")
            if os.getenv('PROXY_HOST'):
                logger.info("[VPN] 📁 Configuración de proxy encontrada en variables de entorno")
                proxies = self.conectar_vpn_proxy_socks5(
                    host=os.getenv('PROXY_HOST'),
                    port=int(os.getenv('PROXY_PORT', 1080)),
                    username=os.getenv('PROXY_USER'),
                    password=os.getenv('PROXY_PASS')
                )
                if proxies:
                    if self.verificar_conexion_quotex():
                        return True
            
            logger.error("[VPN] ❌ No se pudo establecer conexión VPN")
            logger.error("[VPN] 💡 Soluciones gratuitas:")
            logger.error("[VPN]    1. ProtonVPN Free: https://protonvpn.com/free-vpn")
            logger.error("[VPN]    2. Cloudflare WARP: sudo apt install cloudflare-warp")
            logger.error("[VPN]    3. Coloca archivos .conf o .ovpn en: vpn_configs/")
            return False
            
        except Exception as e:
            logger.error(f"[VPN] ❌ Error en auto_conectar: {e}")
            return False
    
    def obtener_estado(self) -> Dict:
        """Obtiene el estado actual de la VPN y ubicación"""
        return {
            'vpn_activa': self.vpn_activa,
            'ubicacion': self.ubicacion_actual,
            'pais_vpn': self.pais_vpn,
            'quotex_accesible': self.verificar_conexion_quotex() if self.vpn_activa else None
        }


# Instancia global
vpn_manager = VPNManager()
