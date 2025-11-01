"""
SISTEMA DE AUTENTICACIÓN Y GESTIÓN DE USUARIOS
Maneja:
- Clave maestra de administrador
- Claves públicas diarias
- Control de acceso
- Lógica de ingreso tardío
- Mensajes personalizados por estado
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
import hashlib
import secrets
import random

class UserManager:
    def __init__(self):
        self.clave_maestra = "Yorji.010702.CubaYDsignal"  # Clave del administrador
        self.admin_id = "5806367733"  # ID de Telegram del administrador (@Ijroy10 - Yorji Fonseca)
        self.usuarios_activos = {}
        self.usuarios_bloqueados = set()  # Lista de usuarios bloqueados
        self.historial_bloqueos = []  # Historial de bloqueos/desbloqueos
        self.clave_publica_diaria = None
        self.fecha_clave_actual = None
        self.señales_del_dia = []
        self.estadisticas_diarias = {}
        self.cargar_datos_usuarios()
        self.generar_clave_diaria_si_necesario()
        self.cargar_lista_blanca()  # Lista blanca de usuarios
        self.cargar_lista_diaria_autorizada()  # Lista diaria de usuarios autorizados
        self.telegram_bot = None  # Referencia al bot de Telegram para notificaciones
        # Confirmaciones en memoria por día
        self.confirmaciones_dia = {
            'presenal': {},   # pre_id -> set(user_id)
            'senal': {}       # signal_id -> set(user_id)
        }
        # Historial de accesos no autorizados
        self.historial_accesos_no_autorizados = []
        self.cargar_historial_accesos_no_autorizados()
        
    def cargar_datos_usuarios(self):
        """Carga datos de usuarios desde archivo"""
        try:
            with open('data/usuarios.json', 'r') as f:
                data = json.load(f)
                self.usuarios_activos = data.get('usuarios_activos', {})
                self.usuarios_bloqueados = set(data.get('usuarios_bloqueados', []))
                self.historial_bloqueos = data.get('historial_bloqueos', [])
                self.clave_publica_diaria = data.get('clave_publica_diaria')
                self.fecha_clave_actual = data.get('fecha_clave_actual')
                self.señales_del_dia = data.get('señales_del_dia', [])
                self.estadisticas_diarias = data.get('estadisticas_diarias', {})
        except FileNotFoundError:
            print("[UserManager] 📁 Creando nuevo archivo de usuarios")
            self.guardar_datos_usuarios()
    
    def cargar_lista_blanca(self):
        self.lista_blanca = set()
        self.lista_blanca_nombres = set()
        try:
            with open('data/usuarios_autorizados.json', 'r') as f:
                data = json.load(f)
                for item in data:
                    if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
                        self.lista_blanca.add(str(item))
                    else:
                        self.lista_blanca_nombres.add(item.lower())
        except FileNotFoundError:
            self.lista_blanca = set()
            self.lista_blanca_nombres = set()
    
    def cargar_lista_diaria_autorizada(self):
        """Carga la lista diaria de usuarios autorizados por el admin"""
        self.lista_diaria_ids = set()
        self.lista_diaria_nombres = set()
        self.fecha_lista_diaria = None
        
        try:
            with open('data/lista_diaria_autorizada.json', 'r') as f:
                data = json.load(f)
                self.fecha_lista_diaria = data.get('fecha')
                usuarios_autorizados = data.get('usuarios', [])
                
                for item in usuarios_autorizados:
                    if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
                        self.lista_diaria_ids.add(str(item))
                    else:
                        self.lista_diaria_nombres.add(item.lower().replace('@', ''))
                        
        except FileNotFoundError:
            self.lista_diaria_ids = set()
            self.lista_diaria_nombres = set()
            self.fecha_lista_diaria = None
    
    def cargar_historial_accesos_no_autorizados(self):
        """Carga el historial de accesos no autorizados"""
        try:
            with open('data/historial_accesos_no_autorizados.json', 'r') as f:
                self.historial_accesos_no_autorizados = json.load(f)
        except FileNotFoundError:
            self.historial_accesos_no_autorizados = []
    
    def guardar_historial_accesos_no_autorizados(self):
        """Guarda el historial de accesos no autorizados"""
        os.makedirs('data', exist_ok=True)
        with open('data/historial_accesos_no_autorizados.json', 'w') as f:
            json.dump(self.historial_accesos_no_autorizados, f, indent=4, ensure_ascii=False)
    
    def registrar_acceso_no_autorizado(self, user_id: str, username: str, motivo: str, clave_usada: str = None):
        """Registra un intento de acceso no autorizado"""
        registro = {
            'user_id': user_id,
            'username': username,
            'motivo': motivo,
            'clave_usada': clave_usada,
            'fecha_hora': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': datetime.now().isoformat()
        }
        self.historial_accesos_no_autorizados.append(registro)
        self.guardar_historial_accesos_no_autorizados()
        print(f"[UserManager] 🚨 Acceso no autorizado registrado: {username} ({user_id}) - {motivo}")
    
    def actualizar_lista_diaria_autorizada(self, usuarios_lista: List[str]) -> str:
        """Actualiza la lista diaria de usuarios autorizados"""
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        
        # Limpiar listas
        self.lista_diaria_ids = set()
        self.lista_diaria_nombres = set()
        
        # Procesar lista de usuarios
        usuarios_procesados = []
        for usuario in usuarios_lista:
            usuario_limpio = usuario.strip().replace('@', '')
            if usuario_limpio.isdigit():
                self.lista_diaria_ids.add(usuario_limpio)
                usuarios_procesados.append(f"ID: {usuario_limpio}")
            else:
                self.lista_diaria_nombres.add(usuario_limpio.lower())
                usuarios_procesados.append(f"@{usuario_limpio}")
        
        # Guardar en archivo
        data = {
            'fecha': fecha_hoy,
            'usuarios': usuarios_lista,
            'total_usuarios': len(usuarios_lista)
        }
        
        os.makedirs('data', exist_ok=True)
        with open('data/lista_diaria_autorizada.json', 'w') as f:
            json.dump(data, f, indent=4)
        
        self.fecha_lista_diaria = fecha_hoy
        
        return f"✅ Lista diaria actualizada para {fecha_hoy}\n📋 {len(usuarios_lista)} usuarios autorizados:\n" + "\n".join(usuarios_procesados)

    def _persistir_lista_diaria(self):
        """Guarda la lista diaria actual a disco con la fecha de hoy"""
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        usuarios = list(self.lista_diaria_ids) + [f"@{n}" for n in self.lista_diaria_nombres]
        data = {
            'fecha': fecha_hoy,
            'usuarios': usuarios,
            'total_usuarios': len(usuarios)
        }
        os.makedirs('data', exist_ok=True)
        with open('data/lista_diaria_autorizada.json', 'w') as f:
            json.dump(data, f, indent=4)
        self.fecha_lista_diaria = fecha_hoy

    def obtener_lista_diaria(self) -> List[str]:
        """Devuelve la lista diaria actual como cadenas (IDs y @usernames)."""
        salida = []
        salida.extend(sorted(list(self.lista_diaria_ids)))
        salida.extend([f"@{n}" for n in sorted(list(self.lista_diaria_nombres))])
        return salida

    def agregar_a_lista_diaria(self, entrada: str) -> str:
        """Agrega un ID o @username a la lista diaria del día actual y persiste."""
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        if not self.fecha_lista_diaria or self.fecha_lista_diaria != fecha_hoy:
            # Reset si es nuevo día
            self.lista_diaria_ids = set()
            self.lista_diaria_nombres = set()
        val = entrada.strip().replace('@', '')
        agregado = None
        if val.isdigit():
            self.lista_diaria_ids.add(val)
            agregado = f"ID: {val}"
        else:
            self.lista_diaria_nombres.add(val.lower())
            agregado = f"@{val}"
        self._persistir_lista_diaria()
        return f"✅ Agregado a lista diaria: {agregado}"

    def quitar_de_lista_diaria(self, entrada: str) -> str:
        """Quita un ID o @username de la lista diaria del día actual y persiste."""
        val = entrada.strip().replace('@', '')
        eliminado = None
        if val.isdigit() and val in self.lista_diaria_ids:
            self.lista_diaria_ids.remove(val)
            eliminado = f"ID: {val}"
        elif not val.isdigit() and val.lower() in self.lista_diaria_nombres:
            self.lista_diaria_nombres.remove(val.lower())
            eliminado = f"@{val}"
        else:
            return f"⚠️ No se encontró en la lista: {entrada}"
        self._persistir_lista_diaria()
        return f"🗑️ Eliminado de lista diaria: {eliminado}"

    def limpiar_lista_diaria(self) -> str:
        """Limpia por completo la lista diaria del día actual y persiste."""
        self.lista_diaria_ids = set()
        self.lista_diaria_nombres = set()
        self._persistir_lista_diaria()
        return "🧹 Lista diaria limpiada para hoy"

    def guardar_lista_blanca(self):
        # Guarda la lista blanca en el archivo json
        data = list(self.lista_blanca) + list(self.lista_blanca_nombres)
        with open('data/usuarios_autorizados.json', 'w') as f:
            json.dump(data, f, indent=4)

    def esta_en_lista_blanca(self, user_id, username):
        # Verifica si un usuario está en la lista blanca por ID o nombre
        if str(user_id) in self.lista_blanca:
            return True
        if username and username.lower() in self.lista_blanca_nombres:
            return True
        return False
    
    def esta_en_lista_diaria_autorizada(self, user_id, username) -> Tuple[bool, str]:
        """Verifica si un usuario está en la lista diaria autorizada"""
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        
        # Si no hay lista diaria o es de otro día, no está autorizado
        if not self.fecha_lista_diaria or self.fecha_lista_diaria != fecha_hoy:
            return False, "no_lista_diaria"
        
        # Verificar por ID
        if str(user_id) in self.lista_diaria_ids:
            return True, "autorizado_por_id"
        
        # Verificar por nombre de usuario
        if username and username.lower() in self.lista_diaria_nombres:
            return True, "autorizado_por_nombre"
        
        return False, "no_autorizado"
    
    def generar_notificacion_usuario_no_autorizado(self, user_id, username, motivo) -> str:
        """Genera notificación para el admin cuando un usuario no autorizado intenta entrar"""
        fecha_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        if motivo == "no_lista_diaria":
            mensaje = f"⚠️ **ACCESO NO AUTORIZADO**\n\n📅 Fecha: {fecha_hora}\n👤 Usuario: @{username or 'Sin username'} (ID: {user_id})\n\n🚨 **Motivo:** No hay lista diaria de usuarios autorizados para hoy\n\n📝 **Acción requerida:**\nEnvía la lista de usuarios autorizados para hoy usando el comando /listahoy"
        else:
            mensaje = f"⚠️ **ACCESO NO AUTORIZADO**\n\n📅 Fecha: {fecha_hora}\n👤 Usuario: @{username or 'Sin username'} (ID: {user_id})\n\n🚨 **Motivo:** Usuario NO está en la lista diaria de autorizados\n\n📋 **Lista actual:** {len(self.lista_diaria_ids) + len(self.lista_diaria_nombres)} usuarios autorizados para hoy\n\n📝 **Acción:** Si este usuario debe tener acceso, agrégalo a la lista diaria con /listahoy"
        
        return mensaje
    
    def configurar_bot_telegram(self, telegram_bot):
        """Configura la referencia al bot de Telegram para notificaciones"""
        self.telegram_bot = telegram_bot

    def agregar_a_lista_blanca(self, user_id=None, username=None):
        if user_id:
            self.lista_blanca.add(str(user_id))
        if username:
            self.lista_blanca_nombres.add(username.lower())
        self.guardar_lista_blanca()

    def quitar_de_lista_blanca(self, user_id=None, username=None):
        if user_id and str(user_id) in self.lista_blanca:
            self.lista_blanca.remove(str(user_id))
        if username and username.lower() in self.lista_blanca_nombres:
            self.lista_blanca_nombres.remove(username.lower())
        self.guardar_lista_blanca()

    def notificar_admin_usuario_no_autorizado(self, user_id, username):
        # Aquí deberías implementar el envío de mensaje al admin (por Telegram o log)
        print(f"[NOTIFICACIÓN ADMIN] Usuario NO autorizado accedió: {username} (ID: {user_id})")

    def registrar_señal_enviada(self, señal):
        """Registra una señal enviada en el historial persistente"""
        os.makedirs('data', exist_ok=True)
        try:
            with open('data/historial_senales.json', 'r') as f:
                historial = json.load(f)
        except FileNotFoundError:
            historial = []
        historial.append(señal)
        with open('data/historial_senales.json', 'w') as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)
    
    def actualizar_resultado_señal(self, señal):
        """Actualiza el resultado de una señal en el historial persistente"""
        os.makedirs('data', exist_ok=True)
        try:
            # Leer historial actual
            with open('data/historial_senales.json', 'r') as f:
                historial = json.load(f)
            
            # Buscar la señal por timestamp o número
            señal_timestamp = señal.get('timestamp')
            señal_numero = señal.get('numero')
            
            actualizado = False
            for i, s in enumerate(historial):
                # Buscar por timestamp (más confiable) o por número y hora
                if (s.get('timestamp') == señal_timestamp) or \
                   (s.get('numero') == señal_numero and s.get('hora') == señal.get('hora')):
                    # Actualizar resultado
                    historial[i]['resultado'] = señal.get('resultado')
                    historial[i]['hora_resultado'] = señal.get('hora_resultado')
                    historial[i]['precio_salida'] = señal.get('precio_salida')
                    historial[i]['diferencia_pips'] = señal.get('diferencia_pips')
                    historial[i]['diferencia_porcentaje'] = señal.get('diferencia_porcentaje')
                    actualizado = True
                    print(f"[UserManager] ✅ Resultado actualizado para señal #{señal_numero}: {señal.get('resultado')}")
                    break
            
            if not actualizado:
                print(f"[UserManager] ⚠️ No se encontró la señal #{señal_numero} en el historial para actualizar")
            
            # Guardar historial actualizado
            with open('data/historial_senales.json', 'w') as f:
                json.dump(historial, f, indent=2, ensure_ascii=False)
                
        except FileNotFoundError:
            print(f"[UserManager] ⚠️ No existe historial de señales para actualizar")
        except Exception as e:
            print(f"[UserManager] ❌ Error actualizando resultado de señal: {e}")

    def registrar_bloqueo(self, user_id, username, accion):
        """Registra un bloqueo/desbloqueo en el historial"""
        os.makedirs('data', exist_ok=True)
        evento = {
            'user_id': user_id,
            'username': username,
            'accion': accion,
            'fecha': datetime.now().isoformat()
        }
        try:
            with open('data/historial_bloqueos.json', 'r') as f:
                historial = json.load(f)
        except FileNotFoundError:
            historial = []
        historial.append(evento)
        with open('data/historial_bloqueos.json', 'w') as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)

    def obtener_usuarios_bloqueados(self):
        """Devuelve la lista de IDs bloqueados (como strings)."""
        try:
            return sorted(list(self.usuarios_bloqueados))
        except Exception:
            return []

    def bloquear_usuario(self, entrada: str, username: Optional[str] = None) -> str:
        """Bloquea por ID numérico. Persiste y registra historial."""
        val = (entrada or '').strip().replace('@', '')
        if not val.isdigit():
            return "⚠️ Debes indicar un ID numérico de Telegram para bloquear."
        uid = str(val)
        if uid in self.usuarios_bloqueados:
            return f"ℹ️ El usuario ID {uid} ya estaba bloqueado."
        self.usuarios_bloqueados.add(uid)
        # quitar de usuarios activos para evitar envíos
        if uid in self.usuarios_activos:
            self.usuarios_activos.pop(uid, None)
        # persistir
        self.guardar_datos_usuarios()
        # historial
        self.registrar_bloqueo(uid, username, 'bloquear')
        return f"🚫 Usuario ID {uid} bloqueado."

    def desbloquear_usuario(self, entrada: str, username: Optional[str] = None) -> str:
        """Desbloquea por ID numérico. Persiste y registra historial."""
        val = (entrada or '').strip().replace('@', '')
        if not val.isdigit():
            return "⚠️ Debes indicar un ID numérico de Telegram para desbloquear."
        uid = str(val)
        if uid not in self.usuarios_bloqueados:
            return f"ℹ️ El usuario ID {uid} no estaba bloqueado."
        self.usuarios_bloqueados.discard(uid)
        self.guardar_datos_usuarios()
        self.registrar_bloqueo(uid, username, 'desbloquear')
        return f"✅ Usuario ID {uid} desbloqueado."

    def consultar_historial_senales(self, fecha=None):
        """Devuelve señales enviadas, opcionalmente filtradas por fecha (YYYY-MM-DD)"""
        try:
            with open('data/historial_senales.json', 'r') as f:
                historial = json.load(f)
        except FileNotFoundError:
            return []
        if fecha:
            return [s for s in historial if s['timestamp'].startswith(fecha)]
        return historial

    def consultar_historial_bloqueos(self, fecha=None):
        """Devuelve historial de bloqueos/desbloqueos, opcionalmente filtrado por fecha (YYYY-MM-DD)"""
        try:
            with open('data/historial_bloqueos.json', 'r') as f:
                historial = json.load(f)
        except FileNotFoundError:
            return []
        if fecha:
            return [e for e in historial if e['fecha'].startswith(fecha)]
        return historial

    # ===================== CONFIRMACIONES PRE-SEÑAL / SEÑAL =====================
    def registrar_confirmacion_presenal(self, user_id: str, username: str, presenal_id: str, estado: str = 'aceptada', senal_id: str = None):
        """Registra una confirmación de Pre-Señal por parte de un usuario.
        estado: 'aceptada' | 'rechazada' | 'caducada'
        """
        os.makedirs('data', exist_ok=True)
        evento = {
            'user_id': str(user_id),
            'username': username,
            'presenal_id': str(presenal_id),
            'senal_id_relacionada': str(senal_id) if senal_id is not None else None,
            'estado': estado,
            'fecha_hora': datetime.now().isoformat()
        }
        try:
            with open('data/confirmaciones_presenal.json', 'r') as f:
                historial = json.load(f)
        except FileNotFoundError:
            historial = []
        historial.append(evento)
        with open('data/confirmaciones_presenal.json', 'w') as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)
        # In-memory mark when accepted
        if estado == 'aceptada':
            try:
                usuarios = self.confirmaciones_dia.setdefault('presenal', {}).setdefault(str(presenal_id), set())
                usuarios.add(str(user_id))
            except Exception:
                pass

    def registrar_confirmacion_senal(self, user_id: str, username: str, presenal_id: str, senal_id: str, estado: str = 'aceptada'):
        """Registra una confirmación de Señal por parte de un usuario (requiere haber confirmado Pre-Señal).
        estado: 'aceptada' | 'rechazada' | 'caducada'
        """
        os.makedirs('data', exist_ok=True)
        evento = {
            'user_id': str(user_id),
            'username': username,
            'presenal_id': str(presenal_id),
            'senal_id': str(senal_id),
            'estado': estado,
            'fecha_hora': datetime.now().isoformat()
        }
        try:
            with open('data/confirmaciones_senal.json', 'r') as f:
                historial = json.load(f)
        except FileNotFoundError:
            historial = []
        historial.append(evento)
        with open('data/confirmaciones_senal.json', 'w') as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)
        # In-memory mark when accepted
        if estado == 'aceptada':
            try:
                usuarios = self.confirmaciones_dia.setdefault('senal', {}).setdefault(str(senal_id), set())
                usuarios.add(str(user_id))
            except Exception:
                pass

    # ===================== REPORTES DE CONFIRMACIONES =====================
    def _leer_json_seguro(self, ruta: str):
        try:
            with open(ruta, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception:
            return []

    def generar_reporte_confirmaciones_aceptadas(self, fecha: str) -> str:
        """Genera un reporte resumido de confirmaciones (pre‑señal y señal) del día indicado (YYYY-MM-DD)."""
        pres = [e for e in self._leer_json_seguro('data/confirmaciones_presenal.json') if e.get('fecha_hora', '').startswith(fecha)]
        sen = [e for e in self._leer_json_seguro('data/confirmaciones_senal.json') if e.get('fecha_hora', '').startswith(fecha)]
        total_pre = len(pres)
        total_pre_ok = sum(1 for e in pres if e.get('estado') == 'aceptada')
        total_pre_no = sum(1 for e in pres if e.get('estado') == 'rechazada')
        total_pre_cad = sum(1 for e in pres if e.get('estado') == 'caducada')
        total_sig = len(sen)
        total_sig_ok = sum(1 for e in sen if e.get('estado') == 'aceptada')
        total_sig_no = sum(1 for e in sen if e.get('estado') == 'rechazada')
        total_sig_cad = sum(1 for e in sen if e.get('estado') == 'caducada')
        # Top usuarios por aceptaciones de señal
        conteo_por_user = {}
        for e in sen:
            if e.get('estado') == 'aceptada':
                uid = str(e.get('user_id'))
                conteo_por_user[uid] = conteo_por_user.get(uid, 0) + 1
        top = sorted(conteo_por_user.items(), key=lambda x: x[1], reverse=True)[:5]
        top_txt = '\n'.join([f"• ID {uid}: {cnt} confirmaciones de señal" for uid, cnt in top]) or "• (sin datos)"
        msg = (
            f"📜 CONFIRMACIONES [{fecha}]\n\n"
            f"🔔 Pre‑señal: {total_pre} (✅ {total_pre_ok} | ❌ {total_pre_no} | ⏳ {total_pre_cad})\n"
            f"📩 Señal: {total_sig} (✅ {total_sig_ok} | ❌ {total_sig_no} | ⏳ {total_sig_cad})\n\n"
            f"🏅 Top usuarios (señal aceptada):\n{top_txt}"
        )
        return msg

    def generar_reporte_confirmaciones_por_usuario(self, fecha: str, query_usuario: str) -> str:
        """Reporte filtrado por @usuario o ID para el día dado."""
        q = (query_usuario or '').strip().replace('@', '').lower()
        pres = [e for e in self._leer_json_seguro('data/confirmaciones_presenal.json') if e.get('fecha_hora', '').startswith(fecha)]
        sen = [e for e in self._leer_json_seguro('data/confirmaciones_senal.json') if e.get('fecha_hora', '').startswith(fecha)]
        def coincide(e):
            uid = str(e.get('user_id', ''))
            uname = (e.get('username') or '').lower()
            return uid == q or uname == q
        pres_f = [e for e in pres if coincide(e)]
        sen_f = [e for e in sen if coincide(e)]
        if not pres_f and not sen_f:
            return f"ℹ️ Sin confirmaciones para '{query_usuario}' en {fecha}."
        def listar(lista):
            if not lista:
                return "(ninguna)"
            out = []
            for e in lista:
                out.append(
                    f"• {e.get('fecha_hora','')}: estado={e.get('estado')} pre={e.get('presenal_id')} senal={e.get('senal_id') or e.get('senal_id_relacionada') or '-'}"
                )
            return '\n'.join(out)
        msg = (
            f"📜 CONFIRMACIONES de {query_usuario} [{fecha}]\n\n"
            f"🔔 Pre‑señal:\n{listar(pres_f)}\n\n"
            f"📩 Señal:\n{listar(sen_f)}"
        )
        return msg

    def usuario_confirmo_presenal(self, user_id: str, presenal_id: str) -> bool:
        """Retorna True si el usuario confirmó la Pre-Señal indicada (en cualquier momento del día)."""
        try:
            with open('data/confirmaciones_presenal.json', 'r') as f:
                historial = json.load(f)
        except FileNotFoundError:
            return False
        for e in historial:
            if str(e.get('user_id')) == str(user_id) and str(e.get('presenal_id')) == str(presenal_id):
                return True
        return False

    def obtener_estadisticas_confirmaciones(self, fecha: str):
        """Devuelve resumen para una fecha YYYY-MM-DD: conteos y listados de Pre-Señal y Señal."""
        # Pre-Señal
        try:
            with open('data/confirmaciones_presenal.json', 'r') as f:
                pres = json.load(f)
        except FileNotFoundError:
            pres = []
        pres_hoy = [e for e in pres if str(e.get('fecha_hora','')).startswith(fecha)]

        # Señal
        try:
            with open('data/confirmaciones_senal.json', 'r') as f:
                sen = json.load(f)
        except FileNotFoundError:
            sen = []
        sen_hoy = [e for e in sen if str(e.get('fecha_hora','')).startswith(fecha)]

        return {
            'fecha': fecha,
            'presenal_total': len(pres_hoy),
            'senal_total': len(sen_hoy),
            'presenal_listado': pres_hoy,
            'senal_listado': sen_hoy
        }

    def generar_reporte_confirmaciones_detallado(self, fecha: str) -> str:
        """Genera un reporte detallado por usuario de Pre‑Señal y Señal para la fecha YYYY-MM-DD.
        Incluye: quien aceptó o dejó caducar, hora y relación pre/senal.
        """
        # Cargar confirmaciones del día
        try:
            with open('data/confirmaciones_presenal.json', 'r') as f:
                pres = json.load(f)
        except FileNotFoundError:
            pres = []
        pres_hoy = [e for e in pres if str(e.get('fecha_hora','')).startswith(fecha)]

        try:
            with open('data/confirmaciones_senal.json', 'r') as f:
                sen = json.load(f)
        except FileNotFoundError:
            sen = []
        sen_hoy = [e for e in sen if str(e.get('fecha_hora','')).startswith(fecha)]

        # Cargar señales para mostrar breve info
        try:
            with open('data/historial_senales.json', 'r') as f:
                hist = json.load(f)
        except FileNotFoundError:
            hist = []
        senales_por_id = {}
        for s in hist:
            sid = str(s.get('id') or s.get('signal_id') or s.get('timestamp'))
            senales_por_id[str(sid)] = s

        # Construir reporte
        lineas = []
        lineas.append(f"📆 Reporte de confirmaciones {fecha}")
        lineas.append("")
        # Pre‑Señal
        lineas.append("— Pre‑Señal ACEPTADA —")
        if not pres_hoy:
            lineas.append("(sin eventos)")
        else:
            # Agrupar por pre_id y listar usuarios
            grupos_pre = {}
            for e in pres_hoy:
                pid = str(e.get('presenal_id'))
                grupos_pre.setdefault(pid, []).append(e)
            for pid, eventos in grupos_pre.items():
                lineas.append(f"PreID {pid}:")
                aceptadas = [ev for ev in eventos if ev.get('estado') == 'aceptada']
                caducadas = [ev for ev in eventos if ev.get('estado') == 'caducada']
                if aceptadas:
                    lineas.append("  ✅ Aceptaron:")
                    for ev in aceptadas:
                        lineas.append(f"    • @{ev.get('username') or 'sin_username'} (ID {ev.get('user_id')}) a las {ev.get('fecha_hora')[11:16]}")
                if caducadas:
                    lineas.append("  ⏳ Caducó a:")
                    for ev in caducadas:
                        lineas.append(f"    • @{ev.get('username') or 'sin_username'} (ID {ev.get('user_id')}) a las {ev.get('fecha_hora')[11:16]}")

        lineas.append("")
        # Señal
        lineas.append("— Señal ACEPTADA —")
        if not sen_hoy:
            lineas.append("(sin eventos)")
        else:
            grupos_sen = {}
            for e in sen_hoy:
                sid = str(e.get('senal_id'))
                grupos_sen.setdefault(sid, []).append(e)
            for sid, eventos in grupos_sen.items():
                info = senales_por_id.get(str(sid), {})
                resumen = ''
                if info:
                    resumen = f" {info.get('symbol','')} {info.get('direccion','')} {info.get('hora','')} (efect. {info.get('efectividad','?')}%)"
                lineas.append(f"SignalID {sid}:{resumen}")
                aceptadas = [ev for ev in eventos if ev.get('estado') == 'aceptada']
                caducadas = [ev for ev in eventos if ev.get('estado') == 'caducada']
                if aceptadas:
                    lineas.append("  ✅ Aceptaron:")
                    for ev in aceptadas:
                        lineas.append(f"    • @{ev.get('username') or 'sin_username'} (ID {ev.get('user_id')}) a las {ev.get('fecha_hora')[11:16]}")
                if caducadas:
                    lineas.append("  ⏳ Caducó a:")
                    for ev in caducadas:
                        lineas.append(f"    • @{ev.get('username') or 'sin_username'} (ID {ev.get('user_id')}) a las {ev.get('fecha_hora')[11:16]}")

        texto = "\n".join(lineas)
        # Limitar tamaño básico (Telegram 4096). Si excede, truncar con aviso.
        if len(texto) > 3900:
            texto = texto[:3800] + "\n… (reporte truncado, refine por fecha o filtrar)"
        return texto

    def generar_reporte_confirmaciones_aceptadas(self, fecha: str) -> str:
        """Genera un reporte SOLO de confirmaciones aceptadas del día indicado (YYYY-MM-DD),
        agrupadas por usuario con resumen de señales cuando aplique."""
        try:
            with open('data/confirmaciones_presenal.json', 'r') as f:
                pres = json.load(f)
        except FileNotFoundError:
            pres = []
        pres_hoy = [e for e in pres if str(e.get('fecha_hora','')).startswith(fecha) and e.get('estado') == 'aceptada']

        try:
            with open('data/confirmaciones_senal.json', 'r') as f:
                sen = json.load(f)
        except FileNotFoundError:
            sen = []
        sen_hoy = [e for e in sen if str(e.get('fecha_hora','')).startswith(fecha) and e.get('estado') == 'aceptada']

        # Cargar señales para enriquecer
        try:
            with open('data/historial_senales.json', 'r') as f:
                hist = json.load(f)
        except FileNotFoundError:
            hist = []
        senales_por_id = {}
        for s in hist:
            sid = str(s.get('id') or s.get('signal_id') or s.get('timestamp'))
            senales_por_id[str(sid)] = s

        por_usuario = {}
        for ev in pres_hoy:
            uid = str(ev.get('user_id'))
            por_usuario.setdefault(uid, {'username': ev.get('username'), 'pre': [], 'sen': []})
            por_usuario[uid]['pre'].append(ev)
        for ev in sen_hoy:
            uid = str(ev.get('user_id'))
            por_usuario.setdefault(uid, {'username': ev.get('username'), 'pre': [], 'sen': []})
            por_usuario[uid]['sen'].append(ev)

        if not por_usuario:
            return f"📆 Confirmaciones ACEPTADAS {fecha}\n\n(sin eventos)"

        lineas = [f"📆 Confirmaciones ACEPTADAS {fecha}", ""]
        for uid, info in por_usuario.items():
            uname = info.get('username') or ''
            header = f"👤 {uname} (ID {uid})" if uname else f"👤 ID {uid}"
            lineas.append(header)
            # Pre‑Señal
            if info['pre']:
                lineas.append("  — Pre‑Señal —")
                for ev in sorted(info['pre'], key=lambda e: e.get('fecha_hora')):
                    hora = str(ev.get('fecha_hora',''))[11:16]
                    pid = ev.get('presenal_id')
                    rel = ev.get('senal_id_relacionada')
                    lineas.append(f"  • PreID {pid} aceptada a las {hora} (rel Señal {rel or '-'})")
            # Señal
            if info['sen']:
                lineas.append("  — Señal —")
                for ev in sorted(info['sen'], key=lambda e: e.get('fecha_hora')):
                    hora = str(ev.get('fecha_hora',''))[11:16]
                    sid = str(ev.get('senal_id'))
                    s = senales_por_id.get(sid, {})
                    resumen = f" {s.get('symbol','')} {s.get('direccion','')} {s.get('hora','')} (efect. {s.get('efectividad','?')}%)" if s else ''
                    lineas.append(f"  • SignalID {sid}:{resumen} aceptada a las {hora}")
            lineas.append("")
        texto = "\n".join(lineas).rstrip()
        if len(texto) > 3900:
            texto = texto[:3800] + "\n… (reporte truncado, refine por usuario)"
        return texto

    def generar_reporte_confirmaciones_por_usuario(self, fecha: str, query: str) -> str:
        """Genera un reporte filtrado por usuario (username @ o ID) para la fecha dada.
        query: '@usuario' o 'usuario' o '123456789' (ID).
        """
        q = (query or '').strip()
        if not q:
            return "⚠️ Debes indicar un @usuario o un ID."
        buscar_por_id = q.isdigit()
        buscar_username = q.replace('@', '').lower()

        # Cargar confirmaciones
        try:
            with open('data/confirmaciones_presenal.json', 'r') as f:
                pres = json.load(f)
        except FileNotFoundError:
            pres = []
        pres_hoy = [e for e in pres if str(e.get('fecha_hora','')).startswith(fecha)]

        try:
            with open('data/confirmaciones_senal.json', 'r') as f:
                sen = json.load(f)
        except FileNotFoundError:
            sen = []
        sen_hoy = [e for e in sen if str(e.get('fecha_hora','')).startswith(fecha)]

        # Filtrar por usuario
        def match_user(e):
            if buscar_por_id:
                return str(e.get('user_id')) == q
            else:
                return (e.get('username') or '').lower() == buscar_username

        pres_user = [e for e in pres_hoy if match_user(e) and e.get('estado') == 'aceptada']
        sen_user = [e for e in sen_hoy if match_user(e) and e.get('estado') == 'aceptada']

        # Cargar señales para resumen
        try:
            with open('data/historial_senales.json', 'r') as f:
                hist = json.load(f)
        except FileNotFoundError:
            hist = []
        senales_por_id = {}
        for s in hist:
            sid = str(s.get('id') or s.get('signal_id') or s.get('timestamp'))
            senales_por_id[str(sid)] = s

        header_user = q if buscar_por_id else f"@{buscar_username}"
        lineas = [f"📆 Confirmaciones {fecha} - Usuario {header_user}", ""]
        # Pre‑Señal
        lineas.append("— Pre‑Señal —")
        if not pres_user:
            lineas.append("(sin eventos)")
        else:
            for ev in pres_user:
                hora = str(ev.get('fecha_hora',''))[11:16]
                pid = ev.get('presenal_id')
                rel = ev.get('senal_id_relacionada')
                lineas.append(f"• PreID {pid} aceptada a las {hora} (rel Señal {rel or '-'})")
        lineas.append("")
        # Señal
        lineas.append("— Señal —")
        if not sen_user:
            lineas.append("(sin eventos)")
        else:
            for ev in sen_user:
                hora = str(ev.get('fecha_hora',''))[11:16]
                sid = str(ev.get('senal_id'))
                info = senales_por_id.get(sid, {})
                resumen = ''
                if info:
                    resumen = f" {info.get('symbol','')} {info.get('direccion','')} {info.get('hora','')} (efect. {info.get('efectividad','?')}%)"
                lineas.append(f"• SignalID {sid}:{resumen} aceptada a las {hora}")

        texto = "\n".join(lineas)
        if len(texto) > 3900:
            texto = texto[:3800] + "\n… (reporte truncado, afine por fecha)"
        return texto
    
    def es_administrador(self, user_id: str) -> bool:
        """Verifica si un usuario es el administrador"""
        return str(user_id) == self.admin_id
    
    def obtener_administradores(self) -> list:
        """Retorna lista con el ID del administrador"""
        return [self.admin_id]
    
    def verificar_admin_por_clave(self, clave: str) -> bool:
        """Verifica si una clave es la clave maestra del administrador"""
        return clave == self.clave_maestra

    def guardar_datos_usuarios(self):
        """Guarda datos de usuarios en archivo"""
        os.makedirs('data', exist_ok=True)
        data = {
            'usuarios_activos': self.usuarios_activos,
            'usuarios_bloqueados': list(self.usuarios_bloqueados),
            'historial_bloqueos': self.historial_bloqueos,
            'clave_publica_diaria': self.clave_publica_diaria,
            'fecha_clave_actual': self.fecha_clave_actual,
            'señales_del_dia': self.señales_del_dia,
            'estadisticas_diarias': self.estadisticas_diarias,
            'ultima_actualizacion': datetime.now().isoformat()
        }
        
        with open('data/usuarios.json', 'w') as f:
            json.dump(data, f, indent=4)
    
    def generar_clave_diaria_si_necesario(self, forzar: bool = False):
        """
        Genera nueva clave pública diaria si es necesario.
        Si `forzar=True`, regenera la clave aunque ya exista para hoy.
        """
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        
        if forzar or self.fecha_clave_actual != fecha_hoy:
            # Generar nueva clave para el día
            self.clave_publica_diaria = self.generar_clave_publica()
            self.fecha_clave_actual = fecha_hoy
            # Reset de contexto diario
            self.usuarios_activos = {}
            self.señales_del_dia = []
            self.confirmaciones_dia = {'presenal': {}, 'senal': {}}
            
            print(f"[UserManager] 🔑 Nueva clave diaria generada: {self.clave_publica_diaria}")
            print(f"[UserManager] 📅 Fecha: {fecha_hoy}")
            
            # Resetear estadísticas diarias
            self.estadisticas_diarias = {
                'fecha': fecha_hoy,
                'total_usuarios': 0,
                'usuarios_tardios': 0,
                'señales_enviadas': 0,
                'efectividad_promedio': 0,
                'hora_inicio': None,
                'hora_fin': None
            }
            
            self.guardar_datos_usuarios()
            return self.clave_publica_diaria
        # Si no se generó nueva, retorna la actual
        return self.clave_publica_diaria
    
    def generar_clave_publica(self) -> str:
        """Genera una clave pública diaria única"""
        fecha = datetime.now().strftime('%Y%m%d')
        aleatorio = secrets.token_hex(4).upper()
        return f"CUBA{fecha}{aleatorio}"

    def generar_clave_publica_manual(self) -> str:
        """Genera y establece una nueva clave pública del día (automática) y persiste."""
        clave = self.generar_clave_publica()
        self.clave_publica_diaria = clave
        self.fecha_clave_actual = datetime.now().strftime('%Y-%m-%d')
        self.guardar_datos_usuarios()
        return clave

    def generar_clave_diaria(self) -> str:
        """
        Alias conveniente para generar una nueva clave automática del día
        y persistirla. Utilizado por callbacks del bot.
        """
        clave = self.generar_clave_publica_manual()
        # Al cambiar la clave, revocar accesos de usuarios no admin y notificarles
        try:
            self.revocar_acceso_usuarios_por_cambio_clave()
        except Exception as _:
            pass
        return clave

    def generar_clave_publica_personalizada(self, clave_personalizada: str) -> str:
        """Establece una clave pública personalizada para el día actual y persiste.
        La clave se guarda en MAYÚSCULAS.
        """
        clave = (clave_personalizada or "").strip().upper()
        if len(clave) < 6:
            raise ValueError("La clave personalizada debe tener al menos 6 caracteres")
        self.clave_publica_diaria = clave
        self.fecha_clave_actual = datetime.now().strftime('%Y-%m-%d')
        self.guardar_datos_usuarios()
        # Al cambiar la clave, revocar accesos de usuarios no admin y notificarles
        try:
            self.revocar_acceso_usuarios_por_cambio_clave()
        except Exception as _:
            pass
        return clave
    
    def validar_clave_maestra(self, clave: str) -> bool:
        """Valida si la clave ingresada es la clave maestra"""
        return clave.strip().upper() == self.clave_maestra
    
    def validar_clave_publica(self, clave: str) -> bool:
        """Valida si la clave ingresada es la clave pública del día"""
        return clave.strip().upper() == self.clave_publica_diaria
    
    def es_administrador(self, user_id: str) -> bool:
        """Verifica si un usuario es administrador por ID o por estar autenticado como admin"""
        # Verificar por ID directo
        if user_id == self.admin_id:
            return True
        
        # Verificar si está autenticado como admin
        if user_id in self.usuarios_activos:
            return self.usuarios_activos[user_id]['tipo'] == 'admin'
        
        return False
    
    def autenticar_usuario(self, user_id: str, username: str, clave: str) -> Dict:
        """
        Autentica un usuario y devuelve su estado
        """
        # Verificar si el usuario está bloqueado
        if user_id in self.usuarios_bloqueados:
            return {
                'autenticado': False,
                'tipo': None,
                'mensaje': self.generar_mensaje_usuario_bloqueado(username),
                'señales_perdidas': 0,
                'es_tardio': False,
                'bloqueado': True
            }
        
        clave = clave.strip().upper()
        ahora = datetime.now()
        hora_actual = ahora.strftime('%H:%M')
        es_horario_señales = self.esta_en_horario_señales()
        
        # Verificar si es administrador por ID o clave maestra
        if user_id == self.admin_id or self.validar_clave_maestra(clave):
            self.usuarios_activos[user_id] = {
                'username': username,
                'tipo': 'admin',
                'hora_ingreso': hora_actual,
                'clave_usada': 'ADMIN_ID' if user_id == self.admin_id else 'MASTER',
                'señales_recibidas': len(self.señales_del_dia),
                'es_tardio': False
            }
            
            self.guardar_datos_usuarios()
            
            return {
                'autenticado': True,
                'tipo': 'admin',
                'mensaje': self.generar_mensaje_bienvenida_admin(username, hora_actual),
                'clave_publica': self.clave_publica_diaria,
                'señales_perdidas': 0,
                'es_tardio': False
            }
        
        # Verificar clave pública diaria
        elif self.validar_clave_publica(clave):
            # VERIFICAR LISTA DIARIA AUTORIZADA (SOLO PARA NOTIFICACIÓN)
            esta_autorizado, motivo_autorizacion = self.esta_en_lista_diaria_autorizada(user_id, username)
            
            # Si no está autorizado, REGISTRAR y PERMITIR ACCESO pero notificar al admin
            if not esta_autorizado:
                # Registrar acceso no autorizado en historial
                self.registrar_acceso_no_autorizado(user_id, username, motivo_autorizacion, clave)
                # Se preserva 'motivo_autorizacion' detallado para que el bot formatee la notificación.
                # No se envía notificación aquí para evitar duplicados.
                pass
            
            # PROCEDER NORMALMENTE - SIEMPRE PERMITIR ACCESO CON CLAVE CORRECTA
            es_tardio = not es_horario_señales or len(self.señales_del_dia) > 0
            señales_perdidas = len(self.señales_del_dia)
            
            self.usuarios_activos[user_id] = {
                'username': username,
                'tipo': 'usuario',
                'hora_ingreso': hora_actual,
                'clave_usada': self.clave_publica_diaria,
                'señales_recibidas': 0,
                'es_tardio': es_tardio,
                'autorizado_por': motivo_autorizacion,
                'motivo_autorizacion': motivo_autorizacion,
                'en_lista_diaria': esta_autorizado
            }
            
            if es_tardio:
                self.estadisticas_diarias['usuarios_tardios'] += 1
            
            self.estadisticas_diarias['total_usuarios'] += 1
            self.guardar_datos_usuarios()
            
            return {
                'autenticado': True,
                'tipo': 'usuario',
                'mensaje': self.generar_mensaje_bienvenida_usuario(username, hora_actual, es_tardio, señales_perdidas),
                'señales_perdidas': señales_perdidas,
                'es_tardio': es_tardio,
                'resumen_señales_perdidas': self.generar_resumen_señales_perdidas() if es_tardio else None,
                'en_lista_diaria': esta_autorizado,
                'autorizado_por': motivo_autorizacion,
                'motivo_autorizacion': motivo_autorizacion
            }
        
        # Clave incorrecta
        else:
            # Registrar intento con clave incorrecta
            self.registrar_acceso_no_autorizado(user_id, username, 'clave_incorrecta', clave)
            return {
                'autenticado': False,
                'tipo': None,
                'mensaje': self.generar_mensaje_acceso_denegado(username, hora_actual),
                'señales_perdidas': 0,
                'es_tardio': False
            }
    
    def esta_en_horario_señales(self) -> bool:
        """Verifica si estamos en horario de señales (8:00 AM - 8:00 PM, Lun-Sáb)"""
        ahora = datetime.now()
        
        # Verificar si es día de semana (0=Lunes, 6=Domingo)
        if ahora.weekday() >= 6:  # Solo domingo (sábado ahora es operativo)
            return False
        
        # Verificar horario (8:00 - 20:00)
        hora_actual = ahora.hour
        return 8 <= hora_actual < 20

    def revocar_acceso_usuarios_por_cambio_clave(self):
        """Revoca el acceso de todos los usuarios no administradores cuando se cambia la clave del día.
        Envía una notificación por Telegram informando que la clave fue actualizada y que contacten al admin.
        """
        try:
            if not hasattr(self, 'usuarios_activos') or not self.usuarios_activos:
                return
            afectados = []
            for uid, info in list(self.usuarios_activos.items()):
                try:
                    if str(uid) == str(self.admin_id):
                        continue
                    if info.get('tipo') == 'admin':
                        continue
                    afectados.append((str(uid), info.get('username') or ''))
                except Exception:
                    continue
            # Limpiar usuarios no admin del registro de activos
            for uid, _ in afectados:
                try:
                    self.usuarios_activos.pop(uid, None)
                except Exception:
                    pass
            # Persistir cambios
            try:
                self.guardar_datos_usuarios()
            except Exception:
                pass
            # Notificar por Telegram si el bot está configurado
            if afectados and getattr(self, 'telegram_bot', None):
                mensaje = (
                    "🔒 Acceso revocado\n\n"
                    "Tu acceso fue cerrado porque el administrador actualizó la clave del día.\n"
                    "Por favor, contacta al administrador para obtener la nueva clave."
                )
                for uid, _username in afectados:
                    try:
                        # Enviar sin parse_mode
                        coro = self.telegram_bot.send_message(uid, mensaje)
                        # Si estamos dentro de PTB loop, esto es un coro; intentamos agendarlo
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            if loop and loop.is_running():
                                asyncio.create_task(coro)
                            else:
                                asyncio.run(coro)
                        except RuntimeError:
                            # Si no hay loop, ejecutarlo directamente
                            asyncio.run(coro)
                    except Exception:
                        pass
            # Notificar al admin un resumen
            try:
                if getattr(self, 'telegram_bot', None):
                    total = len(afectados)
                    if total:
                        admin_msg = f"🔑 Clave del día actualizada. {total} usuarios perdieron el acceso y fueron notificados."
                        asyncio_coro = self.telegram_bot.notificar_admin_telegram(admin_msg)
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            if loop and loop.is_running():
                                asyncio.create_task(asyncio_coro)
                            else:
                                asyncio.run(asyncio_coro)
                        except RuntimeError:
                            asyncio.run(asyncio_coro)
            except Exception:
                pass
        except Exception:
            # Evitar que un fallo en notificaciones impida el cambio de clave
            pass
    
    def generar_mensaje_bienvenida_admin(self, username: str, hora: str) -> str:
        """Genera mensaje de bienvenida para administrador"""
        frases_admin = [
            "¡Bienvenido, Maestro del Trading! 🎯",
            "¡El Comandante ha llegado! 💪",
            "¡Acceso total concedido, Jefe! 🚀",
            "¡Bienvenido al centro de control! 👑"
        ]
        
        frase = random.choice(frases_admin)
        
        mensaje = f"""
{frase}

