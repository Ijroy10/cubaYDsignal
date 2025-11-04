# 🔒 Configuración de VPN Automática para Quotex

## 📋 Descripción

El bot ahora incluye **detección geográfica automática** y **conexión VPN** para evitar el bloqueo de Quotex cuando el servidor está en **Estados Unidos**.

### ¿Cómo funciona?

1. **Detección Automática**: Al iniciar, el bot detecta tu ubicación geográfica
2. **Activación Inteligente**: Si detecta que estás en Estados Unidos, activa la VPN automáticamente
3. **Conexión Segura**: Se conecta a un servidor VPN en país permitido (Cuba, Canadá, México, Argentina)
4. **Sin Intervención**: Todo es automático, no necesitas hacer nada manualmente

---

## 🌍 Países Soportados

### ✅ Países Permitidos (No necesitan VPN)
- 🇨🇺 Cuba
- 🇨🇦 Canadá
- 🇲🇽 México
- 🇦🇷 Argentina
- 🇧🇷 Brasil
- 🇨🇱 Chile
- 🇨🇴 Colombia
- 🇵🇪 Perú
- 🇻🇪 Venezuela
- 🇪🇨 Ecuador

### 🚫 Países Bloqueados (Requieren VPN)
- 🇺🇸 Estados Unidos

---

## 🔧 Opciones de Configuración VPN

### **Opción 1: WireGuard (Recomendado)** ⭐

WireGuard es más rápido y moderno que OpenVPN.

#### Instalación en Linux (Render/VPS):
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install wireguard

# CentOS/RHEL
sudo yum install wireguard-tools
```

#### Instalación en Windows:
1. Descargar desde: https://www.wireguard.com/install/
2. Instalar el cliente

#### Configuración:
1. Obtén un archivo `.conf` de tu proveedor VPN (Mullvad, ProtonVPN, etc.)
2. Colócalo en: `vpn_configs/wireguard.conf`

**Ejemplo de archivo `wireguard.conf`:**
```ini
[Interface]
PrivateKey = TU_CLAVE_PRIVADA_AQUI
Address = 10.64.0.2/32
DNS = 10.64.0.1

[Peer]
PublicKey = CLAVE_PUBLICA_DEL_SERVIDOR
Endpoint = ca-montreal.vpn.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

---

### **Opción 2: OpenVPN**

#### Instalación en Linux:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openvpn

# CentOS/RHEL
sudo yum install openvpn
```

#### Instalación en Windows:
1. Descargar desde: https://openvpn.net/community-downloads/
2. Instalar el cliente

#### Configuración:
1. Obtén un archivo `.ovpn` de tu proveedor VPN
2. Colócalo en: `vpn_configs/config.ovpn`

**Ejemplo de archivo `config.ovpn`:**
```
client
dev tun
proto udp
remote ca-montreal.vpn.com 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth SHA512
cipher AES-256-CBC
verb 3
auth-user-pass auth.txt
```

3. Si requiere usuario/contraseña, crea `vpn_configs/auth.txt`:
```
tu_usuario
tu_contraseña
```

---

### **Opción 3: Proxy SOCKS5** 🚀

La opción más simple si tienes un proxy SOCKS5.

#### Configuración en el código:

Edita `src/utils/vpn_manager.py` y agrega al final del método `auto_conectar`:

```python
# Configurar proxy SOCKS5
proxies = self.conectar_vpn_proxy_socks5(
    host='tu-proxy.com',
    port=1080,
    username='tu_usuario',  # Opcional
    password='tu_contraseña'  # Opcional
)

if proxies:
    # Configurar requests para usar el proxy
    import requests
    requests.Session().proxies = proxies
    return True
