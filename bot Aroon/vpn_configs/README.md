# 📁 Carpeta de Configuración VPN

Esta carpeta contiene los archivos de configuración para la VPN automática.

## 📋 Archivos Soportados

### WireGuard (Recomendado)
- **Archivo**: `wireguard.conf` o cualquier `.conf`
- **Formato**: Configuración WireGuard estándar

### OpenVPN
- **Archivo**: `config.ovpn` o cualquier `.ovpn`
- **Formato**: Configuración OpenVPN estándar
- **Credenciales** (opcional): `auth.txt` con usuario y contraseña

## 🚀 Configuración Rápida

### Opción 1: WireGuard

1. Obtén un archivo `.conf` de tu proveedor VPN
2. Cópialo aquí con el nombre `wireguard.conf`
3. El bot lo detectará automáticamente

### Opción 2: OpenVPN

1. Obtén un archivo `.ovpn` de tu proveedor VPN
2. Cópialo aquí con el nombre `config.ovpn`
3. Si requiere autenticación, crea `auth.txt`:
   ```
   tu_usuario
   tu_contraseña
   ```

### Opción 3: Proxy SOCKS5

Si prefieres usar un proxy SOCKS5, edita `src/utils/vpn_manager.py` y configura:

```python
proxies = vpn_manager.conectar_vpn_proxy_socks5(
    host='tu-proxy.com',
    port=1080,
    username='usuario',  # Opcional
    password='contraseña'  # Opcional
)
```

## 🔒 Seguridad

⚠️ **IMPORTANTE**: 
- No subas estos archivos a repositorios públicos
- Agrega `vpn_configs/` al `.gitignore`
- Usa permisos restrictivos: `chmod 600 *.conf *.ovpn`

## 📝 Ejemplo de .gitignore

Agrega esto a tu `.gitignore`:
```
# VPN Configs (privados)
vpn_configs/*.conf
vpn_configs/*.ovpn
vpn_configs/auth.txt
```

## ✅ Verificación

Después de configurar, el bot mostrará:
```
[VPN] 🌍 Verificando ubicación geográfica...
[VPN] 🚫 Servidor en Estados Unidos detectado
[VPN] 🔌 Intentando conectar VPN automáticamente...
[VPN] 📁 Usando configuración WireGuard: wireguard.conf
[VPN] ✅ VPN conectada exitosamente
```

## 🎯 Proveedores Recomendados

- **Mullvad**: https://mullvad.net (€5/mes, sin logs)
- **ProtonVPN**: https://protonvpn.com (Gratis disponible)
- **NordVPN**: https://nordvpn.com ($3.99/mes)
- **PIA**: https://privateinternetaccess.com ($2.19/mes)

## 📞 Ayuda

Si tienes problemas, revisa `VPN_SETUP.md` en la raíz del proyecto.