👤 **Usuario:** {username}
🔑 **Acceso:** ADMINISTRADOR
⏰ **Hora de ingreso:** {hora}
📊 **Estado del sistema:** ACTIVO

**PANEL DE CONTROL DISPONIBLE:**
• 🔑 Clave pública del día: `{self.clave_publica_diaria}`
• 👥 Usuarios activos: {len(self.usuarios_activos)}
• 📈 Señales enviadas hoy: {len(self.señales_del_dia)}
• 📊 Estadísticas completas disponibles

¡Que tengas un día de trading excepcional! 💰
        """
        return mensaje.strip()
    
    def generar_mensaje_bienvenida_usuario(self, username: str, hora: str, es_tardio: bool, señales_perdidas: int) -> str:
        """Genera mensaje de bienvenida para usuario regular"""
        if es_tardio:
            frases_tardio = [
                "¡Mejor tarde que nunca! 😊",
                "¡Aún hay tiempo para ganar! 💪",
                "¡Bienvenido al equipo! 🎯",
                "¡Llegaste justo a tiempo! ⏰"
            ]
            frase = random.choice(frases_tardio)
            
            mensaje = f"""
{frase}

👤 **Usuario:** {username}
⏰ **Hora de ingreso:** {hora}
📊 **Estado:** INGRESO TARDÍO

