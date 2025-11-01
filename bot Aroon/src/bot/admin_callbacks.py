"""
Métodos de callback para botones inline del panel de administrador
"""
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest

class AdminCallbacks:
    """Maneja todos los callbacks del panel de administrador"""
    async def safe_edit(self, query, text, **kwargs):
        """Edita mensaje de forma segura ignorando 'Message is not modified'.
        Si ocurre este caso, añade un carácter invisible para forzar cambio mínimo.
        """
        try:
            await query.edit_message_text(text, **kwargs)
        except BadRequest as e:
            if 'Message is not modified' in str(e):
                try:
                    # Añadir espacio de no separación (U+2060) para forzar cambio
                    texto_min = f"{text}\u2060"
                    await query.edit_message_text(texto_min, **kwargs)
                except Exception:
                    pass
            else:
                # Re-lanzar otros BadRequest
                raise
        except Exception:
            # Silenciar otros errores de edición para no romper la UX
            pass
    
    async def handle_admin_estado_callback(self, query):
        """Callback para mostrar estado del sistema"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        
        # Obtener información REAL del sistema
        usuarios_activos = len(self.user_manager.usuarios_activos)
        señales_hoy = len(getattr(self.signal_scheduler, 'señales_enviadas_hoy', []))
        
        # Estado de conexión a Quotex (REAL)
        estado_quotex = "🔴 DESCONECTADO"
        mercados_disponibles = 0
        try:
            if hasattr(self, 'market_manager') and self.market_manager:
                conectado = getattr(self.market_manager, 'conectado', False)
                if conectado or getattr(self.market_manager, 'quotex', None):
                    estado_quotex = "🟢 CONECTADO"
                # Contar mercados reales
                mercados_normales = len(getattr(self.market_manager, 'mercados_disponibles', []))
                mercados_otc = len(getattr(self.market_manager, 'mercados_otc', []))
                mercados_disponibles = mercados_normales + mercados_otc
        except Exception:
            pass
        
        # Estado operativo (REAL)
        horario_activo = self.signal_scheduler.esta_en_horario_operativo() if self.signal_scheduler else False
        estado_operativo = "🟢 ACTIVO" if horario_activo else "🔴 FUERA DE HORARIO"
        
        # Clave actual del día (REAL)
        clave_actual = getattr(self.user_manager, 'clave_publica_diaria', 'No generada')
        
        # Mercado actual (REAL)
        mercado_actual = "No seleccionado"
        try:
            if self.signal_scheduler and hasattr(self.signal_scheduler, 'mercado_actual'):
                merc = self.signal_scheduler.mercado_actual
                if merc and isinstance(merc, dict):
                    mercado_actual = merc.get('symbol', 'No seleccionado')
        except Exception:
            pass
        
        mensaje_estado = f"""
📊 **ESTADO DEL SISTEMA - CUBAYDSIGNAL**

🎯 **ESTADO OPERATIVO:**
• **Estado:** {estado_operativo}
• **Horario:** 8:00 AM - 8:00 PM (Lun-Sáb)
• **Hora actual:** {datetime.now().strftime('%H:%M:%S')}

🔗 **CONEXIONES:**
• **Quotex:** {estado_quotex}
• **Telegram:** 🟢 CONECTADO
• **Scheduler:** {'🟢 ACTIVO' if self.signal_scheduler else '🔴 INACTIVO'}

💱 **MERCADOS:**
• **Mercado actual:** {mercado_actual}
• **Mercados disponibles:** {mercados_disponibles}
• **Tipo:** {'OTC' if datetime.now().weekday() == 5 else 'Normal'}

👥 **USUARIOS:**
• **Usuarios activos:** {usuarios_activos}
• **Clave del día:** `{clave_actual}`

📈 **SEÑALES:**
• **Señales enviadas hoy:** {señales_hoy}
• **Próxima señal:** {'Calculando...' if horario_activo else 'Mañana 8:00 AM'}

