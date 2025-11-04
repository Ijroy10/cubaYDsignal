# 🌐 Proxies SOCKS5 Gratuitos de Latinoamérica

## ✅ **YA CONFIGURADO - Listo para Usar**

El bot ya está configurado con **proxies SOCKS5 gratuitos de Brasil** que se actualizan automáticamente.

---

## 📋 **Proxies Configurados**

### **Proxy Principal (Activo):**
```
País: 🇧🇷 Brasil
Tipo: SOCKS5
IP: 187.63.9.62
Puerto: 63253
Autenticación: No requiere
```

### **Proxies de Respaldo (7 adicionales):**
Ver archivo: `vpn_configs/proxies_latam_gratis.json`

---

## 🚀 **Cómo Funciona**

1. **Bot detecta USA** → Activa proxy automáticamente
2. **Intenta conectar** → Proxy SOCKS5 Brasil (187.63.9.62:63253)
3. **Si falla** → Prueba con proxies de respaldo
4. **Conecta a Quotex** → Desde Brasil (sin bloqueo)

---

## ✅ **Ventajas de Proxies Gratuitos**

| Característica | Valor |
|----------------|-------|
| **Costo** | 🆓 **GRATIS** |
| **Configuración** | ✅ Ya está lista |
| **País** | 🇧🇷 Brasil (Quotex permitido) |
| **Autenticación** | ❌ No requiere cuenta |
| **Respaldos** | 7 proxies adicionales |

---

## ⚠️ **Limitaciones**

- 🐌 **Velocidad variable** (depende del proxy)
- ⏱️ **Puede ser lento** en horas pico
- 🔄 **Disponibilidad no garantizada** (proxies públicos)
- 📊 **Sin soporte técnico**

---

## 🔄 **Actualizar Lista de Proxies (Semanal)**

Los proxies gratuitos cambian frecuentemente. Actualiza cada semana:

### **Opción 1: Automático (Recomendado)**

```powershell
# Descargar lista actualizada de Brasil
curl -sL https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/countries/BR/data.json -o proxies_br.json

# Ver proxies SOCKS5
cat proxies_br.json | grep "socks5"
```

### **Opción 2: Manual**

1. Ve a: https://github.com/proxifly/free-proxy-list/tree/main/proxies/countries/BR
2. Descarga `data.json`
3. Busca proxies con `"protocol": "socks5"`
4. Actualiza `vpn_configs/proxy_config.json`

---

## 📊 **Fuentes de Proxies Gratuitos**

### **1. Proxifly (Recomendado)**
- **URL:** https://github.com/proxifly/free-proxy-list
- **Actualización:** Cada 5 minutos
- **Países:** Brasil, México, Argentina, Chile
- **Tipos:** SOCKS4, SOCKS5, HTTP

### **2. FreeProxy.World**
- **URL:** https://www.freeproxy.world/?type=socks5
- **Actualización:** Diaria
- **Filtros:** Por país y tipo

### **3. ProxyScrape**
- **URL:** https://proxyscrape.com/free-proxy-list
- **Actualización:** Cada hora
- **API:** Disponible

---

## 🔧 **Cambiar Proxy Manualmente**

Si el proxy actual no funciona, edita: `vpn_configs/proxy_config.json`

```json
{
  "tipo": "socks5",
  "host": "NUEVO_IP_AQUI",
  "puerto": NUEVO_PUERTO_AQUI,
  "usuario": "",
  "password": "",
  "pais": "BR",
  "descripcion": "Proxy SOCKS5 Brasil - Gratis"
}
```

Luego:
```powershell
git add vpn_configs/proxy_config.json
git commit -m "Actualizar proxy SOCKS5"
git push origin main
```

---

## 🎯 **Proxies por País**

### **🇧🇷 Brasil (Recomendado)**
```
https://github.com/proxifly/free-proxy-list/tree/main/proxies/countries/BR
```

### **🇲🇽 México**
```
https://github.com/proxifly/free-proxy-list/tree/main/proxies/countries/MX
```

### **🇦🇷 Argentina**
```
https://github.com/proxifly/free-proxy-list/tree/main/proxies/countries/AR
```

### **🇨🇱 Chile**
```
https://github.com/proxifly/free-proxy-list/tree/main/proxies/countries/CL
```

---

## 🆚 **Comparación: Gratis vs Pago**

| Característica | Gratis | Webshare ($10/mes) |
|----------------|--------|-------------------|
| **Velocidad** | 🐌 Variable | ⚡ Rápida |
| **Estabilidad** | ⚠️ Baja | ✅ Alta |
| **Soporte** | ❌ No | ✅ Sí |
| **Ancho de banda** | ♾️ Ilimitado | 1GB/mes |
| **Uptime** | ~60% | ~99% |
| **Recomendación** | Pruebas | Producción |

---

## 📝 **Logs Esperados en Render**

### **✅ Conexión Exitosa:**
```
[VPN] 🌍 Ubicación detectada: US - Portland, OR
[VPN] 🚫 País bloqueado detectado: US
[VPN] 📁 Configuración de proxy encontrada: Proxy SOCKS5 Brasil - Gratis
[VPN] 🔌 Configurando proxy SOCKS5: 187.63.9.62:63253
[VPN] ✅ Proxy SOCKS5 configurado exitosamente
[VPN] ✅ Quotex es accesible desde esta ubicación
[Quotex] ✅ Conexión WebSocket establecida
```

### **❌ Proxy No Disponible:**
```
[VPN] ❌ Proxy no responde: Connection timeout
[VPN] 🔄 Intentando con proxy de respaldo...
[VPN] 🔌 Configurando proxy SOCKS5: 170.245.248.45:60606
```

---

## 🔍 **Solución de Problemas**

### **Problema: "Proxy no responde"**

**Causa:** Proxy caído o bloqueado

**Solución:**
1. Actualiza `proxy_config.json` con otro proxy de la lista
2. O descarga lista actualizada de Proxifly
3. Redeploy en Render

### **Problema: "Connection timeout"**

**Causa:** Proxy muy lento

**Solución:**
- Prueba con otro proxy de la lista
- Considera upgrade a Webshare ($10/mes)

### **Problema: "Quotex still blocked"**

**Causa:** Proxy de país bloqueado

**Solución:**
- Verifica que el proxy sea de Brasil, México o Argentina
- Evita proxies de USA, UK, Canadá

---

## 💡 **Recomendaciones**

### **Para Desarrollo/Pruebas:**
✅ **Usar proxies gratuitos** (suficiente)

### **Para Producción 24/7:**
⭐ **Upgrade a Webshare** ($10/mes)
- Más estable
- Mejor velocidad
- Soporte técnico
- 99% uptime

---

## 🎉 **¡Listo para Usar!**

El bot ya está configurado con proxy gratuito de Brasil. Solo necesitas:

1. ✅ **Subir cambios a GitHub**
2. ✅ **Redeploy en Render**
3. ✅ **Verificar logs**

```powershell
git add .
git commit -m "Configurar proxies SOCKS5 gratuitos de Brasil"
git push origin main
```

---

## 📚 **Recursos Adicionales**

- **Proxifly GitHub:** https://github.com/proxifly/free-proxy-list
- **Guía Webshare:** `CONFIGURAR_PROXY_WEBSHARE.md`
- **VPN Manager:** `src/utils/vpn_manager.py`

---

**Desarrollado por:** Yorji Fonseca (@Ijroy10)  
**Fecha:** Noviembre 2025  
**Última actualización de proxies:** 04/11/2025