⚠️ **Has perdido {señales_perdidas} señal(es) del día**

Pero no te preocupes, ¡aún quedan muchas oportunidades! 
Recibirás todas las próximas señales automáticamente.

💡 **Consejo:** Mañana ingresa antes de las 8:00 AM para no perderte ninguna señal.

¡Vamos por esas ganancias! 🚀💰
            """
        else:
            frases_temprano = [
                "¡Perfecto timing! 🎯",
                "¡Excelente, llegaste temprano! ⭐",
                "¡Listo para conquistar el mercado! 💪",
                "¡Bienvenido al equipo ganador! 🏆"
            ]
            frase = random.choice(frases_temprano)
            
            mensaje = f"""
{frase}

👤 **Usuario:** {username}
⏰ **Hora de ingreso:** {hora}
📊 **Estado:** ACCESO COMPLETO

✅ **¡Perfecto! No te has perdido ninguna señal**

Recibirás automáticamente:
• 📈 Todas las señales del día (20-25 aprox)
• 📊 Análisis técnico detallado
• 💰 Notificaciones pre-señal
• 📋 Resumen diario de rendimiento

¡Prepárate para un día exitoso! 🚀💰
            """
        
        return mensaje.strip()
    
    def generar_mensaje_acceso_denegado(self, username: str, hora: str) -> str:
        """Genera mensaje de acceso denegado"""
        frases_denegado = [
            "¡Ups! Clave incorrecta 🔐",
            "Acceso denegado ❌",
            "Clave no válida 🚫",
            "Verificación fallida ⚠️"
        ]
        
        frase = random.choice(frases_denegado)
        
        mensaje = f"""
{frase}