⚙️ **SISTEMA:**
• **Bot:** 🟢 OPERATIVO
• **Análisis:** {'🟢 ACTIVO' if horario_activo else '🔴 PAUSADO'}
• **Umbral señales:** ≥80% efectividad

👑 **Panel de administrador activo**
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_estado")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit(query, mensaje_estado, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    # ============ Confirmaciones (inline) ============
    async def handle_admin_confirmaciones_menu(self, query):
        """Menú principal de confirmaciones (pre‑señal / señal)."""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        # Resetear estado de espera (si existiera)
        try:
            self.esperando_conf_usuario.discard(user_id)
        except Exception:
            # Inicializar set si no existe
            try:
                self.esperando_conf_usuario = set()
            except Exception:
                pass
        kb = [
            [InlineKeyboardButton("📅 Confirmaciones de HOY", callback_data="admin_conf_hoy")],
            [InlineKeyboardButton("🔎 Buscar por usuario", callback_data="admin_conf_usuario")],
            [InlineKeyboardButton("📅 Buscar por fecha", callback_data="admin_conf_fecha")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text("📜 Confirmaciones — elige una opción:", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_confirmaciones_fecha(self, query):
        """Prepara la captura de una fecha para mostrar confirmaciones del día solicitado."""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        try:
            self.esperando_fecha_confirmaciones.add(user_id)
        except Exception:
            try:
                self.esperando_fecha_confirmaciones = set([user_id])
            except Exception:
                pass
        kb = [[InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_confirmaciones")]]
        await query.edit_message_text(
            "📅 Envía la fecha (YYYY-MM-DD) para ver las confirmaciones de ese día.",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    async def handle_admin_confirmaciones_hoy(self, query):
        """Muestra el resumen de confirmaciones del día (YYYY-MM-DD)."""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        fecha = datetime.now().strftime('%Y-%m-%d')
        try:
            reporte = self.user_manager.generar_reporte_confirmaciones_aceptadas(fecha)
        except Exception as e:
            reporte = f"❌ Error generando reporte: {e}"
        kb = [[InlineKeyboardButton("⬅️ Atrás", callback_data="admin_confirmaciones")]]
        await self.safe_edit(query, reporte, reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_confirmaciones_usuario(self, query):
        """Prepara la búsqueda por usuario (ID o @username)."""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        # Activar espera de texto en el chat
        try:
            self.esperando_conf_usuario.add(user_id)
        except Exception:
            self.esperando_conf_usuario = {user_id}
        kb = [[InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_confirmaciones")]]
        await query.edit_message_text("Envía por chat el ID numérico o @usuario para consultar confirmaciones de HOY.", reply_markup=InlineKeyboardMarkup(kb))
    
    async def handle_admin_stats_callback(self, query):
        """Callback para mostrar estadísticas REALES del sistema"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        
        # DATOS REALES del sistema
        usuarios_activos = len(self.user_manager.usuarios_activos)
        señales_hoy = getattr(self.signal_scheduler, 'señales_enviadas_hoy', [])
        total_señales = len(señales_hoy)
        
        # Calcular efectividad REAL de las señales
        señales_exitosas = 0
        señales_fallidas = 0
        señales_pendientes = 0
        
        for señal in señales_hoy:
            resultado = señal.get('resultado', 'PENDIENTE')
            if resultado == 'WIN':
                señales_exitosas += 1
            elif resultado == 'LOSS':
                señales_fallidas += 1
            else:
                señales_pendientes += 1
        
        # Efectividad real (solo de señales completadas)
        señales_completadas = señales_exitosas + señales_fallidas
        if señales_completadas > 0:
            efectividad_real = (señales_exitosas / señales_completadas) * 100
        else:
            efectividad_real = 0
        
        # Usuarios tempranos vs tardíos (REAL)
        usuarios_tempranos = 0
        usuarios_tardios = 0
        for user_info in self.user_manager.usuarios_activos.values():
            if user_info.get('es_tardio', False):
                usuarios_tardios += 1
            else:
                usuarios_tempranos += 1
        
        # Tasa de puntualidad REAL
        tasa_puntualidad = (usuarios_tempranos / usuarios_activos * 100) if usuarios_activos > 0 else 0
        
        # Mercados REALES
        mercados_disponibles = 0
        mercados_normales = 0
        mercados_otc = 0
        try:
            if hasattr(self, 'market_manager') and self.market_manager:
                mercados_normales = len(getattr(self.market_manager, 'mercados_disponibles', []))
                mercados_otc = len(getattr(self.market_manager, 'mercados_otc', []))
                mercados_disponibles = mercados_normales + mercados_otc
        except Exception:
            pass
        
        # Estado de conexión REAL
        estado_quotex = "🔴 DESCONECTADO"
        try:
            if hasattr(self, 'market_manager') and self.market_manager:
                conectado = getattr(self.market_manager, 'conectado', False)
                if conectado or getattr(self.market_manager, 'quotex', None):
                    estado_quotex = "🟢 CONECTADO"
        except Exception:
            pass
        
        mensaje_stats = f"""
📊 **ESTADÍSTICAS REALES - CUBAYDSIGNAL**

📈 **RENDIMIENTO HOY:**
• **Señales enviadas:** {total_señales}
• **Señales exitosas:** {señales_exitosas} ✅
• **Señales fallidas:** {señales_fallidas} ❌
• **Señales pendientes:** {señales_pendientes} ⏳
• **Efectividad real:** {efectividad_real:.1f}%

👥 **USUARIOS ACTIVOS:** {usuarios_activos}
• **Usuarios tempranos:** {usuarios_tempranos}
• **Usuarios tardíos:** {usuarios_tardios}
• **Tasa de puntualidad:** {tasa_puntualidad:.1f}%

💱 **MERCADOS DISPONIBLES:**
• **Total mercados:** {mercados_disponibles}
• **Mercados normales:** {mercados_normales}
• **Mercados OTC:** {mercados_otc}
• **Estado Quotex:** {estado_quotex}

⏰ **CONFIGURACIÓN:**
• **Horario operativo:** 8:00 AM - 8:00 PM
• **Días operativos:** Lunes a Sábado
• **Análisis continuo:** Cada 60 segundos
• **Umbral señales:** ≥80% efectividad

🎯 **OBJETIVOS DIARIOS:**
• **Meta señales:** 15-25 por día
• **Meta efectividad:** ≥80%
• **Progreso hoy:** {(total_señales/20*100):.1f}% ({total_señales}/20)

📊 **DATOS EN TIEMPO REAL**
Actualizado: {datetime.now().strftime('%H:%M:%S')}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit(query, mensaje_stats, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def handle_volver_panel_admin_callback(self, query):
        """Callback para volver al panel principal de admin"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        
        username = query.from_user.username or query.from_user.first_name or "Admin"
        
        mensaje_admin = f"""
👑 **¡BIENVENIDO ADMINISTRADOR {username.upper()}!**

✅ **Acceso confirmado como administrador**

🎛️ **PANEL DE CONTROL COMPLETO**
Usa los botones de abajo para acceder a todas las funciones de administración:

👑 **¡Control total del sistema a tu alcance!**
        """
        
        # Panel completo de botones inline para admin
        keyboard = [
            [InlineKeyboardButton("📊 Estado Sistema", callback_data="admin_estado"),
             InlineKeyboardButton("📈 Estadísticas", callback_data="admin_stats")],
            [InlineKeyboardButton("💱 Mercados", callback_data="admin_mercados"),
             InlineKeyboardButton("🔗 Quotex", callback_data="admin_quotex")],
            [InlineKeyboardButton("👤 Mi Perfil", callback_data="admin_perfil"),
             InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nuevaclave")],
            [InlineKeyboardButton("🗝️ Clave Hoy", callback_data="admin_clavehoy"),
             InlineKeyboardButton("📋 Lista Hoy", callback_data="admin_listahoy")],
            [InlineKeyboardButton("🚫 Gestión Bloqueos", callback_data="admin_bloqueos"),
             InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📚 Historial", callback_data="admin_historial"),
             InlineKeyboardButton("📜 Confirmaciones", callback_data="admin_confirmaciones")],
            [InlineKeyboardButton("❓ Ayuda Admin", callback_data="admin_ayuda"),
             InlineKeyboardButton("👥 Usuarios Activos", callback_data="admin_usuarios")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit(query, mensaje_admin, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    # ============ Lista diaria (inline) ============
    async def handle_admin_listahoy_menu(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        # Limpiar estados de espera relacionados
        try:
            self.esperando_lista_agregar.discard(user_id)
            self.esperando_lista_quitar.discard(user_id)
            self.esperando_confirmar_limpiar_lista.discard(user_id)
        except Exception:
            pass
        kb = [
            [InlineKeyboardButton("👀 Ver lista", callback_data="admin_listahoy_ver")],
            [InlineKeyboardButton("➕ Agregar", callback_data="admin_listahoy_agregar")],
            [InlineKeyboardButton("➖ Quitar", callback_data="admin_listahoy_quitar")],
            [InlineKeyboardButton("🧹 Limpiar", callback_data="admin_listahoy_limpiar")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="volver_panel_admin")]
        ]
        await self.safe_edit(query, "📋 Lista diaria autorizada — elige una acción:", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_listahoy_ver(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        try:
            lista = self.user_manager.obtener_lista_diaria()
        except Exception:
            lista = []
        texto = "\n".join(lista) if lista else "(vacía)"
        kb = [[InlineKeyboardButton("⬅️ Atrás", callback_data="admin_listahoy")]]
        await self.safe_edit(query, f"📋 Lista de hoy:\n\n{texto}", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_listahoy_agregar(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        # Activar espera de texto
        self.esperando_lista_agregar.add(user_id)
        kb = [[InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_listahoy")]]
        await self.safe_edit(query, "Envía por chat el ID numérico o @usuario a AGREGAR a la lista de hoy.", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_listahoy_quitar(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        self.esperando_lista_quitar.add(user_id)
        kb = [[InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_listahoy")]]
        await self.safe_edit(query, "Envía por chat el ID numérico o @usuario a QUITAR de la lista de hoy.", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_listahoy_limpiar(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        kb = [
            [InlineKeyboardButton("Sí, limpiar", callback_data="admin_listahoy_limpiar_confirm|si")],
            [InlineKeyboardButton("No, cancelar", callback_data="admin_listahoy_limpiar_confirm|no")]
        ]
        await self.safe_edit(query, "¿Confirmas limpiar totalmente la lista del día?", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_listahoy_limpiar_confirm(self, query, opt: str):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        if opt == 'si':
            try:
                msg = self.user_manager.limpiar_lista_diaria()
            except Exception:
                msg = "❌ Error al limpiar la lista."
            kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_listahoy")]]
            await self.safe_edit(query, msg, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await self.safe_edit(query, "Operación cancelada.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver", callback_data="admin_listahoy")]]))

    # ============ Gestión de Bloqueos (inline) ============
    async def handle_admin_bloqueos_menu(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        # Limpiar estados de espera relacionados
        try:
            self.esperando_bloquear.discard(user_id)
            self.esperando_desbloquear.discard(user_id)
            self.esperando_bloq_hist_usuario.discard(user_id)
            self.esperando_bloq_hist_id.discard(user_id)
        except Exception:
            pass
        kb = [
            [InlineKeyboardButton("👀 Ver bloqueados", callback_data="admin_bloqueos_ver")],
            [InlineKeyboardButton("🚫 Bloquear ID", callback_data="admin_bloqueos_bloquear")],
            [InlineKeyboardButton("✅ Desbloquear ID", callback_data="admin_bloqueos_desbloquear")],
            [InlineKeyboardButton("📜 Historial", callback_data="admin_bloqueos_hist")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="volver_panel_admin")]
        ]
        await self.safe_edit(query, "🚫 Gestión de bloqueos — elige una acción:", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_bloqueos_ver(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        try:
            bloqueados = self.user_manager.obtener_usuarios_bloqueados()
        except Exception:
            bloqueados = []
        lista = "\n".join(bloqueados) if bloqueados else "(sin bloqueados)"
        kb = [[InlineKeyboardButton("⬅️ Atrás", callback_data="admin_bloqueos")]]
        await self.safe_edit(query, f"🚫 Usuarios bloqueados:\n\n{lista}", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_bloqueos_bloquear(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        self.esperando_bloquear.add(user_id)
        kb = [[InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_bloqueos")]]
        await self.safe_edit(query, "Envía por chat el ID numérico a BLOQUEAR.", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_bloqueos_desbloquear(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        self.esperando_desbloquear.add(user_id)
        kb = [[InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_bloqueos")]]
        await self.safe_edit(query, "Envía por chat el ID numérico a DESBLOQUEAR.", reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_bloqueos_hist(self, query):
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        from datetime import datetime as _dt
        hoy = _dt.now().strftime('%Y-%m-%d')
        try:
            eventos = self.user_manager.consultar_historial_bloqueos(hoy)
        except Exception:
            eventos = []
        if not eventos:
            texto = f"📜 Historial de bloqueos {hoy}\n\n(sin eventos)"
        else:
            lineas = [f"📜 Historial de bloqueos {hoy}", ""]
            for e in eventos[-40:]:
                lineas.append(f"• {e.get('fecha','')[:16]} – {e.get('accion','?').upper()} – ID {e.get('user_id','?')} – @{e.get('username') or ''}")
            texto = "\n".join(lineas)
        kb = [
            [InlineKeyboardButton("🔎 Buscar por fecha", callback_data="admin_bloq_hist_fecha")],
            [InlineKeyboardButton("⬅️ Atrás", callback_data="admin_bloqueos")]
        ]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_bloq_hist_fecha(self, query):
        """Prepara el flujo para consultar historial de bloqueos por fecha (YYYY-MM-DD)."""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        try:
            self.esperando_bloq_hist_fecha.add(user_id)
        except Exception:
            try:
                self.esperando_bloq_hist_fecha = set([user_id])
            except Exception:
                pass
        kb = [[InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_bloqueos")]]
        await query.edit_message_text(
            "📅 Envía la fecha a consultar (formato YYYY-MM-DD).",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    
    # ============ Panel de Mercados (nuevo) ============
    async def handle_admin_mercados_menu(self, query):
        """Menú principal del panel de mercados"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        
        # Obtener información de mercados
        try:
            if hasattr(self, 'market_manager') and self.market_manager:
                mercados_normales = len(getattr(self.market_manager, 'mercados_disponibles', []))
                mercados_otc = len(getattr(self.market_manager, 'mercados_otc', []))
                total_mercados = mercados_normales + mercados_otc
                
                # Calcular estadísticas de payouts
                todos_mercados = (getattr(self.market_manager, 'mercados_disponibles', []) + 
                                 getattr(self.market_manager, 'mercados_otc', []))
                
                if todos_mercados:
                    payouts = [m.get('payout', 0) for m in todos_mercados]
                    payout_min = min(payouts)
                    payout_max = max(payouts)
                    payout_avg = sum(payouts) / len(payouts)
                else:
                    payout_min = payout_max = payout_avg = 0
            else:
                mercados_normales = mercados_otc = total_mercados = 0
                payout_min = payout_max = payout_avg = 0
        except Exception:
            mercados_normales = mercados_otc = total_mercados = 0
            payout_min = payout_max = payout_avg = 0
        
        mensaje = f"""
💱 **PANEL DE MERCADOS - CUBAYDSIGNAL**

📊 **RESUMEN DE MERCADOS:**
• **Total de mercados:** {total_mercados}
• **Mercados normales:** {mercados_normales}
• **Mercados OTC:** {mercados_otc}

💰 **ESTADÍSTICAS DE PAYOUTS:**
• **Payout mínimo:** {payout_min:.1f}%
• **Payout máximo:** {payout_max:.1f}%
• **Payout promedio:** {payout_avg:.1f}%

🎯 **FILTROS ACTIVOS:**
• Solo mercados con payout ≥ 80%
• Datos en tiempo real de Quotex

📋 **Usa los botones para explorar:**
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 Ver Todos", callback_data="admin_mercados_todos"),
             InlineKeyboardButton("🌐 Ver Normales", callback_data="admin_mercados_normales")],
            [InlineKeyboardButton("🌙 Ver OTC", callback_data="admin_mercados_otc"),
             InlineKeyboardButton("🔍 Buscar", callback_data="admin_mercados_buscar")],
            [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_mercados"),
             InlineKeyboardButton("⬅️ Volver", callback_data="volver_panel_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit(query, mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def handle_admin_mercados_todos(self, query):
        """Muestra todos los mercados disponibles"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        
        try:
            if hasattr(self, 'market_manager') and self.market_manager:
                mercados_normales = getattr(self.market_manager, 'mercados_disponibles', [])
                mercados_otc = getattr(self.market_manager, 'mercados_otc', [])
                todos_mercados = mercados_normales + mercados_otc
                
                if not todos_mercados:
                    mensaje = "⚠️ No hay mercados disponibles.\n\nConéctate a Quotex primero."
                else:
                    # Ordenar por payout descendente
                    todos_mercados.sort(key=lambda x: x.get('payout', 0), reverse=True)
                    
                    lineas = ["💱 **TODOS LOS MERCADOS**\n"]
                    for i, m in enumerate(todos_mercados[:30], 1):  # Mostrar máximo 30
                        symbol = m.get('symbol', 'N/A')
                        nombre = m.get('nombre', symbol)
                        payout = m.get('payout', 0)
                        tipo = "🌙 OTC" if m.get('otc', False) else "🌐 Normal"
                        estado = "🟢" if m.get('open', True) else "🔴"
                        
                        lineas.append(f"{i}. {estado} **{nombre}** ({tipo})")
                        lineas.append(f"   💰 Payout: {payout:.1f}%")
                    
                    if len(todos_mercados) > 30:
                        lineas.append(f"\n... y {len(todos_mercados) - 30} mercados más")
                    
                    mensaje = "\n".join(lineas)
            else:
                mensaje = "❌ MarketManager no disponible"
        except Exception as e:
            mensaje = f"❌ Error obteniendo mercados: {e}"
        
        keyboard = [
            [InlineKeyboardButton("📄 Exportar como PDF", callback_data="admin_mercados_pdf_todos")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_mercados")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit(query, mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def handle_admin_mercados_normales(self, query):
        """Muestra solo mercados normales"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        
        try:
            if hasattr(self, 'market_manager') and self.market_manager:
                mercados = getattr(self.market_manager, 'mercados_disponibles', [])
                
                if not mercados:
                    mensaje = "⚠️ No hay mercados normales disponibles.\n\nPueden estar cerrados fuera de horario."
                else:
                    # Ordenar por payout descendente
                    mercados.sort(key=lambda x: x.get('payout', 0), reverse=True)
                    
                    lineas = ["🌐 **MERCADOS NORMALES**\n"]
                    for i, m in enumerate(mercados, 1):
                        symbol = m.get('symbol', 'N/A')
                        nombre = m.get('nombre', symbol)
                        payout = m.get('payout', 0)
                        estado = "🟢" if m.get('open', True) else "🔴"
                        
                        lineas.append(f"{i}. {estado} **{nombre}**")
                        lineas.append(f"   💰 Payout: {payout:.1f}%")
                    
                    mensaje = "\n".join(lineas)
            else:
                mensaje = "❌ MarketManager no disponible"
        except Exception as e:
            mensaje = f"❌ Error obteniendo mercados: {e}"
        
        keyboard = [
            [InlineKeyboardButton("📄 Exportar como PDF", callback_data="admin_mercados_pdf_normales")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_mercados")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit(query, mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def handle_admin_mercados_otc(self, query):
        """Muestra solo mercados OTC"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        
        try:
            if hasattr(self, 'market_manager') and self.market_manager:
                mercados = getattr(self.market_manager, 'mercados_otc', [])
                
                if not mercados:
                    mensaje = "⚠️ No hay mercados OTC disponibles."
                else:
                    # Ordenar por payout descendente
                    mercados.sort(key=lambda x: x.get('payout', 0), reverse=True)
                    
                    lineas = ["🌙 **MERCADOS OTC**\n"]
                    for i, m in enumerate(mercados[:30], 1):  # Máximo 30
                        symbol = m.get('symbol', 'N/A')
                        nombre = m.get('nombre', symbol)
                        payout = m.get('payout', 0)
                        estado = "🟢" if m.get('open', True) else "🔴"
                        
                        lineas.append(f"{i}. {estado} **{nombre}**")
                        lineas.append(f"   💰 Payout: {payout:.1f}%")
                    
                    if len(mercados) > 30:
                        lineas.append(f"\n... y {len(mercados) - 30} mercados más")
                    
                    mensaje = "\n".join(lineas)
            else:
                mensaje = "❌ MarketManager no disponible"
        except Exception as e:
            mensaje = f"❌ Error obteniendo mercados: {e}"
        
        keyboard = [
            [InlineKeyboardButton("📄 Exportar como PDF", callback_data="admin_mercados_pdf_otc")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_mercados")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit(query, mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def handle_admin_mercados_buscar(self, query):
        """Activa el modo de búsqueda de mercados"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        
        # Activar estado de espera para búsqueda
        try:
            if not hasattr(self, 'esperando_busqueda_mercado'):
                self.esperando_busqueda_mercado = set()
            self.esperando_busqueda_mercado.add(user_id)
        except Exception:
            self.esperando_busqueda_mercado = {user_id}
        
        mensaje = """
🔍 **BUSCAR MERCADO**

Envía el nombre del mercado que quieres buscar.

**Ejemplos:**
• `EURUSD`
• `GBPUSD`
• `BTCUSD`
• `AUDCAD`

El bot buscará el mercado y te mostrará:
• Payout actual
• Estado (abierto/cerrado)
• Tipo (Normal/OTC)
• Análisis técnico reciente
        """
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_mercados")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.safe_edit(query, mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def handle_admin_mercados_pdf(self, query, tipo="todos"):
        """Genera y envía un PDF con la lista de mercados"""
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.answer("❌ Acceso denegado.", show_alert=True)
            return
        
        try:
            # Mensaje de progreso
            await query.answer("📄 Generando PDF...", show_alert=False)
            
            if not hasattr(self, 'market_manager') or not self.market_manager:
                await query.answer("❌ MarketManager no disponible", show_alert=True)
                return
            
            # Obtener mercados según el tipo
            if tipo == "todos":
                mercados_normales = getattr(self.market_manager, 'mercados_disponibles', [])
                mercados_otc = getattr(self.market_manager, 'mercados_otc', [])
                mercados = mercados_normales + mercados_otc
                titulo = "TODOS LOS MERCADOS"
            elif tipo == "normales":
                mercados = getattr(self.market_manager, 'mercados_disponibles', [])
                titulo = "MERCADOS NORMALES"
            elif tipo == "otc":
                mercados = getattr(self.market_manager, 'mercados_otc', [])
                titulo = "MERCADOS OTC"
            else:
                mercados = []
                titulo = "MERCADOS"
            
            if not mercados:
                await query.answer("⚠️ No hay mercados disponibles para exportar", show_alert=True)
                return
            
            # Ordenar por payout descendente
            mercados.sort(key=lambda x: x.get('payout', 0), reverse=True)
            
            # Generar PDF
            from datetime import datetime
            import os
            
            try:
                from reportlab.lib.pagesizes import letter, A4
                from reportlab.lib import colors
                from reportlab.lib.units import inch
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.enums import TA_CENTER, TA_LEFT
                
                # Crear directorio temporal si no existe
                os.makedirs('temp', exist_ok=True)
                
                # Nombre del archivo
                fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'temp/mercados_{tipo}_{fecha_hora}.pdf'
                
                # Crear documento
                doc = SimpleDocTemplate(filename, pagesize=A4)
                elements = []
                styles = getSampleStyleSheet()
                
                # Estilo personalizado para título
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=18,
                    textColor=colors.HexColor('#1a73e8'),
                    spaceAfter=30,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Bold'
                )
                
                # Título
                elements.append(Paragraph(f"📊 {titulo}", title_style))
                elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
                elements.append(Spacer(1, 0.3*inch))
                
                # Estadísticas
                payouts = [m.get('payout', 0) for m in mercados]
                payout_min = min(payouts) if payouts else 0
                payout_max = max(payouts) if payouts else 0
                payout_prom = sum(payouts) / len(payouts) if payouts else 0
                
                stats_text = f"""
                <b>Total de mercados:</b> {len(mercados)}<br/>
                <b>Payout mínimo:</b> {payout_min:.1f}%<br/>
                <b>Payout máximo:</b> {payout_max:.1f}%<br/>
                <b>Payout promedio:</b> {payout_prom:.1f}%
                """
                elements.append(Paragraph(stats_text, styles['Normal']))
                elements.append(Spacer(1, 0.3*inch))
                
                # Tabla de mercados
                data = [['#', 'Mercado', 'Símbolo', 'Payout', 'Tipo', 'Estado']]
                
                for i, m in enumerate(mercados, 1):
                    symbol = m.get('symbol', 'N/A')
                    nombre = m.get('nombre', symbol)
                    payout = m.get('payout', 0)
                    tipo_mercado = "OTC" if m.get('otc', False) else "Normal"
                    estado = "Abierto" if m.get('open', True) else "Cerrado"
                    
                    data.append([
                        str(i),
                        nombre[:20],  # Limitar longitud
                        symbol[:15],
                        f"{payout:.1f}%",
                        tipo_mercado,
                        estado
                    ])
                
                # Crear tabla
                table = Table(data, colWidths=[0.5*inch, 1.8*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch])
                table.setStyle(TableStyle([
                    # Encabezado
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    
                    # Contenido
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                
                elements.append(table)
                
                # Pie de página
                elements.append(Spacer(1, 0.5*inch))
                footer_text = f"Generado por CubaYDSignal Bot - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                elements.append(Paragraph(footer_text, styles['Italic']))
                
                # Construir PDF
                doc.build(elements)
                
                # Enviar PDF
                with open(filename, 'rb') as pdf_file:
                    await query.message.reply_document(
                        document=pdf_file,
                        filename=f"mercados_{tipo}_{fecha_hora}.pdf",
                        caption=f"📄 **Lista de {titulo}**\n\n"
                                f"📊 Total: {len(mercados)} mercados\n"
                                f"💰 Payout: {payout_min:.1f}% - {payout_max:.1f}%\n"
                                f"📅 Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Eliminar archivo temporal
                try:
                    os.remove(filename)
                except:
                    pass
                
                await query.answer("✅ PDF generado exitosamente", show_alert=False)
                
            except ImportError:
                await query.answer("❌ Librería reportlab no instalada. Instala con: pip install reportlab", show_alert=True)
            except Exception as e:
                await query.answer(f"❌ Error generando PDF: {str(e)[:100]}", show_alert=True)
                print(f"[PDF] Error: {e}")
                import traceback
                print(traceback.format_exc())
                
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)[:100]}", show_alert=True)
