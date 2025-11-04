# 🆓 Cloudflare WARP - VPN Gratis e Ilimitado

## ✅ Cloudflare WARP - 100% Gratis

Cloudflare WARP es un VPN gratuito, ilimitado y muy rápido.

### Ventajas
- ✅ Completamente gratis
- ✅ Sin límite de datos
- ✅ Muy rápido (red de Cloudflare)
- ✅ Fácil de instalar
- ✅ Cambia tu ubicación automáticamente

### Desventajas
- ⚠️ No puedes elegir el país específico (en versión gratis)
- ⚠️ Puede asignarte cualquier país de su red

---

## 📦 Instalación en Linux (Render/VPS)

### Paso 1: Instalar Cloudflare WARP

```bash
# Agregar repositorio de Cloudflare
curl https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list

# Instalar
sudo apt update
sudo apt install cloudflare-warp
```

### Paso 2: Registrar y Conectar

```bash
# Registrar el cliente
warp-cli register

# Conectar
warp-cli connect

# Verificar estado
warp-cli status
```

### Paso 3: Verificar IP

```bash
# Ver tu nueva IP
curl https://ipapi.co/json/

# Debería mostrar una IP de Cloudflare en un país diferente
```

---

## 🤖 Integración Automática en el Bot

Modifica `src/utils/vpn_manager.py` para incluir Cloudflare WARP:

### Agregar al método `auto_conectar()`:

```python
# Después de intentar WireGuard y OpenVPN, agregar:

# Intentar Cloudflare WARP
logger.info("[VPN] 🔌 Intentando Cloudflare WARP...")
if self.conectar_cloudflare_warp():
    time.sleep(3)
    if self.verificar_conexion_quotex():
        return True
```

### Agregar nuevo método a la clase `VPNManager`:

```python
def conectar_cloudflare_warp(self) -> bool:
    """Conecta usando Cloudflare WARP"""
    try:
        import subprocess
        
        logger.info("[VPN] 🔌 Conectando a Cloudflare WARP...")
        
        # Verificar si WARP está instalado
        result = subprocess.run(['which', 'warp-cli'], capture_output=True)
        if result.returncode != 0:
            logger.warning("[VPN] ⚠️ Cloudflare WARP no está instalado")
            return False
        
        # Registrar si es necesario
        subprocess.run(['warp-cli', 'register'], capture_output=True)
        
        # Conectar
        result = subprocess.run(['warp-cli', 'connect'], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.success("[VPN] ✅ Cloudflare WARP conectado")
            self.vpn_activa = True
            return True
        else:
            logger.error(f"[VPN] ❌ Error conectando WARP: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"[VPN] ❌ Error con Cloudflare WARP: {e}")
        return False
```

---

## 🐳 Para Docker/Render

Agrega al `Dockerfile`:

```dockerfile
# Instalar Cloudflare WARP
RUN curl https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ jammy main" > /etc/apt/sources.list.d/cloudflare-client.list && \
    apt update && \
    apt install -y cloudflare-warp

# Registrar WARP al iniciar
RUN warp-cli register || true
```

---

## 🔍 Verificación

```bash
# Estado de WARP
warp-cli status

# Debería mostrar: Status update: Connected

# Verificar IP
curl https://ipapi.co/json/

# Debería mostrar IP de Cloudflare
```

---

## 💡 Ventajas de Cloudflare WARP

1. **Gratis e Ilimitado**: Sin restricciones de datos o tiempo
2. **Muy Rápido**: Red global de Cloudflare
3. **Fácil de Usar**: Un solo comando para conectar
4. **Automático**: El bot lo activa cuando detecta USA
5. **Confiable**: Infraestructura de Cloudflare

---

## ⚠️ Limitación

- No puedes elegir el país específico en la versión gratis
- Cloudflare asigna automáticamente el mejor servidor
- Puede asignarte USA, Europa, Asia, etc.

**Solución**: Si te asigna USA, desconecta y reconecta:
```bash
warp-cli disconnect
warp-cli connect
```

---

## 🎯 Comparación: ProtonVPN vs Cloudflare WARP

| Característica | ProtonVPN Free | Cloudflare WARP |
|----------------|----------------|-----------------|
| Precio | Gratis | Gratis |
| Datos | Ilimitado | Ilimitado |
| Velocidad | Media | Muy Alta |
| Elegir país | ✅ Sí (3 países) | ❌ No (automático) |
| Instalación | Media | Fácil |
| Latencia | ~150ms | ~50-100ms |
| Recomendado | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🚀 Recomendación

**Usa ambos:**
1. **Cloudflare WARP** como primera opción (más rápido)
2. **ProtonVPN** como respaldo (puedes elegir país)

El bot intentará en orden:
1. WireGuard (si tienes archivo .conf)
2. OpenVPN (si tienes archivo .ovpn)
3. Cloudflare WARP (si está instalado)
4. Proxy SOCKS5 (si está configurado)

---

## ✅ ¡Listo!

Con Cloudflare WARP tienes:
- ✅ VPN gratis e ilimitado
- ✅ Muy rápido para trading
- ✅ Fácil de configurar
- ✅ Automático en el bot

**¡Perfecto para Render sin costos adicionales!** 🎉