👤 **Usuario:** {username}
⏰ **Hora:** {hora}

❌ **La clave ingresada no es válida**

💡 **¿Necesitas ayuda?**
• Verifica que hayas copiado la clave correctamente
• Asegúrate de no incluir espacios extra
• La clave cambia diariamente a las 00:00

🔑 **Para obtener la clave del día:**
• Contacta al administrador
• Únete al grupo oficial
• Sigue nuestras redes sociales

¡Esperamos verte pronto en el equipo! 💪
        """
        return mensaje.strip()
    
    def generar_resumen_señales_perdidas(self) -> str:
        """Genera resumen de las señales perdidas para usuarios tardíos"""
        if not self.señales_del_dia:
            return "No hay señales perdidas."
        
        # Mensaje informativo inicial
        hora_actual = datetime.now().strftime('%I:%M %p').replace('AM', 'AM').replace('PM', 'PM')
        total_señales = len(self.señales_del_dia)
        
        mensaje_inicial = f"""
📢 ¡Hola, trader!
Has ingresado tu clave del día a las {hora_actual} 🕑
Actualmente ya se han generado {total_señales} señales desde las 8:00 AM.

🔁 Te enviamos a continuación las señales anteriores para que revises el resumen de la jornada.

⚠️ Aún puedes recibir las señales restantes del día. Mantente atento.
📅 Horario de señales activas: 8:00 AM – 8:00 PM