```

---

## 🎯 Proveedores VPN Recomendados

### **1. Mullvad VPN** ⭐⭐⭐⭐⭐
- **Precio**: €5/mes
- **Sin logs**: Política estricta de no registro
- **Anónimo**: No requiere email
- **Protocolos**: WireGuard, OpenVPN
- **Servidores**: Canadá, México, Argentina
- **Web**: https://mullvad.net

### **2. ProtonVPN** ⭐⭐⭐⭐
- **Precio**: Gratis (limitado) / $4.99/mes
- **Sin logs**: Política verificada
- **Protocolos**: WireGuard, OpenVPN
- **Servidores**: Canadá, México
- **Web**: https://protonvpn.com

### **3. NordVPN** ⭐⭐⭐⭐
- **Precio**: $3.99/mes (plan 2 años)
- **Sin logs**: Auditado independientemente
- **Protocolos**: NordLynx (WireGuard), OpenVPN
- **Servidores**: Canadá, México, Argentina, Brasil
- **Web**: https://nordvpn.com

### **4. Private Internet Access (PIA)** ⭐⭐⭐
- **Precio**: $2.19/mes (plan 3 años)
- **Sin logs**: Política verificada en corte
- **Protocolos**: WireGuard, OpenVPN
- **Servidores**: Canadá, México
- **Web**: https://www.privateinternetaccess.com

---

## 📁 Estructura de Archivos

```
bot Aroon/
├── vpn_configs/              ← Crear esta carpeta
│   ├── wireguard.conf       ← Archivo WireGuard
│   ├── config.ovpn          ← Archivo OpenVPN
│   └── auth.txt             ← Credenciales (si se necesitan)
├── src/
│   └── utils/
│       └── vpn_manager.py   ← Módulo VPN (ya creado)
└── VPN_SETUP.md             ← Esta guía
```

---

## 🚀 Pasos de Configuración Rápida

### Para Render (Servidor en USA):

1. **Obtener configuración VPN:**
   ```bash
   # Ejemplo con Mullvad
   # 1. Crear cuenta en mullvad.net
   # 2. Descargar archivo WireGuard para Canadá
   # 3. Subir a tu repositorio en: vpn_configs/wireguard.conf
   ```

2. **Instalar WireGuard en Render:**
   
   Agrega al `Dockerfile` o script de inicio:
   ```dockerfile
   RUN apt-get update && apt-get install -y wireguard
   ```

3. **Dar permisos:**
   ```bash
   chmod 600 vpn_configs/wireguard.conf
   ```

4. **Iniciar el bot:**
   El bot detectará automáticamente que está en USA y activará la VPN.

---

## 🔍 Verificación

### Ver logs del bot:
```bash
# Busca estos mensajes:
[VPN] 🌍 Verificando ubicación geográfica...
[VPN] 🚫 Servidor en Estados Unidos detectado
[VPN] 🔌 Intentando conectar VPN automáticamente...
[VPN] ✅ VPN conectada exitosamente
[VPN] 🌍 Nueva ubicación establecida
```

### Verificar IP manualmente:
```bash
curl https://ipapi.co/json/
```

---

## ⚠️ Troubleshooting

### Problema: "No se pudo conectar VPN"

**Solución 1:** Verificar que el archivo de configuración existe
```bash
ls -la vpn_configs/
```

**Solución 2:** Verificar permisos
```bash
chmod 600 vpn_configs/*.conf
chmod 600 vpn_configs/*.ovpn
```

**Solución 3:** Instalar dependencias
```bash
# Linux
sudo apt install wireguard openvpn

# Verificar instalación
which wg-quick
which openvpn
```

### Problema: "Quotex sigue bloqueado"

**Solución:** Verificar que la VPN cambió la IP
```bash
# Antes de VPN
curl https://ipapi.co/country/

# Después de VPN (debería mostrar CA, MX, AR, etc.)
curl https://ipapi.co/country/
```

---

## 🔐 Seguridad

### Recomendaciones:

1. ✅ **No guardes credenciales en el código**
   - Usa variables de entorno
   - O archivos de configuración con permisos restringidos

2. ✅ **Usa VPN sin logs**
   - Mullvad, ProtonVPN, PIA

3. ✅ **Verifica la conexión**
   - El bot verifica automáticamente que Quotex sea accesible

4. ✅ **Mantén actualizado**
   - Actualiza regularmente los archivos de configuración VPN

---

## 📞 Soporte

Si tienes problemas:

1. Revisa los logs del bot
2. Verifica que el archivo VPN esté en `vpn_configs/`
3. Prueba manualmente la conexión VPN
4. Contacta al soporte de tu proveedor VPN

---

## 🎉 ¡Listo!

Una vez configurado, el bot:
- ✅ Detectará automáticamente si está en USA
- ✅ Activará la VPN sin intervención
- ✅ Se conectará a Quotex desde ubicación permitida
- ✅ Te notificará por Telegram del estado

**¡Disfruta del trading sin restricciones geográficas!** 🚀
