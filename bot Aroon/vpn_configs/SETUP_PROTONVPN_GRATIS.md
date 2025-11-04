# 🆓 Configuración de ProtonVPN GRATIS

## ✅ ProtonVPN Free - Sin límite de datos

### Paso 1: Crear cuenta gratis

1. Ir a: https://protonvpn.com/free-vpn
2. Click en "Get ProtonVPN Free"
3. Crear cuenta (solo necesitas email)
4. Verificar email

### Paso 2: Descargar configuración OpenVPN

1. Iniciar sesión en: https://account.protonvpn.com/login
2. Ir a: **Downloads** → **OpenVPN configuration files**
3. Seleccionar:
   - **Platform**: Linux
   - **Protocol**: UDP (más rápido) o TCP (más estable)
   - **Country**: Selecciona un país cercano a Cuba:
     * **Netherlands** (Países Bajos) - Recomendado
     * **Japan** (Japón)
     * **USA** (solo para salir de USA, no para entrar)

4. Descargar el archivo `.ovpn` (ejemplo: `nl-free-01.protonvpn.udp.ovpn`)

### Paso 3: Obtener credenciales OpenVPN

1. En la misma página de Downloads
2. Buscar sección: **OpenVPN / IKEv2 username**
3. Copiar:
   - **Username**: (algo como `abc123+f1`)
   - **Password**: (tu contraseña especial de OpenVPN)

### Paso 4: Configurar en el bot

1. **Copiar archivo .ovpn:**
   ```bash
   cp ~/Downloads/nl-free-01.protonvpn.udp.ovpn vpn_configs/proton.ovpn
   ```

2. **Crear archivo de credenciales:**
   ```bash
   # Crear vpn_configs/auth.txt con:
   tu_username_openvpn
   tu_password_openvpn
   ```

3. **Dar permisos:**
   ```bash
   chmod 600 vpn_configs/proton.ovpn
   chmod 600 vpn_configs/auth.txt
   ```

### Paso 5: Instalar OpenVPN (si no lo tienes)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openvpn

# Verificar instalación
which openvpn
```

### Paso 6: ¡Listo!

El bot detectará automáticamente el archivo `proton.ovpn` y se conectará cuando esté en USA.

---

## 🔍 Verificación

### Probar manualmente:
```bash
# Conectar manualmente para probar
sudo openvpn --config vpn_configs/proton.ovpn --auth-user-pass vpn_configs/auth.txt

# En otra terminal, verificar IP:
curl https://ipapi.co/json/
```

### Ver logs del bot:
```
[VPN] 🌍 Verificando ubicación geográfica...
[VPN] 🚫 Servidor en Estados Unidos detectado
[VPN] 🔌 Intentando conectar VPN automáticamente...
[VPN] 📁 Usando configuración OpenVPN: proton.ovpn
[VPN] ✅ OpenVPN conectado exitosamente
```

---

## ⚡ Alternativa: WireGuard (Más Rápido)

ProtonVPN Free también soporta WireGuard:

1. En Downloads, seleccionar: **WireGuard configuration**
2. Descargar archivo `.conf`
3. Copiar a: `vpn_configs/proton.conf`
4. El bot lo detectará automáticamente

---

## 💡 Tips

- **Velocidad**: WireGuard es más rápido que OpenVPN
- **Estabilidad**: OpenVPN TCP es más estable en conexiones inestables
- **Latencia**: Elige servidor más cercano a Cuba (Netherlands recomendado)

---

## 🎯 Países Disponibles en ProtonVPN Free

| País | Código | Latencia desde Cuba | Recomendado |
|------|--------|---------------------|-------------|
| Netherlands | NL | ~150ms | ⭐⭐⭐⭐⭐ |
| Japan | JP | ~250ms | ⭐⭐⭐ |
| USA | US | ~50ms | ❌ (solo para salir) |

---

## ✅ Ventajas de ProtonVPN Free

- ✅ Sin límite de datos (ilimitado)
- ✅ Sin límite de tiempo
- ✅ Sin logs (política verificada)
- ✅ Empresa suiza (privacidad fuerte)
- ✅ Soporta OpenVPN y WireGuard
- ✅ No requiere tarjeta de crédito

---

## 🚀 ¡Listo para usar!

Una vez configurado, el bot:
1. Detectará que está en USA
2. Se conectará automáticamente a ProtonVPN
3. Cambiará la IP a Netherlands
4. Accederá a Quotex sin restricciones

**¡Todo gratis y automático!** 🎉