🤖 – Bot CubaYDsignal
        """
        
        return mensaje_inicial.strip()
    
    def generar_señales_perdidas_detalladas(self) -> List[str]:
        """Genera lista de señales perdidas en formato detallado"""
        if not self.señales_del_dia:
            return []
        
        señales_formateadas = []
        
        for i, señal in enumerate(self.señales_del_dia, 1):
            # Formatear hora a AM/PM
            hora_raw = señal.get('hora', '00:00')
            try:
                # Convertir de 24h a 12h con AM/PM
                from datetime import datetime
                hora_obj = datetime.strptime(hora_raw, '%H:%M')
                hora_formateada = hora_obj.strftime('%I:%M %p')
            except:
                hora_formateada = hora_raw
            
            # Formatear dirección
            direccion = señal.get('direccion', 'N/A').upper()
            
            # Crear mensaje de señal individual
            señal_msg = f"📊 Señal #{i:02d} – {hora_formateada} – {señal.get('symbol', 'N/A')} – {direccion} – 5 min – Efectividad: {señal.get('efectividad', 0):.0f}%"
            
            señales_formateadas.append(señal_msg)
        
        return señales_formateadas
    
    def obtener_historial_usuarios(self, fecha=None):
        """Obtiene historial de usuarios autenticados por fecha"""
        from datetime import datetime, date
        
        if fecha is None:
            fecha = datetime.now().date()
        
        # Buscar en el historial diario
        fecha_str = fecha.strftime('%Y-%m-%d')
        historial_fecha = []
        
        # Revisar usuarios autenticados del día
        for user_id, info in self.usuarios_autenticados.items():
            fecha_autenticacion = info.get('fecha_autenticacion')
            if fecha_autenticacion and fecha_autenticacion.startswith(fecha_str):
                historial_fecha.append({
                    'user_id': user_id,
                    'username': info.get('username', 'N/A'),
                    'hora_autenticacion': info.get('hora_autenticacion', 'N/A'),
                    'es_tardio': info.get('es_tardio', False),
                    'fecha': fecha_autenticacion
                })
        
        # Ordenar por hora de autenticación
        historial_fecha.sort(key=lambda x: x.get('hora_autenticacion', '00:00'))
        
        return historial_fecha
    
    def generar_mensaje_usuario_bloqueado(self, username: str) -> str:
        """Genera mensaje para usuario bloqueado"""
        mensaje = f"""
