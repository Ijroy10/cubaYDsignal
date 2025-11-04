# 🔒 Configurar ProtonVPN Free en Render

## ⚡ Guía Rápida (10 minutos)

Esta guía te ayudará a configurar ProtonVPN Free para que el bot funcione en Render (USA).

---

## 📋 **Paso 1: Crear Cuenta ProtonVPN Free**

1. Ve a: https://account.protonvpn.com/signup?plan=free
2. Completa el registro (es gratis)
3. Confirma tu email

---

## 📥 **Paso 2: Descargar Configuración OpenVPN**

1. Inicia sesión en: https://account.protonvpn.com
2. Ve a: **Downloads** → **OpenVPN configuration files**
3. Selecciona:
   - **Platform**: Router
   - **Protocol**: UDP
   - **Country**: Netherlands (NL) o Brasil (BR)
   - **Server**: Free server (cualquiera)
4. Descarga el archivo `.ovpn`

**Ejemplo de archivo descargado:**
```
nl-free-01.protonvpn.udp.ovpn
```

---

## 🔑 **Paso 3: Obtener Credenciales OpenVPN**

1. En la misma página de Downloads
2. Busca la sección: **OpenVPN / IKEv2 username**
3. Copia:
   - **Username**: (algo como `abc123+pmp`)
   - **Password**: (una contraseña larga)

**IMPORTANTE:** Estas credenciales son DIFERENTES a tu contraseña de ProtonVPN.

---

## 📁 **Paso 4: Agregar Archivos al Proyecto**

### **4.1. Copiar archivo .ovpn**

```powershell
# En PowerShell, navega al proyecto
cd "C:\Users\tahiyana\Documents\Bot señales Aron\bot Aroon"

# Copia el archivo descargado y renómbralo
copy "C:\Users\tahiyana\Downloads\nl-free-01.protonvpn.udp.ovpn" "vpn_configs\proton.ovpn"
```

### **4.2. Crear archivo de credenciales**

Crea el archivo: `vpn_configs\proton_auth.txt`

**Contenido:**
```
tu_username_openvpn
tu_password_openvpn
```

**Ejemplo:**
```
abc123+pmp
Xk9mP2nQ7vR4sT8w
```

---

## 📤 **Paso 5: Subir a GitHub**

```powershell
# Agregar archivos
git add .gitignore
git add vpn_configs/proton.ovpn
git add vpn_configs/proton_auth.txt

# Verificar que se agregaron
git status

# Commit
git commit -m "Agregar configuración ProtonVPN Free para Render"

# Push
git push origin main
```

---

## 🔄 **Paso 6: Redeploy en Render**

1. Ve a: https://dashboard.render.com
2. Selecciona tu servicio
3. Click en **Manual Deploy** → **Deploy latest commit**
4. Espera 2-3 minutos

---

## ✅ **Paso 7: Verificar en Logs**

Busca estas líneas en los logs de Render:

```
[VPN] 🌍 Verificando ubicación geográfica...
[VPN] 🌍 Ubicación detectada: US - Portland, OR
[VPN] 🚫 País bloqueado detectado: US
[VPN] 🔌 Intentando conectar VPN automáticamente...
[VPN] 📁 Configuraciones OpenVPN encontradas: 1
[VPN] 📁 Usando configuración OpenVPN: proton.ovpn
[VPN] ✅ OpenVPN conectado exitosamente
[VPN] 🌍 Nueva ubicación: NL - Netherlands
[VPN] ✅ Quotex es accesible desde esta ubicación
[Quotex] Intentando conectar con usuario: ijroyquotex@gmail.com
[Quotex] ✅ Conexión WebSocket establecida
```

---

## 🎯 **Resultado Esperado**

Después de configurar ProtonVPN:

- ✅ Bot detecta que está en USA
- ✅ Activa ProtonVPN automáticamente
- ✅ Cambia ubicación a Netherlands/Brasil
- ✅ Conecta a Quotex exitosamente
- ✅ Envía señales normalmente

---

## 🔧 **Solución de Problemas**

### **Problema: "No se encontraron configuraciones OpenVPN"**

**Solución:**
- Verifica que el archivo se llame exactamente: `proton.ovpn`
- Verifica que esté en: `vpn_configs/proton.ovpn`

### **Problema: "Error de autenticación OpenVPN"**

**Solución:**
- Verifica que `proton_auth.txt` tenga 2 líneas
- Línea 1: username OpenVPN
- Línea 2: password OpenVPN
- Sin espacios extra

### **Problema: "OpenVPN no está instalado"**

**Solución:**
Render debe tener OpenVPN preinstalado. Si no, crea `render-build.sh`:

```bash
#!/bin/bash
apt-get update
apt-get install -y openvpn
pip install -r "bot Aroon/requirements.txt"
```

Y en Render:
- **Build Command**: `bash render-build.sh`

---

## 📊 **Comparación de Servidores ProtonVPN Free**

| País | Latencia desde USA | Velocidad | Recomendación |
|------|-------------------|-----------|---------------|
| 🇳🇱 Netherlands | ~100ms | ⭐⭐⭐⭐⭐ | ⭐ Mejor opción |
| 🇯🇵 Japan | ~150ms | ⭐⭐⭐⭐ | Buena |
| 🇺🇸 USA | 0ms | ⭐⭐⭐⭐⭐ | ❌ Bloqueado por Quotex |

**Recomendación:** Usa **Netherlands** (mejor velocidad y latencia).

---

## 💡 **Notas Importantes**

1. **ProtonVPN Free tiene límites:**
   - 1 conexión simultánea
   - 3 países disponibles (NL, JP, USA)
   - Velocidad media (suficiente para trading)

2. **Alternativa si ProtonVPN no funciona:**
   - Windscribe Free: 10GB/mes
   - Hide.me Free: 10GB/mes

3. **Seguridad:**
   - Las credenciales OpenVPN son seguras para subir a GitHub
   - Son específicas para OpenVPN, no tu contraseña principal
   - Puedes regenerarlas en cualquier momento

---

## 🎉 **¡Listo!**

Una vez configurado, el bot:
- ✅ Detectará automáticamente USA
- ✅ Activará ProtonVPN
- ✅ Conectará a Quotex
- ✅ Funcionará 24/7 en Render

**¿Problemas?** Revisa los logs de Render o contacta al desarrollador.

---

**Desarrollado por:** Yorji Fonseca (@Ijroy10)  
**Fecha:** Noviembre 2025
