# 🌐 Configurar Proxy SOCKS5 con Webshare (GRATIS)

## ⚡ Guía Rápida (5 minutos)

Esta guía te ayudará a configurar un proxy SOCKS5 gratuito para que el bot funcione en Render (USA).

---

## 📋 **Paso 1: Crear Cuenta en Webshare**

1. Ve a: https://www.webshare.io/
2. Click en **"Sign Up"** (arriba derecha)
3. Completa:
   - Email
   - Contraseña
   - Acepta términos
4. Click en **"Create Account"**
5. **Verifica tu email** (revisa spam si no llega)

---

## 🔑 **Paso 2: Obtener Credenciales del Proxy**

1. Inicia sesión en: https://proxy.webshare.io/
2. Ve a: **"Proxy" → "Proxy List"** (menú izquierdo)
3. Verás una tabla con proxies disponibles

### **Buscar Proxy de Brasil o México:**

Filtra por país:
- **BR** (Brasil) - Recomendado
- **MX** (México)
- **AR** (Argentina)

### **Copiar Credenciales:**

Verás algo como:

```
IP Address       Port    Username           Password
138.128.59.42    80      username_123       pass_abc456
```

**Copia:**
- IP Address (ejemplo: `138.128.59.42`)
- Port (ejemplo: `80`)
- Username (ejemplo: `username_123`)
- Password (ejemplo: `pass_abc456`)

---

## 📝 **Paso 3: Configurar en el Proyecto**

### **3.1. Editar archivo `proxy_config.json`**

Abre el archivo: `vpn_configs/proxy_config.json`

Reemplaza los valores:

```json
{
  "tipo": "socks5",
  "host": "138.128.59.42",
  "puerto": 80,
  "usuario": "username_123",
  "password": "pass_abc456",
  "pais": "BR",
  "descripcion": "Proxy Webshare Brasil - Gratis"
}
```

**Importante:**
- `host`: IP del proxy
- `puerto`: Puerto del proxy (usualmente 80 o 1080)
- `usuario`: Username de Webshare
- `password`: Password de Webshare
- `pais`: Código del país (BR, MX, AR)

---

## 📤 **Paso 4: Subir a GitHub**

```powershell
# Navegar al proyecto
cd "C:\Users\tahiyana\Documents\Bot señales Aron\bot Aroon"

# Agregar archivos
git add .gitignore
git add vpn_configs/proxy_config.json
git add src/utils/vpn_manager.py
git add CONFIGURAR_PROXY_WEBSHARE.md

# Commit
git commit -m "Agregar configuración de proxy SOCKS5 Webshare"

# Push
git push origin main
```

---

## 🔄 **Paso 5: Redeploy en Render**

1. Ve a: https://dashboard.render.com
2. Selecciona tu servicio
3. Click en **"Manual Deploy"** → **"Deploy latest commit"**
4. Espera 3-5 minutos

---

## ✅ **Paso 6: Verificar en Logs**

Busca estas líneas en los logs de Render:

```
[VPN] 🌍 Ubicación detectada: US - Portland, OR
[VPN] 🚫 País bloqueado detectado: US
[VPN] 🔌 Buscando configuración de proxy SOCKS5...
[VPN] 📁 Configuración de proxy encontrada: Proxy Webshare Brasil - Gratis
[VPN] ✅ Proxy SOCKS5 configurado exitosamente
[VPN] 🌍 Verificando acceso a Quotex...
[VPN] ✅ Quotex es accesible desde esta ubicación
[Quotex] ✅ Conexión WebSocket establecida
```

---

## 🎯 **Resultado Esperado**

Después de configurar el proxy:

- ✅ Bot detecta que está en USA
- ✅ Activa proxy SOCKS5 automáticamente
- ✅ Conecta a través de Brasil/México
- ✅ Conecta a Quotex exitosamente
- ✅ Envía señales normalmente

---

## 📊 **Plan Gratuito de Webshare**

| Característica | Valor |
|----------------|-------|
| **Proxies** | 10 proxies |
| **Ancho de banda** | 1 GB/mes |
| **Velocidad** | Rápida |
| **Países** | 50+ países |
| **Rotación** | Manual |
| **Costo** | **GRATIS** |

**Nota:** 1 GB/mes es suficiente para señales de trading (bajo consumo de datos).

---

## 🔧 **Solución de Problemas**

### **Problema: "Proxy connection failed"**

**Solución:**
- Verifica que las credenciales sean correctas
- Verifica que el proxy esté activo en Webshare
- Prueba con otro proxy de la lista

### **Problema: "Bandwidth limit exceeded"**

**Solución:**
- Has superado 1 GB/mes
- Opciones:
  1. Esperar al próximo mes (se resetea)
  2. Upgrade a plan pago ($2.99/mes por 5GB)
  3. Crear otra cuenta con otro email

### **Problema: "Quotex still blocked"**

**Solución:**
- Verifica que el proxy sea de Brasil o México
- Evita proxies de USA, UK, Canadá
- Prueba con otro proxy de la lista

---

## 💰 **Planes de Pago (Opcional)**

Si necesitas más ancho de banda:

| Plan | Ancho de Banda | Precio |
|------|----------------|--------|
| **Starter** | 5 GB/mes | $2.99/mes |
| **Basic** | 25 GB/mes | $9.99/mes |
| **Plus** | 100 GB/mes | $29.99/mes |

**Recomendación:** El plan gratuito (1GB/mes) es suficiente para el bot de trading.

---

## 🆚 **Alternativas a Webshare**

Si Webshare no funciona:

### **1. ProxyMesh** ($10/mes)
- https://proxymesh.com
- Más estable
- Mejor soporte

### **2. Bright Data** (Caro)
- https://brightdata.com
- Muy profesional
- Desde $500/mes

### **3. ProxyScrape** (Gratis)
- https://proxyscrape.com
- Calidad variable
- Proxies públicos

---

## 🎉 **¡Listo!**

Una vez configurado, el bot:
- ✅ Detectará automáticamente USA
- ✅ Activará el proxy SOCKS5
- ✅ Conectará a Quotex desde Brasil/México
- ✅ Funcionará 24/7 en Render

**¿Problemas?** Revisa los logs de Render o contacta al desarrollador.

---

**Desarrollado por:** Yorji Fonseca (@Ijroy10)  
**Fecha:** Noviembre 2025