❌ **ACCESO BLOQUEADO**

👤 **Usuario:** {username}
⏰ **Hora:** {datetime.now().strftime('%H:%M')}

🚫 **Tu acceso ha sido bloqueado por el administrador**

Si crees que esto es un error, contacta al administrador para resolver la situación.

📞 **Para soporte:**
• Contacta al administrador del bot
• Explica tu situación
• Solicita la reactivación de tu cuenta

¡Esperamos resolver esto pronto! 🤝
        """
        return mensaje.strip()
    
    def bloquear_usuario(self, user_id: str, admin_user_id: str) -> Dict:
        """Bloquea un usuario (solo admin)"""
        if not self.es_administrador(admin_user_id):
            return {'exito': False, 'mensaje': 'Solo administradores pueden bloquear usuarios'}
        
        if user_id == admin_user_id:
            return {'exito': False, 'mensaje': 'No puedes bloquearte a ti mismo'}
        
        self.usuarios_bloqueados.add(user_id)
        
        # Remover de usuarios activos si está conectado
        if user_id in self.usuarios_activos:
            username = self.usuarios_activos[user_id]['username']
            del self.usuarios_activos[user_id]
        else:
            username = f'Usuario_{user_id}'
        
        # Registrar en historial
        admin_username = self.usuarios_activos.get(admin_user_id, {}).get('username', f'Admin_{admin_user_id}')
        self.historial_bloqueos.append({
            'accion': 'BLOQUEO',
            'usuario_afectado': user_id,
            'username_afectado': username,
            'admin_responsable': admin_user_id,
            'admin_username': admin_username,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M'),
            'timestamp': datetime.now().isoformat()
        })
        
        self.guardar_datos_usuarios()
        
        return {
            'exito': True, 
            'mensaje': f'✅ Usuario {username} ({user_id}) ha sido bloqueado exitosamente',
            'username': username
        }
    
    def desbloquear_usuario(self, user_id: str, admin_user_id: str) -> Dict:
        """Desbloquea un usuario (solo admin)"""
        if not self.es_administrador(admin_user_id):
            return {'exito': False, 'mensaje': 'Solo administradores pueden desbloquear usuarios'}
        
        if user_id not in self.usuarios_bloqueados:
            return {'exito': False, 'mensaje': 'Este usuario no está bloqueado'}
        
        self.usuarios_bloqueados.discard(user_id)
        
        # Registrar en historial
        admin_username = self.usuarios_activos.get(admin_user_id, {}).get('username', f'Admin_{admin_user_id}')
        self.historial_bloqueos.append({
            'accion': 'DESBLOQUEO',
            'usuario_afectado': user_id,
            'username_afectado': f'Usuario_{user_id}',
            'admin_responsable': admin_user_id,
            'admin_username': admin_username,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M'),
            'timestamp': datetime.now().isoformat()
        })
        
        self.guardar_datos_usuarios()
        
        return {
            'exito': True, 
            'mensaje': f'✅ Usuario {user_id} ha sido desbloqueado exitosamente'
        }
    
    def obtener_usuarios_bloqueados(self) -> List[str]:
        """Obtiene lista de usuarios bloqueados"""
        return list(self.usuarios_bloqueados)
    
    def obtener_historial_bloqueos(self, limite: int = 50) -> List[Dict]:
        """Obtiene el historial de bloqueos/desbloqueos"""
        # Devolver los más recientes primero
        return sorted(self.historial_bloqueos, key=lambda x: x['timestamp'], reverse=True)[:limite]
    
    def generar_reporte_historial_bloqueos(self) -> str:
        """Genera un reporte del historial de bloqueos"""
        if not self.historial_bloqueos:
            return "📋 **HISTORIAL DE BLOQUEOS**\n\nNo hay registros de bloqueos/desbloqueos."
        
        historial = self.obtener_historial_bloqueos(20)  # Últimos 20
        
        reporte = "📋 **HISTORIAL DE BLOQUEOS/DESBLOQUEOS**\n\n"
        reporte += f"**Total de acciones:** {len(self.historial_bloqueos)}\n"
        reporte += f"**Usuarios actualmente bloqueados:** {len(self.usuarios_bloqueados)}\n\n"
        
        reporte += "**ÚLTIMAS ACCIONES:**\n"
        
        for i, accion in enumerate(historial, 1):
            emoji = "🚫" if accion['accion'] == 'BLOQUEO' else "✅"
            reporte += f"\n**{i}.** {emoji} **{accion['accion']}**\n"
            reporte += f"• **Usuario:** {accion['username_afectado']} (`{accion['usuario_afectado']}`)\n"
            reporte += f"• **Admin:** {accion['admin_username']} (`{accion['admin_responsable']}`)\n"
            reporte += f"• **Fecha:** {accion['fecha']} a las {accion['hora']}\n"
        
        return reporte
    
    def registrar_señal_enviada(self, señal_data: Dict):
        """Registra una señal enviada"""
        señal_data['timestamp'] = datetime.now().isoformat()
        señal_data['hora'] = datetime.now().strftime('%H:%M')
        self.señales_del_dia.append(señal_data)
        self.estadisticas_diarias['señales_enviadas'] = len(self.señales_del_dia)
        
        # Actualizar contador de señales recibidas para usuarios activos
        for user_id in self.usuarios_activos:
            self.usuarios_activos[user_id]['señales_recibidas'] += 1
        
        self.guardar_datos_usuarios()
        print(f"[UserManager] 📈 Señal #{len(self.señales_del_dia)} registrada")
    
    def obtener_usuarios_activos(self) -> List[str]:
        """Obtiene lista de IDs de usuarios activos"""
        return list(self.usuarios_activos.keys())
    
    def obtener_estadisticas_diarias(self) -> Dict:
        """Obtiene estadísticas del día actual"""
        efectividad_promedio = 0
        if self.señales_del_dia:
            efectividades = [s.get('efectividad', 0) for s in self.señales_del_dia]
            efectividad_promedio = sum(efectividades) / len(efectividades)
        
        self.estadisticas_diarias.update({
            'efectividad_promedio': efectividad_promedio,
            'total_usuarios': len(self.usuarios_activos),
            'señales_enviadas': len(self.señales_del_dia)
        })
        
        return self.estadisticas_diarias
    
    def generar_clave_publica_manual(self) -> str:
        """Permite al admin generar manualmente una nueva clave pública"""
        from datetime import datetime as _dt
        self.clave_publica_diaria = self.generar_clave_publica()
        # Fecha de validez: hoy
        self.fecha_clave_actual = _dt.now().strftime('%Y-%m-%d')
        self.guardar_datos_usuarios()
        return self.clave_publica_diaria
    
    def generar_clave_publica_personalizada(self, clave: str) -> str:
        """Permite al admin establecer manualmente una nueva clave pública personalizada"""
        from datetime import datetime as _dt
        self.clave_publica_diaria = str(clave).strip().upper()
        # Asegurar fecha de validez de la clave al día actual
        self.fecha_clave_actual = _dt.now().strftime('%Y-%m-%d')
        self.guardar_datos_usuarios()
        return self.clave_publica_diaria
    
    def obtener_info_sistema(self) -> Dict:
        """Obtiene información completa del sistema para el admin"""
        return {
            'clave_publica_actual': self.clave_publica_diaria,
            'fecha_clave': self.fecha_clave_actual,
            'usuarios_activos': len(self.usuarios_activos),
            'usuarios_bloqueados': len(self.usuarios_bloqueados),
            'señales_enviadas': len(self.señales_del_dia),
            'estadisticas': self.obtener_estadisticas_diarias(),
            'horario_activo': self.esta_en_horario_señales(),
            'usuarios_detalle': self.usuarios_activos,
            'lista_bloqueados': list(self.usuarios_bloqueados)
        }

    def actualizar_clave_publica(self, nueva_clave: str):
        """Actualiza la clave pública del día, persiste y aplica revocación con notificación."""
        self.clave_publica_diaria = nueva_clave
        self.fecha_clave_actual = datetime.now().strftime('%Y-%m-%d')
        self.guardar_datos_usuarios()
        # Unificar lógica de revocación y notificación
        try:
            self.revocar_acceso_usuarios_por_cambio_clave()
        except Exception:
            pass

    def notificar_usuario_clave_cambiada(self, user_id: str):
        """Notifica a un usuario que la clave del día ha cambiado."""
        mensaje = (
            "🔒 Acceso revocado\n\n"
            "La clave del día fue actualizada por el administrador.\n"
            "Contacta al administrador para obtener la nueva clave."
        )
        if getattr(self, 'telegram_bot', None):
            try:
                coro = self.telegram_bot.send_message(user_id, mensaje)
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        asyncio.create_task(coro)
                    else:
                        asyncio.run(coro)
                except RuntimeError:
                    asyncio.run(coro)
            except Exception:
                pass
    
    def bloquear_usuario(self, user_id: str, admin_user_id: str) -> Dict:
        """Bloquea un usuario (solo admin)"""
        if not self.es_administrador(admin_user_id):
            return {'exito': False, 'mensaje': 'Solo administradores pueden bloquear usuarios'}
        
        if user_id == admin_user_id:
            return {'exito': False, 'mensaje': 'No puedes bloquearte a ti mismo'}
        
        self.usuarios_bloqueados.add(user_id)
        
        # Remover de usuarios activos si está conectado
        if user_id in self.usuarios_activos:
            username = self.usuarios_activos[user_id]['username']
            del self.usuarios_activos[user_id]
        else:
            username = f'Usuario_{user_id}'
        
        # Registrar en historial
        admin_username = self.usuarios_activos.get(admin_user_id, {}).get('username', f'Admin_{admin_user_id}')
        self.historial_bloqueos.append({
            'accion': 'BLOQUEO',
            'usuario_afectado': user_id,
            'username_afectado': username,
            'admin_responsable': admin_user_id,
            'admin_username': admin_username,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M'),
            'timestamp': datetime.now().isoformat()
        })
        
        self.guardar_datos_usuarios()
        
        return {
            'exito': True, 
            'mensaje': f'✅ Usuario {username} ({user_id}) ha sido bloqueado exitosamente',
            'username': username
        }
    
    def desbloquear_usuario(self, user_id: str, admin_user_id: str) -> Dict:
        """Desbloquea un usuario (solo admin)"""
        if not self.es_administrador(admin_user_id):
            return {'exito': False, 'mensaje': 'Solo administradores pueden desbloquear usuarios'}
        
        if user_id not in self.usuarios_bloqueados:
            return {'exito': False, 'mensaje': 'Este usuario no está bloqueado'}
        
        self.usuarios_bloqueados.discard(user_id)
        
        # Registrar en historial
        admin_username = self.usuarios_activos.get(admin_user_id, {}).get('username', f'Admin_{admin_user_id}')
        self.historial_bloqueos.append({
            'accion': 'DESBLOQUEO',
            'usuario_afectado': user_id,
            'username_afectado': f'Usuario_{user_id}',
            'admin_responsable': admin_user_id,
            'admin_username': admin_username,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M'),
            'timestamp': datetime.now().isoformat()
        })
        
        self.guardar_datos_usuarios()
        
        return {
            'exito': True, 
            'mensaje': f'✅ Usuario {user_id} ha sido desbloqueado exitosamente'
        }
    
    def obtener_usuarios_bloqueados(self) -> List[str]:
        """Obtiene lista de usuarios bloqueados"""
        return list(self.usuarios_bloqueados)
    
    def obtener_historial_bloqueos(self, limite: int = 50) -> List[Dict]:
        """Obtiene el historial de bloqueos/desbloqueos"""
        # Devolver los más recientes primero
        return sorted(self.historial_bloqueos, key=lambda x: x['timestamp'], reverse=True)[:limite]
    
    def generar_reporte_historial_bloqueos(self) -> str:
        """Genera un reporte del historial de bloqueos"""
        if not self.historial_bloqueos:
            return "📋 **HISTORIAL DE BLOQUEOS**\n\nNo hay registros de bloqueos/desbloqueos."
        
        historial = self.obtener_historial_bloqueos(20)  # Últimos 20
        
        reporte = "📋 **HISTORIAL DE BLOQUEOS/DESBLOQUEOS**\n\n"
        reporte += f"**Total de acciones:** {len(self.historial_bloqueos)}\n"
        reporte += f"**Usuarios actualmente bloqueados:** {len(self.usuarios_bloqueados)}\n\n"
        
        reporte += "**ÚLTIMAS ACCIONES:**\n"
        
        for i, accion in enumerate(historial, 1):
            emoji = "🚫" if accion['accion'] == 'BLOQUEO' else "✅"
            reporte += f"\n**{i}.** {emoji} **{accion['accion']}**\n"
            reporte += f"• **Usuario:** {accion['username_afectado']} (`{accion['usuario_afectado']}`)\n"
            reporte += f"• **Admin:** {accion['admin_username']} (`{accion['admin_responsable']}`)\n"
            reporte += f"• **Fecha:** {accion['fecha']} a las {accion['hora']}\n"
        
        return reporte
    
    def registrar_señal_enviada(self, señal_data: Dict):
        """Registra una señal enviada"""
        señal_data['timestamp'] = datetime.now().isoformat()
        señal_data['hora'] = datetime.now().strftime('%H:%M')
        self.señales_del_dia.append(señal_data)
        self.estadisticas_diarias['señales_enviadas'] = len(self.señales_del_dia)
        
        # Actualizar contador de señales recibidas para usuarios activos
        for user_id in self.usuarios_activos:
            self.usuarios_activos[user_id]['señales_recibidas'] += 1
        
        self.guardar_datos_usuarios()
        print(f"[UserManager] 📈 Señal #{len(self.señales_del_dia)} registrada")
    
    def obtener_usuarios_activos(self) -> List[str]:
        """Obtiene lista de IDs de usuarios activos"""
        return list(self.usuarios_activos.keys())
    
    def obtener_estadisticas_diarias(self) -> Dict:
        """Obtiene estadísticas del día actual"""
        efectividad_promedio = 0
        if self.señales_del_dia:
            efectividades = [s.get('efectividad', 0) for s in self.señales_del_dia]
            efectividad_promedio = sum(efectividades) / len(efectividades)
        
        self.estadisticas_diarias.update({
            'efectividad_promedio': efectividad_promedio,
            'total_usuarios': len(self.usuarios_activos),
            'señales_enviadas': len(self.señales_del_dia)
        })
        
        return self.estadisticas_diarias
    
    def generar_clave_diaria_si_necesario(self):
        """Genera una nueva clave diaria si no existe o si es un nuevo día."""
        hoy = datetime.now().strftime('%Y-%m-%d')
        if not self.clave_publica_diaria or self.fecha_clave_actual != hoy:
            nueva_clave = secrets.token_hex(8).upper()
            self.actualizar_clave_publica(nueva_clave)
            self.guardar_datos_usuarios()
    
# Funciones de utilidad
def autenticar_usuario_telegram(user_id: str, username: str, clave: str) -> Dict:
    """Función principal para autenticar usuarios desde Telegram"""
    manager = UserManager()
    return manager.autenticar_usuario(user_id, username, clave)

def obtener_usuarios_para_señal() -> List[str]:
    """Obtiene lista de usuarios que deben recibir señales"""
    manager = UserManager()
    return manager.obtener_usuarios_activos()

def registrar_nueva_señal(señal_data: Dict):
    """Registra una nueva señal enviada"""
    manager = UserManager()
    manager.registrar_señal_enviada(señal_data)

if __name__ == "__main__":
    # Prueba del sistema
    manager = UserManager()
    print(f"🔑 Clave pública del día: {manager.clave_publica_diaria}")
    print(f"📅 Fecha: {manager.fecha_clave_actual}")
    print(f"⏰ Horario de señales activo: {manager.esta_en_horario_señales()}")
    
    # Simular autenticación
    resultado = manager.autenticar_usuario("123456", "TestUser", manager.clave_publica_diaria)
    print(f"\n📱 Resultado autenticación:")
    print(f"✅ Autenticado: {resultado['autenticado']}")
    print(f"👤 Tipo: {resultado['tipo']}")
    print(f"📝 Mensaje:\n{resultado['mensaje']}")
