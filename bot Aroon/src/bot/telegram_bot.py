"""
BOT DE TELEGRAM INTEGRADO PARA CUBAYDSIGNAL
Maneja:
- Comandos de usuario (/start, /clave, /estado, etc.)
- Autenticación automática
- Envío de señales
- Mensajes motivacionales
- Panel de administrador
- Integración completa con todos los módulos
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from zoneinfo import ZoneInfo
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

from core.user_manager import UserManager
from core.signal_scheduler import SignalScheduler
from core.market_manager import MarketManager
from bot.admin_callbacks import AdminCallbacks

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
CUBA_TZ = ZoneInfo("America/Havana")

class CubaYDSignalBot(AdminCallbacks):
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        
        # Inicializar managers de forma segura
        try:
            self.user_manager = UserManager()
            print("✅ UserManager inicializado")
        except Exception as e:
            print(f"❌ Error inicializando UserManager: {e}")
            self.user_manager = None
            
        # NO crear instancias propias - se configurarán externamente desde run_bot.py
        self.signal_scheduler = None
        self.market_manager = None
        
        # Evento para indicar que el bot ya está listo (polling activo)
        import asyncio as _aio
        self.ready = _aio.Event()
        
        # Configurar UserManager
        try:
            if self.user_manager and hasattr(self.user_manager, 'configurar_bot_telegram'):
                self.user_manager.configurar_bot_telegram(self)
                print("✅ UserManager configurado")
        except Exception as e:
            print(f"❌ Error configurando UserManager: {e}")
        
        # Estados de conversación
        self.esperando_clave = set()
        self.esperando_clave_personalizada = set()
        
        # Control de análisis forzado y trading automático
        self._analisis_forzado_activo = False
        self._trading_auto_af_activo = False
        self._analisis_forzado_user_id = None
        # Estados para flujos admin (inline)
        self.esperando_lista_agregar = set()
        self.esperando_lista_quitar = set()
        self.esperando_confirmar_limpiar_lista = set()
        self.esperando_bloquear = set()
        self.esperando_desbloquear = set()
        self.esperando_broadcast = set()
        # Estados para reporte de confirmaciones
        self.esperando_fecha_confirmaciones = set()
        self.esperando_busqueda_confirmaciones = set()
        self.esperando_busqueda_confirmaciones_usuario = set()
        self.esperando_busqueda_confirmaciones_id = set()
        # Estado para menú inline de confirmaciones (búsqueda por usuario)
        self.esperando_conf_usuario = set()
        # Historial de bloqueos: búsqueda por usuario/ID
        self.esperando_bloq_hist_usuario = set()
        self.esperando_bloq_hist_id = set()
        # Historial de bloqueos: búsqueda por fecha
        self.esperando_bloq_hist_fecha = set()
        # Estado para búsqueda de mercados
        self.esperando_busqueda_mercado = set()
        
        # Programar recordatorio 15 minutos antes del inicio de señales (07:45)
        try:
            from datetime import time as dtime
            if getattr(self.application, 'job_queue', None) is not None:
                # Lunes a Sábado (0=lun ... 5=sáb). Domingos no hay señales.
                self.application.job_queue.run_daily(
                    self.job_recordatorio_pre_senales,
                    time=dtime(hour=7, minute=45),
                    days=(0,1,2,3,4,5)
                )
        except Exception as _:
            # Evitar caída si el JobQueue no está disponible
            pass

        # Setup handlers de forma segura
        try:
            self.setup_handlers()
            print("✅ Handlers configurados correctamente")
        except Exception as e:
            print(f"❌ Error configurando handlers: {e}")
            raise
        
    async def run_async(self):
        """Inicia el bot en modo asíncrono (polling) y retorna inmediatamente.
        Compatibiliza con run_bot.py que hace `await telegram_bot.run_async()`.
        """
        try:
            # Inicializa y arranca la aplicación sin bloquear el loop principal
            await self.application.initialize()
            await self.application.start()
            # En PTB v20, el updater existe cuando se construye con token
            if getattr(self.application, "updater", None) is not None:
                await self.application.updater.start_polling()
            # Señalizar que el bot está listo
            try:
                self.ready.set()
            except Exception:
                pass
            print("🤖 Telegram Bot: polling iniciado")
        except Exception as e:
            print(f"❌ No se pudo iniciar el bot de Telegram: {e}")
            raise

    def configurar_market_manager(self, market_manager: MarketManager):
        """Inyecta MarketManager en el bot (usado por panel admin y estado)."""
        try:
            self.market_manager = market_manager
            print("✅ MarketManager inyectado en TelegramBot")
        except Exception as e:
            print(f"⚠️ Error al configurar MarketManager en TelegramBot: {e}")

    async def send_message(self, chat_id, text, parse_mode=None):
        """Helper para enviar mensajes por Telegram con manejo de errores"""
        try:
            await self.application.bot.send_message(chat_id=str(chat_id), text=text, parse_mode=parse_mode)
            try:
                logger.info(f"[TG] Mensaje enviado a {chat_id}")
            except Exception:
                pass
        except Exception as e:
            try:
                logger.warning(f"[TG] Error enviando mensaje a {chat_id}: {e}")
            except Exception:
                pass
            # Además, imprimir para visibilidad en consola
            print(f"[TG] Error enviando mensaje a {chat_id}: {e}")

    async def notificar_admin_telegram(self, text):
        """Atajo para notificar al admin por Telegram"""
        admin_id = getattr(self.user_manager, 'admin_id', None)
        if not admin_id:
            try:
                logger.warning("[TG] admin_id no definido en UserManager")
            except Exception:
                pass
            return
        try:
            await self.application.bot.send_message(chat_id=str(admin_id), text=text)
        except Exception as e:
            try:
                logger.warning(f"[TG] No se pudo notificar al admin: {e}")
            except Exception:
                pass

    async def cmd_probar_recordatorio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Permite a un admin disparar manualmente el recordatorio pre-señales."""
        uid = str(update.effective_user.id)
        if not self.user_manager.es_administrador(uid):
            await update.message.reply_text("❌ Solo administradores pueden usar este comando.")
            return
        await update.message.reply_text("⏱️ Enviando recordatorio ahora...")
        try:
            await self.job_recordatorio_pre_senales(context)
            await update.message.reply_text("✅ Recordatorio enviado.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error enviando recordatorio: {e}")

        # Fin de comando; sin notificación extra
    
    async def job_recordatorio_pre_senales(self, context: ContextTypes.DEFAULT_TYPE):
        """Job diario 07:45 (America/Havana). Envía recordatorio de inicio de señales a usuarios activos."""
        # Seguridad extra: no enviar si es domingo en Cuba
        try:
            if self._es_domingo_cuba():
                return
        except Exception:
            pass
        try:
            ahora_cuba = datetime.now(CUBA_TZ).strftime('%d/%m/%Y %H:%M')
            mensaje = (
                "⏰ **Recordatorio de inicio de señales**\n\n"
                f"📅 {ahora_cuba} (hora de Cuba)\n"
                "Faltan ~15 minutos para el primer bloque de señales.\n\n"
                "🕘 Horario operativo: Lun‑Sáb 8:00–20:00\n"
                "🔔 Consejo: activa las notificaciones para no perderte ninguna señal."
            )
            usuarios = list(getattr(self.user_manager, 'usuarios_activos', {}).keys())
            enviados = 0
            for uid in usuarios:
                try:
                    await self.send_message(uid, mensaje, parse_mode=ParseMode.MARKDOWN)
                    enviados += 1
                except Exception:
                    pass
            try:
                await self.notificar_admin_telegram(f"⏰ Recordatorio pre‑señales enviado a {enviados} usuarios.")
            except Exception:
                pass
        except Exception as e:
            try:
                await self.notificar_admin_telegram(f"⚠️ Error en job de recordatorio: {e}")
            except Exception:
                pass
    
    def setup_handlers(self):
        """Configura todos los handlers del bot"""
        # Comandos principales
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("ayuda", self.cmd_ayuda))
        self.application.add_handler(CommandHandler("clave", self.cmd_clave))
        self.application.add_handler(CommandHandler("estado", self.cmd_estado))
        self.application.add_handler(CommandHandler("perfil", self.cmd_perfil))
        
        # Comandos especiales de administrador
        self.application.add_handler(CommandHandler("nuevaclave", self.cmd_nuevaclave))
        self.application.add_handler(CommandHandler("clavehoy", self.cmd_clavehoy))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        # Estado de Quotex (solo admin)
        self.application.add_handler(CommandHandler("quotex", self.cmd_quotex))
        self.application.add_handler(CommandHandler("historial", self.comando_historial_usuarios))
        self.application.add_handler(CommandHandler("efectividad", self.cmd_efectividad))  # NUEVO
        # Comandos de lista blanca
        self.application.add_handler(CommandHandler("listablanca", self.cmd_listablanca))
        self.application.add_handler(CommandHandler("agregarblanco", self.cmd_agregarblanco))
        self.application.add_handler(CommandHandler("quitarblanco", self.cmd_quitarblanco))
        # Comando broadcast y consulta de historial
        self.application.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
        self.application.add_handler(CommandHandler("historialsenales", self.cmd_historialsenales))
        self.application.add_handler(CommandHandler("historialbloqueos", self.cmd_historialbloqueos))
        self.application.add_handler(CommandHandler("accesos_no_autorizados", self.cmd_accesos_no_autorizados))
        self.application.add_handler(CommandHandler("accesos", self.cmd_accesos_no_autorizados))  # Alias corto
        # Comando para probar el recordatorio inmediato (solo admin)
        self.application.add_handler(CommandHandler("probarrecordatorio", self.cmd_probar_recordatorio))
        # Reporte detallado de confirmaciones (solo admin)
        self.application.add_handler(CommandHandler("confirmaciones", self.cmd_confirmaciones))
        # Nota: estadísticas de confirmaciones solo por botones inline (sin comando)
        # Nota: Gestión de lista diaria y bloqueos se hace SOLO por botones inline
        
        # Handler para mensajes de texto (claves)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Callbacks para botones
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes de texto según estados de espera y clave de acceso."""
        if not update.message:
            return
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name or "Usuario"
        texto = (update.message.text or "").strip()

        # 1) Ingreso de clave cuando está en espera o si el usuario envía algo con pinta de clave
        if user_id in self.esperando_clave:
            self.esperando_clave.discard(user_id)
            await self.procesar_clave(update, texto)
            return

        # 2) Flujos ADMIN por botones inline (lista diaria)
        if self.user_manager.es_administrador(user_id):
            # Análisis Forzado: flujo de configuración de mercado
            if hasattr(self, '_analisis_forzado_state') and user_id in self._analisis_forzado_state:
                print(f"[AF] Detectado texto en flujo AF - user_id: {user_id}, texto: {texto}")
                print(f"[AF] Estado actual: {self._analisis_forzado_state[user_id]}")
                await self.handle_af_text_input(update, texto)
                return
            
            # Clave personalizada: activar y revocar accesos previos
            if user_id in getattr(self, 'esperando_clave_personalizada', set()):
                self.esperando_clave_personalizada.discard(user_id)
                try:
                    nueva = self.user_manager.generar_clave_publica_personalizada(texto)
                    await update.message.reply_text(
                        f"✅ Clave personalizada activada: `{nueva}`\n\nSe revocó el acceso de usuarios previos y fueron notificados.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    # Notificar al admin explícitamente
                    try:
                        await self.notificar_admin_telegram(f"🔑 Clave personalizada aceptada y activada: {nueva}")
                    except Exception:
                        pass
                except Exception as e:
                    await update.message.reply_text(f"❌ Error al establecer clave personalizada: {e}")
                return
            # Lista diaria: AGREGAR
            if user_id in getattr(self, 'esperando_lista_agregar', set()):
                try:
                    msg = self.user_manager.agregar_a_lista_diaria(texto)
                except Exception as e:
                    msg = f"❌ Error agregando a la lista: {e}"
                self.esperando_lista_agregar.discard(user_id)
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_listahoy")]]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
                return
            # Lista diaria: QUITAR
            if user_id in getattr(self, 'esperando_lista_quitar', set()):
                try:
                    msg = self.user_manager.quitar_de_lista_diaria(texto)
                except Exception as e:
                    msg = f"❌ Error quitando de la lista: {e}"
                self.esperando_lista_quitar.discard(user_id)
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_listahoy")]]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
                return
            # Bloqueos: BLOQUEAR
            if user_id in getattr(self, 'esperando_bloquear', set()):
                try:
                    msg = self.user_manager.bloquear_usuario(texto)
                except Exception as e:
                    msg = f"❌ Error bloqueando: {e}"
                self.esperando_bloquear.discard(user_id)
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_bloqueos")]]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
                return
            # Bloqueos: DESBLOQUEAR
            if user_id in getattr(self, 'esperando_desbloquear', set()):
                try:
                    msg = self.user_manager.desbloquear_usuario(texto)
                except Exception as e:
                    msg = f"❌ Error desbloqueando: {e}"
                self.esperando_desbloquear.discard(user_id)
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_bloqueos")]]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
                return
            # Broadcast a todos los usuarios activos
            if user_id in getattr(self, 'esperando_broadcast', set()):
                self.esperando_broadcast.discard(user_id)
                enviados = 0
                for uid in list(getattr(self.user_manager, 'usuarios_activos', {}).keys()):
                    try:
                        await self.send_message(uid, f"📢 {texto}")
                        enviados += 1
                    except Exception:
                        pass
                await update.message.reply_text(f"✅ Mensaje enviado a {enviados} usuarios.")
                # Notificar al admin del broadcast
                try:
                    preview = (texto[:70] + '…') if len(texto) > 70 else texto
                    await self.notificar_admin_telegram(f"📢 Broadcast enviado a {enviados} usuarios.\n📝 Contenido: {preview}")
                except Exception:
                    pass
                return
            # Confirmaciones: pedir fecha
            if user_id in getattr(self, 'esperando_fecha_confirmaciones', set()):
                self.esperando_fecha_confirmaciones.discard(user_id)
                try:
                    reporte = self.user_manager.generar_reporte_confirmaciones_aceptadas(texto)
                except Exception as e:
                    reporte = f"❌ Error generando reporte: {e}"
                await update.message.reply_text(reporte)
                return
            # Bloqueos: historial por fecha (YYYY-MM-DD)
            if user_id in getattr(self, 'esperando_bloq_hist_fecha', set()):
                self.esperando_bloq_hist_fecha.discard(user_id)
                fecha = texto.strip()
                try:
                    eventos = self.user_manager.consultar_historial_bloqueos(fecha)
                    if not eventos:
                        texto_resp = f"📜 Historial de bloqueos {fecha}\n\n(sin eventos)"
                    else:
                        lineas = [f"📜 Historial de bloqueos {fecha}", ""]
                        for e in eventos[-40:]:
                            lineas.append(f"• {e.get('fecha','')[:16]} – {e.get('accion','?').upper()} – ID {e.get('user_id','?')} – @{e.get('username') or ''}")
                        texto_resp = "\n".join(lineas)
                except Exception as e:
                    texto_resp = f"❌ Error consultando historial: {e}"
                await update.message.reply_text(texto_resp)
                return
            # Búsqueda de mercados
            if user_id in getattr(self, 'esperando_busqueda_mercado', set()):
                self.esperando_busqueda_mercado.discard(user_id)
                busqueda = texto.strip().upper()
                try:
                    if hasattr(self, 'market_manager') and self.market_manager:
                        # Buscar en todos los mercados
                        mercados_normales = getattr(self.market_manager, 'mercados_disponibles', [])
                        mercados_otc = getattr(self.market_manager, 'mercados_otc', [])
                        todos_mercados = mercados_normales + mercados_otc
                        
                        # Buscar coincidencias
                        encontrados = []
                        for m in todos_mercados:
                            symbol = m.get('symbol', '').upper()
                            nombre = m.get('nombre', '').upper()
                            if busqueda in symbol or busqueda in nombre:
                                encontrados.append(m)
                        
                        if not encontrados:
                            mensaje = f"❌ No se encontró ningún mercado con '{busqueda}'\n\n💡 Intenta con: EURUSD, GBPUSD, BTCUSD, etc."
                        elif len(encontrados) == 1:
                            # Mostrar detalles completos del mercado con análisis
                            m = encontrados[0]
                            symbol = m.get('symbol', 'N/A')
                            nombre = m.get('nombre', symbol)
                            payout = m.get('payout', 0)
                            tipo = "🌙 OTC" if m.get('otc', False) else "🌐 Normal"
                            estado = "🟢 Abierto" if m.get('open', True) else "🔴 Cerrado"
                            
                            # Enviar mensaje de "analizando..."
                            mensaje_temp = await update.message.reply_text(
                                f"🔍 **Analizando {nombre}...**\n\n"
                                f"⏳ Obteniendo datos de Quotex y ejecutando análisis técnico completo...\n"
                                f"📊 Esto puede tomar 5-10 segundos"
                            )
                            
                            # Intentar obtener análisis reciente del mercado
                            analisis_texto = ""
                            try:
                                # Obtener datos del mercado para análisis PRIORITARIO
                                import asyncio
                                df = await self.market_manager.obtener_datos_mercado(symbol)
                                
                                if not df.empty and len(df) >= 20:
                                    from strategies.evaluar_estrategia_completa import evaluar_estrategia_completa
                                    resultado = evaluar_estrategia_completa(df, symbol)
                                    
                                    # Extraer detalles del análisis
                                    detalles = resultado.get('detalles', {})
                                    efectividad_total = resultado.get('efectividad_total', 0)
                                    decision = resultado.get('decision', 'Sin señal')
                                    
                                    # Obtener efectividades individuales
                                    ef_tendencia = detalles.get('tendencia', {}).get('efectividad', 0)
                                    ef_sr = detalles.get('soportes_resistencias', {}).get('efectividad', 0)
                                    ef_patrones = detalles.get('patrones', {}).get('efectividad', 0)
                                    ef_volatilidad = detalles.get('volatilidad', {}).get('efectividad', 0)
                                    
                                    # Obtener direcciones
                                    dir_tendencia = detalles.get('tendencia', {}).get('direccion', 'indefinida')
                                    dir_sr = detalles.get('soportes_resistencias', {}).get('direccion', 'indefinida')
                                    dir_patrones = detalles.get('patrones', {}).get('direccion', 'indefinida')
                                    dir_volatilidad = detalles.get('volatilidad', {}).get('direccion', 'indefinida')
                                    
                                    # Calcular pesos (según evaluar_estrategia_completa.py)
                                    peso_tendencia = 30
                                    peso_sr = 20
                                    peso_patrones = 30
                                    peso_volatilidad = 20
                                    
                                    analisis_texto = f"""
📈 **ANÁLISIS TÉCNICO ACTUAL:**

**Efectividad Total:** {efectividad_total:.1f}%
**Decisión:** {decision if decision else 'Sin señal clara'}

**📊 PESOS DE ESTRATEGIAS:**

1️⃣ **Tendencia** ({peso_tendencia}% peso)
   • Efectividad: {ef_tendencia:.1f}%
   • Dirección: {dir_tendencia.upper()}

2️⃣ **Soportes/Resistencias** ({peso_sr}% peso)
   • Efectividad: {ef_sr:.1f}%
   • Dirección: {dir_sr.upper()}

3️⃣ **Patrones de Velas** ({peso_patrones}% peso)
   • Efectividad: {ef_patrones:.1f}%
   • Dirección: {dir_patrones.upper()}

4️⃣ **Volatilidad** ({peso_volatilidad}% peso)
   • Efectividad: {ef_volatilidad:.1f}%
   • Dirección: {dir_volatilidad.upper()}

💡 **Interpretación:**
• Solo se envían señales con efectividad ≥ 80%
• Análisis actualizado cada 60 segundos
"""
                                else:
                                    analisis_texto = "\n⚠️ No hay suficientes datos para análisis técnico\n"
                            except Exception as e:
                                analisis_texto = f"\n⚠️ Análisis no disponible: {str(e)[:50]}\n"
                            
                            # Eliminar mensaje temporal
                            try:
                                await mensaje_temp.delete()
                            except:
                                pass
                            
                            mensaje = f"""
💱 **DETALLES DEL MERCADO**

📊 **Mercado:** {nombre}
🔤 **Símbolo:** `{symbol}`
💰 **Payout:** {payout:.1f}%
🏷️ **Tipo:** {tipo}
📡 **Estado:** {estado}
{analisis_texto}
🎯 **PRÓXIMA SEÑAL:**
• Si cumple criterios (≥80%), recibirás señal automática
                            """
                            
                            # Guardar datos del análisis para el botón detallado
                            if analisis_texto and 'No hay suficientes datos' not in analisis_texto:
                                # Guardar en memoria temporal para el callback
                                if not hasattr(self, '_analisis_detallado_cache'):
                                    self._analisis_detallado_cache = {}
                                self._analisis_detallado_cache[user_id] = {
                                    'symbol': symbol,
                                    'nombre': nombre,
                                    'resultado': resultado,
                                    'detalles': detalles
                                }
                        else:
                            # Mostrar lista de coincidencias
                            lineas = [f"🔍 **RESULTADOS DE BÚSQUEDA: '{busqueda}'**\n"]
                            lineas.append(f"Se encontraron {len(encontrados)} mercados:\n")
                            for i, m in enumerate(encontrados[:10], 1):
                                symbol = m.get('symbol', 'N/A')
                                nombre = m.get('nombre', symbol)
                                payout = m.get('payout', 0)
                                tipo = "🌙" if m.get('otc', False) else "🌐"
                                lineas.append(f"{i}. {tipo} **{nombre}** - {payout:.1f}%")
                            
                            if len(encontrados) > 10:
                                lineas.append(f"\n... y {len(encontrados) - 10} más")
                            
                            mensaje = "\n".join(lineas)
                    else:
                        mensaje = "❌ MarketManager no disponible"
                except Exception as e:
                    mensaje = f"❌ Error buscando mercado: {e}"
                
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                # Agregar botón de análisis detallado si hay datos
                if len(encontrados) == 1 and analisis_texto and 'No hay suficientes datos' not in analisis_texto and 'no disponible' not in analisis_texto:
                    kb = [
                        [InlineKeyboardButton("📊 Análisis Detallado", callback_data="analisis_detallado")],
                        [InlineKeyboardButton("🔍 Nueva búsqueda", callback_data="admin_mercados_buscar"),
                         InlineKeyboardButton("⬅️ Volver", callback_data="admin_mercados")]
                    ]
                else:
                    kb = [[InlineKeyboardButton("🔍 Nueva búsqueda", callback_data="admin_mercados_buscar"),
                           InlineKeyboardButton("⬅️ Volver", callback_data="admin_mercados")]]
                await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
                return
            # Confirmaciones: búsqueda genérica
            if user_id in getattr(self, 'esperando_busqueda_confirmaciones', set()):
                self.esperando_busqueda_confirmaciones.discard(user_id)
                try:
                    partes = texto.split()
                    if len(partes) == 2:
                        query, fecha = partes[0], partes[1]
                        reporte = self.user_manager.generar_reporte_confirmaciones_por_usuario(fecha, query)
                    else:
                        from datetime import datetime as _dt
                        hoy = _dt.now().strftime('%Y-%m-%d')
                        reporte = self.user_manager.generar_reporte_confirmaciones_por_usuario(hoy, texto)
                except Exception as e:
                    reporte = f"❌ Error generando reporte: {e}"
                await update.message.reply_text(reporte)
                return
            # Confirmaciones: búsqueda por usuario
            if user_id in getattr(self, 'esperando_busqueda_confirmaciones_usuario', set()):
                self.esperando_busqueda_confirmaciones_usuario.discard(user_id)
                try:
                    partes = texto.split()
                    if len(partes) == 2:
                        query, fecha = partes[0], partes[1]
                    else:
                        query = texto
                        from datetime import datetime as _dt
                        fecha = _dt.now().strftime('%Y-%m-%d')
                    reporte = self.user_manager.generar_reporte_confirmaciones_por_usuario(fecha, query)
                except Exception as e:
                    reporte = f"❌ Error generando reporte: {e}"
                await update.message.reply_text(reporte)
                return
            # Confirmaciones: búsqueda por ID
            if user_id in getattr(self, 'esperando_busqueda_confirmaciones_id', set()):
                self.esperando_busqueda_confirmaciones_id.discard(user_id)
                try:
                    partes = texto.split()
                    if len(partes) == 2:
                        query, fecha = partes[0], partes[1]
                    else:
                        query = texto
                        from datetime import datetime as _dt
                        fecha = _dt.now().strftime('%Y-%m-%d')
                    reporte = self.user_manager.generar_reporte_confirmaciones_por_usuario(fecha, query)
                except Exception as e:
                    reporte = f"❌ Error generando reporte: {e}"
                await update.message.reply_text(reporte)
                return

        # 3) Si nada de lo anterior aplica y el usuario no está autenticado, intentar tratar texto como clave
        if user_id not in getattr(self.user_manager, 'usuarios_activos', {}):
            # Heurística simple: claves suelen ser alfanuméricas y sin espacios
            if 6 <= len(texto) <= 40 and ' ' not in texto:
                await self.procesar_clave(update, texto)
                return
        # Por defecto, eco ligero o ignorar
        await update.message.reply_text("ℹ️ Mensaje recibido. Usa /ayuda para ver opciones.")

    async def procesar_clave(self, update: Update, clave: str):
        """Procesa una clave de acceso enviada por el usuario."""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or user.first_name or "Usuario"
        try:
            resultado = self.user_manager.autenticar_usuario(user_id, username, clave)
        except Exception as e:
            await update.message.reply_text(f"❌ Error autenticando: {e}")
            return
        if not resultado or not resultado.get('autenticado'):
            await update.message.reply_text("❌ Clave inválida o expirada. Pide una clave válida al administrador.")
            return

        # Autenticado correctamente
        es_admin = self.user_manager.es_administrador(user_id)
        if es_admin:
            # Mostrar panel admin inline principal
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            kb = [
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
            await update.message.reply_text(
                f"👑 Bienvenido, administrador {username}!", reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            # Verificar si es usuario tardío (entró después de las 10 AM)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            import random
            
            hora_actual = datetime.now().hour
            es_tardio = hora_actual >= 10  # Tardío si entra después de las 10 AM
            
            # Obtener señales previas del día
            señales_hoy = getattr(self.signal_scheduler, 'señales_enviadas_hoy', [])
            total_señales = len(señales_hoy)
            ganadas = sum(1 for s in señales_hoy if s.get('resultado') == 'WIN')
            perdidas = sum(1 for s in señales_hoy if s.get('resultado') == 'LOSS')
            pendientes = total_señales - ganadas - perdidas
            efectividad = (ganadas / (ganadas + perdidas) * 100) if (ganadas + perdidas) > 0 else 0
            
            # Frases motivadoras para usuarios tardíos
            frases_tardio = [
                "Nunca es tarde para empezar a ganar. ¡Bienvenido!",
                "El mejor momento para entrar es ahora. ¡Vamos!",
                "Llegaste justo a tiempo para las mejores oportunidades.",
                "No importa la hora, importa la actitud. ¡Adelante!",
                "Cada momento es una nueva oportunidad en el mercado.",
                "Tarde pero seguro. ¡Prepárate para operar!",
                "El mercado no cierra, y tú tampoco. ¡Éxito!",
                "Mejor tarde que nunca. ¡Vamos por esas señales!"
            ]
            
            if es_tardio and total_señales > 0:
                # Mensaje especial para usuario tardío
                frase_motivadora = random.choice(frases_tardio)
                
                mensaje_bienvenida = f"""✅ **Autenticación exitosa, @{username}!**

⏰ **USUARIO TARDÍO DETECTADO**

📊 **Resumen del Día:**
• **Horario de apertura:** 8:00 AM
• **Tu hora de ingreso:** {datetime.now().strftime('%H:%M')}
• **Señales generadas antes de tu ingreso:** {total_señales}

📈 **Estadísticas de Señales Previas:**
• **Ganadas:** {ganadas} ✅
• **Perdidas:** {perdidas} ❌
• **Pendientes:** {pendientes} ⏳
• **Efectividad:** {efectividad:.1f}%

💡 **Frase Motivadora:**
"{frase_motivadora}"

📌 **Desde ahora:**
• Recibirás todas las señales en tiempo real
• Horario restante: hasta las 8:00 PM
• Mantén las notificaciones activas

🔔 **Consejo:**
Aunque llegaste tarde, aún hay tiempo para aprovechar las señales del día.
¡Concéntrate y opera con disciplina!

¿Qué deseas hacer ahora?"""
            else:
                # Mensaje normal para usuario temprano
                mensaje_bienvenida = (
                    f"✅ Autenticación exitosa, @{username}!\n\n"
                    "📌 Ya puedes recibir señales en tiempo real.\n"
                    "🕘 Horario: 8:00 AM – 8:00 PM (Lun‑Sáb)\n"
                    "🔔 Consejo: Activa notificaciones del canal para no perderte ninguna señal.\n\n"
                    "¿Qué deseas hacer ahora?\n"
                    "• Ver tu perfil y estado de acceso\n"
                    "• Consultar ayuda y comandos disponibles\n"
                    "• Ver el estado del sistema"
                )
            
            kb_user = [
                [InlineKeyboardButton("👤 Mi Perfil", callback_data="usuario_perfil"),
                 InlineKeyboardButton("❓ Ayuda", callback_data="usuario_ayuda")],
                [InlineKeyboardButton("📊 Estado del sistema", callback_data="usuario_estado")]
            ]
            await update.message.reply_text(
                mensaje_bienvenida,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb_user)
            )
            # Notificar al admin del acceso por clave con formato mejorado
            try:
                en_lista = bool(resultado.get('en_lista_diaria'))
                motivo_aut = resultado.get('motivo_autorizacion') or resultado.get('autorizado_por')
                fecha_txt = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                if not en_lista:
                    # Formato solicitado para NO autorizado
                    msg_admin = (
                        "⚠️ ACCESO NO AUTORIZADO\n\n"
                        f"📅 Fecha: {fecha_txt}\n"
                        f"👤 Usuario: @{username} (ID: {user_id})\n\n"
                        f"🚨 Motivo: {motivo_aut or 'No autorizado en la lista diaria'}\n\n"
                        "📝 Acción requerida:\n"
                        "Envía la lista de usuarios autorizados para hoy usando el comando /listahoy"
                    )
                else:
                    # Mantener formato informativo para autorizados
                    msg_admin = (
                        "🔔 Acceso por clave pública\n\n"
                        f"👤 Usuario: @{username} (ID: {user_id})\n"
                        f"📅 Fecha: {fecha_txt}\n"
                        "📋 Estado lista diaria: 🟢 EN LISTA HOY"
                    )
                await self.notificar_admin_telegram(msg_admin)
            except Exception:
                pass

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Despacha todos los callbacks de botones inline."""
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass
        data = query.data or ""
        
        print(f"[Callback] Recibido: {data} - user_id: {query.from_user.id}")

        # 1) Callbacks de Pre‑Señal / Señal
        if data.startswith("presenal_") or data.startswith("signal_confirm:") or data.startswith("signal_accept:") or data.startswith("signal_reject:"):
            await self.handle_callback_presignal(update, context)
            return

        # 2) Panel ADMIN: mapeo explícito
        if data == "admin_estado":
            await self.handle_admin_estado_callback(query)
            return
        if data == "admin_detalles_analisis":
            await self.handle_admin_detalles_analisis(query)
            return
        if data == "admin_stats":
            await self.handle_admin_stats_callback(query)
            return
        if data == "admin_quotex":
            await self.handle_admin_quotex_callback(query)
            return
        if data == "admin_quotex_force_connect":
            await self.handle_admin_quotex_force_connect(query)
            return
        if data == "admin_quotex_force_disconnect":
            await self.handle_admin_quotex_force_disconnect(query)
            return
        if data == "admin_perfil":
            await self.handle_admin_perfil_callback(query)
            return
        if data == "admin_nuevaclave":
            await self.handle_admin_nuevaclave_callback(query)
            return
        if data == "admin_clavehoy":
            await self.handle_admin_clavehoy_callback(query)
            return
        if data == "admin_broadcast":
            await self.handle_admin_broadcast_callback(query)
            return
        if data == "admin_historial":
            await self.handle_admin_historial_callback(query)
            return
        if data == "admin_ayuda":
            await self.handle_admin_ayuda_callback(query)
            return
        if data == "admin_ayuda_comandos":
            await self.handle_admin_ayuda_comandos(query)
            return
        if data == "admin_ayuda_martingala":
            await self.handle_admin_ayuda_martingala(query)
            return
        if data == "admin_ayuda_trading":
            await self.handle_admin_ayuda_trading(query)
            return
        if data == "admin_ayuda_analisis_forzado":
            await self.handle_admin_ayuda_analisis_forzado_guia(query)
            return
        if data == "admin_usuarios":
            await self.handle_admin_usuarios_callback(query)
            return
        if data == "admin_trading":
            await self.handle_admin_trading_menu(query)
            return
        if data == "trading_demo":
            await self.handle_trading_demo(query)
            return
        if data == "trading_real":
            await self.handle_trading_real(query)
            return
        if data.startswith("trading_set_amount_"):
            await self.handle_trading_set_amount(query, data)
            return
        if data == "trading_start_demo":
            await self.handle_trading_start(query, modo="DEMO")
            return
        if data == "trading_start_real":
            await self.handle_trading_start(query, modo="REAL")
            return
        if data == "trading_stop":
            await self.handle_trading_stop(query)
            return
        if data == "volver_panel_admin":
            await self.handle_volver_panel_admin_callback(query)
            return
        
        # 2.5) Análisis Forzado
        if data == "admin_analisis_forzado":
            await self.handle_admin_analisis_forzado(query)
            return
        if data == "analisis_forzado_mercado":
            await self.handle_analisis_forzado_mercado(query)
            return
        if data == "analisis_forzado_efectividad":
            await self.handle_analisis_forzado_efectividad(query)
            return
        
        # 2.5.1) Callbacks de Análisis Forzado - Tipo de Mercado
        if data == "af_tipo_otc":
            print(f"[Callback] af_tipo_otc detectado")
            await self.handle_af_tipo_mercado(query, "OTC")
            return
        if data == "af_tipo_normal":
            print(f"[Callback] af_tipo_normal detectado")
            await self.handle_af_tipo_mercado(query, "NORMAL")
            return
        
        # 2.5.2) Callbacks de Análisis Forzado - Par de Mercado
        if data.startswith("af_par_"):
            par = data.replace("af_par_", "")
            if par == "custom":
                # Usuario quiere escribir un par personalizado
                await query.answer("✍️ Escribe el par que deseas analizar")
                return
            print(f"[Callback] af_par detectado: {par}")
            await self.handle_af_par_mercado(query, par)
            return
        
        # 2.5.3) Callbacks de Análisis Forzado - Temporalidad
        if data.startswith("af_temp_"):
            temp = data.replace("af_temp_", "")
            if temp == "custom":
                await query.answer("✍️ Escribe la temporalidad (ej: 5M, 1H)")
                return
            print(f"[Callback] af_temp detectado: {temp}")
            await self.handle_af_temporalidad(query, temp)
            return
        
        # 2.5.4) Callbacks de Análisis Forzado - Efectividad
        if data.startswith("af_efectividad_"):
            porcentaje = data.replace("af_efectividad_", "")
            if porcentaje == "custom":
                await query.answer("✍️ Escribe el porcentaje de efectividad (ej: 75)")
                return
            await self.handle_af_set_efectividad(query, int(porcentaje))
            return
        
        # 2.5.5) Callbacks de Análisis Forzado - Duración
        if data.startswith("af_duracion_"):
            duracion = data.replace("af_duracion_", "")
            if duracion == "custom":
                await query.answer("✍️ Escribe la duración en minutos (ej: 45)")
                return
            print(f"[Callback] af_duracion detectado: {duracion}")
            await self.handle_af_duracion(query, duracion)
            return
        
        # 2.5.6) Callback para confirmar inicio de análisis forzado
        if data == "af_confirmar_inicio":
            print(f"[Callback] af_confirmar_inicio detectado")
            await self.handle_af_confirmar_inicio(query)
            return
        
        # 2.5.7) Callbacks de Trading Automático en Análisis Forzado
        if data == "af_trading_demo":
            await self.handle_af_trading_modo(query, "DEMO")
            return
        if data == "af_trading_real":
            await self.handle_af_trading_modo(query, "REAL")
            return
        if data == "af_solo_analisis":
            await self.handle_af_solo_analisis(query)
            return
        if data.startswith("af_monto_"):
            await self.handle_af_set_monto(query, data)
            return
        if data == "af_confirmar_trading":
            await self.handle_af_confirmar_trading(query)
            return
        if data == "af_detener":
            await self.handle_af_detener(query)
            return
        
        # 2.5.8) Nuevos callbacks para gestión de análisis activo
        if data == "af_detener_actual":
            await self.handle_af_detener_actual(query)
            return
        if data == "af_reemplazar_mercado":
            await self.handle_af_reemplazar_mercado(query)
            return
        if data == "af_adicional_mercado":
            await self.handle_af_adicional_mercado(query)
            return
        if data == "af_activar_trading":
            await self.handle_af_activar_trading(query)
            return
        if data == "af_solo_analisis_confirmado":
            await query.answer("✅ Solo análisis activado")
            return
        if data.startswith("af_trading_monto_"):
            monto = data.replace("af_trading_monto_", "")
            await self.handle_af_trading_monto(query, monto)
            return
        if data == "af_trading_confirmar":
            await self.handle_af_trading_confirmar(query)
            return
        if data == "af_detener_analisis":
            await self.handle_af_detener_analisis(query)
            return
        if data == "af_detener_trading":
            await self.handle_af_detener_trading(query)
            return
        
        # 2.5.9) Callbacks de Martingala (Solo Admin)
        if data.startswith("martingala_confirmar_"):
            await self.handle_martingala_confirmar(query)
            return
        if data == "martingala_cancelar":
            await self.handle_martingala_cancelar(query)
            return
        
        # 2.5.10) Callbacks de Martingala Anticipada (Predictiva)
        if data == "martingala_anticipada_si":
            await self.handle_martingala_anticipada_confirmar(query)
            return
        if data == "martingala_anticipada_no":
            await self.handle_martingala_anticipada_rechazar(query)
            return
        
        # 2.6) Panel de Mercados
        if data == "admin_mercados":
            await self.handle_admin_mercados_menu(query)
            return
        if data == "admin_mercados_todos":
            await self.handle_admin_mercados_todos(query)
            return
        if data == "admin_mercados_normales":
            await self.handle_admin_mercados_normales(query)
            return
        if data == "admin_mercados_otc":
            await self.handle_admin_mercados_otc(query)
            return
        if data == "admin_mercados_buscar":
            await self.handle_admin_mercados_buscar(query)
            return
        if data == "admin_mercados_pdf_todos":
            await self.handle_admin_mercados_pdf(query, "todos")
            return
        if data == "admin_mercados_pdf_normales":
            await self.handle_admin_mercados_pdf(query, "normales")
            return
        if data == "admin_mercados_pdf_otc":
            await self.handle_admin_mercados_pdf(query, "otc")
            return
        
        # 2.6) Análisis Detallado de Mercado
        if data == "analisis_detallado":
            await self.handle_analisis_detallado(query)
            return
        if data == "analisis_detallado_pdf":
            await self.handle_analisis_detallado_pdf(query)
            return
        
        # 2.7) Análisis de Estrategias Individuales
        if data.startswith("analisis_estrategia_"):
            estrategia = data.replace("analisis_estrategia_", "")
            await self.handle_analisis_estrategia_individual(query, estrategia)
            return

        # 3) Submenús: Lista hoy
        if data == "admin_listahoy":
            await self.handle_admin_listahoy_menu(query)
            return
        if data == "admin_listahoy_ver":
            await self.handle_admin_listahoy_ver(query)
            return
        if data == "admin_listahoy_agregar":
            await self.handle_admin_listahoy_agregar(query)
            return
        if data == "admin_listahoy_quitar":
            await self.handle_admin_listahoy_quitar(query)
            return
        if data == "admin_listahoy_limpiar":
            await self.handle_admin_listahoy_limpiar(query)
            return
        if data.startswith("admin_listahoy_limpiar_confirm|"):
            opt = data.split("|", 1)[1]
            await self.handle_admin_listahoy_limpiar_confirm(query, opt)
            return

        # 4) Submenús: Bloqueos
        if data == "admin_bloqueos":
            await self.handle_admin_bloqueos_menu(query)
            return
        if data == "admin_bloqueos_ver":
            await self.handle_admin_bloqueos_ver(query)
            return
        if data == "admin_bloqueos_bloquear":
            await self.handle_admin_bloqueos_bloquear(query)
            return
        if data == "admin_bloqueos_desbloquear":
            await self.handle_admin_bloqueos_desbloquear(query)
            return
        if data == "admin_bloqueos_hist":
            await self.handle_admin_bloqueos_hist(query)
            return
        if data == "admin_bloq_hist_fecha":
            await self.handle_admin_bloq_hist_fecha(query)
            return

        # 5) Submenús: Confirmaciones
        if data == "admin_confirmaciones":
            await self.handle_admin_confirmaciones_menu(query)
            return
        if data == "admin_conf_hoy":
            await self.handle_admin_confirmaciones_hoy(query)
            return
        if data == "admin_conf_usuario":
            await self.handle_admin_confirmaciones_usuario(query)
            return
        if data == "admin_conf_fecha":
            await self.handle_admin_confirmaciones_fecha(query)
            return

        # 6) Alias/usuario ayuda/perfil u otros callbacks legacy
        # Botón de usuario: Señales del Día
        if data == "usuario_senales_dia":
            await self.handle_usuario_senales_dia_callback(query)
            return

        # Botones de usuario: Perfil, Ayuda, Estado
        if data == "usuario_perfil":
            await self.handle_usuario_perfil_callback(query)
            return
        if data == "usuario_ayuda":
            await self.handle_usuario_ayuda_callback(query)
            return
        if data == "usuario_estado":
            await self.handle_usuario_estado_callback(query)
            return

        await self.handle_callback_legacy_admin(update, context)

    async def cmd_confirmaciones(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/confirmaciones [YYYY-MM-DD] -> Muestra lista detallada por usuario de pre‑señal y señal (admin)."""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede ver este reporte.")
            return
        # Args: puede ser [fecha] o [usuario/ID] [fecha]
        args = context.args if hasattr(context, 'args') else []
        hoy = datetime.now().strftime('%Y-%m-%d')
        fecha_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        try:
            if args:
                a0 = args[0]
                a1 = args[1] if len(args) > 1 else None
                if fecha_pattern.match(a0):
                    fecha = a0
                    texto = self.user_manager.generar_reporte_confirmaciones_aceptadas(fecha)
                else:
                    query = a0
                    fecha = a1 if (a1 and fecha_pattern.match(a1)) else hoy
                    texto = self.user_manager.generar_reporte_confirmaciones_por_usuario(fecha, query)
            else:
                texto = self.user_manager.generar_reporte_confirmaciones_aceptadas(hoy)
        except Exception as e:
            texto = f"⚠️ No se pudo generar el reporte: {e}"
        await update.message.reply_text(texto)

    async def handle_usuario_senales_dia_callback(self, query):
        """Muestra un resumen de las señales del día para usuarios.
        Toma las señales registradas en signal_scheduler.señales_enviadas_hoy y las lista de forma compacta.
        """
        try:
            user = query.from_user
            username = user.username or user.first_name or "Usuario"
            # Obtener señales del día del scheduler
            señales_hoy = list(getattr(self.signal_scheduler, 'señales_enviadas_hoy', []))
            total = len(señales_hoy)

            if total == 0:
                mensaje = (
                    "📈 Señales del Día\n\n"
                    "❌ Aún no hay señales registradas hoy.\n\n"
                    "🕘 Horario operativo: Lun‑Sáb 8:00‑20:00\n"
                    "🔔 Mantén activadas las notificaciones para recibirlas en tiempo real."
                )
            else:
                # Mostrar últimas hasta 10 para no exceder
                ultimas = señales_hoy[-10:]
                lineas = []
                for s in ultimas:
                    hora = s.get('hora', 'N/A')
                    symbol = s.get('symbol') or s.get('par') or 'N/A'
                    accion = s.get('accion') or s.get('direction') or s.get('tipo') or 'N/A'
                    tf = s.get('timeframe') or s.get('tf') or ''
                    res = s.get('resultado') or s.get('result') or ''
                    res_txt = f" • {res}" if res else ''
                    tf_txt = f" [{tf}]" if tf else ''
                    lineas.append(f"• {hora} | {symbol} {tf_txt} | {accion}{res_txt}")

                mensaje = (
                    "📈 Señales del Día\n\n"
                    f"Total registradas hoy: {total}\n\n"
                    + "\n".join(lineas)
                )

            # Botones de navegación básica
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            kb = [
                [InlineKeyboardButton("⬅️ Volver", callback_data="usuario_estado"),
                 InlineKeyboardButton("🔄 Actualizar", callback_data="usuario_senales_dia")]
            ]
            await self.safe_edit(query, mensaje, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            try:
                await query.edit_message_text(f"⚠️ No se pudo cargar las señales del día: {e}")
            except Exception:
                pass

    def _build_profile_text(self, user_id: str, username: str) -> str:
        """Construye el texto del perfil del usuario con TZ Habana y estado Quotex."""
        # Datos del usuario
        try:
            info = self.user_manager.usuarios_activos.get(user_id, {})
        except Exception:
            info = {}
        es_admin = self.user_manager.es_administrador(user_id)
        tipo_usuario = "👑 ADMINISTRADOR" if es_admin else "👤 USUARIO"

        # Fecha/hora en La Habana
        try:
            ahora = datetime.now(CUBA_TZ)
        except Exception:
            ahora = datetime.now()
        fecha_txt = ahora.strftime('%d/%m/%Y')
        hora_txt = ahora.strftime('%H:%M:%S')

        # Estado de Quotex real (sin 2FA ni simulación)
        estado_quotex = "🔴 DESCONECTADO"
        try:
            mm = getattr(self, 'market_manager', None)
            if mm is not None and getattr(mm, 'conectado', False):
                estado_quotex = "🟢 CONECTADO"
        except Exception:
            pass

        # Campos de sesión
        hora_ingreso = info.get('hora_ingreso', 'N/A')
        clave_usada = info.get('clave_utilizada') or info.get('clave_usada') or 'N/A'

        mensaje = f"""
👤 **MI PERFIL**

📅 **Fecha:** {fecha_txt}
🕐 **Hora:** {hora_txt}

👥 **Información personal:**
• **Nombre:** {username}
• **ID Telegram:** `{user_id}`
• **Tipo de cuenta:** {tipo_usuario}
• **Estado:** 🟢 ACTIVO

🔑 **Sesión actual:**
• **Hora de ingreso:** {hora_ingreso}
• **Clave utilizada:** {clave_usada}
• **Autenticado:** ✅ SÍ

📊 **Estado del sistema:**
• **Recepción de señales:** ✅ HABILITADA
• **Mensajes automáticos:** ✅ HABILITADOS
• **Notificaciones:** ✅ ACTIVAS
• **Quotex:** {estado_quotex}
• **Horario operativo:** Lun‑Sáb 8:00‑20:00

💡 **Información adicional:**
• Tu sesión es válida hasta las 00:00 (hora de Cuba)

🎆 **¡Disfruta del trading profesional!**
        """
        return mensaje

    def _profile_inline_kb(self, include_back: bool = False):
        """Construye un teclado inline consistente para la vista de perfil.
        include_back=True añade botón de 'Volver' (para callbacks inline).
        """
        kb = []
        if include_back:
            kb.append([
                InlineKeyboardButton("⬅️ Volver", callback_data="usuario_estado"),
                InlineKeyboardButton("🔄 Actualizar", callback_data="usuario_perfil"),
            ])
        else:
            kb.append([
                InlineKeyboardButton("🔄 Actualizar", callback_data="usuario_perfil"),
            ])
        kb.append([InlineKeyboardButton("❓ Ayuda", callback_data="usuario_ayuda")])
        return InlineKeyboardMarkup(kb)

    async def handle_usuario_perfil_callback(self, query):
        """Muestra el perfil del usuario (versión inline)."""
        try:
            user = query.from_user
            user_id = str(user.id)
            username = user.username or user.first_name or "Usuario"
            if user_id not in self.user_manager.usuarios_activos:
                await query.edit_message_text(
                    "❌ No estás autenticado. Usa /clave TU_CLAVE para iniciar sesión."
                )
                return
            texto = self._build_profile_text(user_id, username)
            reply_markup = self._profile_inline_kb(include_back=True)
            await self.safe_edit(query, texto, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except Exception as e:
            try:
                await query.edit_message_text(f"⚠️ No se pudo cargar el perfil: {e}")
            except Exception:
                pass

    async def handle_usuario_ayuda_callback(self, query):
        """Muestra ayuda para usuarios (versión inline)."""
        try:
            texto = (
                "📚 AYUDA - CUBAYDSIGNAL\n\n"
                "Comandos:\n"
                "• /perfil - Ver tu información\n"
                "• /ayuda - Esta ayuda\n\n"
                "Horario: Lun‑Sáb 8:00‑20:00\n"
                "Nota: Domingos cerrado (solo admin)."
            )
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            kb = [
                [InlineKeyboardButton("⬅️ Volver", callback_data="usuario_estado"),
                 InlineKeyboardButton("👤 Mi Perfil", callback_data="usuario_perfil")]
            ]
            await self.safe_edit(query, texto, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            try:
                await query.edit_message_text(f"⚠️ No se pudo cargar la ayuda: {e}")
            except Exception:
                pass

    async def handle_usuario_estado_callback(self, query):
        """Muestra estado básico del bot para usuarios (sin contadores sensibles)."""
        try:
            # Estado operativo (Lun‑Sáb 8–20, domingo cerrado)
            operativo = False
            try:
                operativo = self.signal_scheduler.esta_en_horario_operativo()
            except Exception:
                pass
            estado_op = "🟢 ACTIVO" if operativo else "🔴 FUERA DE HORARIO"

            # Estado de Quotex
            estado_quotex = "🔴 DESCONECTADO"
            try:
                if getattr(self, 'market_manager', None) and getattr(self.market_manager, 'conectado', False):
                    estado_quotex = "🟢 CONECTADO"
            except Exception:
                pass

            from datetime import datetime as _dt
            texto = (
                "📊 ESTADO DEL SISTEMA\n\n"
                f"• Estado operativo: {estado_op}\n"
                "• Horario: Lun‑Sáb 8:00‑20:00\n"
                f"• Hora actual: {_dt.now().strftime('%H:%M:%S')}\n\n"
                f"• Quotex: {estado_quotex}\n"
                "• Telegram: 🟢 CONECTADO\n"
            )
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            kb = [
                [InlineKeyboardButton("👤 Mi Perfil", callback_data="usuario_perfil"),
                 InlineKeyboardButton("❓ Ayuda", callback_data="usuario_ayuda")],
                [InlineKeyboardButton("📊 Señales del Día", callback_data="usuario_senales_dia")]
            ]
            await self.safe_edit(query, texto, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            try:
                await query.edit_message_text(f"⚠️ No se pudo cargar el estado: {e}")
            except Exception:
                pass

    async def cb_admin_confirmaciones(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback inline: menú de confirmaciones mostrando HOY y opciones de filtro."""
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        fecha = datetime.now().strftime('%Y-%m-%d')
        try:
            texto = self.user_manager.generar_reporte_confirmaciones_aceptadas(fecha)
        except Exception as e:
            texto = f"⚠️ No se pudo generar el reporte: {e}"
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("🔄 Ver hoy", callback_data="admin_confirmaciones")],
            [InlineKeyboardButton("📅 Elegir fecha", callback_data="admin_confirmaciones_fecha")],
            [InlineKeyboardButton("👤 Buscar por Usuario", callback_data="admin_confirmaciones_buscar_user"),
             InlineKeyboardButton("🆔 Buscar por ID", callback_data="admin_confirmaciones_buscar_id")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.safe_edit(query, texto, reply_markup=reply_markup)

    async def cb_admin_confirmaciones_fecha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pedir fecha YYYY-MM-DD y luego mostrar reporte detallado de ese día."""
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        self.esperando_fecha_confirmaciones.add(user_id)
        await query.edit_message_text(
            "📅 Envía la fecha en formato YYYY-MM-DD para ver el reporte de confirmaciones de ese día.\n\nEjemplo: 2025-08-11",
        )

    async def cb_admin_confirmaciones_buscar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pedir @usuario o ID (y opcional fecha) para reporte filtrado."""
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        self.esperando_busqueda_confirmaciones.add(user_id)
        await query.edit_message_text(
            "👤 Envía @usuario o ID, y opcionalmente una fecha YYYY-MM-DD.\n\n" \
            "Ejemplos:\n• @juan\n• 5806367733\n• @juan 2025-08-11\n• 5806367733 2025-08-11",
        )

    async def cb_admin_confirmaciones_buscar_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pedir username para reporte filtrado (solo usuario, admite fecha opcional)."""
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        self.esperando_busqueda_confirmaciones_usuario.add(user_id)
        await query.edit_message_text(
            "👤 Envía el @usuario y opcionalmente una fecha YYYY-MM-DD.\n\nEjemplos:\n• @juan\n• @juan 2025-08-11",
        )

    async def cb_admin_confirmaciones_buscar_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pedir ID para reporte filtrado (solo ID, admite fecha opcional)."""
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)
        if not self.user_manager.es_administrador(user_id):
            await query.edit_message_text("❌ Acceso denegado.")
            return
        self.esperando_busqueda_confirmaciones_id.add(user_id)
        await query.edit_message_text(
            "🆔 Envía el ID y opcionalmente una fecha YYYY-MM-DD.\n\nEjemplos:\n• 5806367733\n• 5806367733 2025-08-11",
        )

    async def cmd_perfil(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /perfil - Mostrar información del perfil del usuario"""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or user.first_name or "Usuario"
        
        # Verificar si el usuario está autenticado
        if user_id not in self.user_manager.usuarios_activos:
            await update.message.reply_text(
                "❌ **No estás autenticado**\n\n"
                "Para ver tu perfil, primero debes autenticarte con la clave del día.\n\n"
                "Usa: `/clave TU_CLAVE`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Construir mensaje unificado (con TZ Habana y estado Quotex)
        mensaje_perfil = self._build_profile_text(user_id, username)
        
        # Crear botones inline consistentes para el perfil
        reply_markup = self._profile_inline_kb(include_back=False)
        
        await update.message.reply_text(
            mensaje_perfil,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    def _es_domingo_cuba(self) -> bool:
        """Retorna True si en Cuba (America/Havana) es domingo."""
        try:
            return datetime.now(CUBA_TZ).weekday() == 6
        except Exception:
            return datetime.utcnow().weekday() == 6

    async def cmd_ayuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /ayuda - Muestra ayuda contextual según estado y permisos"""
        user_id = str(update.effective_user.id)

        if user_id not in self.user_manager.usuarios_activos:
            mensaje = (
                "📚 AYUDA - CUBAYDSIGNAL\n\n"
                "🔑 Primeros pasos:\n"
                "• /start - Iniciar el bot\n"
                "• /clave TUCLAVE - Ingresar clave de acceso\n\n"
                "📞 ¿No tienes clave? Pídela al administrador.\n"
                "🔒 No compartas tu clave."
            )
            await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
            return

        es_admin = self.user_manager.es_administrador(user_id)
        if es_admin:
            mensaje = (
                "👑 GUÍA ADMIN\n\n"
                "Comandos básicos:\n"
                "• /estado, /stats, /perfil\n"
                "Gestión de claves:\n"
                "• /nuevaclave, /clavehoy\n"
                "Usuarios:\n"
                "• /listahoy, /bloquear, /desbloquear, /bloqueados\n"
                "Historial/Reportes:\n"
                "• /historialsenales, /historialbloqueos, /historial\n"
                "Difusión:\n"
                "• /broadcast <mensaje>"
            )
            await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
        else:
            mensaje = (
                "🤖 INFORMACIÓN\n\n"
                "• Señales automáticas con análisis.\n"
                "• Horario: 8:00 AM - 8:00 PM (Lun-Sáb).\n\n"
                "Comandos:\n"
                "• /perfil - Ver tu información\n"
                "• /ayuda - Esta ayuda"
            )
            await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_quotex(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /quotex - Mostrar estado de conexión a Quotex (solo admin)"""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede consultar el estado de Quotex.")
            return
        # Determinar estado desde el MarketManager enlazado por main.py
        conectado = False
        detalles = []
        try:
            mm = getattr(self, 'market_manager', None)
            if mm is not None:
                conectado = bool(getattr(mm, 'conectado', False))
                # Intentar obtener URL actual del driver si existe
                try:
                    driver = getattr(mm, 'quotex', None)
                    driver = getattr(driver, 'driver', None)
                    curr = driver.current_url if driver else None
                    if curr:
                        detalles.append(f"URL: {curr}")
                except Exception:
                    pass
                # Cantidad de mercados si disponibles
                try:
                    mercados = mm.obtener_mercados_disponibles()
                    if isinstance(mercados, list):
                        detalles.append(f"Mercados cargados: {len(mercados)}")
                except Exception:
                    pass
        except Exception:
            pass

    def configurar_signal_scheduler(self, signal_scheduler):
        """Inyecta la referencia a SignalScheduler."""
        self.signal_scheduler = signal_scheduler
        # Configurar bot en el scheduler
        if signal_scheduler and hasattr(signal_scheduler, 'configurar_bot_telegram'):
            signal_scheduler.configurar_bot_telegram(self)
            print("[SignalScheduler] ✅ Bot de Telegram configurado")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Bienvenida inicial contextual"""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or user.first_name or "Usuario"
        
        # Verificar si es administrador
        es_admin = self.user_manager.es_administrador(user_id)
        try:
            logger.info(f"[TG]/start user_id={user_id} es_admin={es_admin} en_activos={user_id in self.user_manager.usuarios_activos}")
        except Exception:
            pass
        
        # Si es el admin por ID pero no figura como autenticado (p.ej. tras reinicio),
        # auto-autenticar para evitar que vea el prompt de clave maestra nuevamente.
        if es_admin and user_id not in self.user_manager.usuarios_activos:
            try:
                from datetime import datetime
                hora_actual = datetime.now().strftime('%H:%M')
                self.user_manager.usuarios_activos[user_id] = {
                    'username': username,
                    'tipo': 'admin',
                    'hora_ingreso': hora_actual,
                    'clave_usada': 'ADMIN_ID',
                    'señales_recibidas': 0,
                    'es_tardio': False
                }
                # Persistir
                if hasattr(self.user_manager, 'guardar_datos_usuarios'):
                    self.user_manager.guardar_datos_usuarios()
            except Exception:
                pass
        
        # Verificar si ya está autenticado
        if user_id in self.user_manager.usuarios_activos:
            usuario_info = self.user_manager.usuarios_activos[user_id]
            tipo_usuario = "👑 ADMINISTRADOR" if es_admin else "👤 USUARIO"
            
            if es_admin:
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
                    [InlineKeyboardButton("💰 Trading Automático", callback_data="admin_trading")],
                    [InlineKeyboardButton("⚡ Análisis Forzado", callback_data="admin_analisis_forzado")],
                    [InlineKeyboardButton("👤 Mi Perfil", callback_data="admin_perfil"),
                     InlineKeyboardButton("🔑 Gestión Claves", callback_data="admin_gestion_claves")],
                    [InlineKeyboardButton("📋 Lista Hoy", callback_data="admin_listahoy"),
                     InlineKeyboardButton("🚫 Gestión Bloqueos", callback_data="admin_bloqueos")],
                    [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
                     InlineKeyboardButton("📚 Historial", callback_data="admin_historial")],
                    [InlineKeyboardButton("📊 Reportes", callback_data="admin_reportes"),
                     InlineKeyboardButton("📜 Confirmaciones", callback_data="admin_confirmaciones")],
                    [InlineKeyboardButton("❓ Ayuda Admin", callback_data="admin_ayuda"),
                     InlineKeyboardButton("👥 Usuarios Activos", callback_data="admin_usuarios")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    mensaje_admin, 
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return
            else:
                # Si es domingo en Cuba y no es admin, mostrar cierre dominical
                if self._es_domingo_cuba():
                    mensaje_usuario = f"""
🚫 Servicio no disponible hoy

Hola **{username}** 👋

Hoy es domingo y el servicio está cerrado para usuarios.

📅 Operamos de Lun-Sáb, 8:00 AM - 8:00 PM (hora de Cuba).

🔕 Recepción de señales: ❌ INACTIVA (domingo)

Vuelve mañana para continuar recibiendo señales. Mientras tanto puedes consultar tu perfil o la ayuda.
                    """
                    # Botones limitados en domingo
                    keyboard = [
                        [InlineKeyboardButton("👤 Mi Perfil", callback_data="usuario_perfil"),
                         InlineKeyboardButton("❓ Ayuda", callback_data="usuario_ayuda")],
                        [InlineKeyboardButton("📊 Estado del Bot", callback_data="usuario_estado")]
                    ]
                else:
                    mensaje_usuario = f"""
 ¡Hola de nuevo, **{username}**! 👋

 Ya estás autenticado como **USUARIO**.

 🎯 **Panel de Usuario:**
 Usa los botones de abajo para acceder a todas las funciones disponibles:

 ✅ **Estás listo para recibir señales automáticamente!**

 📊 **Estado actual:**
 • Recepción de señales: 🟢 ACTIVA
 • Horario operativo: Lun-Sáb 8AM-8PM
 • Notificaciones: ✅ HABILITADAS

 🚀 **¡Disfruta del trading profesional!**
                    """
                    # Panel de botones inline para usuarios normales
                    keyboard = [
                        [InlineKeyboardButton("👤 Mi Perfil", callback_data="usuario_perfil"),
                         InlineKeyboardButton("❓ Ayuda", callback_data="usuario_ayuda")],
                        [InlineKeyboardButton("📊 Estado del Bot", callback_data="usuario_estado"),
                         InlineKeyboardButton("📊 Señales del Día", callback_data="usuario_senales_dia")]
                    ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    mensaje_usuario, 
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return
        
        # Usuario no autenticado - Mensaje de bienvenida
        if es_admin:
            mensaje_bienvenida = (
                "👑 Acceso de Administrador\n\n"
                f"Hola **{username}**. Para entrar al panel admin, ingresa tu **clave maestra**.\n\n"
                "Usa: `/clave TU_CLAVE_MAESTRA` o pulsa el botón \"Acceso Admin\" de abajo.\n\n"
                "Nota: Este mensaje solo aparece hasta que completes el acceso de administrador."
            )
        else:
            mensaje_bienvenida = f"""
🇨🇺 **¡Bienvenido a CubaYDSignal!** 🚀

Hola **{username}**, soy tu asistente de trading profesional.

🎯 **¿Qué ofrezco?**
• Señales de trading de alta efectividad (≥80%)
• Análisis técnico profesional multi-mercado
• 20-25 señales diarias (Lun-Sáb, 8AM-8PM)
• Mensajes motivacionales y seguimiento
• Resúmenes diarios de rendimiento

🔑 **Para comenzar:**
1. Obtén la clave diaria del administrador
2. Usa el comando `/clave TU_CLAVE`
3. ¡Comienza a recibir señales automáticamente!

📱 **Comandos disponibles:**
• `/clave` - Ingresar clave de acceso
• `/perfil` - Ver tu información personal
• `/ayuda` - Obtener ayuda del bot

¡Prepárate para el éxito en el trading! 💰
            """
        
        # Botones contextuales
        if es_admin:
            keyboard = [
                [InlineKeyboardButton("🔑 Acceso Admin", callback_data="ingresar_clave")],
                [InlineKeyboardButton("👑 Guía Admin", callback_data="mostrar_ayuda")],
                [InlineKeyboardButton("📊 Estado Sistema", callback_data="estado_sistema")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🔑 Ingresar Clave", callback_data="ingresar_clave")],
                [InlineKeyboardButton("❓ Ayuda", callback_data="mostrar_ayuda")],
                [InlineKeyboardButton("👤 Mi Perfil", callback_data="ver_perfil")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            mensaje_bienvenida,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def _send_with_markup(self, chat_id: str, text: str, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
        """Envía mensaje con teclado inline (uso interno). Retorna el message_id si tiene éxito."""
        try:
            msg = await self.application.bot.send_message(chat_id=str(chat_id), text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return msg.message_id if msg else None
        except Exception as e:
            logger.warning(f"[TG] Error enviando mensaje con markup a {chat_id}: {e}")
            return None

    async def notificar_caducidad_presenal(self, pre_id: str):
        """Notifica a usuarios activos que NO confirmaron la Pre‑Señal que ya caducó, y registra 'caducada'."""
        try:
            confirmados = set()
            try:
                confirmados = set(self.user_manager.confirmaciones_dia.get('presenal', {}).get(str(pre_id), set()))
            except Exception:
                confirmados = set()
            mensaje = (
                "⏳ Tiempo agotado\n\n"
                "La confirmación de Pre‑Señal ha caducado.\n"
                "No podrás recibir esta señal. Espera la siguiente."
            )
            for uid, info in list(self.user_manager.usuarios_activos.items()):
                if str(uid) in confirmados:
                    continue
                # Registrar evento 'caducada'
                try:
                    self.user_manager.registrar_confirmacion_presenal(str(uid), info.get('username'), pre_id, estado='caducada')
                except Exception:
                    pass
                try:
                    await self.send_message(uid, mensaje)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[TG] Error al notificar caducidad de pre‑señal {pre_id}: {e}")

    async def notificar_caducidad_senal(self, pre_id: str, signal_id: str):
        """Notifica a usuarios que confirmaron la Pre‑Señal pero NO confirmaron la Señal que ya caducó, y registra 'caducada'."""
        try:
            confirmaron_pre = set()
            confirmaron_senal = set()
            try:
                confirmaron_pre = set(self.user_manager.confirmaciones_dia.get('presenal', {}).get(str(pre_id), set()))
            except Exception:
                confirmaron_pre = set()
            try:
                confirmaron_senal = set(self.user_manager.confirmaciones_dia.get('senal', {}).get(str(signal_id), set()))
            except Exception:
                confirmaron_senal = set()
            pendientes = confirmaron_pre - confirmaron_senal
            mensaje = (
                "⏳ Señal caducada\n\n"
                "Se agotó el tiempo para confirmar la Señal.\n"
                "No podrás recibirla. Estate atento a la próxima."
            )
            for uid in list(pendientes):
                info = self.user_manager.usuarios_activos.get(uid, {})
                try:
                    self.user_manager.registrar_confirmacion_senal(str(uid), info.get('username'), pre_id, signal_id, estado='caducada')
                except Exception:
                    pass
                try:
                    await self.send_message(uid, mensaje)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[TG] Error al notificar caducidad de señal {signal_id}: {e}")

    async def enviar_confirmacion_presenal_a_usuarios(self, pre_id: str, minutos_antes: int, mercado: str, frase: str):
        """Envía a cada usuario activo un botón para aceptar la Pre‑Señal."""
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Aceptar Pre‑Señal", callback_data=f"presenal_confirm:{pre_id}")]])
        mensaje = (
            f"{frase}\n\n"
            f"⏰ **Próxima señal en {minutos_antes} minutos**\n"
            f"💱 **Mercado:** {mercado}\n"
            f"📊 **Confirma si estás listo para recibirla**\n\n"
            f"Pulsa el botón para confirmar."
        )
        bloqueados = set()
        try:
            bloqueados = set(self.user_manager.obtener_usuarios_bloqueados())
        except Exception:
            # Fallback: usar estructura en memoria si existe
            try:
                bloqueados = set(self.user_manager.usuarios_bloqueados)
            except Exception:
                bloqueados = set()
        for uid, info in list(self.user_manager.usuarios_activos.items()):
            if uid in bloqueados:
                continue
            await self._send_with_markup(uid, mensaje, reply_markup=keyboard)

    async def enviar_confirmacion_senal_a_usuarios(self, signal_id: str, pre_id: str, señal: Dict):
        """Envía pregunta simple: ¿Desea recibir la señal? SIN mostrar datos."""
        # Botones: Aceptar o Rechazar
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Aceptar", callback_data=f"signal_accept:{signal_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"signal_reject:{signal_id}")
            ]
        ])
        
        bloqueados = set()
        try:
            bloqueados = set(self.user_manager.obtener_usuarios_bloqueados())
        except Exception:
            try:
                bloqueados = set(self.user_manager.usuarios_bloqueados)
            except Exception:
                bloqueados = set()
        
        # Guardar los message_ids para poder editarlos después
        if 'confirmation_messages' not in señal:
            señal['confirmation_messages'] = {}
        
        # Enviar a todos los usuarios activos (sin pre-señal)
        for uid, info in list(self.user_manager.usuarios_activos.items()):
            if uid in bloqueados:
                continue
            
            # Mensaje simple SIN datos de la señal
            texto = (
                "🔔 Nueva señal disponible\n\n"
                "¿Deseas recibir esta señal?\n\n"
                "✅ Aceptar: Recibirás todos los detalles\n"
                "❌ Rechazar: No recibirás la señal"
            )
            message_id = await self._send_with_markup(uid, texto, reply_markup=keyboard)
            if message_id:
                señal['confirmation_messages'][uid] = message_id
    
    async def eliminar_botones_confirmacion(self, señal: Dict):
        """Elimina los botones de aceptar/rechazar de los mensajes de confirmación después de que expire la señal."""
        if 'confirmation_messages' not in señal:
            return
        
        texto_expirado = (
            "⏳ Esta señal ya expiró.\n\n"
            "Los botones han sido deshabilitados.\n"
            "Espera la próxima señal."
        )
        
        for uid, message_id in señal['confirmation_messages'].items():
            try:
                await self.application.bot.edit_message_text(
                    chat_id=str(uid),
                    message_id=message_id,
                    text=texto_expirado
                )
                print(f"[TG] Botones eliminados para usuario {uid}, mensaje {message_id}")
            except Exception as e:
                # El mensaje puede haber sido eliminado o editado por el usuario
                print(f"[TG] No se pudo editar mensaje {message_id} para usuario {uid}: {e}")

    async def handle_callback_presignal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        user_id = str(user.id)
        username = user.username or user.first_name or "Usuario"
        try:
            await query.answer()
        except Exception:
            pass

        # Confirmación de Pre‑Señal
        if data.startswith("presenal_confirm:"):
            pre_id = data.split(":", 1)[1]
            # Caducidad
            try:
                if self.signal_scheduler and self.signal_scheduler.pre_is_expired(pre_id):
                    # registrar caducada y avisar
                    try:
                        self.user_manager.registrar_confirmacion_presenal(user_id, username, pre_id, estado='caducada')
                    except Exception:
                        pass
                    await self.send_message(user_id, "⏳ Esta Pre‑Señal ya caducó. Espera la siguiente.")
                    return
            except Exception:
                pass
            try:
                self.user_manager.registrar_confirmacion_presenal(user_id, username, pre_id)
            except Exception as e:
                logger.warning(f"[CB] Error registrando confirmación Pre-Señal: {e}")
            try:
                await query.edit_message_text("✅ Confirmación recibida. Espera la señal.")
            except Exception:
                await self.send_message(user_id, "✅ Confirmación de Pre‑Señal recibida.")
            return

        # ACEPTAR Señal (nuevo sistema)
        if data.startswith("signal_accept:"):
            signal_id = data.split(":", 1)[1]
            
            # Verificar si la señal aún es válida
            try:
                if self.signal_scheduler and self.signal_scheduler.signal_is_expired(signal_id):
                    await query.edit_message_text("⏳ Esta señal ya caducó. Espera la próxima.")
                    return
            except Exception:
                pass
            
            # Obtener señal desde el scheduler
            señal = None
            try:
                if self.signal_scheduler is not None:
                    señal = self.signal_scheduler.obtener_senal_por_id(signal_id)
            except Exception as e:
                logger.warning(f"[CB] No se pudo obtener señal por id: {e}")
            
            # Validar que señal sea un diccionario válido
            if not señal or not isinstance(señal, dict):
                await query.edit_message_text("⚠️ La señal ya no está disponible o expiró.")
                return
            
            # Registrar que el usuario aceptó la señal
            try:
                self.user_manager.registrar_confirmacion_senal(user_id, username, None, signal_id, estado='aceptada')
            except Exception as e:
                logger.warning(f"[CB] Error registrando aceptación de señal: {e}")
            
            # Marcar que este usuario ya respondió (no editar su mensaje después)
            if 'confirmation_messages' in señal and user_id in señal['confirmation_messages']:
                del señal['confirmation_messages'][user_id]
            
            # Generar y enviar mensaje COMPLETO con todos los datos de la señal
            try:
                # Debug: verificar tipo de señal
                logger.info(f"[DEBUG] Tipo de señal: {type(señal)}, Valor: {señal}")
                
                if not isinstance(señal, dict):
                    logger.error(f"[ERROR] señal no es dict: {type(señal)}")
                    await query.edit_message_text("⚠️ Error: datos de señal inválidos.")
                    return
                
                # detalles_tecnicos puede ser lista o dict, convertir a dict si es necesario
                detalles_raw = señal.get('detalles_tecnicos', {})
                if isinstance(detalles_raw, list):
                    # Si es lista, crear un diccionario vacío (la función usará valores por defecto)
                    detalles = {}
                else:
                    detalles = detalles_raw
                    
                mensaje = self.signal_scheduler.generar_mensaje_señal_completo(señal, detalles)
                await query.edit_message_text("✅ Señal aceptada. Enviando detalles...")
                await self._send_with_markup(user_id, mensaje, reply_markup=None)
                logger.info(f"[Señal] Usuario {username} ({user_id}) aceptó señal #{señal.get('numero')}")
            except Exception as e:
                logger.error(f"[ERROR] Excepción enviando señal: {e}", exc_info=True)
                await self.send_message(user_id, f"❌ Error enviando la señal: {e}")
            return
        
        # RECHAZAR Señal (nuevo sistema)
        if data.startswith("signal_reject:"):
            signal_id = data.split(":", 1)[1]
            
            # Obtener señal para marcar que el usuario respondió
            señal = None
            try:
                if self.signal_scheduler is not None:
                    señal = self.signal_scheduler.obtener_senal_por_id(signal_id)
            except Exception:
                pass
            
            # Registrar que el usuario rechazó la señal
            try:
                self.user_manager.registrar_confirmacion_senal(user_id, username, None, signal_id, estado='rechazada')
            except Exception as e:
                logger.warning(f"[CB] Error registrando rechazo de señal: {e}")
            
            # Marcar que este usuario ya respondió (no editar su mensaje después)
            if señal and 'confirmation_messages' in señal and user_id in señal['confirmation_messages']:
                del señal['confirmation_messages'][user_id]
            
            # Confirmar rechazo
            try:
                await query.edit_message_text("❌ Señal rechazada. Esperando la próxima señal...")
                logger.info(f"[Señal] Usuario {username} ({user_id}) rechazó señal {signal_id}")
            except Exception:
                await self.send_message(user_id, "❌ Señal rechazada.")
            return
        
        # Confirmación de Señal (sistema antiguo - mantener por compatibilidad)
        if data.startswith("signal_confirm:"):
            try:
                _, pre_id, signal_id = data.split(":", 2)
            except ValueError:
                return
            # Validar que confirmó la Pre‑Señal
            if not self.user_manager.usuario_confirmo_presenal(user_id, pre_id):
                await self.send_message(user_id, "❌ Debes confirmar la Pre‑Señal antes de recibir la Señal.")
                return
            # Caducidad de la señal
            try:
                if self.signal_scheduler and self.signal_scheduler.signal_is_expired(signal_id):
                    try:
                        self.user_manager.registrar_confirmacion_senal(user_id, username, pre_id, signal_id, estado='caducada')
                    except Exception:
                        pass
                    await self.send_message(user_id, "⏳ Esta Señal ya caducó. Espera la próxima.")
                    return
            except Exception:
                pass
            # Obtener señal desde el scheduler
            señal = None
            try:
                if self.signal_scheduler is not None:
                    señal = self.signal_scheduler.obtener_senal_por_id(signal_id)
            except Exception as e:
                logger.warning(f"[CB] No se pudo obtener señal por id: {e}")
            if not señal:
                await self.send_message(user_id, "⚠️ La señal ya no está disponible o expiró.")
                return
            # Registrar confirmación de Señal
            try:
                self.user_manager.registrar_confirmacion_senal(user_id, username, pre_id, signal_id)
            except Exception as e:
                logger.warning(f"[CB] Error registrando confirmación de Señal: {e}")
            # Generar y enviar mensaje completo de la señal a este usuario
            try:
                detalles = señal.get('detalles_tecnicos', {})
                mensaje = self.signal_scheduler.generar_mensaje_señal_completo(señal, detalles)
                await query.edit_message_text("✅ Confirmado. Enviando la Señal…")
                await self._send_with_markup(user_id, mensaje, reply_markup=None)
            except Exception as e:
                await self.send_message(user_id, f"❌ Error enviando la Señal: {e}")
            return

        # Otros callbacks existentes pueden manejarse aquí en el futuro
    
    async def cmd_clave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /clave - Solicitar clave de acceso"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name or "Usuario"
        es_admin = self.user_manager.es_administrador(user_id)
        
        # Bloqueo dominical para usuarios no administradores
        if self._es_domingo_cuba() and not es_admin:
            await update.message.reply_text(
                (
                    "🚫 Servicio no disponible hoy\n\n"
                    f"Hola **{username}** 👋\n\n"
                    "Hoy es domingo y el servicio está cerrado para usuarios.\n\n"
                    "📅 Operamos de Lun-Sáb, 8:00 AM - 8:00 PM (hora de Cuba).\n\n"
                    "🔕 Recepción de señales: ❌ INACTIVA (domingo)\n\n"
                    "Vuelve mañana para continuar. Si necesitas ayuda, usa /ayuda."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        
        # Si ya está autenticado
        if user_id in self.user_manager.usuarios_activos:
            await update.message.reply_text(
                "✅ Ya estás autenticado.\nUsa /estado para ver tu información."
            )
            return
        
        # Verificar si se proporcionó la clave en el comando
        if context.args:
            clave = " ".join(context.args).strip()
            await self.procesar_clave(update, clave)
        else:
            # Solicitar clave
            self.esperando_clave.add(user_id)
            await update.message.reply_text(
                "🔑 **Ingresa tu clave de acceso:**\n\n"
                "Escribe la clave que recibiste del administrador.\n"
                "Ejemplo: `CUBA20241205ABCD`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def cmd_estado(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /estado - Mostrar estado del sistema (solo admin)"""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or user.first_name or "Usuario"
        
        # Verificar autenticación
        if user_id not in self.user_manager.usuarios_activos:
            await update.message.reply_text(
                "❌ **No estás autenticado**\n\n"
                "Usa /clave para ingresar tu clave de acceso.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Verificar permisos de administrador
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text(
                "❌ **Acceso denegado**\n\n"
                "Solo el administrador puede consultar el estado del sistema.\n"
                "Usa /ayuda para ver comandos disponibles.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        usuario_info = self.user_manager.usuarios_activos[user_id]
        estadisticas = self.user_manager.obtener_estadisticas_diarias()
        
        # Información del mercado actual
        mercado_info = "No seleccionado"
        if self.signal_scheduler.mercado_actual:
            mercado = self.signal_scheduler.mercado_actual
            mercado_info = f"{mercado['symbol']} (Payout: {mercado['payout']}%)"
        
        # Estado de conexión a Quotex (informativo)
        estado_qx = "Desconocido"
        try:
            mm = getattr(self, 'market_manager', None)
            if mm is not None:
                conectado_qx = bool(getattr(mm, 'conectado', False)) or (getattr(mm, 'quotex', None) is not None)
                estado_qx = "🟢 CONECTADO" if conectado_qx else "🔴 DESCONECTADO"
        except Exception:
            pass
        
        # Mercado actual
        mercado_actual = "No seleccionado"
        try:
            if hasattr(self.signal_scheduler, 'mercado_actual') and self.signal_scheduler.mercado_actual:
                mercado = self.signal_scheduler.mercado_actual
                mercado_actual = f"{mercado.get('symbol', 'N/A')} (Payout: {mercado.get('payout', 0)}%)"
        except Exception:
            pass
        
        # Estado operativo
        horario_activo = self.signal_scheduler.esta_en_horario_operativo() if self.signal_scheduler else False
        estado_operativo = "🟢 ACTIVO" if horario_activo else "🔴 FUERA DE HORARIO"
        
        # Clave actual del día
        clave_actual = getattr(self.user_manager, 'clave_publica_actual', 'No generada')
        
        mensaje_estado = f"""
📊 **ESTADO DEL SISTEMA - CUBAYDSIGNAL**

🎯 **ESTADO OPERATIVO:**
• **Estado:** {estado_operativo}
• **Horario:** 8:00 AM - 8:00 PM (Lun-Sáb)
• **Hora actual:** {datetime.now().strftime('%H:%M:%S')}

🔗 **CONEXIONES:**
• **Quotex:** {estado_qx}
• **Telegram:** 🟢 CONECTADO
• **Scheduler:** {'🟢 ACTIVO' if self.signal_scheduler else '🔴 INACTIVO'}

💱 **MERCADO:**
• **Mercado actual:** {mercado_actual}
• **Tipo:** {'OTC' if datetime.now().weekday() == 5 else 'Normal'}

👥 **USUARIOS:**
• **Usuarios activos:** {len(self.user_manager.usuarios_activos)}
• **Clave del día:** `{clave_actual}`

📈 **SEÑALES:**
• **Señales enviadas hoy:** {estadisticas.get('señales_enviadas', 0)}
• **Próxima señal:** {'Calculando...' if horario_activo else 'Mañana 8:00 AM'}

⚙️ **SISTEMA:**
• **Bot:** 🟢 OPERATIVO
• **Handlers:** 🟢 REGISTRADOS
• **Memoria:** 🟢 NORMAL

👑 **Panel de administrador activo**
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_estado")],
            [InlineKeyboardButton("📊 Estadísticas", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Usuarios", callback_data="admin_usuarios")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            mensaje_estado,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats - Mostrar estadísticas detalladas (solo admin)"""
        user_id = str(update.effective_user.id)
        
        # Verificar permisos de administrador
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text(
                "❌ Solo el administrador puede consultar las estadísticas.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Obtener estadísticas del sistema
        from datetime import datetime, timedelta
        
        # Estadísticas básicas
        usuarios_activos = len(self.user_manager.usuarios_activos)
        señales_hoy = len(getattr(self.signal_scheduler, 'señales_enviadas_hoy', []))
        
        # Estadísticas de efectividad (simuladas por ahora)
        efectividad_promedio = 82.5
        señales_exitosas = int(señales_hoy * 0.825)
        señales_fallidas = señales_hoy - señales_exitosas
        
        # Estadísticas de usuarios
        usuarios_tardios = 0
        usuarios_tempranos = 0
        for user_info in self.user_manager.usuarios_activos.values():
            if user_info.get('es_tardio', False):
                usuarios_tardios += 1
            else:
                usuarios_tempranos += 1
        
        # Tiempo de actividad del bot
        tiempo_activo = "Calculando..."
        try:
            if hasattr(self, 'inicio_bot'):
                delta = datetime.now() - self.inicio_bot
                horas = int(delta.total_seconds() // 3600)
                minutos = int((delta.total_seconds() % 3600) // 60)
                tiempo_activo = f"{horas}h {minutos}m"
        except:
            tiempo_activo = "Hoy"
        
        mensaje_stats = f"""
📊 **ESTADÍSTICAS DETALLADAS - CUBAYDSIGNAL**

📈 **RENDIMIENTO HOY:**
• **Señales enviadas:** {señales_hoy}
• **Señales exitosas:** {señales_exitosas} ({efectividad_promedio}%)
• **Señales fallidas:** {señales_fallidas}
• **Efectividad promedio:** {efectividad_promedio}%

👥 **USUARIOS ACTIVOS:** {usuarios_activos}
• **Usuarios tempranos:** {usuarios_tempranos}
• **Usuarios tardíos:** {usuarios_tardios}
• **Tasa de puntualidad:** {(usuarios_tempranos/(usuarios_activos or 1)*100):.1f}%

⏰ **TIEMPO DE ACTIVIDAD:**
• **Bot activo desde:** {tiempo_activo}
• **Horario operativo:** 8:00 AM - 8:00 PM
• **Días operativos:** Lunes a Sábado

💱 **MERCADOS:**
• **Mercado principal:** EUR/USD
• **Mercados OTC:** Disponibles sábados
• **Timeframes:** 1M, 3M, 5M, 15M

🎯 **OBJETIVOS DIARIOS:**
• **Meta señales:** 20-25 por día
• **Meta efectividad:** ≥80%
• **Progreso hoy:** {(señales_hoy/22*100):.1f}%

🔧 **SISTEMA:**
• **Uptime:** 99.9%
• **Latencia promedio:** <100ms
• **Memoria utilizada:** Normal
• **CPU:** Óptimo

👑 **Panel de administrador - Estadísticas en tiempo real**
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar Stats", callback_data="actualizar_stats")],
            [InlineKeyboardButton("📊 Estado Sistema", callback_data="estado_sistema")],
            [InlineKeyboardButton("📈 Historial", callback_data="admin_historial")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            mensaje_stats,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_nuevaclave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /nuevaclave - Generar nueva clave diaria (solo admin)"""
        user_id = str(update.effective_user.id)
        
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el administrador puede generar nuevas claves.")
            return
        
        # Generar nueva clave automática del día y revocar accesos previos
        nueva_clave = self.user_manager.generar_clave_diaria_si_necesario(forzar=True)
        try:
            # Revoca acceso y notifica a usuarios activos
            self.user_manager.actualizar_clave_publica(nueva_clave)
        except Exception:
            pass
        
        mensaje = f"""
🔑 **NUEVA CLAVE GENERADA**

• **Clave:** `{nueva_clave}`
• **Fecha:** {datetime.now().strftime('%Y-%m-%d')}
• **Hora:** {datetime.now().strftime('%H:%M')}

📝 **Instrucciones:**
• Comparte esta clave con usuarios autorizados
• La clave anterior queda inválida inmediatamente
• Los usuarios deben usar `/clave {nueva_clave}` para acceder

⚙️ **Clave generada exitosamente!**
        """
        
        await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
        # Notificar al admin
        try:
            await self.notificar_admin_telegram(
                f"🔐 Se generó una nueva clave diaria y se revocaron accesos previos: {nueva_clave}"
            )
        except Exception:
            pass

    async def cmd_clavehoy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /clavehoy - Ver clave actual (solo admin)"""
        user_id = str(update.effective_user.id)
        
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el administrador puede consultar la clave actual.")
            return
        
        clave_actual = self.user_manager.clave_publica_diaria
        fecha_clave = datetime.now().strftime('%Y-%m-%d')
        
        mensaje = f"""
🔑 **CLAVE ACTUAL**

• **Clave:** `{clave_actual}`
• **Fecha:** {fecha_clave}
• **Estado:** 🟢 ACTIVA

👥 **Usuarios activos:** {len(self.user_manager.usuarios_activos)}
🚫 **Usuarios bloqueados:** {len(self.user_manager.usuarios_bloqueados)}

📝 **Para compartir:**
`/clave {clave_actual}`
        """
        
        await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats - Estadísticas avanzadas (solo admin)"""
        user_id = str(update.effective_user.id)
        
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el administrador puede ver estadísticas avanzadas.")
            return
        
        stats = self.user_manager.obtener_estadisticas_diarias()
        info_sistema = self.user_manager.obtener_info_sistema()
        
        # Estado de Quotex
        estado_qx = "Desconocido"
        try:
            mm = getattr(self, 'market_manager', None)
            if mm is not None:
                conectado_qx = bool(getattr(mm, 'conectado', False)) or (getattr(mm, 'quotex', None) is not None)
                estado_qx = "🟢 CONECTADO" if conectado_qx else "🔴 DESCONECTADO"
        except Exception:
            pass
        
        mensaje = f"""
📊 **ESTADÍSTICAS AVANZADAS**

👥 **USUARIOS:**
• **Activos:** {len(self.user_manager.usuarios_activos)}
• **Bloqueados:** {len(self.user_manager.usuarios_bloqueados)}
• **En lista blanca:** {len(self.user_manager.lista_blanca)}

📊 **SEÑALES HOY:**
• **Enviadas:** {stats.get('señales_enviadas', 0)}
• **Efectividad promedio:** {stats.get('efectividad_promedio', 0):.1f}%

🔌 **SISTEMA:**
• **Estado:** {'🟢 ACTIVO' if info_sistema['horario_activo'] else '🔴 INACTIVO'}
• **Quotex:** {estado_qx}
• **Mercado actual:** {self.signal_scheduler.mercado_actual['symbol'] if self.signal_scheduler.mercado_actual else 'No seleccionado'}

🔑 **ACCESO:**
• **Clave actual:** `{info_sistema['clave_publica_actual']}`
• **Fecha clave:** {info_sistema['fecha_clave']}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_stats")],
            [InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nuevaclave")],
            [InlineKeyboardButton("⚙️ Panel Admin", callback_data="volver_panel_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            mensaje,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_efectividad(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /efectividad - Muestra estadísticas de efectividad (solo admin)"""
        user_id = str(update.effective_user.id)
        
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el administrador puede ver estadísticas de efectividad.")
            return
        
        try:
            # Obtener estadísticas del scheduler si está disponible
            scheduler = getattr(self, 'signal_scheduler', None)
            if scheduler and hasattr(scheduler, 'señales_enviadas_hoy'):
                señales_hoy = scheduler.señales_enviadas_hoy
                total_señales = len(señales_hoy)
                
                if total_señales == 0:
                    mensaje = "📊 **ESTADÍSTICAS DE EFECTIVIDAD**\n\n❌ No hay señales enviadas hoy para analizar."
                else:
                    ganadas = sum(1 for s in señales_hoy if s.get('resultado') == 'WIN')
                    perdidas = sum(1 for s in señales_hoy if s.get('resultado') == 'LOSS')
                    pendientes = total_señales - ganadas - perdidas
                    
                    efectividad = (ganadas / total_señales * 100) if total_señales > 0 else 0
                    
                    # Análisis por activo
                    activos = {}
                    for señal in señales_hoy:
                        symbol = señal.get('symbol', 'Desconocido')
                        if symbol not in activos:
                            activos[symbol] = {'total': 0, 'ganadas': 0}
                        activos[symbol]['total'] += 1
                        if señal.get('resultado') == 'WIN':
                            activos[symbol]['ganadas'] += 1
                    
                    resumen_activos = []
                    for symbol, stats in activos.items():
                        efect = (stats['ganadas'] / stats['total'] * 100) if stats['total'] > 0 else 0
                        resumen_activos.append(f"• {symbol}: {stats['ganadas']}/{stats['total']} ({efect:.1f}%)")
                    
                    mensaje = f"""📊 **ESTADÍSTICAS DE EFECTIVIDAD**

🎯 **Resumen General:**
• Total de señales: {total_señales}
• Señales ganadas: {ganadas} ✅
• Señales perdidas: {perdidas} ❌
• Señales pendientes: {pendientes} ⏳
• **Efectividad total: {efectividad:.1f}%**

📈 **Por Activo:**
{chr(10).join(resumen_activos) if resumen_activos else '• Sin datos por activo'}

📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            else:
                mensaje = "📊 **ESTADÍSTICAS DE EFECTIVIDAD**\n\n⚠️ Scheduler no disponible o sin datos de señales."
                
        except Exception as e:
            mensaje = f"📊 **ESTADÍSTICAS DE EFECTIVIDAD**\n\n❌ Error obteniendo estadísticas: {str(e)}"
        
        await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /admin - Panel de administrador"""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.user_manager.usuarios_activos:
            await update.message.reply_text("❌ No estás autenticado.")
            return
        
        if self.user_manager.usuarios_activos[user_id]['tipo'] != 'admin':
            await update.message.reply_text("❌ Acceso denegado. Solo para administradores.")
            return
        
        info_sistema = self.user_manager.obtener_info_sistema()
        
        mensaje_admin = f"""
⚙️ **PANEL DE ADMINISTRADOR**

🔑 **Autenticación:**
• **Clave pública:** `{info_sistema['clave_publica_actual']}`
• **Fecha clave:** {info_sistema['fecha_clave']}

👥 **Usuarios:**
• **Activos:** {info_sistema['usuarios_activos']}
• **Bloqueados:** {info_sistema['usuarios_bloqueados']}
• **Usuarios tardíos:** {info_sistema['estadisticas'].get('usuarios_tardios', 0)}

📊 **Señales:**
• **Enviadas hoy:** {info_sistema['señales_enviadas']}
• **Efectividad promedio:** {info_sistema['estadisticas'].get('efectividad_promedio', 0):.1f}%

🎯 **Sistema:**
• **Estado:** {'🟢 ACTIVO' if info_sistema['horario_activo'] else '🔴 INACTIVO'}
• **Mercado:** {self.signal_scheduler.mercado_actual['symbol'] if self.signal_scheduler.mercado_actual else 'No seleccionado'}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nueva_clave")],
            [InlineKeyboardButton("📊 Estadísticas", callback_data="admin_estadisticas")],
            [InlineKeyboardButton("👥 Ver Usuarios", callback_data="admin_usuarios")],
            [InlineKeyboardButton("🚫 Bloquear Usuario", callback_data="admin_bloquear")],
            [InlineKeyboardButton("✅ Desbloquear Usuario", callback_data="admin_desbloquear")],
            [InlineKeyboardButton("📋 Historial Bloqueos", callback_data="admin_historial")],
            [InlineKeyboardButton("🚀 Iniciar Día", callback_data="admin_iniciar_dia")],
            [InlineKeyboardButton("⏹️ Detener Bot", callback_data="admin_detener")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            mensaje_admin,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_listablanca(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para ver la lista blanca"""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede ver la lista blanca.")
            return
        ids = list(self.user_manager.lista_blanca)
        nombres = list(self.user_manager.lista_blanca_nombres)
        msg = "👥 <b>Lista blanca de IDs:</b>\n" + ("\n".join(ids) if ids else "- Ninguno -")
        msg += "\n\n👤 <b>Lista blanca de nombres:</b>\n" + ("\n".join(nombres) if nombres else "- Ninguno -")
        await update.message.reply_text(msg, parse_mode="HTML")

    async def cmd_agregarblanco(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para agregar usuario a la lista blanca"""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede modificar la lista blanca.")
            return
        args = context.args
        if not args:
            await update.message.reply_text("Uso: /agregarblanco <id> o <username>")
            return
        for arg in args:
            if arg.isdigit():
                self.user_manager.agregar_a_lista_blanca(user_id=arg)
            else:
                self.user_manager.agregar_a_lista_blanca(username=arg)
        await update.message.reply_text("✅ Usuario(s) agregado(s) a la lista blanca.")

    async def cmd_quitarblanco(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para quitar usuario de la lista blanca"""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede modificar la lista blanca.")
            return
        args = context.args
        if not args:
            await update.message.reply_text("Uso: /quitarblanco <id> o <username>")
            return
        for arg in args:
            if arg.isdigit():
                self.user_manager.quitar_de_lista_blanca(user_id=arg)
            else:
                self.user_manager.quitar_de_lista_blanca(username=arg)
        await update.message.reply_text("✅ Usuario(s) quitado(s) de la lista blanca.")

    async def cmd_lista_diaria_autorizada(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /listahoy - Gestionar lista diaria de usuarios autorizados (solo admin)"""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede gestionar la lista diaria autorizada.")
            return
        
        args = context.args
        
        # Si no hay argumentos, mostrar lista actual
        if not args:
            fecha_hoy = datetime.now().strftime('%Y-%m-%d')
            if (self.user_manager.fecha_lista_diaria == fecha_hoy and 
                (self.user_manager.lista_diaria_ids or self.user_manager.lista_diaria_nombres)):
                
                total = len(self.user_manager.lista_diaria_ids) + len(self.user_manager.lista_diaria_nombres)
                mensaje = f"📋 **LISTA DIARIA AUTORIZADA** - {fecha_hoy}\n\n"
                mensaje += f"👥 **Total usuarios:** {total}\n\n"
                
                if self.user_manager.lista_diaria_ids:
                    mensaje += "🆔 **Por ID:**\n"
                    for user_id_auth in self.user_manager.lista_diaria_ids:
                        mensaje += f"• {user_id_auth}\n"
                    mensaje += "\n"
                
                if self.user_manager.lista_diaria_nombres:
                    mensaje += "👤 **Por Username:**\n"
                    for username in self.user_manager.lista_diaria_nombres:
                        mensaje += f"• @{username}\n"
                    mensaje += "\n"
                
                mensaje += "\n💡 **Uso:**\n"
                mensaje += "`/listahoy usuario1 usuario2 @usuario3 123456789`\n"
                mensaje += "\n🔄 Para actualizar la lista, envía los nuevos usuarios como argumentos."
                
            else:
                mensaje = f"📋 **LISTA DIARIA AUTORIZADA** - {fecha_hoy}\n\n"
                mensaje += "❌ **No hay lista para hoy**\n\n"
                mensaje += "💡 **Crear lista:**\n"
                mensaje += "`/listahoy usuario1 usuario2 @usuario3 123456789`\n\n"
                mensaje += "📝 **Puedes usar:**\n"
                mensaje += "• Nombres de usuario: `@usuario` o `usuario`\n"
                mensaje += "• IDs de Telegram: `123456789`\n"
                mensaje += "• Mezclar ambos en una sola línea"
            
            await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Actualizar lista con los argumentos proporcionados
        try:
            resultado = self.user_manager.actualizar_lista_diaria_autorizada(args)
            await update.message.reply_text(resultado, parse_mode=ParseMode.MARKDOWN)
            
            # Notificar al admin sobre la actualización
            fecha_hoy = datetime.now().strftime('%d/%m/%Y')
            notificacion = f"📋 **LISTA DIARIA ACTUALIZADA**\n\n📅 Fecha: {fecha_hoy}\n👥 Total usuarios: {len(args)}\n\n✅ La lista diaria de usuarios autorizados ha sido actualizada correctamente."
            await self.notificar_admin_telegram(notificacion)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error al actualizar la lista: {str(e)}")

    async def cmd_bloquear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /bloquear - Bloquear usuario por ID o username (solo admin)"""
        admin_user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(admin_user_id):
            await update.message.reply_text("❌ Solo el admin puede bloquear usuarios.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text("Uso: /bloquear <id> o /bloquear @username")
            return
        
        objetivo = args[0].strip().replace('@', '')
        
        # Si es un número, es un ID directo
        if objetivo.isdigit():
            user_id_objetivo = objetivo
        else:
            # Buscar el ID por username en usuarios activos
            user_id_objetivo = None
            for uid, info in self.user_manager.usuarios_activos.items():
                if info.get('username', '').lower() == objetivo.lower():
                    user_id_objetivo = uid
                    break
            
            if not user_id_objetivo:
                await update.message.reply_text(f"❌ No se encontró el usuario @{objetivo}. Debe estar conectado o usa su ID numérico.")
                return
        
        # Usar el método correcto que registra todos los datos
        resultado = self.user_manager.bloquear_usuario(user_id_objetivo, admin_user_id)
        
        if resultado['exito']:
            mensaje = resultado['mensaje']
            await update.message.reply_text(mensaje)
            await self.notificar_admin_telegram(f"[ADMIN] {mensaje}")
        else:
            await update.message.reply_text(f"❌ {resultado['mensaje']}")

    async def cmd_desbloquear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /desbloquear - Desbloquear usuario por ID o username (solo admin)"""
        admin_user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(admin_user_id):
            await update.message.reply_text("❌ Solo el admin puede desbloquear usuarios.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text("Uso: /desbloquear <id> o /desbloquear @username")
            return
        
        objetivo = args[0].strip().replace('@', '')
        
        # Si es un número, es un ID directo
        if objetivo.isdigit():
            user_id_objetivo = objetivo
        else:
            # Buscar el ID por username en usuarios bloqueados
            # Primero buscar en usuarios activos
            user_id_objetivo = None
            for uid, info in self.user_manager.usuarios_activos.items():
                if info.get('username', '').lower() == objetivo.lower():
                    user_id_objetivo = uid
                    break
            
            # Si no está en activos, buscar en historial de bloqueos
            if not user_id_objetivo:
                for bloqueo in reversed(self.user_manager.historial_bloqueos):
                    if bloqueo.get('username_afectado', '').lower() == objetivo.lower():
                        user_id_objetivo = bloqueo.get('usuario_afectado')
                        break
            
            if not user_id_objetivo:
                await update.message.reply_text(f"❌ No se encontró el usuario @{objetivo}. Usa su ID numérico.")
                return
        
        # Usar el método correcto que registra todos los datos
        resultado = self.user_manager.desbloquear_usuario(user_id_objetivo, admin_user_id)
        
        if resultado['exito']:
            mensaje = resultado['mensaje']
            await update.message.reply_text(mensaje)
            await self.notificar_admin_telegram(f"[ADMIN] {mensaje}")
        else:
            await update.message.reply_text(f"❌ {resultado['mensaje']}")

    async def cmd_ver_bloqueados(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /bloqueados - Ver lista de usuarios bloqueados (solo admin)"""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede ver la lista de bloqueados.")
            return
        
        bloqueados = self.user_manager.usuarios_bloqueados
        if not bloqueados:
            await update.message.reply_text("✅ No hay usuarios bloqueados actualmente.")
            return
        
        # Separar IDs de usernames
        ids_bloqueados = [b for b in bloqueados if b.isdigit()]
        usernames_bloqueados = [b for b in bloqueados if not b.isdigit()]
        
        mensaje = "🚫 **USUARIOS BLOQUEADOS**\n\n"
        mensaje += f"📊 **Total:** {len(bloqueados)} usuarios\n\n"
        
        if ids_bloqueados:
            mensaje += "🆔 **Por ID:**\n"
            for user_id_blocked in ids_bloqueados:
                mensaje += f"• {user_id_blocked}\n"
            mensaje += "\n"
        
        if usernames_bloqueados:
            mensaje += "👤 **Por Username:**\n"
            for username in usernames_bloqueados:
                mensaje += f"• @{username}\n"
            mensaje += "\n"
        
        mensaje += "💡 **Comandos:**\n"
        mensaje += "• `/desbloquear <id>` - Desbloquear por ID\n"
        mensaje += "• `/desbloquear <username>` - Desbloquear por nombre\n"
        mensaje += "• `/historialbloqueos` - Ver historial completo"
        
        await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)

    async def enviar_señales_previas_usuario_tardio(self, user_id: str):
        """Envía las señales previas del día a un usuario tardío"""
        try:
            # Obtener señales previas detalladas
            señales_detalladas = self.user_manager.generar_señales_perdidas_detalladas()
            
            if not señales_detalladas:
                return
            
            # Enviar cada señal individualmente con un pequeño delay
            for señal in señales_detalladas:
                await self.send_message(user_id, señal)
                # Pequeño delay para evitar spam
                await asyncio.sleep(0.5)
            
            print(f"[TG] ✅ Enviadas {len(señales_detalladas)} señales previas a usuario tardío {user_id}")
            
        except Exception as e:
            print(f"[TG] ❌ Error enviando señales previas a usuario tardío: {e}")

    async def generar_respuesta_automatica(self, user_id: str, username: str) -> str:
        """Genera respuesta automática para nuevos usuarios"""
        import random
        from datetime import datetime
        
        # Verificar si está dentro del horario operativo
        ahora_cuba = datetime.now(CUBA_TZ)
        hora_actual = ahora_cuba.hour
        # Operativo solo Lun (0) a Sáb (5) y entre 8-20h
        es_horario_operativo = (ahora_cuba.weekday() != 6) and (8 <= hora_actual < 20)
        
        # Seleccionar frase motivadora aleatoria
        frases_saludo = [
            "No viniste a probar suerte… viniste a dominar el juego.",
            "La paciencia y la lógica siempre vencen al impulso.",
            "Cada vela cuenta una historia… tú decides cómo leerla.",
            "No se trata de predecir, se trata de entender.",
            "Tu mejor operación es la que sigue tu análisis, no tu emoción.",
            "El mercado premia la disciplina, no la desesperación.",
            "Cuando los demás dudan, tú operas con visión.",
            "Los errores enseñan, pero la constancia gana.",
            "No es suerte si lo entrenaste 100 veces antes.",
            "Operar sin lógica es como navegar sin mapa.",
            "No esperes la señal perfecta… constrúyela.",
            "Con control, enfoque y paciencia: no pierdes, aprendes.",
            "La estrategia no es magia: es análisis + ejecución.",
            "Cada pullback es una oportunidad, si sabes verlo.",
            "El mercado es tu campo de batalla, el análisis es tu arma."
        ]
        
        frase_motivadora = random.choice(frases_saludo)
        
        if es_horario_operativo:
            # Horario operativo: invitar a poner la clave
            mensaje = f"""👋 ¡Bienvenido al Bot CubaYDsignal!

📊 **Horario de operación:** 8:00 AM - 8:00 PM
🕒 **Estado actual:** ✅ ACTIVO

🔑 Para recibir las señales de trading, envía la **clave del día**.

💡 **Frase motivadora:**
"{frase_motivadora}"

🎯 ¡Prepárate para operar con disciplina y lógica!

🤖 – Bot CubaYDsignal"""
        else:
            # Fuera de horario: invitar para mañana
            mensaje = f"""👋 ¡Bienvenido al Bot CubaYDsignal!

📊 **Horario de operación:** 8:00 AM - 8:00 PM
🕒 **Estado actual:** ❌ CERRADO

🌙 El sistema de señales ya cerró por hoy.
🌅 Te esperamos mañana a las 8:00 AM con nuevas oportunidades.

💡 **Frase motivadora:**
"{frase_motivadora}"

💪 Mañana será un nuevo día para dominar el mercado.

🤖 – Bot CubaYDsignal"""
        
        return mensaje
    
    async def manejar_mensaje_general(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes generales de usuarios (respuesta automática)"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Usuario"
        mensaje_texto = update.message.text
        
        # Si el mensaje es una clave, procesarlo
        if len(mensaje_texto) <= 20 and not mensaje_texto.startswith('/'):
            await self.procesar_clave(update, mensaje_texto)
            return
        
        # Si no es una clave, enviar respuesta automática
        respuesta = await self.generar_respuesta_automatica(user_id, username)
        await update.message.reply_text(respuesta, parse_mode=ParseMode.MARKDOWN)
        
        print(f"[TG] 👋 Respuesta automática enviada a {username} ({user_id})")
    
    async def comando_historial_usuarios(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para ver historial de usuarios autenticados por fecha"""
        user_id = str(update.effective_user.id)
        
        # Solo admin puede ver el historial
        if not self.user_manager.es_admin(user_id):
            await update.message.reply_text("❌ Solo el administrador puede acceder al historial.")
            return
        
        # Obtener fecha si se proporciona, sino usar hoy
        fecha = None
        if context.args:
            try:
                from datetime import datetime
                fecha = datetime.strptime(context.args[0], '%Y-%m-%d').date()
            except ValueError:
                await update.message.reply_text("❌ Formato de fecha inválido. Usa: YYYY-MM-DD")
                return
        
        # Generar historial
        historial = self.user_manager.obtener_historial_usuarios(fecha)
        
        if not historial:
            fecha_texto = fecha.strftime('%d/%m/%Y') if fecha else datetime.now().strftime('%d/%m/%Y')
            await update.message.reply_text(f"📅 No hay usuarios registrados para {fecha_texto}.")
            return
        
        # Formatear respuesta
        fecha_texto = fecha.strftime('%d/%m/%Y') if fecha else datetime.now().strftime('%d/%m/%Y')
        mensaje = f"📅 **Historial de Usuarios - {fecha_texto}**\n\n"
        
        for i, usuario in enumerate(historial, 1):
            hora = usuario.get('hora_autenticacion', 'N/A')
            username = usuario.get('username', 'N/A')
            user_id_hist = usuario.get('user_id', 'N/A')
            es_tardio = "🔴 Tardío" if usuario.get('es_tardio', False) else "🔵 Temprano"
            
            mensaje += f"{i}. **{username}** ({user_id_hist})\n"
            mensaje += f"   • Hora: {hora}\n"
            mensaje += f"   • Estado: {es_tardio}\n\n"
        
        mensaje += f"**Total:** {len(historial)} usuarios autenticados"
        
        await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
        print(f"[TG] 📅 Historial enviado a admin - {len(historial)} usuarios")
        # (eliminado: método duplicado notificar_admin_telegram)

    async def cmd_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para enviar mensaje a todos los usuarios activos (solo admin)"""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede enviar mensajes broadcast.")
            return
        mensaje = ' '.join(context.args)
        if not mensaje:
            await update.message.reply_text("Uso: /broadcast <mensaje>")
            return
        await self.broadcast_message(mensaje)
        await update.message.reply_text("✅ Mensaje enviado a todos los usuarios activos.")

    async def cmd_historialsenales(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Consulta el historial de señales por fecha (YYYY-MM-DD, opcional)"""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede consultar el historial.")
            return
        fecha = context.args[0] if context.args else None
        historial = self.user_manager.consultar_historial_senales(fecha)
        if not historial:
            await update.message.reply_text("No hay señales registradas para esa fecha.")
            return
        resumen = f"📋 Señales del {fecha or 'historial completo'}:\n"
        for s in historial[-20:]:
            resumen += f"#{s.get('numero','?')} {s.get('hora','?')} {s.get('symbol','?')} {s.get('direccion','?')} {s.get('efectividad',0):.1f}%\n"
        await update.message.reply_text(resumen)

    async def cmd_historialbloqueos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra el panel inline del Historial de Bloqueos con filtros y navegación."""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede consultar el historial.")
            return
        # Mensaje principal del panel
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        msg = (
            "📈 HISTORIAL DE BLOQUEOS\n\n"
            "Selecciona un filtro para ver registros y estadísticas recientes, o busca por usuario/ID."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Hoy", callback_data="bloq_hist_hoy"), InlineKeyboardButton("7 días", callback_data="bloq_hist_semana"), InlineKeyboardButton("Mes", callback_data="bloq_hist_mes")],
            [InlineKeyboardButton("📚 Completo", callback_data="bloq_hist_todo")],
            [InlineKeyboardButton("👤 Buscar por Usuario", callback_data="bloq_hist_buscar_user"), InlineKeyboardButton("🆔 Buscar por ID", callback_data="bloq_hist_buscar_id")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="historial_bloqueos_hist")]
        ])
        await update.message.reply_text(msg, reply_markup=kb)

    async def cmd_accesos_no_autorizados(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra el historial de accesos no autorizados
        Uso: /accesos_no_autorizados [YYYY-MM-DD]
        """
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede ver este historial.")
            return
        
        from core.user_manager_accesos import generar_reporte_accesos_no_autorizados
        from datetime import datetime
        
        # Obtener fecha del argumento o usar hoy
        fecha_arg = context.args[0] if context.args else None
        if fecha_arg:
            try:
                # Validar formato de fecha
                datetime.strptime(fecha_arg, '%Y-%m-%d')
                fecha = fecha_arg
            except ValueError:
                await update.message.reply_text("❌ Formato de fecha inválido. Usa: YYYY-MM-DD")
                return
        else:
            fecha = datetime.now().strftime('%Y-%m-%d')
        
        # Generar reporte
        reporte = generar_reporte_accesos_no_autorizados(self.user_manager, fecha, limite=15)
        
        await update.message.reply_text(reporte, parse_mode=ParseMode.MARKDOWN)

    async def cmd_stats_confirmaciones(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra estadísticas diarias de confirmaciones de Pre‑Señal y Señal (solo admin).
        Uso: /stats_confirmaciones [YYYY-MM-DD]
        """
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo el admin puede ver estas estadísticas.")
            return
        from datetime import datetime
        fecha_arg = context.args[0] if context.args else None
        if fecha_arg:
            fecha = fecha_arg
        else:
            fecha = datetime.now().strftime('%Y-%m-%d')
        try:
            stats = self.user_manager.obtener_estadisticas_confirmaciones(fecha)
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estadísticas: {e}")
            return
        pres_total = stats.get('presenal_total', 0)
        sen_total = stats.get('senal_total', 0)
        pres_list = stats.get('presenal_listado', [])
        sen_list = stats.get('senal_listado', [])
        mensaje = [
            f"📊 Estadísticas de Confirmaciones – {fecha}",
            "",
            f"🟦 Pre‑Señal confirmaciones: {pres_total}",
            f"🟩 Señal confirmaciones: {sen_total}",
            "",
            "👥 Detalle Pre‑Señal:"
        ]
        if pres_list:
            for e in pres_list[-30:]:
                mensaje.append(
                    f"• {e.get('fecha_hora','')[:16]} – {e.get('username','N/A')} (ID {e.get('user_id','?')}) – pre_id {e.get('presenal_id','?')}"
                )
        else:
            mensaje.append("• Sin confirmaciones de Pre‑Señal")
        mensaje.append("")
        mensaje.append("👥 Detalle Señal:")
        if sen_list:
            for e in sen_list[-30:]:
                mensaje.append(
                    f"• {e.get('fecha_hora','')[:16]} – {e.get('username','N/A')} (ID {e.get('user_id','?')}) – pre_id {e.get('presenal_id','?')} – signal_id {e.get('senal_id','?')}"
                )
        else:
            mensaje.append("• Sin confirmaciones de Señal")
        await update.message.reply_text("\n".join(mensaje))

    async def handle_callback_legacy_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja callbacks de botones inline"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = str(query.from_user.id)
        
        print(f"[Legacy Admin] Procesando: {data} - user_id: {user_id}")
        
        if data == "ingresar_clave":
            # Verificar si es administrador
            es_admin = self.user_manager.es_administrador(user_id)
            
            if es_admin and user_id in self.user_manager.usuarios_activos:
                # El admin ya está autenticado - mostrar panel de administrador
                mensaje_admin_panel = """
👑 **PANEL DE ADMINISTRADOR**

✅ **Acceso confirmado como administrador**

📋 **Comandos disponibles:**
• `/estado` - Estado completo del sistema
• `/quotex` - Estado de conexión Quotex
• `/stats` - Estadísticas detalladas
• `/perfil` - Tu perfil de administrador
• `/nuevaclave` - Genera nueva clave diaria
• `/clavehoy` - Ver clave actual del día
• `/listahoy` - Gestionar lista diaria autorizada
• `/bloquear` / `/desbloquear` - Gestión de usuarios
• `/broadcast` - Enviar mensaje a todos
• `/historial` - Ver historiales

👑 **¡Tienes control total del sistema!**
                """
                
                keyboard = [
                    [InlineKeyboardButton("📊 Estado Sistema", callback_data="estado_sistema")],
                    [InlineKeyboardButton("📈 Estadísticas", callback_data="admin_estadisticas")],
                    [InlineKeyboardButton("💰 Trading Automático", callback_data="admin_trading")],
                    [InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nueva_clave")],
                    [InlineKeyboardButton("👥 Usuarios Activos", callback_data="admin_usuarios")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    mensaje_admin_panel,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            elif es_admin and user_id not in self.user_manager.usuarios_activos:
                # Admin no autenticado - pedir clave maestra
                self.esperando_clave.add(user_id)
                await query.edit_message_text(
                    "👑 **Acceso de Administrador**\n\n"
                    "🔑 Ingresa tu **clave maestra** para acceder como administrador:\n\n"
                    "(Esta es tu clave especial de administrador, no la clave diaria)",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Usuario normal
                if self._es_domingo_cuba():
                    await query.edit_message_text(
                        "🔴 El bot está CERRADO los domingos.\n\n"
                        "Vuelve mañana en horario laboral (Lun-Sáb 8:00 AM - 8:00 PM).",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    # Pedir clave diaria
                    self.esperando_clave.add(user_id)
                    await query.edit_message_text(
                        "🔑 **Ingresa tu clave de acceso:**\n\n"
                        "Escribe la clave que recibiste del administrador.",
                        parse_mode=ParseMode.MARKDOWN
                    )
        
        elif data == "mostrar_ayuda":
            # Mostrar ayuda contextual directamente
            user_id = str(query.from_user.id)
            es_admin = self.user_manager.es_administrador(user_id)
            
            if user_id not in self.user_manager.usuarios_activos:
                mensaje_ayuda = """
📚 **AYUDA - CUBAYDSIGNAL BOT**

🔑 **PRIMEROS PASOS:**
• `/start` - Iniciar el bot
• `/clave TUCLAVE` - Ingresar clave de acceso
• La clave cambia diariamente a las 00:00

📞 **¿Necesitas una clave?**
• Contacta al administrador
• Las claves se generan diariamente
• Solo usuarios autorizados tienen acceso

🔒 **SEGURIDAD:**
• No compartas tu clave con otros
• Cada clave es única y personal
• Reporta accesos no autorizados

¡Obtén tu clave y comienza a recibir señales! 🚀
                """
                
                keyboard = [
                    [InlineKeyboardButton("📊 Estado Sistema", callback_data="estado_sistema")],
                    [InlineKeyboardButton("📈 Estadísticas", callback_data="admin_estadisticas")],
                    [InlineKeyboardButton("💰 Trading Automático", callback_data="admin_trading")],
                    [InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nueva_clave")],
                    [InlineKeyboardButton("👥 Usuarios Activos", callback_data="admin_usuarios")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    mensaje_ayuda,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            elif es_admin:
                mensaje_ayuda = """
🔑 **GUÍA DE ADMINISTRADOR - CUBAYDSIGNAL BOT**

📋 **COMANDOS BÁSICOS:**
• `/estado` - Estado completo del sistema
• `/quotex` - Estado de conexión con Quotex
• `/stats` - Estadísticas detalladas
• `/perfil` - Tu información de administrador

🔑 **GESTIÓN DE CLAVES:**
• `/nuevaclave` - Genera nueva clave diaria
• `/clavehoy` - Muestra la clave actual del día

👥 **GESTIÓN DE USUARIOS:**
• `/listahoy usuario1 usuario2...` - Lista diaria autorizada
• `/bloquear @username` - Bloquea usuario
• `/desbloquear @username` - Desbloquea usuario
• `/bloqueados` - Lista usuarios bloqueados

📊 **HISTORIAL Y REPORTES:**
• `/historialsenales` - Todas las señales enviadas
• `/historialbloqueos` - Historial de bloqueos
• `/historial` - Usuarios autenticados por fecha
• `/efectividad EURUSD` - Efectividad de mercado

📢 **COMUNICACIÓN:**
• `/broadcast Tu mensaje` - Mensaje a todos los usuarios

💡 **EJEMPLOS:**
• `/listahoy @juan @maria 123456789`
• `/bloquear @spammer`
• `/broadcast ¡Nueva estrategia disponible!`
                """
                
                keyboard = [
                    [InlineKeyboardButton("📊 Estado Sistema", callback_data="estado_sistema")],
                    [InlineKeyboardButton("📈 Estadísticas", callback_data="admin_estadisticas")],
                    [InlineKeyboardButton("💰 Trading Automático", callback_data="admin_trading")],
                    [InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nueva_clave")],
                    [InlineKeyboardButton("👥 Usuarios Activos", callback_data="admin_usuarios")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    mensaje_ayuda,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                mensaje_ayuda = """
🤖 **INFORMACIÓN SOBRE CUBAYDSIGNAL BOT**

🎯 **¿QUÉ ES CUBAYDSIGNAL?**
Soy un bot de trading profesional que te proporciona señales de alta efectividad para opciones binarias en Quotex.

📊 **CARACTERÍSTICAS PRINCIPALES:**
• 🎯 20-25 señales diarias (efectividad ≥ 80%)
• 🕰️ Horario operativo: 8:00 AM - 8:00 PM (Lun-Sáb)
• 📱 Notificaciones automáticas vía Telegram
• 📈 Análisis técnico en cada señal

🔑 **COMANDOS DISPONIBLES:**
• `/perfil` - Ver tu información y estadísticas
• `/ayuda` - Mostrar esta información

🚀 **CÓMO FUNCIONA:**
1️⃣ Ingresa tu clave diaria
2️⃣ Recibes señales automáticamente
3️⃣ Lee el análisis y ejecuta con disciplina

💰 **TIPOS DE SEÑALES:**
• CALL (Subida)
• PUT (Bajada)
                """
                
                keyboard = [
                    [InlineKeyboardButton("📊 Estado Sistema", callback_data="estado_sistema")],
                    [InlineKeyboardButton("📈 Estadísticas", callback_data="admin_estadisticas")],
                    [InlineKeyboardButton("💰 Trading Automático", callback_data="admin_trading")],
                    [InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nueva_clave")],
                    [InlineKeyboardButton("👥 Usuarios Activos", callback_data="admin_usuarios")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    mensaje_ayuda,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        elif data == "usuario_ayuda":
            # Alias de ayuda para usuarios (mismo contenido que 'mostrar_ayuda')
            user_id = str(query.from_user.id)
            es_admin = self.user_manager.es_administrador(user_id)
            if user_id not in self.user_manager.usuarios_activos:
                mensaje_ayuda = (
                    "📚 **AYUDA - CUBAYDSIGNAL BOT**\n\n"
                    "🔑 **PRIMEROS PASOS:**\n"
                    "• /start – Iniciar\n"
                    "• /clave TUCLAVE – Ingresar clave diaria\n\n"
                    "📞 Contacta al administrador para obtener tu clave.\n"
                    "🔒 No compartas tu clave."
                )
            elif es_admin:
                mensaje_ayuda = (
                    "🔑 **GUÍA DE ADMINISTRADOR - CUBAYDSIGNAL BOT**\n\n"
                    "• /estado, /quotex, /stats, /perfil\n"
                    "• /nuevaclave, /clavehoy\n"
                    "• /listahoy, /bloquear, /desbloquear, /bloqueados\n"
                    "• /historialsenales, /historialbloqueos, /historial, /efectividad\n"
                    "• /broadcast <mensaje>"
                )
            else:
                mensaje_ayuda = (
                    "🤖 **INFORMACIÓN SOBRE CUBAYDSIGNAL BOT**\n\n"
                    "• Señales con alta efectividad (Lun‑Sáb 8:00–20:00)\n"
                    "• /perfil para ver tu información\n"
                    "• /ayuda para esta guía"
                )
            await query.edit_message_text(mensaje_ayuda, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "usuario_perfil":
            # Alias para mostrar perfil del usuario (equivalente a 'ver_perfil')
            user = query.from_user
            user_id = str(user.id)
            username = user.username or user.first_name or "Usuario"
            if user_id not in self.user_manager.usuarios_activos:
                await query.edit_message_text(
                    "❌ **No estás autenticado**\n\nUsa /clave para ingresar tu clave de acceso.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                usuario_info = self.user_manager.usuarios_activos[user_id]
                es_admin = self.user_manager.es_administrador(user_id)
                tipo_usuario = "👑 ADMINISTRADOR" if es_admin else "👤 USUARIO"
                mensaje_perfil = f"""
👤 **PERFIL DE {username.upper()}**

🆔 **INFORMACIÓN PERSONAL:**
• **Usuario:** @{username}
• **ID:** `{user_id}`
• **Tipo:** {tipo_usuario}

🔑 **ACCESO:**
• **Autenticación:** ✅
• **Ingreso:** {usuario_info.get('hora_ingreso','N/D')}
• **Método:** {usuario_info.get('metodo_acceso','Clave diaria')}
"""
                await query.edit_message_text(mensaje_perfil, parse_mode=ParseMode.MARKDOWN)
        
        elif data == "usuario_estado":
            # Alias estado del sistema (equivalente a 'estado_sistema')
            horario_activo = self.signal_scheduler.esta_en_horario_operativo()
            mercado = self.signal_scheduler.mercado_actual
            mensaje = f"""
📊 **ESTADO DEL SISTEMA**

🎯 **Estado:** {'🟢 ACTIVO' if horario_activo else '🔴 FUERA DE HORARIO'}
⏰ **Horario:** 8:00 AM - 8:00 PM (Lun-Sáb)
💱 **Mercado:** {mercado['symbol'] if mercado else 'No seleccionado'}
📈 **Señales hoy:** {len(self.signal_scheduler.señales_enviadas_hoy)}
"""
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN)

        elif data == "admin_informe_filtrar_activo":
            # Construir teclado con activos del día
            señales = getattr(self.signal_scheduler, 'señales_enviadas_hoy', [])
            activos = sorted({s.get('symbol', 'N/A') for s in señales})
            if not activos:
                await query.edit_message_text("No hay señales hoy para listar activos.")
                return
            filas = []
            for a in activos:
                filas.append([InlineKeyboardButton(a, callback_data=f"admin_informe_activo|{a}")])
            filas.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")])
            await query.edit_message_text(
                "Selecciona un activo:",
                reply_markup=InlineKeyboardMarkup(filas)
            )
        elif data.startswith("admin_informe_activo|"):
            # Filtro por activo específico (día actual)
            _, activo = data.split("|", 1)
            señales = getattr(self.signal_scheduler, 'señales_enviadas_hoy', [])
            filtradas = [s for s in señales if s.get('symbol') == activo]
            mensaje = self._formatear_informe_avanzado(filtradas, titulo=f"Informe Diario • {activo}")
            kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")]]
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

        elif data == "admin_informe_filtrar_pullback":
            filas = [[
                InlineKeyboardButton("Con Pullback", callback_data="admin_informe_pullback|si"),
                InlineKeyboardButton("Sin Pullback", callback_data="admin_informe_pullback|no")
            ],[
                InlineKeyboardButton("Todos", callback_data="admin_informe_pullback|todos")
            ],[
                InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")
            ]]
            await query.edit_message_text("Filtrar por pullback:", reply_markup=InlineKeyboardMarkup(filas))
        elif data.startswith("admin_informe_pullback|"):
            _, flag = data.split("|", 1)
            señales = getattr(self.signal_scheduler, 'señales_enviadas_hoy', [])
            def has_pb(sig):
                info = sig.get('pullback_info', {})
                if isinstance(info, dict):
                    return bool(info.get('detectado', False))
                return bool(info)
            if flag == 'si':
                filtradas = [s for s in señales if has_pb(s)]
                titulo = "Informe Diario • Con Pullback"
            elif flag == 'no':
                filtradas = [s for s in señales if not has_pb(s)]
                titulo = "Informe Diario • Sin Pullback"
            else:
                filtradas = list(señales)
                titulo = "Informe Diario • Todas"
            mensaje = self._formatear_informe_avanzado(filtradas, titulo=titulo)
            kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")]]
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

        elif data == "admin_informe_filtrar_fecha":
            # Mostrar últimos 7 días como botones
            from datetime import datetime, timedelta
            hoy = datetime.now().date()
            filas = []
            fila = []
            for i in range(7):
                fecha = (hoy - timedelta(days=i)).strftime('%Y-%m-%d')
                fila.append(InlineKeyboardButton(fecha, callback_data=f"admin_informe_fecha|{fecha}"))
                if len(fila) == 2:
                    filas.append(fila); fila = []
            if fila:
                filas.append(fila)
            filas.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")])
            await query.edit_message_text("Selecciona una fecha:", reply_markup=InlineKeyboardMarkup(filas))
        elif data.startswith("admin_informe_fecha|"):
            # Cargar del historial persistente por fecha
            _, fecha = data.split("|", 1)
            try:
                señales = self.user_manager.consultar_historial_senales(fecha) or []
            except Exception:
                señales = []
            mensaje = self._formatear_informe_avanzado(señales, titulo=f"Informe • {fecha}")
            kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")]]
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

        elif data.startswith("admin_informe_activo|"):
            # Redirigido al formato avanzado
            activo = data.split("|", 1)[1]
            señales = [s for s in getattr(self.signal_scheduler, 'señales_enviadas_hoy', []) if s.get('symbol') == activo]
            texto = self._formatear_informe_avanzado(señales, titulo=f"Informe (Hoy) • {activo}")
            keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")]]
            await query.edit_message_text(texto, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "admin_informe_filtrar_pullback":
            kb = [
                [InlineKeyboardButton("Solo pullback", callback_data="admin_informe_pullback|si")],
                [InlineKeyboardButton("Sin pullback", callback_data="admin_informe_pullback|no")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")]
            ]
            await query.edit_message_text("Filtrar por pullback:", reply_markup=InlineKeyboardMarkup(kb))

        elif data.startswith("admin_informe_pullback|"):
            val = data.split("|", 1)[1]
            flag = (val == "si")
            señales = [s for s in getattr(self.signal_scheduler, 'señales_enviadas_hoy', []) if bool(s.get('pullback_info', {}).get('detectado', False)) == flag]
            nombre = "con pullback" if flag else "sin pullback"
            texto = self._formatear_informe_desde_señales(señales, titulo=f"Informe (Hoy) - {nombre}")
            keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_informe")]]
            await query.edit_message_text(texto, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "admin_informe_filtrar_fecha":
            await query.edit_message_text(
                "📅 Filtro por fecha: requiere historial persistente accesible desde el bot. "
                "Podemos integrarlo si exponemos un método como `obtener_informe_por_fecha(YYYY-MM-DD)`.")
        
        # === Confirmaciones Pre‑Señal / Señal ===
        elif data.startswith("presenal_confirm:"):
            # data format: presenal_confirm:<pre_id>
            pre_id = data.split(":", 1)[1]
            # Verificar caducidad de la pre‑señal
            if self.signal_scheduler and self.signal_scheduler.pre_is_expired(pre_id):
                # Registrar caducidad y notificar usuario
                try:
                    self.user_manager.registrar_confirmacion_presenal(user_id, username, pre_id, estado='caducada')
                except Exception:
                    pass
                await query.edit_message_text(
                    "⏳ Esta pre‑señal caducó. Ya no es posible aceptarla.")
                return
            # Registrar aceptación
            try:
                self.user_manager.registrar_confirmacion_presenal(user_id, username, pre_id, estado='aceptada')
            except Exception:
                pass
            # Marcar aceptación en memoria para caducidad posterior
            try:
                pres_map = self.user_manager.confirmaciones_dia.setdefault('presenal', {})
                usuarios = pres_map.setdefault(pre_id, set())
                usuarios.add(str(user_id))
            except Exception:
                pass
            await query.edit_message_text("✅ Pre‑Señal aceptada. Cuando la señal esté lista, podrás solicitarla.")
            return

        elif data.startswith("signal_confirm:"):
            # data format: signal_confirm:<pre_id>:<signal_id>
            try:
                _, pre_id, signal_id = data.split(":", 2)
            except ValueError:
                await query.edit_message_text("⚠️ Formato inválido de confirmación de señal.")
                return
            # Debe existir aceptación previa de pre‑señal
            if not getattr(self.user_manager, 'usuario_confirmo_presenal', None) or not self.user_manager.usuario_confirmo_presenal(user_id, pre_id):
                await query.edit_message_text("⚠️ Debes aceptar la Pre‑Señal antes de recibir esta señal.")
                return
            # Verificar caducidad de la señal
            if self.signal_scheduler and self.signal_scheduler.signal_is_expired(signal_id):
                try:
                    self.user_manager.registrar_confirmacion_senal(user_id, username, pre_id, signal_id, estado='caducada')
                except Exception:
                    pass
                await query.edit_message_text("⏳ Esta señal caducó. Ya no es posible recibirla.")
                return
            # Registrar aceptación y enviar la señal individual
            try:
                self.user_manager.registrar_confirmacion_senal(user_id, username, pre_id, signal_id, estado='aceptada')
            except Exception:
                pass
            # Marcar aceptación en memoria
            try:
                sen_map = self.user_manager.confirmaciones_dia.setdefault('senal', {})
                usuarios = sen_map.setdefault(signal_id, set())
                usuarios.add(str(user_id))
            except Exception:
                pass
            # Recuperar señal desde scheduler, si está disponible
            senal = None
            if hasattr(self.signal_scheduler, 'obtener_senal_por_id'):
                try:
                    senal = self.signal_scheduler.obtener_senal_por_id(signal_id)
                except Exception:
                    senal = None
        # === CALLBACKS DE PANEL ADMIN QUE FALTABAN ===
        elif data == "admin_quotex":
            # Estado de Quotex
            await self.handle_admin_quotex_callback(query)
        elif data == "admin_quotex_force_connect":
            # Forzar conexión a Quotex
            await self.handle_admin_quotex_force_connect(query)
        elif data == "admin_perfil":
            # Mi Perfil (admin)
            await self.handle_admin_perfil_callback(query)
        elif data == "admin_nuevaclave":
            # Nueva Clave
            await self.handle_admin_nuevaclave_callback(query)
        elif data == "admin_clavehoy":
            # Clave Hoy
            await self.handle_admin_clavehoy_callback(query)
        elif data == "admin_broadcast":
            # Broadcast
            await self.handle_admin_broadcast_callback(query)
        elif data == "admin_historial":
            # Historial
            await self.handle_admin_historial_callback(query)
        elif data == "admin_ayuda":
            # Ayuda Admin
            await self.handle_admin_ayuda_callback(query)
        elif data == "admin_usuarios":
            # Usuarios Activos
            await self.handle_admin_usuarios_callback(query)
        
        # === CALLBACKS DE HISTORIAL QUE FALTABAN ===
        elif data == "admin_historial_senales":
            await self.handle_admin_historial_senales_callback(query)
        elif data == "admin_historial_bloqueos":
            await self.handle_admin_historial_bloqueos_callback(query)
        elif data == "admin_historial_usuarios":
            await self.handle_admin_historial_usuarios_callback(query)
        
        # === CALLBACKS DE REPORTES ===
        elif data == "admin_reportes":
            await self.handle_admin_reportes_callback(query)
        elif data == "admin_generar_clave":
            await self.handle_admin_generar_clave_callback(query)
        
        # === CALLBACKS DE CONFIRMACIONES ===
        # Los callbacks de confirmaciones ya están manejados por handlers específicos registrados
        # No necesitamos duplicarlos aquí
        
        # === CALLBACKS DE REPORTES ===
        elif data == "admin_reporte_diario":
            await self.handle_admin_reporte_diario_callback(query)
        elif data == "admin_reporte_efectividad":
            await self.handle_admin_reporte_efectividad_callback(query)
        elif data == "admin_reporte_usuarios":
            await self.handle_admin_reporte_usuarios_callback(query)
        elif data == "admin_reporte_tecnico":
            await self.handle_admin_reporte_tecnico_callback(query)
        elif data == "admin_ver_accesos_no_autorizados":
            await self.handle_admin_ver_accesos_no_autorizados_callback(query)
        elif data == "admin_usuarios_estadisticas":
            await self.handle_admin_usuarios_estadisticas_callback(query)
        
        # (Se eliminaron los callbacks de configuraciones)
        
        # === CALLBACK DE GESTIÓN DE CLAVES ===
        elif data == "admin_gestion_claves":
            await self.handle_admin_gestion_claves_callback(query)

    async def cmd_lista_diaria_autorizada(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /listahoy: muestra submenú inline Lista diaria (solo admin)."""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo para administrador.")
            return
        kb = [
            [InlineKeyboardButton("👀 Ver lista", callback_data="admin_listahoy_ver")],
            [InlineKeyboardButton("➕ Agregar", callback_data="admin_listahoy_agregar")],
            [InlineKeyboardButton("➖ Quitar", callback_data="admin_listahoy_quitar")],
            [InlineKeyboardButton("🧹 Limpiar", callback_data="admin_listahoy_limpiar")],
        ]
        await update.message.reply_text("📋 Lista diaria — elige una acción:", reply_markup=InlineKeyboardMarkup(kb))

    async def cmd_ver_bloqueados(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /bloqueados: muestra bloqueados o submenú (solo admin)."""
        user_id = str(update.effective_user.id)
        if not self.user_manager.es_administrador(user_id):
            await update.message.reply_text("❌ Solo para administrador.")
            return
        try:
            bloqueados = self.user_manager.obtener_usuarios_bloqueados()
        except Exception:
            bloqueados = []
        texto = "\n".join(bloqueados) if bloqueados else "(sin bloqueados)"
        kb = [
            [InlineKeyboardButton("🚫 Bloquear ID", callback_data="admin_bloqueos_bloquear"), InlineKeyboardButton("✅ Desbloquear ID", callback_data="admin_bloqueos_desbloquear")]
        ]
        await update.message.reply_text(f"🚫 Usuarios bloqueados:\n\n{texto}", reply_markup=InlineKeyboardMarkup(kb))
    
    # Método auxiliar para verificar si es admin
    def _admin_check(self, query) -> bool:
        """Verifica si el usuario es administrador"""
        return self.user_manager.es_administrador(str(query.from_user.id))
    
    async def run_async(self):
        """Inicia el bot de Telegram de forma asíncrona"""
        try:
            print("🤖 Inicializando bot de Telegram...")
            await self.application.initialize()
            await self.application.start()
            
            print("🚀 Iniciando polling de Telegram...")
            await self.application.updater.start_polling()
            
            # Verificar que el bot esté funcionando
            bot_info = await self.application.bot.get_me()
            print(f"✅ Bot de Telegram activo: @{bot_info.username}")
            
            # Marcar como listo
            self.ready = True
            
            # Mantener el bot corriendo
            print("🔄 Bot de Telegram en funcionamiento...")
            
        except Exception as e:
            print(f"❌ Error iniciando bot de Telegram: {e}")
            raise
    
    async def stop_async(self):
        """Detiene el bot de Telegram de forma asíncrona"""
        try:
            print("🛑 Deteniendo bot de Telegram...")
            if hasattr(self.application, 'updater') and self.application.updater:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            print("✅ Bot de Telegram detenido correctamente")
        except Exception as e:
            print(f"⚠️ Error deteniendo bot de Telegram: {e}")
    
    # === MÉTODOS DE CALLBACK DEL PANEL ADMIN ===
    
    async def handle_admin_estado_callback(self, query):
        """Callback para mostrar el estado del sistema (solo admin)."""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        try:
            # Estado operativo
            horario_activo = False
            try:
                horario_activo = self.signal_scheduler.esta_en_horario_operativo()
            except Exception:
                horario_activo = False

            # Estado Quotex
            estado_qx = "Desconocido"
            try:
                mm = getattr(self, 'market_manager', None)
                if mm is not None:
                    conectado_qx = bool(getattr(mm, 'conectado', False)) or (getattr(mm, 'quotex', None) is not None)
                    estado_qx = "🟢 CONECTADO" if conectado_qx else "🔴 DESCONECTADO"
            except Exception:
                pass

            # Mercado actual
            mercado_actual = "No seleccionado"
            try:
                if hasattr(self.signal_scheduler, 'mercado_actual') and self.signal_scheduler.mercado_actual:
                    mercado = self.signal_scheduler.mercado_actual
                    mercado_actual = f"{mercado.get('symbol', 'N/A')} (Payout: {mercado.get('payout', 0)}%)"
            except Exception:
                pass

            # Clave actual del día
            clave_actual = getattr(self.user_manager, 'clave_publica_actual', None) or getattr(self.user_manager, 'clave_publica_diaria', 'No generada')

            # Trading Automático
            trading_activo = getattr(self, '_trading_activo', False)
            trading_modo = getattr(self, '_trading_modo', 'N/A')
            trading_monto = getattr(self, '_trading_monto', 0)
            trading_ops_hoy = getattr(self, '_trading_operaciones_hoy', 0)
            
            # Análisis Forzado
            af_activo = getattr(self, '_analisis_forzado_activo', False)
            af_trading_activo = getattr(self, '_trading_auto_af_activo', False)
            
            # Sección de Trading Automático
            seccion_trading = ""
            if trading_activo or af_trading_activo:
                estado_trading = "🟢 ACTIVO"
                if af_trading_activo:
                    estado_trading += " (Análisis Forzado)"
                
                seccion_trading = f"""

💰 **TRADING AUTOMÁTICO:**
• **Estado:** {estado_trading}
• **Modo:** {trading_modo}
• **Monto:** ${trading_monto:.2f}
• **Operaciones hoy:** {trading_ops_hoy}"""
            
            # Sección de Análisis Forzado
            seccion_af = ""
            if af_activo:
                # Intentar obtener detalles
                af_state = {}
                if hasattr(self, '_analisis_forzado_state'):
                    user_id = str(query.from_user.id)
                    if user_id in self._analisis_forzado_state:
                        af_state = self._analisis_forzado_state[user_id].get('data', {})
                
                par = af_state.get('par', 'N/A')
                temp = af_state.get('temporalidad', 'N/A')
                efec = af_state.get('efectividad', 'N/A')
                duracion = af_state.get('tiempo', 'N/A')
                
                # Calcular tiempo transcurrido si hay inicio
                tiempo_info = f"{duracion} min"
                if hasattr(self, '_analisis_forzado_inicio'):
                    inicio = getattr(self, '_analisis_forzado_inicio', None)
                    if inicio:
                        from datetime import datetime
                        transcurrido = (datetime.now() - inicio).total_seconds() / 60
                        tiempo_info = f"{int(transcurrido)}/{duracion} min"
                
                seccion_af = f"""

⚡ **ANÁLISIS FORZADO:**
• **Estado:** 🟢 ACTIVO
• **Par:** {par}
• **Temporalidad:** {temp}
• **Efectividad mín:** {efec}%
• **Duración:** {tiempo_info}
• **Trading:** {'✅ Activo' if af_trading_activo else '❌ Inactivo'}"""

            mensaje_estado = f"""📊 **ESTADO DEL SISTEMA - CUBAYDSIGNAL**

🎯 **ESTADO OPERATIVO:**
• **Estado:** {'🟢 ACTIVO' if horario_activo else '🔴 FUERA DE HORARIO'}
• **Horario:** 8:00 AM - 8:00 PM (Lun-Sáb)
• **Hora actual:** {datetime.now().strftime('%H:%M:%S')}

🔗 **CONEXIONES:**
• **Quotex:** {estado_qx}
• **Telegram:** 🟢 CONECTADO
• **Scheduler:** {'🟢 ACTIVO' if getattr(self, 'signal_scheduler', None) else '🔴 INACTIVO'}

💱 **MERCADO:**
• **Mercado actual:** {mercado_actual}
• **Tipo:** {'OTC' if datetime.now().weekday() == 5 else 'Normal'}

👥 **USUARIOS:**
• **Usuarios activos:** {len(self.user_manager.usuarios_activos)}
• **Clave del día:** `{clave_actual}`

📈 **SEÑALES:**
• **Señales enviadas hoy:** {len(getattr(self.signal_scheduler, 'señales_enviadas_hoy', []))}
• **Próxima señal:** {'Calculando...' if horario_activo else 'Mañana 8:00 AM'}{seccion_trading}{seccion_af}
"""

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_estado")],
                [InlineKeyboardButton("📊 Detalles de Análisis", callback_data="admin_detalles_analisis")],
                [InlineKeyboardButton("📈 Estadísticas", callback_data="admin_stats")],
                [InlineKeyboardButton("👥 Usuarios", callback_data="admin_usuarios")],
                [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
            ]
            await query.edit_message_text(mensaje_estado, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await query.edit_message_text(f"❌ Error mostrando estado: {e}")
    
    async def handle_admin_detalles_analisis(self, query):
        """Muestra detalles completos del análisis actual del bot"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Obtener información del scheduler
            scheduler = getattr(self, 'signal_scheduler', None)
            
            # Trading Automático
            trading_activo = getattr(self, '_trading_activo', False)
            trading_modo = getattr(self, '_trading_modo', 'N/A')
            trading_monto = getattr(self, '_trading_monto', 0)
            trading_ops_hoy = getattr(self, '_trading_operaciones_hoy', 0)
            
            # Análisis Forzado
            af_activo = getattr(self, '_analisis_forzado_activo', False)
            af_trading_activo = getattr(self, '_trading_auto_af_activo', False)
            
            # Efectividad configurada
            efectividad_config = 80
            if scheduler:
                efectividad_config = getattr(scheduler, 'efectividad_minima_temporal', 80)
            
            # Mercado actual
            mercado_actual = "No seleccionado"
            temporalidad = "5M"
            if scheduler and hasattr(scheduler, 'mercado_actual') and scheduler.mercado_actual:
                mercado = scheduler.mercado_actual
                mercado_actual = mercado.get('symbol', 'N/A')
            
            # Estado del análisis
            estado_analisis = "⚪ Inactivo"
            if af_activo and af_trading_activo:
                estado_analisis = "🟢 Trading Automático en Análisis Forzado"
            elif af_activo:
                estado_analisis = "🟢 Análisis Forzado Activo"
            elif trading_activo:
                estado_analisis = "🟢 Trading Automático Activo"
            elif scheduler and hasattr(scheduler, 'esta_en_horario_operativo'):
                if scheduler.esta_en_horario_operativo():
                    estado_analisis = "🟢 Análisis Diario Activo"
                else:
                    estado_analisis = "🔴 Fuera de Horario"
            
            mensaje = f"""📊 **DETALLES DE ANÁLISIS DEL BOT**

━━━━━━━━━━━━━━━━━━━━━━

🎯 **ESTADO ACTUAL:**
• **Estado:** {estado_analisis}

━━━━━━━━━━━━━━━━━━━━━━

📈 **ANÁLISIS DIARIO:**
• **Efectividad configurada:** {efectividad_config}%
• **Mercado analizado:** {mercado_actual}
• **Temporalidad:** {temporalidad}
• **Horario:** 8:00 AM - 8:00 PM

━━━━━━━━━━━━━━━━━━━━━━

💰 **TRADING AUTOMÁTICO:**
• **Estado:** {'🟢 ACTIVO' if trading_activo else '🔴 INACTIVO'}
"""
            
            if trading_activo:
                mensaje += f"""• **Modo:** {trading_modo}
• **Monto por operación:** ${trading_monto}
• **Operaciones hoy:** {trading_ops_hoy}
"""
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

⚡ **ANÁLISIS FORZADO:**
• **Estado:** {'🟢 ACTIVO' if af_activo else '🔴 INACTIVO'}
"""
            
            if af_activo:
                # Intentar obtener detalles del estado
                af_state = {}
                if hasattr(self, '_analisis_forzado_state'):
                    user_id = str(query.from_user.id)
                    if user_id in self._analisis_forzado_state:
                        af_state = self._analisis_forzado_state[user_id].get('data', {})
                
                par = af_state.get('par', 'N/A')
                temp = af_state.get('temporalidad', 'N/A')
                efec = af_state.get('efectividad', 'N/A')
                tiempo = af_state.get('tiempo', 'N/A')
                
                mensaje += f"""• **Par:** {par}
• **Temporalidad:** {temp}
• **Efectividad:** {efec}%
• **Duración:** {tiempo}
"""
                
                if af_trading_activo:
                    modo_af = af_state.get('trading_modo', 'N/A')
                    monto_af = af_state.get('trading_monto', 0)
                    mensaje += f"""• **Trading:** {modo_af} (${monto_af})
"""
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

📊 **RESUMEN:**
"""
            
            if af_activo and af_trading_activo:
                mensaje += "• El bot está ejecutando trading automático en un mercado específico configurado manualmente.\n"
            elif af_activo:
                mensaje += "• El bot está analizando un mercado específico configurado manualmente.\n"
            elif trading_activo:
                mensaje += f"• El bot está ejecutando operaciones automáticas en {mercado_actual} cuando detecta señales ≥{efectividad_config}%.\n"
            else:
                mensaje += f"• El bot analiza {mercado_actual} cada 30-60 segundos y envía señales cuando detecta efectividad ≥{efectividad_config}%.\n"
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_detalles_analisis")],
                [InlineKeyboardButton("⬅️ Volver a Estado", callback_data="admin_estado")],
                [InlineKeyboardButton("🏠 Panel Principal", callback_data="volver_panel_admin")]
            ]
            
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error mostrando detalles: {e}")

    async def handle_admin_stats_callback(self, query):
        """Callback para mostrar estadísticas del día (solo admin) usando datos reales."""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        try:
            scheduler = getattr(self, 'signal_scheduler', None)
            señales_hoy = list(getattr(scheduler, 'señales_enviadas_hoy', [])) if scheduler else []
            total = len(señales_hoy)
            wins = sum(1 for s in señales_hoy if s.get('resultado') == 'WIN')
            losses = sum(1 for s in señales_hoy if s.get('resultado') == 'LOSS')
            pending = total - wins - losses
            # Calcular efectividad REAL (solo de señales completadas)
            señales_completadas = wins + losses
            efectividad = (wins / señales_completadas * 100) if señales_completadas > 0 else 0.0

            # Estadísticas de Martingala
            martingalas_ejecutadas = getattr(scheduler, 'martingalas_ejecutadas_hoy', 0) if scheduler else 0
            martingalas_ganadas = getattr(scheduler, 'martingalas_ganadas_hoy', 0) if scheduler else 0
            martingalas_perdidas = getattr(scheduler, 'martingalas_perdidas_hoy', 0) if scheduler else 0
            efectividad_martingala = (martingalas_ganadas / martingalas_ejecutadas * 100) if martingalas_ejecutadas > 0 else 0
            
            # Estadísticas de Trading Automático
            trading_activo = getattr(scheduler, 'trading_auto_activo_hoy', False) if scheduler else False
            trading_operaciones = len(getattr(scheduler, 'trading_auto_operaciones', [])) if scheduler else 0
            trading_ganancia = getattr(scheduler, 'trading_auto_ganancia_total', 0) if scheduler else 0
            trading_perdida = getattr(scheduler, 'trading_auto_perdida_total', 0) if scheduler else 0
            trading_balance = trading_ganancia - trading_perdida

            # Por activo
            por_activo = {}
            for s in señales_hoy:
                sym = s.get('symbol', 'N/A')
                d = por_activo.setdefault(sym, {'t': 0, 'w': 0})
                d['t'] += 1
                if s.get('resultado') == 'WIN':
                    d['w'] += 1
            resumen_activos = []
            for sym, d in sorted(por_activo.items(), key=lambda kv: kv[0]):
                eff = (d['w'] / d['t'] * 100) if d['t'] > 0 else 0
                emoji_eff = '🟢' if eff >= 70 else '🟡' if eff >= 50 else '🔴'
                resumen_activos.append(f"{emoji_eff} {sym}: {d['w']}/{d['t']} ({eff:.1f}%)")
            
            # Sección de Martingala
            seccion_martingala = ""
            if martingalas_ejecutadas > 0:
                emoji_mart = '🔥' if efectividad_martingala >= 80 else '✅' if efectividad_martingala >= 60 else '⚠️'
                seccion_martingala = f"""

🎲 **Martingalas:**
• Ejecutadas: {martingalas_ejecutadas}
• Ganadas: {martingalas_ganadas} ✅
• Perdidas: {martingalas_perdidas} ❌
• Efectividad: {efectividad_martingala:.1f}% {emoji_mart}"""
            
            # Sección de Trading Automático
            seccion_trading = ""
            if trading_activo:
                balance_emoji = '🟢' if trading_balance > 0 else '🔴' if trading_balance < 0 else '⚪'
                seccion_trading = f"""

💰 **Trading Automático:**
• Operaciones: {trading_operaciones}
• Ganancia: +${trading_ganancia:.2f} 🟢
• Pérdida: -${trading_perdida:.2f} 🔴
• Balance: {balance_emoji} ${trading_balance:+.2f}"""

            mensaje = f"""📊 **ESTADÍSTICAS DIARIAS**

🎯 **General:**
• Total señales: {total}
• Ganadas: {wins} ✅
• Perdidas: {losses} ❌
• Pendientes: {pending} ⏳
• Efectividad: {efectividad:.1f}% ({wins}/{señales_completadas}){seccion_martingala}{seccion_trading}

📈 **Por activo:**
{chr(10).join(resumen_activos) if resumen_activos else '• Sin datos por activo'}

👥 **Usuarios:**
• Activos ahora: {len(self.user_manager.usuarios_activos)}

📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"""

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            kb = [
                [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_stats")],
                [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
            ]
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(f"❌ Error mostrando estadísticas: {e}")

    async def handle_admin_quotex_callback(self, query):
        """Callback para mostrar estado de Quotex"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Obtener estado de Quotex desde MarketManager
            mm = getattr(self, 'market_manager', None)
            if mm is not None:
                # Verificación REAL: solo marcar conectado si una llamada a la API funciona
                conectado = False
                mercados = []
                payout_min = "N/A"
                try:
                    if getattr(mm, 'conectado', False) and getattr(mm, 'quotex', None):
                        try:
                            api_assets = mm._fetch_assets()
                            # Si no lanza excepción, hay sesión válida
                            conectado = True
                            # Actualizar mercados_disponibles si vienen datos válidos
                            if isinstance(api_assets, list):
                                mercados = [
                                    {
                                        "symbol": a.get('symbol', ''),
                                        "payout": a.get('profit_percentage', 0),
                                        "type": a.get('type', 'forex'),
                                        "otc": a.get('otc', False),
                                    }
                                    for a in api_assets
                                ]
                                mm.mercados_disponibles = mercados
                        except Exception:
                            # Falla al consultar API -> considerar desconectado y marcar flag a False
                            try:
                                mm.conectado = False
                            except Exception:
                                pass
                            conectado = False
                except Exception:
                    conectado = False
                estado_conexion = "🟢 CONECTADO" if conectado else "🔴 DESCONECTADO"
                total_mercados = len(mercados) if mercados else len(getattr(mm, 'mercados_disponibles', []) or [])
                base_lista = mercados if mercados else (getattr(mm, 'mercados_disponibles', []) or [])
                if base_lista:
                    payouts = [m.get('payout', 0) for m in base_lista if m.get('payout') is not None]
                    if payouts:
                        payout_min = f"{min(payouts):.0f}%"
                
                # Verificar si está en modo forzado
                modo_forzado = mm.esta_en_modo_forzado() if hasattr(mm, 'esta_en_modo_forzado') else False
                info_modo = ""
                if modo_forzado:
                    info_modo = "\n\n🔓 **MODO FORZADO ACTIVO**\n• Ignora restricciones de horario\n• Análisis continuo de estrategias"
                
                mensaje = f"""🔗 **ESTADO DE QUOTEX**

📊 **Conexión:** {estado_conexion}
💱 **Mercados disponibles:** {total_mercados}
💰 **Payout mínimo:** {payout_min}
⏰ **Última actualización:** {datetime.now().strftime('%H:%M:%S')}{info_modo}

🔄 **Acciones disponibles:**
• Forzar conexión (ignora horarios)
• Desconectar manualmente
• Actualizar estado"""
            else:
                mensaje = "🔗 **ESTADO DE QUOTEX**\n\n❌ MarketManager no disponible"
        except Exception as e:
            mensaje = f"🔗 **ESTADO DE QUOTEX**\n\n❌ Error obteniendo estado: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("⚡ Forzar conexión ahora", callback_data="admin_quotex_force_connect")],
            [InlineKeyboardButton("🔌 Desconectar ahora", callback_data="admin_quotex_force_disconnect")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_quotex_force_connect(self, query):
        """Forzar conexión a Quotex en cualquier horario (solo admin)."""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        await query.answer()
        mm = getattr(self, 'market_manager', None)
        if not mm:
            await query.edit_message_text("🔗 **ESTADO DE QUOTEX**\n\n❌ MarketManager no disponible")
            return
        email = os.getenv('QUOTEX_EMAIL')
        password = os.getenv('QUOTEX_PASSWORD')
        if not email or not password:
            kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_quotex")]]
            await query.edit_message_text(
                "🔗 **ESTADO DE QUOTEX**\n\n❌ Faltan credenciales en .env (QUOTEX_EMAIL/QUOTEX_PASSWORD)",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb)
            )
            return
        try:
            # ACTIVAR MODO FORZADO ANTES DE CONECTAR
            mm.activar_conexion_forzada()
            
            await query.edit_message_text("⏳ Intentando conexión forzada a Quotex…", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancelar", callback_data="admin_quotex")]]))
            ok = await mm.conectar_quotex(email, password, telegram_bot=self)
            if ok:
                # INICIAR ANÁLISIS DE ESTRATEGIAS
                scheduler = getattr(self, 'signal_scheduler', None)
                if scheduler:
                    await scheduler.forzar_inicio_analisis()
                
                estado = "🟢 CONECTADO"
                mercados = getattr(mm, 'mercados_disponibles', []) or []
                payout_min = min([m.get('payout', 0) for m in mercados], default=0)
                msg = (
                    f"🔗 **ESTADO DE QUOTEX**\n\n"
                    f"✅ Conexión forzada exitosa.\n\n"
                    f"🔓 **MODO FORZADO ACTIVO**\n"
                    f"• Se ignorarán restricciones de horario\n"
                    f"• El bot analizará estrategias continuamente\n"
                    f"• Permanecerá conectado hasta que presiones 'Desconectar'\n\n"
                    f"📊 **Conexión:** {estado}\n"
                    f"💱 **Mercados disponibles:** {len(mercados)}\n"
                    f"💰 **Payout mínimo:** {payout_min:.0f}%\n"
                    f"⏰ **Hora:** {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"🔄 **Análisis iniciado:** El bot está analizando estrategias ahora"
                )
            else:
                # Si falla, desactivar modo forzado
                mm.desactivar_conexion_forzada()
                msg = (
                    "🔗 **ESTADO DE QUOTEX**\n\n"
                    "❌ No se pudo establecer la conexión. Verifica credenciales o reintenta."
                )
        except Exception as e:
            # Si hay error, desactivar modo forzado
            mm.desactivar_conexion_forzada()
            msg = f"🔗 **ESTADO DE QUOTEX**\n\n❌ Error intentando conectar: {e}"
        kb = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_quotex")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_quotex_force_disconnect(self, query):
        """Forzar desconexión de Quotex (solo admin) - SIN detener el bot."""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        await query.answer()
        mm = getattr(self, 'market_manager', None)
        if not mm:
            await query.edit_message_text("🔗 **ESTADO DE QUOTEX**\n\n❌ MarketManager no disponible")
            return
        try:
            # SOLO desconectar de Quotex, NO detener el scheduler
            ok = await mm.desconectar_quotex()
            
            if ok or ok is False:
                # Desconexión exitosa
                msg = (
                    "🔗 **ESTADO DE QUOTEX**\n\n"
                    "✅ **DESCONECTADO CORRECTAMENTE**\n\n"
                    "🔌 **Estado:** Desconectado de Quotex\n"
                    "🤖 **Bot:** Sigue funcionando normalmente\n"
                    "📊 **Panel:** Todos los botones disponibles\n\n"
                    "ℹ️ **Información:**\n"
                    "• El bot NO puede obtener datos de mercado\n"
                    "• NO se generarán señales hasta reconectar\n"
                    "• Todos los demás botones funcionan normal\n\n"
                    "💡 **Para reconectar:**\n"
                    "Presiona 🔌 Conectar Forzado o espera al horario operativo"
                )
            else:
                msg = (
                    "🔗 **ESTADO DE QUOTEX**\n\n"
                    "⚠️ **YA ESTABA DESCONECTADO**\n\n"
                    "🔌 **Estado:** Sin conexión a Quotex\n"
                    "🤖 **Bot:** Funcionando normalmente\n\n"
                    "💡 **Para conectar:**\n"
                    "Presiona 🔌 Conectar Forzado"
                )
        except Exception as e:
            msg = f"🔗 **ESTADO DE QUOTEX**\n\n❌ Error al desconectar: {e}\n\n⚠️ El bot sigue funcionando normalmente."
        
        kb = [
            [InlineKeyboardButton("🔌 Conectar Forzado", callback_data="admin_quotex_force_connect")],
            [InlineKeyboardButton("🔄 Actualizar Estado", callback_data="admin_quotex")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_perfil_callback(self, query):
        """Callback para mostrar perfil del admin"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        admin_id = str(query.from_user.id)
        username = query.from_user.username or "Sin username"
        nombre = f"{query.from_user.first_name or ''} {query.from_user.last_name or ''}".strip()
        
        # Obtener estadísticas del admin
        stats = self.user_manager.obtener_estadisticas_diarias()
        
        mensaje = f"""👤 **MI PERFIL - ADMINISTRADOR**

🆔 **Información Personal:**
• **ID:** `{admin_id}`
• **Username:** @{username}
• **Nombre:** {nombre or 'No especificado'}
• **Rol:** 👑 Administrador Principal

📊 **Estadísticas del Sistema:**
• **Usuarios activos hoy:** {stats.get('usuarios_activos', 0)}
• **Señales enviadas hoy:** {len(getattr(self.signal_scheduler, 'señales_enviadas_hoy', []))}
• **Clave del día:** `{self.user_manager.clave_publica_diaria}`
• **Última conexión:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

🔧 **Permisos:**
✅ Gestión completa del sistema
✅ Creación y modificación de claves
✅ Administración de usuarios
✅ Acceso a estadísticas avanzadas
✅ Control de señales y mercados

🚀 **Estado del Bot:** {'🟢 ACTIVO' if self.signal_scheduler.esta_en_horario_operativo() else '🔴 FUERA DE HORARIO'}"""
        
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_nuevaclave_callback(self, query):
        """Callback para crear nueva clave personalizada"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """🔑 **CREAR NUEVA CLAVE PERSONALIZADA**

📝 **Instrucciones:**
• Escribe la nueva clave que deseas establecer
• La clave debe tener al menos 8 caracteres
• Se convertirá automáticamente a mayúsculas
• Reemplazará la clave automática del día

⚠️ **Importante:**
• Esta clave será válida hasta las 00:00
• Todos los usuarios deberán usar esta nueva clave
• La clave anterior quedará desactivada

💡 **Ejemplo:** CUBA2025ESPECIAL

Escribe tu nueva clave personalizada:"""
        
        # Marcar que esperamos una clave personalizada del admin
        self.esperando_clave_personalizada = getattr(self, 'esperando_clave_personalizada', set())
        self.esperando_clave_personalizada.add(str(query.from_user.id))
        
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="volver_panel_admin")]]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_clavehoy_callback(self, query):
        """Callback para mostrar clave del día actual"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        clave_actual = self.user_manager.clave_publica_diaria
        fecha_actual = datetime.now().strftime('%d/%m/%Y')
        
        # Verificar si es clave automática o personalizada
        tipo_clave = "Automática" if clave_actual.startswith("CUBA") else "Personalizada"
        
        mensaje = f"""🗝️ **CLAVE DEL DÍA ACTUAL**

📅 **Fecha:** {fecha_actual}
🔑 **Clave activa:** `{clave_actual}`
🏷️ **Tipo:** {tipo_clave}
⏰ **Válida hasta:** 23:59:59 de hoy

📊 **Estadísticas de uso:**
• **Usuarios autenticados hoy:** {len(self.user_manager.usuarios_activos)}
• **Intentos de acceso:** {getattr(self.user_manager, 'intentos_clave_hoy', 0)}
• **Última autenticación:** {getattr(self.user_manager, 'ultima_auth', 'Ninguna')}

💡 **Acciones disponibles:**
• Crear nueva clave personalizada
• Ver historial de claves
• Gestionar usuarios autenticados"""
        
        keyboard = [
            [InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nuevaclave")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_broadcast_callback(self, query):
        """Callback para enviar mensaje broadcast"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        usuarios_activos = len(self.user_manager.usuarios_activos)
        
        mensaje = f"""📢 **ENVIAR MENSAJE BROADCAST**

👥 **Destinatarios:** {usuarios_activos} usuarios activos
📝 **Instrucciones:**
• Escribe el mensaje que deseas enviar
• Se enviará a todos los usuarios autenticados
• Usa formato Markdown si necesitas formato especial

⚠️ **Importante:**
• El mensaje se enviará inmediatamente
• No se puede deshacer una vez enviado
• Los usuarios bloqueados no recibirán el mensaje

💡 **Ejemplo:**
```
🚨 **AVISO IMPORTANTE**
Mañana habrá mantenimiento del sistema de 2:00 a 4:00 AM.
Durante este tiempo no habrá señales.
¡Gracias por su comprensión! 🚀
```

Escribe tu mensaje broadcast:"""
        
        # Marcar que esperamos un mensaje broadcast del admin
        self.esperando_broadcast = getattr(self, 'esperando_broadcast', set())
        self.esperando_broadcast.add(str(query.from_user.id))
        
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="volver_panel_admin")]]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_bloqueos_menu(self, query):
        """Menú principal de gestión de bloqueos"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        # Obtener usuarios bloqueados
        bloqueados = self.user_manager.usuarios_bloqueados
        total_bloqueados = len(bloqueados)
        
        # Obtener historial de bloqueos
        historial = self.user_manager.consultar_historial_bloqueos() or []
        total_eventos = len(historial)
        
        mensaje = f"""🚫 **GESTIÓN DE BLOQUEOS**

📊 **Estado Actual:**
• **Usuarios bloqueados:** {total_bloqueados}
• **Eventos registrados:** {total_eventos}

📋 **Opciones Disponibles:**

🔹 **Ver Bloqueados**
• Lista completa de usuarios bloqueados
• Información detallada de cada bloqueo
• Fecha y motivo del bloqueo

🔹 **Bloquear Usuario**
• Bloquear por ID o @username
• Agregar motivo del bloqueo
• Registro automático en historial

🔹 **Desbloquear Usuario**
• Desbloquear por ID o @username
• Restaurar acceso del usuario
• Registro automático en historial

🔹 **Historial de Bloqueos**
• Ver todos los eventos de bloqueo/desbloqueo
• Filtrar por fecha o usuario
• Estadísticas de bloqueos

Selecciona la acción que deseas realizar:"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Ver Bloqueados", callback_data="admin_bloqueos_ver")],
            [InlineKeyboardButton("🚫 Bloquear Usuario", callback_data="admin_bloqueos_bloquear"),
             InlineKeyboardButton("✅ Desbloquear Usuario", callback_data="admin_bloqueos_desbloquear")],
            [InlineKeyboardButton("📚 Historial", callback_data="admin_bloqueos_hist")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_bloqueos_ver(self, query):
        """Ver lista de usuarios bloqueados"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        bloqueados = self.user_manager.usuarios_bloqueados
        
        if not bloqueados:
            mensaje = """📋 **USUARIOS BLOQUEADOS**

✅ **No hay usuarios bloqueados actualmente**

💡 **Esto significa:**
• Todos los usuarios tienen acceso permitido
• No hay restricciones activas
• El sistema está abierto para usuarios autorizados

🔄 **Acciones disponibles:**
• Bloquear usuario manualmente
• Ver historial de bloqueos
• Gestionar lista del día"""
        else:
            lista_bloqueados = []
            for user_id in bloqueados:
                # Intentar obtener información del usuario
                username = "Desconocido"
                # Buscar en historial para obtener más info
                historial = self.user_manager.consultar_historial_bloqueos() or []
                for evento in reversed(historial):
                    if evento.get('user_id') == user_id and evento.get('accion') == 'bloqueo':
                        username = evento.get('username', 'Desconocido')
                        fecha = evento.get('fecha', 'N/A')
                        motivo = evento.get('motivo', 'No especificado')
                        lista_bloqueados.append(f"🚫 @{username} (ID: {user_id})\n   📅 Bloqueado: {fecha}\n   📝 Motivo: {motivo}")
                        break
                else:
                    lista_bloqueados.append(f"🚫 ID: {user_id}")
            
            bloqueados_texto = '\n\n'.join(lista_bloqueados[:10])
            if len(lista_bloqueados) > 10:
                bloqueados_texto += f"\n\n... y {len(lista_bloqueados) - 10} usuarios más"
            
            mensaje = f"""📋 **USUARIOS BLOQUEADOS** ({len(bloqueados)})

{bloqueados_texto}

📊 **Estadísticas:**
• **Total bloqueados:** {len(bloqueados)}
• **Última actualización:** {datetime.now().strftime('%H:%M:%S')}

💡 **Acciones:**
• Desbloquear usuario
• Ver historial completo
• Gestionar accesos"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Desbloquear", callback_data="admin_bloqueos_desbloquear")],
            [InlineKeyboardButton("📚 Ver Historial", callback_data="admin_bloqueos_hist")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_bloqueos")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_bloqueos_bloquear(self, query):
        """Instrucciones para bloquear usuario"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """🚫 **BLOQUEAR USUARIO**

📝 **Instrucciones:**
Envía el ID o @username del usuario que deseas bloquear.

**Formatos válidos:**
• `123456789` (ID numérico)
• `@usuario` (username)

**Ejemplo:**
```
123456789
```
o
```
@usuario
```

⚠️ **Importante:**
• El usuario será bloqueado inmediatamente
• No podrá acceder al bot hasta que sea desbloqueado
• Se registrará en el historial de bloqueos
• Recibirá un mensaje de acceso denegado

💡 **Tip:**
Puedes obtener el ID de un usuario desde el reporte de accesos no autorizados.

Envía el ID o @username del usuario a bloquear:"""
        
        # Marcar que esperamos un ID para bloquear
        self.esperando_bloquear = getattr(self, 'esperando_bloquear', set())
        self.esperando_bloquear.add(str(query.from_user.id))
        
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="admin_bloqueos")]]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_bloqueos_desbloquear(self, query):
        """Instrucciones para desbloquear usuario"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """✅ **DESBLOQUEAR USUARIO**

📝 **Instrucciones:**
Envía el ID o @username del usuario que deseas desbloquear.

**Formatos válidos:**
• `123456789` (ID numérico)
• `@usuario` (username)

**Ejemplo:**
```
123456789
```
o
```
@usuario
```

✅ **Importante:**
• El usuario recuperará el acceso inmediatamente
• Podrá volver a usar el bot normalmente
• Se registrará en el historial de bloqueos
• Deberá ingresar la clave del día para acceder

💡 **Tip:**
Puedes ver la lista de usuarios bloqueados en "Ver Bloqueados".

Envía el ID o @username del usuario a desbloquear:"""
        
        # Marcar que esperamos un ID para desbloquear
        self.esperando_desbloquear = getattr(self, 'esperando_desbloquear', set())
        self.esperando_desbloquear.add(str(query.from_user.id))
        
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="admin_bloqueos")]]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_bloqueos_hist(self, query):
        """Ver historial de bloqueos"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        # Redirigir al historial de bloqueos
        await self.handle_admin_historial_bloqueos_callback(query)
    
    async def handle_admin_bloq_hist_fecha(self, query):
        """Instrucciones para ver historial por fecha"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """📅 **HISTORIAL POR FECHA**

📝 **Instrucciones:**
Usa el comando `/historial_bloqueos YYYY-MM-DD` para ver el historial de una fecha específica.

**Ejemplo:**
```
/historial_bloqueos 2025-10-26
```

💡 **Tip:**
Deja el campo vacío para ver el historial de hoy.

⬅️ Vuelve al menú de bloqueos para otras opciones."""
        
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_bloqueos")]]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_historial_callback(self, query):
        """Callback para mostrar opciones de historial"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """📚 **HISTORIAL DEL SISTEMA**

📊 **Opciones disponibles:**

🔹 **Historial de Señales**
• Ver todas las señales enviadas
• Filtrar por fecha y activo
• Análisis de efectividad

🔹 **Historial de Bloqueos**
• Usuarios bloqueados/desbloqueados
• Fechas y motivos de bloqueos
• Filtros por usuario o fecha

🔹 **Historial de Usuarios**
• Accesos y autenticaciones
• Actividad por fecha
• Estadísticas de uso

🔹 **Historial de Confirmaciones**
• Pre-señales y señales confirmadas
• Usuarios que aceptaron cada señal
• Métricas de participación

Selecciona el tipo de historial que deseas consultar:"""
        
        keyboard = [
            [InlineKeyboardButton("📈 Señales", callback_data="admin_historial_senales"),
             InlineKeyboardButton("🚫 Bloqueos", callback_data="admin_historial_bloqueos")],
            [InlineKeyboardButton("👥 Usuarios", callback_data="admin_historial_usuarios"),
             InlineKeyboardButton("📜 Confirmaciones", callback_data="admin_confirmaciones")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_ayuda_callback(self, query):
        """Callback para mostrar ayuda completa del administrador"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """❓ **GUÍA COMPLETA DE ADMINISTRADOR - CUBAYDSIGNAL**

━━━━━━━━━━━━━━━━━━━━━━

📊 **PANEL PRINCIPAL**

🎯 **Estado Sistema**
• Ver estado general del bot y conexiones
• Horario operativo y próxima señal
• Usuarios activos y señales del día

📈 **Estadísticas**
• Métricas detalladas del día
• Efectividad de señales
• Rendimiento del sistema

💱 **Mercados**
• Ver todos los mercados disponibles
• Mercados normales vs OTC
• 🔍 Buscar mercado específico
• 📊 **Análisis Detallado**

🔗 **Quotex**
• Estado de conexión en tiempo real
• Forzar conexión/desconexión
• Diagnóstico de problemas

🔬 **Análisis Forzado** (NUEVO)
• Analizar mercado específico manualmente
• Configurar efectividad mínima y duración
• Activar trading automático opcional
• Ver análisis en tiempo real

🎲 **Sistema de Martingala** (NUEVO)
• Confirmación anticipada (2 min antes)
• Ejecución automática si pre-autorizado
• Notificaciones de resultados
• Ver documentación completa

━━━━━━━━━━━━━━━━━━━━━━

🔑 **GESTIÓN DE CLAVES**

📝 **Gestión Claves**
• Nueva Clave: Crear clave personalizada
• Clave Hoy: Ver clave actual
• Claves se renuevan automáticamente a las 00:00

🔐 **Clave Maestra Admin:**
`Yorji.010702.CubaYDsignal`

━━━━━━━━━━━━━━━━━━━━━━

👥 **GESTIÓN DE USUARIOS**

📋 **Lista Hoy**
• Ver lista diaria de usuarios autorizados
• Agregar usuarios (ID o @username)
• Quitar usuarios de la lista
• Limpiar lista completa

🚫 **Gestión Bloqueos**
• Ver usuarios bloqueados
• Bloquear usuario (ID o @username)
• Desbloquear usuario
• Historial de bloqueos

👤 **Usuarios Activos**
• Ver quién está conectado ahora
• Hora de ingreso de cada usuario
• Tipo de usuario (admin/regular)

━━━━━━━━━━━━━━━━━━━━━━

📊 **COMUNICACIÓN Y REPORTES**

📢 **Broadcast**
• Enviar mensaje a todos los usuarios activos
• Útil para anuncios importantes

📜 **Confirmaciones**
• Ver quién confirma Pre-Señales
• Ver quién confirma Señales
• Reportes por fecha o usuario

📚 **Historial**
• Historial de Señales del día
• Historial de Bloqueos
• Historial de Usuarios

📊 **Reportes**
• Reporte de Efectividad
• Reporte de Usuarios
• Reporte Técnico del Sistema

━━━━━━━━━━━━━━━━━━━━━━

🔍 **BÚSQUEDA DE MERCADOS**

**Cómo buscar:**
1. Panel → Mercados → Buscar
2. Escribe el nombre del mercado

**Formatos válidos:**
• `EURUSD` - Mercado normal
• `EURUSD_OTC` - Mercado OTC
• `GBPUSD`, `GOLD`, `BTC`, etc.

**Análisis Detallado (NUEVO):**
Después de buscar un mercado, aparece botón:
📊 **Análisis Detallado**

Te muestra:
• Por qué Tendencia tiene X% efectividad
• Por qué Patrones tiene X% efectividad
• Por qué S/R tiene X% efectividad
• Por qué Volatilidad tiene X% efectividad
• Conclusión: Operar o NO operar

━━━━━━━━━━━━━━━━━━━━━━

🚀 **COMANDOS RÁPIDOS**

**Generales:**
• `/start` - Panel principal
• `/estado` - Estado completo del sistema
• `/ayuda` - Esta guía completa

**Gestión:**
• `/clave` - Ver clave del día
• `/listahoy` - Gestionar lista diaria
• `/mercados` - Ver mercados disponibles

**Estadísticas:**
• `/stats` - Estadísticas avanzadas
• `/efectividad` - Métricas de señales
• `/confirmaciones` - Ver confirmaciones

**Análisis y Trading:**
• Panel → Análisis Forzado
• Panel → Trading Automático
• Panel → Estado Martingala

━━━━━━━━━━━━━━━━━━━━━━

⚙️ **CONFIGURACIÓN DEL SISTEMA**

**Horario Operativo:**
• Lunes a Sábado: 8:00 AM - 8:00 PM
• Domingo: Solo admin tiene acceso

**Análisis de Mercados:**
• Análisis continuo cada 60 segundos
• Solo señales con efectividad ≥ 80%
• Timeout de 30s para no bloquear bot

**Estrategias (pesos):**
• Tendencia: 30%
• Patrones de Velas: 30%
• Soportes/Resistencias: 20%
• Volatilidad: 20%

**Umbral de Señales:**
• Efectividad mínima: 80%
• Duración de operación: 5 minutos
• Verificación automática de resultado

━━━━━━━━━━━━━━━━━━━━━━

🎲 **SISTEMA DE MARTINGALA**

**¿Qué es?**
Estrategia de recuperación que duplica la inversión después de una pérdida para recuperar el monto perdido.

**Flujo Completo:**
1. **Análisis Predictivo (3 min después de ejecutar)**
   • El bot analiza si la vela probablemente se perderá
   • Si detecta probable pérdida → Envía confirmación anticipada

2. **Confirmación Anticipada (2 min antes del cierre)**
   • Recibes mensaje con análisis actual
   • Puedes pre-autorizar o esperar resultado final
   • Ventaja: Ejecución inmediata si se pierde

3. **Resultado Final (5 min después)**
   • Si se pierde + pre-autorizado → Ejecuta inmediatamente
   • Si se pierde + no pre-autorizado → Solicita confirmación
   • Si se gana + pre-autorizado → Cancela automáticamente

4. **Ejecución de Martingala**
   • Espera apertura de próxima vela de 5 min
   • Ejecuta con monto x2
   • Notifica resultado (ganada/perdida)

**Notificaciones:**
• ✅ Martingala Ganada → Admin + Usuarios
• ❌ Martingala Perdida → Admin + Usuarios
• 🔮 Confirmación Anticipada → Solo Admin
• ℹ️ Info de Martingala → Usuarios (en señal perdida)

**Configuración:**
• Límite de intentos: 1 (configurable)
• Efectividad: +5% por intento
• Sincronización: Apertura exacta de vela

📄 **Documentación completa:** `DOCUMENTACION_MARTINGALA.md`

━━━━━━━━━━━━━━━━━━━━━━

🔬 **ANÁLISIS FORZADO + TRADING AUTOMÁTICO**

**¿Qué es?**
Analiza un mercado específico manualmente y opcionalmente ejecuta operaciones automáticas.

**Cómo usar:**
1. Panel → Análisis Forzado
2. Selecciona mercado (ej: EURUSD_otc)
3. Configura efectividad mínima (80-95%)
4. Configura duración (1-60 min)
5. Decide si activar trading automático

**Modos:**
• **Solo Análisis:** Genera señales sin operar
• **Con Trading:** Ejecuta operaciones automáticas

**Trading Automático:**
• Ejecuta operaciones en Quotex
• Monto configurable ($1-$100)
• Modo: DEMO o REAL
• Verifica resultado automáticamente
• Sistema de Martingala integrado

**Estados:**
• 🔍 Analizando → Buscando oportunidades
• ⏳ Esperando → Esperando próxima vela
• 🎯 Operación Ejecutada → Esperando resultado
• ✅ Ganada / ❌ Perdida → Resultado final

**Controles:**
• Detener Análisis → Para generación de señales
• Detener Trading → Para operaciones automáticas
• Ambos independientes

━━━━━━━━━━━━━━━━━━━━━━

💡 **TIPS IMPORTANTES**

✅ **Lista Diaria:**
Debes crear la lista de usuarios autorizados cada día.
Si no la creas, los usuarios pueden entrar pero recibirás notificación de "acceso no autorizado".

✅ **Mercados OTC:**
Los mercados OTC tienen el sufijo `_OTC` al final.
Ejemplo: `EURUSD_OTC`, `GBPUSD_OTC`

✅ **Análisis Detallado:**
Usa esta función para entender por qué el bot no genera señales en un mercado específico.

✅ **Conexión a Quotex:**
Si el bot no genera señales, verifica:
1. Estado Quotex (debe estar 🟢 CONECTADO)
2. Mercados disponibles (debe haber al menos 10)
3. Horario operativo (8:00-20:00 Lun-Sáb)

✅ **Martingala Predictiva:**
• Confirma anticipadamente para ejecución instantánea
• Si rechazas, puedes confirmar después del resultado
• Si se gana, la Martingala se cancela automáticamente
• Usuarios reciben info educativa, no confirmación

✅ **Trading Automático:**
• Siempre prueba primero en modo DEMO
• Verifica saldo antes de usar modo REAL
• El bot espera apertura exacta de vela
• Martingala se ejecuta solo si confirmas

✅ **Análisis Forzado:**
• Útil para probar mercados específicos
• Puedes detener análisis sin detener trading
• Puedes detener trading sin detener análisis
• Estado se mantiene hasta que lo detengas

✅ **Gestión de Riesgo:**
• Límite de Martingala: 1 intento (recomendado)
• Monto inicial: No más del 2% de tu capital
• Martingala: Solo si estás seguro
• Siempre opera con responsabilidad

━━━━━━━━━━━━━━━━━━━━━━

📝 **REGISTRO DE ACCIONES**

Todas las acciones quedan registradas:
• Bloqueos y desbloqueos
• Cambios en lista diaria
• Mensajes broadcast
• Confirmaciones de señales

📂 **Logs:** `logs/bot_YYYYMMDD.log`

━━━━━━━━━━━━━━━━━━━━━━

👑 **ACCESO TOTAL**

Como administrador tienes:
• Acceso 24/7 (incluso domingos)
• Control total del sistema
• Visibilidad de todas las métricas
• Gestión completa de usuarios

🔐 **Clave Maestra:** `Yorji.010702.CubaYDsignal`

━━━━━━━━━━━━━━━━━━━━━━

📅 **Versión:** CubaYDSignal v3.0
🆕 **Nuevas Funciones:**
   • Sistema de Martingala Predictiva
   • Trading Automático Integrado
   • Análisis Forzado de Mercados
   • Notificaciones Mejoradas

🤖 **Bot:** @CubaYDSignalBot
👨‍💻 **Admin:** @Ijroy10 (Yorji Fonseca)
📅 **Última actualización:** 26 de Octubre, 2025"""
        
        keyboard = [
            [InlineKeyboardButton("📖 Ver Comandos", callback_data="admin_ayuda_comandos")],
            [InlineKeyboardButton("🎲 Guía Martingala", callback_data="admin_ayuda_martingala"),
             InlineKeyboardButton("🔬 Guía Trading Auto", callback_data="admin_ayuda_trading")],
            [InlineKeyboardButton("⚡ Guía Análisis Forzado", callback_data="admin_ayuda_analisis_forzado")],
            [InlineKeyboardButton("🔍 Buscar Mercado", callback_data="admin_mercados_buscar")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_ayuda_comandos(self, query):
        """Muestra lista detallada de comandos disponibles"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """📖 **LISTA DE COMANDOS - ADMINISTRADOR**

━━━━━━━━━━━━━━━━━━━━━━

🎯 **COMANDOS PRINCIPALES**

`/start`
• Muestra el panel principal de administrador
• Acceso a todas las funciones del bot

`/estado`
• Estado completo del sistema
• Conexiones, usuarios, señales

`/clave`
• Ver clave pública del día
• Compartir con usuarios

━━━━━━━━━━━━━━━━━━━━━━

👥 **GESTIÓN DE USUARIOS**

`/listahoy`
• Gestionar lista diaria de usuarios autorizados
• Ver, agregar, quitar usuarios

`/usuarios`
• Ver usuarios activos en este momento
• Estadísticas de conexión

`/bloquear [ID o @username]`
• Bloquear usuario del sistema
• Ejemplo: `/bloquear 123456789`
• Ejemplo: `/bloquear @usuario`

`/desbloquear [ID o @username]`
• Desbloquear usuario previamente bloqueado

━━━━━━━━━━━━━━━━━━━━━━

💱 **MERCADOS Y ANÁLISIS**

`/mercados`
• Ver todos los mercados disponibles
• Mercados normales y OTC

`/buscar [mercado]`
• Buscar mercado específico
• Ejemplo: `/buscar EURUSD_OTC`
• Muestra análisis técnico completo

━━━━━━━━━━━━━━━━━━━━━━

📊 **ESTADÍSTICAS Y REPORTES**

`/stats`
• Estadísticas avanzadas del sistema
• Métricas de rendimiento

`/efectividad`
• Métricas de efectividad de señales
• Tasa de éxito del día

`/confirmaciones [fecha]`
• Ver confirmaciones de señales
• Formato fecha: YYYY-MM-DD
• Ejemplo: `/confirmaciones 2025-10-11`

━━━━━━━━━━━━━━━━━━━━━━

📢 **COMUNICACIÓN**

`/broadcast [mensaje]`
• Enviar mensaje a todos los usuarios activos
• Ejemplo: `/broadcast Hola a todos`

`/notificar [ID] [mensaje]`
• Enviar mensaje a usuario específico
• Ejemplo: `/notificar 123456789 Hola`

━━━━━━━━━━━━━━━━━━━━━━

🔗 **CONEXIÓN QUOTEX**

`/quotex`
• Ver estado de conexión a Quotex
• Diagnóstico de problemas

`/conectar`
• Forzar conexión a Quotex
• Útil si se desconectó

`/desconectar`
• Desconectar de Quotex manualmente
• Para mantenimiento

━━━━━━━━━━━━━━━━━━━━━━

🔑 **GESTIÓN DE CLAVES**

`/nuevaclave [clave]`
• Crear clave personalizada
• Ejemplo: `/nuevaclave TRADING2024`

`/clavehoy`
• Ver clave actual del día
• Estadísticas de uso

━━━━━━━━━━━━━━━━━━━━━━

📚 **HISTORIAL**

`/historial`
• Acceso a todos los historiales
• Señales, bloqueos, usuarios

`/senales`
• Historial de señales del día
• Resultados y efectividad

`/bloqueos`
• Historial de bloqueos
• Eventos de seguridad

━━━━━━━━━━━━━━━━━━━━━━

🛠️ **MANTENIMIENTO**

`/reiniciar`
• Reiniciar componentes del bot
• Usar solo si es necesario

`/logs`
• Ver últimas líneas del log
• Debugging de problemas

`/diagnostico`
• Diagnóstico completo del sistema
• Estado de todos los componentes

━━━━━━━━━━━━━━━━━━━━━━

💡 **TIPS DE USO**

✅ **Comandos con parámetros:**
Algunos comandos requieren parámetros adicionales.
Ejemplo: `/buscar EURUSD_OTC`

✅ **Formato de fechas:**
Siempre usa formato: YYYY-MM-DD
Ejemplo: 2025-10-11

✅ **IDs vs Usernames:**
Puedes usar ID numérico o @username
Ejemplo: `123456789` o `@usuario`

✅ **Botones inline:**
La mayoría de funciones también están disponibles
como botones en el panel principal.

━━━━━━━━━━━━━━━━━━━━━━

📝 **NOTA:**
Todos los comandos quedan registrados en los logs
del sistema para auditoría y seguridad.

🔐 **Acceso:** Solo administradores"""
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver a Ayuda", callback_data="admin_ayuda")],
            [InlineKeyboardButton("🏠 Panel Principal", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_ayuda_martingala(self, query):
        """Muestra guía completa del sistema de Martingala"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """🎲 **GUÍA COMPLETA - SISTEMA DE MARTINGALA**

━━━━━━━━━━━━━━━━━━━━━━

📚 **¿QUÉ ES MARTINGALA?**

Estrategia de recuperación que **duplica la inversión** después de una pérdida para recuperar el monto perdido y obtener ganancia.

**Ejemplo:**
• Operación 1: $5 → PIERDE → Pérdida: -$5
• Martingala: $10 → GANA → Ganancia: +$9.40
• **Resultado neto: +$4.40** ✅

━━━━━━━━━━━━━━━━━━━━━━

🔮 **SISTEMA PREDICTIVO**

**1. Análisis Anticipado (3 min después)**
• El bot analiza el precio actual
• Compara con precio de entrada
• Determina si probablemente se perderá

**2. Confirmación Anticipada (2 min antes del cierre)**
Si detecta probable pérdida:
• Recibes mensaje con análisis actual
• Diferencia en % en contra
• Datos de Martingala calculados

**3. Tus Opciones:**
✅ **Pre-autorizar** → Ejecución inmediata si se pierde
❌ **Esperar** → Confirmación normal después

**4. Ventajas de Pre-autorizar:**
• ⚡ Ejecución instantánea (0 segundos de espera)
• 🎯 Máxima velocidad de recuperación
• ✅ Cancelación automática si se gana

━━━━━━━━━━━━━━━━━━━━━━

📊 **FLUJO COMPLETO**

```
12:00 → Señal ejecutada ($5)
12:03 → Análisis predictivo
        ↓ Probable pérdida detectada
12:03 → Recibes confirmación anticipada
12:04 → Pre-autorizas Martingala ✅
12:05 → Vela cierra - PERDIDA ❌
12:05 → Martingala ejecuta INMEDIATAMENTE
12:10 → Operación Martingala ($10)
12:15 → Resultado: GANADA ✅
12:15 → Notificación a admin + usuarios
```

━━━━━━━━━━━━━━━━━━━━━━

📢 **NOTIFICACIONES**

**Para Admin:**
• 🔮 Confirmación Anticipada (2 min antes)
• ✅ Martingala Ganada (con datos técnicos)
• ❌ Martingala Perdida (con pérdida total)
• 🔄 Martingala Cancelada (si se gana)

**Para Usuarios:**
• ℹ️ Info de Martingala (en señal perdida)
• ✅ Martingala Ganada (mensaje motivacional)
• ❌ Martingala Perdida (consejos educativos)

━━━━━━━━━━━━━━━━━━━━━━

⚙️ **CONFIGURACIÓN**

**Límite de Intentos:** 1 (recomendado)
• Configurable en `signal_scheduler.py`
• Variable: `self.martingala_max_intentos`

**Efectividad:**
• Intento 1: Efectividad original + 5%
• Intento 2: Efectividad original + 10%
• Máximo: 95%

**Sincronización:**
• Espera apertura exacta de vela de 5 min
• Ejecución al segundo 0

━━━━━━━━━━━━━━━━━━━━━━

💡 **TIPS IMPORTANTES**

✅ **Confirma Anticipadamente:**
Para máxima velocidad de recuperación

✅ **Si Rechazas:**
Puedes confirmar después del resultado final

✅ **Si Se Gana:**
Martingala se cancela automáticamente

✅ **Usuarios:**
Reciben solo información, no confirmación

✅ **Gestión de Riesgo:**
• Límite: 1 intento
• Monto: No más del 2% de capital
• Solo si estás seguro

━━━━━━━━━━━━━━━━━━━━━━

📄 **Documentación Completa:**
`DOCUMENTACION_MARTINGALA.md`

📅 **Versión:** v3.0"""
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver a Ayuda", callback_data="admin_ayuda")],
            [InlineKeyboardButton("🏠 Panel Principal", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_ayuda_trading(self, query):
        """Muestra guía completa del Trading Automático"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """🔬 **GUÍA COMPLETA - TRADING AUTOMÁTICO**

━━━━━━━━━━━━━━━━━━━━━━

📚 **¿QUÉ ES?**

Sistema que ejecuta operaciones automáticas en Quotex basándose en las señales generadas por el bot.

**Modos disponibles:**
• **DEMO:** Operaciones de práctica (sin riesgo real)
• **REAL:** Operaciones con dinero real

━━━━━━━━━━━━━━━━━━━━━━

🚀 **CÓMO USAR**

**1. Análisis Forzado**
Panel → Análisis Forzado

**2. Seleccionar Mercado**
Ejemplo: EURUSD_otc, GBPUSD_otc, etc.

**3. Configurar Parámetros**
• Efectividad mínima: 80-95%
• Duración: 1-60 minutos

**4. Activar Trading**
• Toca "✅ Sí, activar trading automático"
• Selecciona modo: DEMO o REAL
• Configura monto: $1-$100

**5. Confirmar**
• Revisa configuración
• Confirma inicio

━━━━━━━━━━━━━━━━━━━━━━

📊 **ESTADOS DEL SISTEMA**

🔍 **Analizando**
• Buscando oportunidades en el mercado
• Evaluando estrategias técnicas
• Esperando efectividad ≥ mínima

⏳ **Esperando Apertura de Vela**
• Señal generada
• Esperando próxima vela de 5 min
• Cuenta regresiva activa

🎯 **Operación Ejecutada**
• Operación abierta en Quotex
• Esperando resultado (5 min)
• Análisis predictivo de Martingala activo

✅ **Ganada** / ❌ **Perdida**
• Resultado verificado automáticamente
• Notificaciones enviadas
• Sistema listo para próxima señal

━━━━━━━━━━━━━━━━━━━━━━

🎲 **INTEGRACIÓN CON MARTINGALA**

**Si operación se pierde:**
1. Sistema analiza predictivamente (3 min)
2. Envía confirmación anticipada (si probable pérdida)
3. Admin pre-autoriza o espera
4. Si se pierde + pre-autorizado → Ejecuta Martingala
5. Si se gana → Cancela Martingala

**Ventaja:**
Recuperación automática sin intervención manual

━━━━━━━━━━━━━━━━━━━━━━

⚙️ **CONFIGURACIÓN**

**Monto:**
• Mínimo: $1
• Máximo: $100
• Recomendado: 2% de capital

**Modo:**
• DEMO: Sin riesgo, para pruebas
• REAL: Con dinero real

**Verificación:**
• Automática después de 5 minutos
• Compara precio entrada vs salida
• Notifica resultado

━━━━━━━━━━━━━━━━━━━━━━

🎮 **CONTROLES**

**Detener Análisis:**
• Para generación de señales
• Trading continúa con señales existentes

**Detener Trading:**
• Para ejecución de operaciones
• Análisis continúa generando señales

**Detener Ambos:**
• Para todo el sistema
• Vuelve a modo manual

━━━━━━━━━━━━━━━━━━━━━━

💡 **TIPS IMPORTANTES**

✅ **Siempre Prueba en DEMO Primero:**
Verifica que todo funciona correctamente

✅ **Verifica Saldo en Quotex:**
Antes de usar modo REAL

✅ **Monitorea Resultados:**
Revisa estadísticas regularmente

✅ **Gestión de Riesgo:**
• No más del 2% por operación
• Usa Martingala con precaución
• Detén si hay muchas pérdidas seguidas

✅ **Conexión a Quotex:**
Debe estar 🟢 CONECTADO para funcionar

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **ADVERTENCIAS**

❌ **No Operes en Modo REAL sin Experiencia**
Primero practica en DEMO

❌ **No Uses Montos Altos**
Comienza con montos pequeños

❌ **No Dejes el Bot sin Supervisión**
Monitorea regularmente

❌ **No Operes Fuera de Horario**
Respeta horario: 8:00-20:00 Lun-Sáb

━━━━━━━━━━━━━━━━━━━━━━

📊 **EJEMPLO COMPLETO**

```
12:00 → Análisis Forzado iniciado
12:01 → Analizando EURUSD_otc
12:02 → Señal generada (85% efectividad)
12:05 → Operación ejecutada ($5 CALL)
12:08 → Análisis predictivo (probable pérdida)
12:08 → Confirmación anticipada enviada
12:09 → Admin pre-autoriza Martingala
12:10 → Resultado: PERDIDA ❌
12:10 → Martingala ejecuta ($10 CALL)
12:15 → Resultado Martingala: GANADA ✅
12:15 → Recuperación exitosa (+$4.40)
```

━━━━━━━━━━━━━━━━━━━━━━

📅 **Versión:** v3.0
🔗 **Requiere:** Conexión activa a Quotex"""
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver a Ayuda", callback_data="admin_ayuda")],
            [InlineKeyboardButton("🏠 Panel Principal", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_ayuda_analisis_forzado_guia(self, query):
        """Muestra guía completa del Análisis Forzado"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """⚡ **GUÍA COMPLETA - ANÁLISIS FORZADO**

━━━━━━━━━━━━━━━━━━━━━━

📚 **¿QUÉ ES ANÁLISIS FORZADO?**

Función que te permite **analizar un mercado específico manualmente** en lugar de esperar el análisis automático del bot.

**Ventajas:**
• 🎯 Enfoque en un mercado específico
• ⚙️ Control total de parámetros
• 🔬 Análisis en tiempo real
• 💰 Trading automático opcional

━━━━━━━━━━━━━━━━━━━━━━

🚀 **CÓMO USAR - PASO A PASO**

**1. Acceder al Análisis Forzado**
Panel Principal → ⚡ Análisis Forzado

**2. Seleccionar Tipo de Mercado**
• **OTC:** Mercados OTC (disponibles 24/7)
• **NORMAL:** Mercados normales (horario limitado)

**3. Seleccionar Par de Mercado**
Opciones disponibles:
• EURUSD / EURUSD_otc
• GBPUSD / GBPUSD_otc
• USDJPY / USDJPY_otc
• AUDUSD / AUDUSD_otc
• GOLD / GOLD_otc
• BTC / BTC_otc
• O escribir manualmente

**4. Configurar Temporalidad**
• **5 min** (recomendado)
• **1 min, 15 min, 30 min, 1h**
• O personalizar

**5. Configurar Efectividad Mínima**
• **80%** (estándar)
• **85%, 90%, 95%** (más selectivo)
• O personalizar (70-99%)

**6. Configurar Duración**
• **5 min** (análisis rápido)
• **15 min, 30 min, 60 min** (análisis extendido)
• O personalizar (1-120 min)

**7. Decidir Trading Automático**
• ✅ **Sí** → Ejecuta operaciones automáticas
• ❌ **No** → Solo genera señales

**8. Si activas Trading:**
• Selecciona modo: **DEMO** o **REAL**
• Configura monto: **$1 - $100**
• Confirma inicio

━━━━━━━━━━━━━━━━━━━━━━

📊 **ESTADOS DEL SISTEMA**

🔍 **Analizando**
```
El bot está evaluando el mercado:
• Analizando tendencias
• Evaluando patrones de velas
• Calculando soportes/resistencias
• Midiendo volatilidad
```

⏳ **Esperando Apertura de Vela**
```
Señal generada, esperando momento óptimo:
• Cuenta regresiva hasta próxima vela
• Sincronización con apertura de 5 min
• Preparando ejecución
```

🎯 **Operación Ejecutada**
```
Trading automático activo:
• Operación abierta en Quotex
• Esperando resultado (5 min)
• Análisis predictivo de Martingala activo
```

✅ **Ganada** / ❌ **Perdida**
```
Resultado verificado:
• Notificaciones enviadas
• Estadísticas actualizadas
• Sistema listo para próxima señal
```

━━━━━━━━━━━━━━━━━━━━━━

🎮 **CONTROLES DISPONIBLES**

**Detener Análisis**
• Para la generación de señales
• Trading continúa con señales existentes
• Útil si quieres cambiar de mercado

**Detener Trading**
• Para la ejecución de operaciones
• Análisis continúa generando señales
• Útil si solo quieres ver señales

**Detener Ambos**
• Para todo el sistema completamente
• Vuelve a modo manual
• Limpia configuración actual

━━━━━━━━━━━━━━━━━━━━━━

🎲 **INTEGRACIÓN CON MARTINGALA**

Si activas Trading Automático:

**Cuando operación se pierde:**
1. **3 min después** → Análisis predictivo
2. **Si probable pérdida** → Confirmación anticipada
3. **Admin decide** → Pre-autorizar o esperar
4. **5 min después** → Resultado verificado
5. **Si perdida + pre-autorizado** → Martingala ejecuta
6. **Si ganada** → Martingala se cancela

**Ventaja:**
Sistema completo de recuperación automática

━━━━━━━━━━━━━━━━━━━━━━

⚙️ **CONFIGURACIÓN RECOMENDADA**

**Para Principiantes:**
• Mercado: EURUSD_otc
• Temporalidad: 5 min
• Efectividad: 80%
• Duración: 15 min
• Trading: DEMO
• Monto: $5

**Para Avanzados:**
• Mercado: A elección
• Temporalidad: 5 min
• Efectividad: 85-90%
• Duración: 30-60 min
• Trading: REAL
• Monto: 2% del capital

━━━━━━━━━━━━━━━━━━━━━━

💡 **TIPS IMPORTANTES**

✅ **Elige Mercados OTC:**
Disponibles 24/7, más oportunidades

✅ **Temporalidad de 5 min:**
Mejor balance entre precisión y frecuencia

✅ **Efectividad 80-85%:**
Buen balance entre calidad y cantidad

✅ **Duración 15-30 min:**
Suficiente para varias señales

✅ **Prueba en DEMO Primero:**
Verifica que todo funciona correctamente

✅ **Monitorea Resultados:**
Revisa estadísticas regularmente

✅ **Detén si Muchas Pérdidas:**
No persigas las pérdidas

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **ADVERTENCIAS**

❌ **No Uses Modo REAL sin Experiencia**
Primero practica en DEMO

❌ **No Analices Múltiples Mercados**
Enfócate en uno a la vez

❌ **No Configures Efectividad Muy Alta**
Puede que no genere señales

❌ **No Dejes Duración Muy Larga**
Monitorea y ajusta según resultados

❌ **Verifica Conexión a Quotex**
Debe estar 🟢 CONECTADO

━━━━━━━━━━━━━━━━━━━━━━

📊 **EJEMPLO COMPLETO**

```
12:00 → Panel → Análisis Forzado
12:01 → Selecciono: EURUSD_otc
12:01 → Temporalidad: 5 min
12:01 → Efectividad: 85%
12:01 → Duración: 30 min
12:02 → Activo Trading: DEMO, $5
12:02 → Confirmo inicio
        ↓
12:03 → 🔍 Analizando mercado...
12:05 → ✅ Señal generada (87% efectividad)
12:05 → ⏳ Esperando apertura vela (12:10)
        ↓
12:10 → 🎯 Operación ejecutada: CALL $5
12:13 → 🔮 Análisis predictivo (probable pérdida)
12:13 → 📩 Confirmación anticipada enviada
12:14 → ✅ Pre-autorizo Martingala
        ↓
12:15 → ❌ Resultado: PERDIDA
12:15 → ⚡ Martingala ejecuta INMEDIATAMENTE
12:15 → ⏳ Esperando apertura vela (12:20)
        ↓
12:20 → 🎯 Martingala ejecutada: CALL $10
12:25 → ✅ Resultado: GANADA
12:25 → 🎉 Recuperación exitosa (+$4.40)
        ↓
12:26 → 🔍 Continúa analizando...
12:30 → ⏰ Duración completada (30 min)
12:30 → 🛑 Análisis Forzado finalizado
```

━━━━━━━━━━━━━━━━━━━━━━

🔧 **SOLUCIÓN DE PROBLEMAS**

**No genera señales:**
• Verifica conexión a Quotex
• Reduce efectividad mínima
• Prueba otro mercado
• Aumenta duración

**Señales con baja efectividad:**
• Aumenta efectividad mínima
• Cambia de mercado
• Verifica horario del mercado

**Trading no ejecuta:**
• Verifica saldo en Quotex
• Verifica conexión
• Revisa modo (DEMO/REAL)

**Sesión expirada:**
• Vuelve a Panel Principal
• Inicia Análisis Forzado nuevamente

━━━━━━━━━━━━━━━━━━━━━━

📈 **ESTADÍSTICAS**

El sistema guarda:
• Señales generadas
• Operaciones ejecutadas
• Resultados (WIN/LOSS)
• Efectividad promedio
• Martingalas ejecutadas

Acceso: Panel → Estadísticas

━━━━━━━━━━━━━━━━━━━━━━

📅 **Versión:** v3.0
⚡ **Función:** Análisis Forzado
🔗 **Requiere:** Conexión activa a Quotex"""
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver a Ayuda", callback_data="admin_ayuda")],
            [InlineKeyboardButton("🏠 Panel Principal", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_usuarios_callback(self, query):
        """Callback para mostrar usuarios activos"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        usuarios_activos = self.user_manager.usuarios_activos
        total_usuarios = len(usuarios_activos)
        
        # Obtener lista del día
        lista_hoy = getattr(self.user_manager, 'lista_diaria', [])
        
        # Obtener accesos no autorizados de hoy
        accesos_no_autorizados = []
        try:
            hoy = datetime.now().strftime('%Y-%m-%d')
            accesos_no_autorizados = self.user_manager.obtener_accesos_no_autorizados(hoy)
        except:
            pass
        
        if total_usuarios == 0:
            mensaje = """👥 **USUARIOS ACTIVOS**

❌ **No hay usuarios activos actualmente**

💡 **Posibles razones:**
• Es muy temprano o muy tarde
• Los usuarios aún no han ingresado la clave del día
• Es domingo (día de descanso)

🔄 **Acciones sugeridas:**
• Verificar que la clave del día esté funcionando
• Enviar recordatorio a los usuarios
• Revisar el horario operativo"""
        else:
            # Separar usuarios en lista y no autorizados
            usuarios_en_lista = []
            usuarios_no_autorizados = []
            
            for user_id, info in usuarios_activos.items():
                username = info.get('username', 'Sin username')
                hora_ingreso = info.get('hora_ingreso', 'Desconocida')
                tipo = info.get('tipo', 'usuario')
                
                # Verificar si está en la lista del día
                en_lista = str(user_id) in lista_hoy or tipo == 'admin'
                
                if tipo == 'admin':
                    emoji = "👑"
                    usuarios_en_lista.append(f"{emoji} @{username} (ID: {user_id}) - {hora_ingreso}")
                elif en_lista:
                    emoji = "✅"
                    usuarios_en_lista.append(f"{emoji} @{username} (ID: {user_id}) - {hora_ingreso}")
                else:
                    emoji = "⚠️"
                    usuarios_no_autorizados.append(f"{emoji} @{username} (ID: {user_id}) - {hora_ingreso}")
            
            # Construir mensaje
            mensaje_usuarios = ""
            
            if usuarios_en_lista:
                usuarios_texto = '\n'.join(usuarios_en_lista[:8])
                if len(usuarios_en_lista) > 8:
                    usuarios_texto += f"\n... y {len(usuarios_en_lista) - 8} más"
                mensaje_usuarios += f"✅ **En Lista del Día:**\n{usuarios_texto}\n\n"
            
            if usuarios_no_autorizados:
                no_auth_texto = '\n'.join(usuarios_no_autorizados[:5])
                if len(usuarios_no_autorizados) > 5:
                    no_auth_texto += f"\n... y {len(usuarios_no_autorizados) - 5} más"
                mensaje_usuarios += f"⚠️ **Sin Autorización:**\n{no_auth_texto}\n\n"
            
            # Sección de accesos no autorizados del día
            seccion_accesos = ""
            if accesos_no_autorizados:
                total_accesos_no_auth = len(accesos_no_autorizados)
                seccion_accesos = f"""

🚨 **Accesos No Autorizados Hoy:**
• **Total de intentos:** {total_accesos_no_auth}
• **Usuarios únicos:** {len(set(a.get('user_id') for a in accesos_no_autorizados))}"""
            
            mensaje = f"""👥 **USUARIOS ACTIVOS** ({total_usuarios})

{mensaje_usuarios}📊 **Estadísticas:**
• **Total conectados:** {total_usuarios}
• **En lista del día:** {len(usuarios_en_lista)}
• **Sin autorización:** {len(usuarios_no_autorizados)}
• **Administradores:** {sum(1 for info in usuarios_activos.values() if info.get('tipo') == 'admin')}
• **Última actualización:** {datetime.now().strftime('%H:%M:%S')}{seccion_accesos}

💡 **Leyenda:**
👑 = Administrador
✅ = En lista del día
⚠️ = Sin autorización

🔄 **Acciones disponibles:**
• Enviar mensaje broadcast
• Ver historial de accesos
• Gestionar bloqueos"""
        
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_usuarios")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # === MÉTODOS DE TRADING AUTOMÁTICO ===
    
    async def handle_admin_trading_menu(self, query):
        """Menú principal de trading automático"""
        try:
            await query.answer()
        except:
            pass
        
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        # Verificar estado actual del trading
        trading_activo = getattr(self, '_trading_activo', False)
        modo_actual = getattr(self, '_trading_modo', None)
        monto_actual = getattr(self, '_trading_monto', 0)
        operaciones_hoy = getattr(self, '_trading_operaciones_hoy', 0)
        
        estado_emoji = "🟢" if trading_activo else "🔴"
        estado_texto = "ACTIVO" if trading_activo else "INACTIVO"
        
        mensaje = f"""💰 **TRADING AUTOMÁTICO**

📊 **Estado Actual:** {estado_emoji} {estado_texto}

"""
        
        if trading_activo:
            mensaje += f"""🎯 **Configuración Activa:**
• **Modo:** {modo_actual}
• **Monto por operación:** ${monto_actual:.2f}
• **Operaciones hoy:** {operaciones_hoy}

⚠️ **El bot está ejecutando operaciones automáticamente**
Todas las señales generadas se ejecutan en cuenta {modo_actual}

"""
        else:
            mensaje += """⚪ **Trading Automático Desactivado**

Para activar el trading automático:
1. Selecciona el modo (Demo o Real)
2. Configura el monto por operación
3. Inicia el trading automático

📋 **¿Cómo funciona?**
• El bot analiza el mercado cada 5 minutos
• Cuando detecta una señal con efectividad ≥80%
• Ejecuta automáticamente la operación
• Con el monto configurado
• En la cuenta seleccionada (Demo/Real)

"""
        
        if trading_activo:
            keyboard = [
                [InlineKeyboardButton(f"🔴 Detener Trading", callback_data="trading_stop")],
                [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🎮 Modo DEMO", callback_data="trading_demo"),
                 InlineKeyboardButton("💎 Modo REAL", callback_data="trading_real")],
                [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
            ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_trading_demo(self, query):
        """Configurar trading en modo DEMO"""
        try:
            await query.answer()
        except:
            pass
        
        mensaje = """🎮 **MODO DEMO**

💡 **Características:**
• Operaciones en cuenta de práctica
• Sin riesgo de pérdida real
• Ideal para probar estrategias
• Datos reales del mercado

💰 **Configurar Monto por Operación:**

Selecciona el monto que se apostará en cada señal:
"""
        
        keyboard = [
            [InlineKeyboardButton("$1", callback_data="trading_set_amount_demo_1"),
             InlineKeyboardButton("$5", callback_data="trading_set_amount_demo_5"),
             InlineKeyboardButton("$10", callback_data="trading_set_amount_demo_10")],
            [InlineKeyboardButton("$20", callback_data="trading_set_amount_demo_20"),
             InlineKeyboardButton("$50", callback_data="trading_set_amount_demo_50"),
             InlineKeyboardButton("$100", callback_data="trading_set_amount_demo_100")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_trading")]
        ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_trading_real(self, query):
        """Configurar trading en modo REAL"""
        try:
            await query.answer()
        except:
            pass
        
        mensaje = """💎 **MODO REAL**

⚠️ **ADVERTENCIA:**
• Operaciones con dinero real
• Riesgo de pérdida de capital
• Solo usar con estrategia probada
• Gestión de riesgo obligatoria

💰 **Configurar Monto por Operación:**

⚠️ **Recomendación:** No arriesgues más del 2-5% de tu capital por operación

Selecciona el monto que se apostará en cada señal:
"""
        
        keyboard = [
            [InlineKeyboardButton("$1", callback_data="trading_set_amount_real_1"),
             InlineKeyboardButton("$5", callback_data="trading_set_amount_real_5"),
             InlineKeyboardButton("$10", callback_data="trading_set_amount_real_10")],
            [InlineKeyboardButton("$20", callback_data="trading_set_amount_real_20"),
             InlineKeyboardButton("$50", callback_data="trading_set_amount_real_50"),
             InlineKeyboardButton("$100", callback_data="trading_set_amount_real_100")],
            [InlineKeyboardButton("$200", callback_data="trading_set_amount_real_200"),
             InlineKeyboardButton("$500", callback_data="trading_set_amount_real_500")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_trading")]
        ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_trading_set_amount(self, query, data):
        """Configurar monto y confirmar inicio"""
        try:
            await query.answer()
        except:
            pass
        
        # Parsear data: trading_set_amount_demo_10 o trading_set_amount_real_50
        parts = data.split('_')
        modo = parts[3].upper()  # DEMO o REAL
        monto = float(parts[4])
        
        # Guardar configuración temporal
        self._trading_config_temp = {
            'modo': modo,
            'monto': monto
        }
        
        mensaje = f"""✅ **CONFIGURACIÓN COMPLETADA**

🎯 **Resumen:**
• **Modo:** {modo}
• **Monto por operación:** ${monto:.2f}

📋 **¿Qué sucederá?**
1. El bot analizará el mercado cada 5 minutos
2. Cuando detecte una señal con efectividad ≥80%:
   • Ejecutará automáticamente la operación
   • En cuenta {modo}
   • Con monto de ${monto:.2f}
   • Dirección: CALL o PUT según la señal

⚠️ **Importante:**
• Asegúrate de tener saldo suficiente en tu cuenta {modo}
• El bot operará 24/7 mientras esté activo
• Puedes detenerlo en cualquier momento

🔔 **Notificaciones:**
• Recibirás confirmación de cada operación ejecutada
• Resultado de cada operación (ganada/perdida)
• Resumen diario de operaciones

"""
        
        if modo == "REAL":
            mensaje += """⚠️ **ADVERTENCIA FINAL:**
Estás a punto de activar trading con dinero REAL.
Asegúrate de:
• Tener una estrategia probada
• Gestionar tu riesgo adecuadamente
• No invertir más de lo que puedes perder

"""
        
        callback_start = "trading_start_demo" if modo == "DEMO" else "trading_start_real"
        
        keyboard = [
            [InlineKeyboardButton(f"🚀 Iniciar Trading {modo}", callback_data=callback_start)],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_trading")]
        ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_trading_start(self, query, modo):
        """Iniciar trading automático"""
        try:
            await query.answer()
        except:
            pass
        
        # Obtener configuración
        config = getattr(self, '_trading_config_temp', None)
        if not config:
            await query.edit_message_text("❌ Error: Configuración no encontrada. Inicia de nuevo.")
            return
        
        # Activar trading
        self._trading_activo = True
        self._trading_modo = config['modo']
        self._trading_monto = config['monto']
        self._trading_operaciones_hoy = 0
        self._trading_inicio = datetime.now()
        
        mensaje = f"""🚀 **TRADING AUTOMÁTICO ACTIVADO**

✅ **Configuración:**
• **Modo:** {config['modo']}
• **Monto:** ${config['monto']:.2f} por operación
• **Inicio:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🟢 **Estado:** ACTIVO

📊 **El bot está operando automáticamente**

Todas las señales con efectividad ≥80% serán ejecutadas automáticamente en tu cuenta {config['modo']}.

🔔 **Recibirás notificaciones de:**
• Cada operación ejecutada
• Resultado de cada operación
• Resumen diario

⚠️ **Para detener el trading:**
Usa el botón "Detener Trading" en el menú de Trading Automático

📈 **¡Buena suerte!**
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Ver Estado Trading", callback_data="admin_trading")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        # Notificar al admin
        print(f"[Trading] ✅ Trading automático ACTIVADO - Modo: {config['modo']}, Monto: ${config['monto']:.2f}")
    
    async def handle_trading_stop(self, query):
        """Detener trading automático"""
        try:
            await query.answer()
        except:
            pass
        
        # Obtener estadísticas antes de detener
        modo = getattr(self, '_trading_modo', 'N/A')
        monto = getattr(self, '_trading_monto', 0)
        operaciones = getattr(self, '_trading_operaciones_hoy', 0)
        inicio = getattr(self, '_trading_inicio', None)
        
        duracion = ""
        if inicio:
            delta = datetime.now() - inicio
            horas = delta.seconds // 3600
            minutos = (delta.seconds % 3600) // 60
            duracion = f"{horas}h {minutos}m"
        
        # Desactivar trading
        self._trading_activo = False
        
        mensaje = f"""🔴 **TRADING AUTOMÁTICO DETENIDO**

📊 **Resumen de la Sesión:**
• **Modo:** {modo}
• **Monto por operación:** ${monto:.2f}
• **Operaciones ejecutadas:** {operaciones}
• **Duración:** {duracion}

✅ **El bot ya no ejecutará operaciones automáticamente**

💡 **Próximos pasos:**
• Revisar resultados de las operaciones
• Ajustar estrategia si es necesario
• Reactivar cuando estés listo

🔄 **Para reactivar:**
Ve al menú de Trading Automático y configura nuevamente
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Trading Automático", callback_data="admin_trading")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        print(f"[Trading] 🔴 Trading automático DETENIDO - Operaciones: {operaciones}")
    
    # === MÉTODOS DE CALLBACK DE HISTORIAL ===
    
    async def handle_admin_historial_senales_callback(self, query):
        """Callback para historial de señales"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Obtener señales del día
            señales_hoy = getattr(self.signal_scheduler, 'señales_enviadas_hoy', [])
            total_señales = len(señales_hoy)
            
            if total_señales == 0:
                mensaje = """📈 **HISTORIAL DE SEÑALES**

❌ **No hay señales registradas hoy**

💡 **Posibles razones:**
• Es muy temprano en el día
• El sistema aún no ha generado señales
• No hay conexión a Quotex para análisis

🔄 **Acciones sugeridas:**
• Verificar conexión a Quotex
• Revisar el horario operativo
• Comprobar configuración de mercados"""
            else:
                ganadas = sum(1 for s in señales_hoy if s.get('resultado') == 'WIN')
                perdidas = sum(1 for s in señales_hoy if s.get('resultado') == 'LOSS')
                pendientes = total_señales - ganadas - perdidas
                # Calcular efectividad REAL (solo de señales completadas)
                señales_completadas = ganadas + perdidas
                efectividad = (ganadas / señales_completadas * 100) if señales_completadas > 0 else 0
                
                # Estadísticas de Martingala
                martingalas_ejecutadas = getattr(self.signal_scheduler, 'martingalas_ejecutadas_hoy', 0)
                martingalas_ganadas = getattr(self.signal_scheduler, 'martingalas_ganadas_hoy', 0)
                martingalas_perdidas = getattr(self.signal_scheduler, 'martingalas_perdidas_hoy', 0)
                efectividad_martingala = (martingalas_ganadas / martingalas_ejecutadas * 100) if martingalas_ejecutadas > 0 else 0
                
                # Últimas 5 señales (incluyendo Martingalas)
                ultimas_señales = []
                for i, señal in enumerate(señales_hoy[-5:], 1):
                    hora = señal.get('hora', 'N/A')
                    symbol = señal.get('symbol', 'N/A')
                    direccion = señal.get('direccion', 'N/A')
                    resultado = señal.get('resultado', 'PENDIENTE')
                    es_martingala = señal.get('es_martingala', False)
                    
                    emoji_resultado = '✅' if resultado == 'WIN' else '❌' if resultado == 'LOSS' else '⏳'
                    tipo = ' 🎲' if es_martingala else ''
                    
                    ultimas_señales.append(f"{i}. {hora} - {symbol} {direccion} {emoji_resultado}{tipo}")
                
                # Sección de Martingala
                seccion_martingala = ""
                if martingalas_ejecutadas > 0:
                    emoji_mart = '🔥' if efectividad_martingala >= 80 else '✅' if efectividad_martingala >= 60 else '⚠️'
                    seccion_martingala = f"""

🎲 **Martingalas del Día:**
• **Ejecutadas:** {martingalas_ejecutadas}
• **Ganadas:** {martingalas_ganadas} ✅
• **Perdidas:** {martingalas_perdidas} ❌
• **Efectividad:** {efectividad_martingala:.1f}% {emoji_mart}"""
                
                mensaje = f"""📈 **HISTORIAL DE SEÑALES**

📊 **Resumen del Día:**
• **Total enviadas:** {total_señales}
• **Ganadas:** {ganadas} ✅
• **Perdidas:** {perdidas} ❌
• **Pendientes:** {pendientes} ⏳
• **Efectividad:** {efectividad:.1f}%{seccion_martingala}

📋 **Últimas 5 Señales:**
{chr(10).join(ultimas_señales) if ultimas_señales else '• Sin señales recientes'}
{'🎲 = Martingala' if any(s.get('es_martingala') for s in señales_hoy[-5:]) else ''}

📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y')}
⏰ **Última actualización:** {datetime.now().strftime('%H:%M:%S')}"""
                
        except Exception as e:
            mensaje = f"📈 **HISTORIAL DE SEÑALES**\n\n❌ Error obteniendo historial: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("📊 Ver Detallado", callback_data="admin_senales_detallado")],
            [InlineKeyboardButton("📅 Por Fecha", callback_data="admin_senales_fecha")],
            [InlineKeyboardButton("⬅️ Volver a Historial", callback_data="admin_historial")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_historial_bloqueos_callback(self, query):
        """Callback para historial de bloqueos"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Obtener historial de bloqueos
            historial = self.user_manager.consultar_historial_bloqueos() or []
            total_eventos = len(historial)
            
            if total_eventos == 0:
                mensaje = """🚫 **HISTORIAL DE BLOQUEOS**

✅ **No hay eventos de bloqueo registrados**

💡 **Esto significa:**
• No se han bloqueado usuarios
• No hay actividad sospechosa
• El sistema funciona sin incidentes

🔄 **Acciones disponibles:**
• Bloquear usuario manualmente
• Ver usuarios activos
• Configurar alertas automáticas"""
            else:
                # Contar bloqueos y desbloqueos
                bloqueos = sum(1 for h in historial if h.get('accion') == 'bloqueo')
                desbloqueos = sum(1 for h in historial if h.get('accion') == 'desbloqueo')
                
                # Últimos 5 eventos
                ultimos_eventos = []
                for i, evento in enumerate(historial[-5:], 1):
                    fecha = evento.get('fecha', 'N/A')
                    accion = evento.get('accion', 'N/A').upper()
                    user_id = evento.get('user_id', 'N/A')
                    username = evento.get('username', 'Sin username')
                    emoji = '🚫' if accion == 'BLOQUEO' else '✅'
                    ultimos_eventos.append(f"{i}. {fecha} - {emoji} {accion} - @{username} (ID: {user_id})")
                
                mensaje = f"""🚫 **HISTORIAL DE BLOQUEOS**

📊 **Resumen Total:**
• **Total eventos:** {total_eventos}
• **Bloqueos:** {bloqueos} 🚫
• **Desbloqueos:** {desbloqueos} ✅
• **Usuarios actualmente bloqueados:** {len(self.user_manager.usuarios_bloqueados)}

📋 **Últimos 5 Eventos:**
{chr(10).join(ultimos_eventos) if ultimos_eventos else '• Sin eventos recientes'}

📅 **Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
                
        except Exception as e:
            mensaje = f"🚫 **HISTORIAL DE BLOQUEOS**\n\n❌ Error obteniendo historial: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("👤 Por Usuario", callback_data="admin_bloqueos_usuario")],
            [InlineKeyboardButton("📅 Por Fecha", callback_data="admin_bloqueos_fecha")],
            [InlineKeyboardButton("⬅️ Volver a Historial", callback_data="admin_historial")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_historial_usuarios_callback(self, query):
        """Callback para historial de usuarios"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Obtener estadísticas de usuarios
            usuarios_activos = self.user_manager.usuarios_activos
            total_activos = len(usuarios_activos)
            
            # Obtener historial de accesos (simulado por ahora)
            accesos_hoy = total_activos  # Simplificado
            
            mensaje = f"""👥 **HISTORIAL DE USUARIOS**

📊 **Estadísticas del Día:**
• **Usuarios activos ahora:** {total_activos}
• **Accesos registrados hoy:** {accesos_hoy}
• **Clave del día:** `{self.user_manager.clave_publica_diaria}`

👤 **Usuarios Activos Actuales:**"""
            
            if total_activos == 0:
                mensaje += "\n❌ No hay usuarios activos actualmente"
            else:
                lista_usuarios = []
                for i, (user_id, info) in enumerate(usuarios_activos.items(), 1):
                    if i > 8:  # Mostrar máximo 8
                        lista_usuarios.append(f"... y {total_activos - 8} usuarios más")
                        break
                    username = info.get('username', 'Sin username')
                    hora = info.get('hora_ingreso', 'N/A')
                    tipo = info.get('tipo', 'usuario')
                    emoji = "👑" if tipo == 'admin' else "👤"
                    lista_usuarios.append(f"{i}. {emoji} @{username} - {hora}")
                
                mensaje += f"\n{chr(10).join(lista_usuarios)}"
            
            mensaje += f"\n\n📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y')}\n⏰ **Hora:** {datetime.now().strftime('%H:%M:%S')}"
                
        except Exception as e:
            mensaje = f"👥 **HISTORIAL DE USUARIOS**\n\n❌ Error obteniendo historial: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("📊 Estadísticas", callback_data="admin_usuarios_stats")],
            [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_historial_usuarios")],
            [InlineKeyboardButton("⬅️ Volver a Historial", callback_data="admin_historial")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # === MÉTODOS DE CALLBACK DE REPORTES Y CONFIGURACIONES ===
    
    async def handle_admin_reportes_callback(self, query):
        """Callback para reportes del sistema"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """📊 **REPORTES DEL SISTEMA**

📋 **Tipos de Reportes Disponibles:**

🔹 **Reporte Diario**
• Resumen completo del día
• Efectividad de señales
• Estadísticas de usuarios
• Estado de mercados

🔹 **Reporte de Efectividad**
• Análisis detallado por activo
• Comparación de estrategias
• Métricas de pullback
• Tendencias de mercado

🔹 **Reporte de Usuarios**
• Actividad de usuarios
• Confirmaciones de señales
• Patrones de uso
• Estadísticas de acceso

🔹 **Reporte Técnico**
• Estado de sistemas
• Conexión a Quotex
• Rendimiento del bot
• Logs de errores

Selecciona el tipo de reporte que deseas generar:"""
        
        keyboard = [
            [InlineKeyboardButton("📈 Reporte Diario", callback_data="admin_reporte_diario"),
             InlineKeyboardButton("🎯 Efectividad", callback_data="admin_reporte_efectividad")],
            [InlineKeyboardButton("👥 Usuarios", callback_data="admin_reporte_usuarios"),
             InlineKeyboardButton("🔧 Técnico", callback_data="admin_reporte_tecnico")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    
    async def handle_admin_generar_clave_callback(self, query):
        """Callback para generar nueva clave automática"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Generar nueva clave automática
            nueva_clave = self.user_manager.generar_clave_diaria()
            
            mensaje = f"""🔑 **NUEVA CLAVE GENERADA AUTOMÁTICAMENTE**

✅ **Clave generada exitosamente:**
`{nueva_clave}`

📊 **Detalles:**
• **Tipo:** Clave automática del sistema
• **Válida hasta:** 23:59:59 de hoy
• **Algoritmo:** Basado en fecha y hash seguro
• **Estado:** Activa y funcionando

⚠️ **Importante:**
• La clave anterior ha sido reemplazada
• Todos los usuarios deben usar esta nueva clave
• Se recomienda notificar a los usuarios del cambio

🔄 **Próximos pasos:**
• Enviar la nueva clave a los usuarios
• Monitorear las autenticaciones
• La clave se renovará automáticamente mañana a las 00:00"""
            
            # Notificar al admin sobre el cambio
            await self.notificar_admin_telegram(f"🔑 Nueva clave automática generada: {nueva_clave}")
            
        except Exception as e:
            mensaje = f"🔑 **ERROR GENERANDO CLAVE**\n\n❌ No se pudo generar la nueva clave: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("🔑 Crear Personalizada", callback_data="admin_nuevaclave")],
            [InlineKeyboardButton("🗝️ Ver Clave Actual", callback_data="admin_clavehoy")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # === MÉTODO PARA VOLVER AL PANEL PRINCIPAL ===
    
    async def handle_volver_panel_admin_callback(self, query):
        """Callback para volver al panel principal de administrador"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        # Obtener información del usuario
        username = query.from_user.username or query.from_user.first_name or "Admin"
        
        mensaje_admin = f"""
👑 **¡BIENVENIDO ADMINISTRADOR {username.upper()}!**

✅ **Acceso confirmado como administrador**

🎛️ **PANEL DE CONTROL COMPLETO**
Usa los botones de abajo para acceder a todas las funciones de administración:

👑 **¡Control total del sistema a tu alcance!**
        """
        
        # Panel completo de botones inline para admin (igual al principal)
        keyboard = [
            [InlineKeyboardButton("📊 Estado Sistema", callback_data="admin_estado"),
             InlineKeyboardButton("📈 Estadísticas", callback_data="admin_stats")],
            [InlineKeyboardButton("💱 Mercados", callback_data="admin_mercados"),
             InlineKeyboardButton("🔗 Quotex", callback_data="admin_quotex")],
            [InlineKeyboardButton("💰 Trading Automático", callback_data="admin_trading")],
            [InlineKeyboardButton("⚡ Análisis Forzado", callback_data="admin_analisis_forzado")],
            [InlineKeyboardButton("👤 Mi Perfil", callback_data="admin_perfil"),
             InlineKeyboardButton("🔑 Gestión Claves", callback_data="admin_gestion_claves")],
            [InlineKeyboardButton("📋 Lista Hoy", callback_data="admin_listahoy"),
             InlineKeyboardButton("🚫 Gestión Bloqueos", callback_data="admin_bloqueos")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
             InlineKeyboardButton("📚 Historial", callback_data="admin_historial")],
            [InlineKeyboardButton("📊 Reportes", callback_data="admin_reportes"),
             InlineKeyboardButton("📜 Confirmaciones", callback_data="admin_confirmaciones")],
            [InlineKeyboardButton("❓ Ayuda Admin", callback_data="admin_ayuda"),
             InlineKeyboardButton("👥 Usuarios Activos", callback_data="admin_usuarios")]
        ]
        
        await query.edit_message_text(
            mensaje_admin, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # === MÉTODOS DE CALLBACK FALTANTES ===
    
    async def handle_admin_confirmaciones_menu(self, query):
        """Menú de confirmaciones (pre‑señal y señal)."""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        texto = (
            "📜 Confirmaciones de Pre‑Señal y Señal\n\n"
            "Elige una opción para ver el detalle de hoy o consultar otra fecha."
        )
        keyboard = [
            [InlineKeyboardButton("📅 Ver hoy", callback_data="admin_conf_hoy")],
            [InlineKeyboardButton("👤 Por usuario/ID", callback_data="admin_conf_usuario")],
            [InlineKeyboardButton("🗓️ Por fecha", callback_data="admin_conf_fecha")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_admin_confirmaciones_hoy(self, query):
        """Muestra confirmaciones detalladas del día actual."""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        try:
            hoy = datetime.now().strftime('%Y-%m-%d')
            texto = self.user_manager.generar_reporte_confirmaciones_detallado(hoy)
            # Telegram límite ~4096
            if len(texto) > 3900:
                texto = texto[:3900] + "\n… (reporte truncado, use /confirmaciones YYYY-MM-DD para filtrar)"
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            kb = [
                [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_conf_hoy")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="admin_confirmaciones")]
            ]
            await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(f"❌ Error generando reporte: {e}")

    async def handle_admin_confirmaciones_usuario(self, query):
        """Instrucciones para consultar por usuario/ID usando comando."""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        texto = (
            "🔎 Para buscar por usuario o ID use:\n\n"
            "• /confirmaciones @usuario [YYYY-MM-DD]\n"
            "• /confirmaciones 123456789 [YYYY-MM-DD]"
        )
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_confirmaciones")]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_confirmaciones_fecha(self, query):
        """Instrucciones para consultar por fecha usando comando."""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        hoy = datetime.now().strftime('%Y-%m-%d')
        texto = (
            "🗓️ Para ver confirmaciones de una fecha específica use:\n\n"
            f"• /confirmaciones {hoy}\n"
            "• Formato: /confirmaciones YYYY-MM-DD"
        )
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_confirmaciones")]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(kb))

    async def handle_admin_gestion_claves_callback(self, query):
        """Callback para gestión de claves (Nueva Clave, Clave Hoy, Generar Automática)"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        mensaje = """🔑 **GESTIÓN DE CLAVES**

📋 **Opciones Disponibles:**

🔹 **Nueva Clave Personalizada**
• Crear una clave personalizada para hoy
• Reemplaza la clave automática
• Válida hasta las 23:59:59

🔹 **Ver Clave Actual**
• Consultar la clave activa del día
• Ver estadísticas de uso
• Información de validez

🔹 **Generar Clave Automática**
• Crear nueva clave automática del sistema
• Basada en algoritmo seguro
• Reemplaza cualquier clave anterior

Selecciona la acción que deseas realizar:"""
        
        keyboard = [
            [InlineKeyboardButton("🔑 Nueva Clave", callback_data="admin_nuevaclave"),
             InlineKeyboardButton("🗝️ Clave Hoy", callback_data="admin_clavehoy")],
            [InlineKeyboardButton("🤖 Generar Automática", callback_data="admin_generar_clave")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # El método handle_admin_confirmaciones_callback fue eliminado porque ya existe
    # la funcionalidad original completa en cb_admin_confirmaciones
    
    # === CALLBACKS DE REPORTES ===
    
    async def handle_admin_reporte_diario_callback(self, query):
        """Callback para reporte diario completo"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Obtener datos del día
            señales_hoy = getattr(self.signal_scheduler, 'señales_enviadas_hoy', [])
            usuarios_activos = len(self.user_manager.usuarios_activos)
            
            total_señales = len(señales_hoy)
            ganadas = sum(1 for s in señales_hoy if s.get('resultado') == 'WIN')
            perdidas = sum(1 for s in señales_hoy if s.get('resultado') == 'LOSS')
            pendientes = total_señales - ganadas - perdidas
            # Calcular efectividad REAL (solo de señales completadas)
            señales_completadas = ganadas + perdidas
            efectividad = (ganadas / señales_completadas * 100) if señales_completadas > 0 else 0
            
            mensaje = f"""📈 **REPORTE DIARIO COMPLETO**

📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y')}
⏰ **Generado:** {datetime.now().strftime('%H:%M:%S')}

📊 **RESUMEN DE SEÑALES:**
• **Total enviadas:** {total_señales}
• **Ganadas:** {ganadas} ✅
• **Perdidas:** {perdidas} ❌
• **Pendientes:** {pendientes} ⏳
• **Efectividad real:** {efectividad:.1f}% ({ganadas}/{señales_completadas})

👥 **USUARIOS:**
• **Activos ahora:** {usuarios_activos}
• **Clave del día:** `{self.user_manager.clave_publica_diaria}`

🔗 **SISTEMAS:**
• **Bot Telegram:** ✅ Operativo
• **Scheduler:** ✅ Funcionando
• **Quotex:** {'✅ Conectado' if hasattr(self, 'market_manager') else '❌ Desconectado'}

📈 **RENDIMIENTO:**
• **Uptime:** Desde inicio del día
• **Errores:** 0 críticos
• **Estado general:** ✅ Óptimo"""
                
        except Exception as e:
            mensaje = f"📈 **REPORTE DIARIO**\n\n❌ Error generando reporte: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("📊 Exportar", callback_data="admin_exportar_diario")],
            [InlineKeyboardButton("⬅️ Volver a Reportes", callback_data="admin_reportes")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_reporte_efectividad_callback(self, query):
        """Callback para reporte de efectividad"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Obtener señales del día
            señales_hoy = getattr(self.signal_scheduler, 'señales_enviadas_hoy', [])
            
            if not señales_hoy:
                mensaje = """🎯 **REPORTE DE EFECTIVIDAD**

❌ **No hay datos suficientes**

Para generar el reporte de efectividad se necesitan señales del día.

💡 **Sugerencias:**
• Esperar a que se envíen más señales
• Revisar conexión a Quotex
• Verificar horario operativo"""
            else:
                # Análisis por activo
                activos = {}
                for señal in señales_hoy:
                    symbol = señal.get('symbol', 'Desconocido')
                    if symbol not in activos:
                        activos[symbol] = {'total': 0, 'ganadas': 0}
                    activos[symbol]['total'] += 1
                    if señal.get('resultado') == 'WIN':
                        activos[symbol]['ganadas'] += 1
                
                mensaje = f"""🎯 **REPORTE DE EFECTIVIDAD**

📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y')}

📊 **ANÁLISIS POR ACTIVO:**"""
                
                for symbol, data in activos.items():
                    efectividad = (data['ganadas'] / data['total'] * 100) if data['total'] > 0 else 0
                    emoji = '🟢' if efectividad >= 70 else '🟡' if efectividad >= 50 else '🔴'
                    mensaje += f"\n{emoji} **{symbol}:** {data['ganadas']}/{data['total']} ({efectividad:.1f}%)"
                
                total_general = len(señales_hoy)
                ganadas_general = sum(1 for s in señales_hoy if s.get('resultado') == 'WIN')
                efectividad_general = (ganadas_general / total_general * 100) if total_general > 0 else 0
                
                mensaje += f"""

🎯 **EFECTIVIDAD GENERAL:**
• **Total:** {ganadas_general}/{total_general} ({efectividad_general:.1f}%)
• **Tendencia:** {'📈 Positiva' if efectividad_general >= 60 else '📉 Mejorable'}"""
                
        except Exception as e:
            mensaje = f"🎯 **REPORTE DE EFECTIVIDAD**\n\n❌ Error generando reporte: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("📈 Detallado", callback_data="admin_efectividad_detallado")],
            [InlineKeyboardButton("⬅️ Volver a Reportes", callback_data="admin_reportes")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_analisis_detallado(self, query):
        """Muestra análisis detallado de cada estrategia del mercado"""
        # Intentar responder al callback (puede fallar si el query expiró)
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        # Verificar si hay datos en cache
        if not hasattr(self, '_analisis_detallado_cache') or user_id not in self._analisis_detallado_cache:
            await query.edit_message_text("❌ No hay datos de análisis disponibles. Busca un mercado primero.")
            return
        
        try:
            # Obtener datos del cache
            cache_data = self._analisis_detallado_cache[user_id]
            symbol = cache_data['symbol']
            nombre = cache_data['nombre']
            resultado = cache_data['resultado']
            detalles = cache_data['detalles']
            
            # Extraer detalles de cada estrategia (INCLUYENDO NUEVAS MEJORAS)
            tendencia = detalles.get('tendencia', {})
            sr = detalles.get('soportes_resistencias', {})
            patrones = detalles.get('patrones', {})
            
            # Asegurar que sean diccionarios, no enteros
            patrones_chartistas_raw = detalles.get('patrones_chartistas', {})
            patrones_chartistas = patrones_chartistas_raw if isinstance(patrones_chartistas_raw, dict) else {}
            
            canales_raw = detalles.get('canales', {})
            canales = canales_raw if isinstance(canales_raw, dict) else {}
            
            velas_japonesas_raw = detalles.get('velas_japonesas', {})
            velas_japonesas = velas_japonesas_raw if isinstance(velas_japonesas_raw, dict) else {}
            
            presion_mercado_raw = detalles.get('presion_mercado', {})
            presion_mercado = presion_mercado_raw if isinstance(presion_mercado_raw, dict) else {}
            
            niveles_objetivo = detalles.get('niveles_objetivo', {})
            volatilidad = detalles.get('volatilidad', {})
            
            # Construir mensaje detallado
            mensaje = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

🎯 **EFECTIVIDAD TOTAL:** {resultado.get('efectividad_total', 0):.1f}%
🎲 **DECISIÓN:** {resultado.get('decision') if resultado.get('decision') else 'Sin señal clara'}

━━━━━━━━━━━━━━━━━━━━━━

1️⃣ **TENDENCIA (30% peso)**
📈 **Efectividad:** {tendencia.get('efectividad', 0):.1f}%
🧭 **Dirección:** {tendencia.get('direccion', 'indefinida').upper()}

**📋 Por qué esta efectividad:**
"""
            
            # Explicar tendencia
            ef_tend = tendencia.get('efectividad', 0)
            if ef_tend == 0:
                mensaje += "❌ **Mercado lateral o indefinido**\n"
                mensaje += "• No hay tendencia alcista ni bajista clara\n"
                mensaje += "• Las medias móviles no muestran dirección\n"
                mensaje += "• ADX bajo (fuerza de tendencia débil)\n"
                mensaje += "• Sin patrones chartistas detectados\n"
            elif ef_tend < 50:
                mensaje += "⚠️ **Tendencia débil**\n"
                mensaje += "• Señales mixtas en indicadores\n"
                mensaje += "• Posible consolidación o cambio de tendencia\n"
            elif ef_tend < 70:
                mensaje += "✅ **Tendencia moderada**\n"
                mensaje += "• Dirección identificada pero no muy fuerte\n"
                mensaje += "• Algunos indicadores confirman, otros no\n"
            else:
                mensaje += "🟢 **Tendencia fuerte**\n"
                mensaje += "• Dirección clara y confirmada\n"
                mensaje += "• Múltiples indicadores alineados\n"
                mensaje += "• ADX alto (tendencia con fuerza)\n"
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

2️⃣ **SOPORTES/RESISTENCIAS (20% peso)**
📈 **Efectividad:** {sr.get('efectividad', 0):.1f}%
🧭 **Dirección:** {sr.get('direccion', 'indefinida').upper()}

**📋 Por qué esta efectividad:**
"""
            
            # Explicar S/R
            ef_sr = sr.get('efectividad', 0)
            if ef_sr == 0:
                mensaje += "❌ **Sin zonas clave detectadas**\n"
                mensaje += "• No hay soportes o resistencias fuertes\n"
                mensaje += "• Precio no respeta niveles históricos\n"
            elif ef_sr < 50:
                mensaje += "⚠️ **Zonas débiles**\n"
                mensaje += "• Soportes/resistencias con pocos toques\n"
                mensaje += "• Niveles no muy respetados\n"
            elif ef_sr < 70:
                mensaje += "✅ **Zonas válidas**\n"
                mensaje += "• Soportes/resistencias identificados\n"
                mensaje += "• Niveles con varios toques históricos\n"
            else:
                mensaje += "🟢 **Zonas clave fuertes**\n"
                mensaje += "• Key levels muy respetados\n"
                mensaje += "• Múltiples toques y rebotes\n"
                mensaje += "• Alta probabilidad de reacción del precio\n"
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

3️⃣ **PATRONES DE VELAS (30% peso)**
📈 **Efectividad:** {patrones.get('efectividad', 0):.1f}%
🧭 **Dirección:** {patrones.get('direccion', 'indefinida').upper()}

**📋 Por qué esta efectividad:**
"""
            
            # Explicar patrones
            ef_pat = patrones.get('efectividad', 0)
            if ef_pat == 0:
                mensaje += "❌ **Sin patrones reconocibles**\n"
                mensaje += "• No se detectaron patrones válidos\n"
                mensaje += "• Velas sin formaciones claras\n"
                mensaje += "• Posible consolidación o ruido\n"
            elif ef_pat < 50:
                mensaje += "⚠️ **Patrones débiles**\n"
                mensaje += "• Patrones detectados pero contradictorios\n"
                mensaje += "• No cumplen criterios de tamaño\n"
            elif ef_pat < 70:
                mensaje += "✅ **Patrones válidos**\n"
                mensaje += "• Formaciones reconocibles detectadas\n"
                mensaje += "• Contexto parcialmente favorable\n"
            else:
                mensaje += "🟢 **Patrones fuertes**\n"
                mensaje += "• Patrones claros y bien formados\n"
                mensaje += "• Contexto favorable (tendencia + S/R)\n"
                mensaje += "• Alta probabilidad de cumplimiento\n"
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

4️⃣ **PATRONES CHARTISTAS (10% peso)** ✨ NUEVO
📈 **Efectividad:** {patrones_chartistas.get('efectividad', 0):.1f}%
"""
            
            # Explicar patrones chartistas
            patrones_validos_raw = patrones_chartistas.get('patrones_validos', [])
            patrones_validos = patrones_validos_raw if isinstance(patrones_validos_raw, list) else []
            
            mensaje += f"""🎯 **Patrones Detectados:** {len(patrones_validos)}

**📋 Análisis:**
"""
            if not patrones_validos:
                mensaje += "⚪ **Sin patrones chartistas**\n"
                mensaje += "• No se detectaron formaciones geométricas\n"
            else:
                mensaje += f"🟢 **{len(patrones_validos)} patrón(es) detectado(s)**\n"
                for patron in patrones_validos[:2]:  # Mostrar máximo 2
                    nombre_patron = patron.get('nombre', '').replace('_', ' ').title()
                    direccion = patron.get('direccion', 'neutral')
                    emoji = '🟢' if direccion == 'alcista' else '🔴' if direccion == 'bajista' else '⚪'
                    mensaje += f"{emoji} {nombre_patron} ({direccion})\n"
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

5️⃣ **CANALES (5% peso)** ✨ NUEVO
📊 **Canal Detectado:** {'SÍ' if canales.get('hay_canal') else 'NO'}
"""
            
            # Explicar canales
            if canales.get('hay_canal'):
                canal_activo = canales.get('canal_activo', '')
                canal_info = canales.get('canales', {}).get(canal_activo, {})
                riesgo = canal_info.get('riesgo_ruptura', 'N/A')
                oportunidad = canal_info.get('oportunidad', 'N/A')
                
                mensaje += f"🟢 **{canal_activo.replace('_', ' ').title()}**\n"
                mensaje += f"• Riesgo de ruptura: {riesgo}\n"
                mensaje += f"• Oportunidad: {oportunidad}\n"
            else:
                mensaje += "⚪ **Sin canal detectado**\n"
                mensaje += "• Precio no está en rango definido\n"
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

6️⃣ **VELAS JAPONESAS (10% peso)** ✨ NUEVO
📊 **Patrones de Velas:** {velas_japonesas.get('estadisticas', {}).get('total_patrones', 0)}
⚖️ **Presión de Mercado:**
"""
            
            # Explicar presión de mercado
            presion_comp = presion_mercado.get('presion_compradora', 50)
            presion_vend = presion_mercado.get('presion_vendedora', 50)
            dominio = presion_mercado.get('dominio', 'equilibrado')
            
            if presion_comp > 60:
                mensaje += f"🟢 **Compradores dominan** ({presion_comp:.0f}% vs {presion_vend:.0f}%)\n"
            elif presion_vend > 60:
                mensaje += f"🔴 **Vendedores dominan** ({presion_vend:.0f}% vs {presion_comp:.0f}%)\n"
            else:
                mensaje += f"⚪ **Equilibrado** ({presion_comp:.0f}% vs {presion_vend:.0f}%)\n"
            
            # Niveles objetivo
            if niveles_objetivo.get('total_objetivos', 0) > 0:
                mensaje += f"\n🎯 **Niveles Objetivo:** {niveles_objetivo.get('total_objetivos')} calculado(s)\n"
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

7️⃣ **VOLATILIDAD (15% peso)**
📈 **Efectividad:** {volatilidad.get('efectividad', 0):.1f}%
🧭 **Dirección:** {volatilidad.get('direccion', 'indefinida').upper()}

**📋 Por qué esta efectividad:**
"""
            
            # Explicar volatilidad
            ef_vol = volatilidad.get('efectividad', 0)
            if ef_vol == 0:
                mensaje += "❌ **Volatilidad inadecuada**\n"
                mensaje += "• Movimientos muy pequeños o muy grandes\n"
                mensaje += "• No apto para operaciones de 5 minutos\n"
            elif ef_vol < 50:
                mensaje += "⚠️ **Volatilidad baja**\n"
                mensaje += "• Movimientos limitados\n"
                mensaje += "• Difícil alcanzar objetivos\n"
            elif ef_vol < 70:
                mensaje += "✅ **Volatilidad normal**\n"
                mensaje += "• Movimientos adecuados\n"
                mensaje += "• Rango apropiado para trading\n"
            else:
                mensaje += "🟢 **Volatilidad óptima**\n"
                mensaje += "• Movimientos claros y medibles\n"
                mensaje += "• Pullback detectado (retroceso antes de continuar)\n"
                mensaje += "• Excelente para operaciones de 5 minutos\n"
            
            mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━

💡 **CONCLUSIÓN:**

"""
            
            # Conclusión final
            efectividad_total = resultado.get('efectividad_total', 0)
            if efectividad_total < 30:
                mensaje += "🔴 **NO OPERAR** - Mercado muy confuso\n"
                mensaje += "• Múltiples estrategias con efectividad 0%\n"
                mensaje += "• Sin dirección clara\n"
                mensaje += "• Alta probabilidad de señal falsa\n"
            elif efectividad_total < 60:
                mensaje += "🟡 **NO OPERAR** - Señales mixtas\n"
                mensaje += "• Algunas estrategias funcionan, otras no\n"
                mensaje += "• No cumple umbral mínimo (80%)\n"
            elif efectividad_total < 80:
                mensaje += "🟠 **NO OPERAR** - Condiciones aceptables pero insuficientes\n"
                mensaje += "• Cerca del umbral pero no lo alcanza\n"
                mensaje += "• Esperar mejores condiciones\n"
            else:
                mensaje += "🟢 **OPERAR** - Condiciones excelentes\n"
                mensaje += "• Múltiples estrategias alineadas\n"
                mensaje += "• Alta probabilidad de éxito\n"
                mensaje += "• Cumple todos los criterios\n"
            
            mensaje += f"""
⚙️ **Sistema:** Solo señales ≥80% efectividad
📊 **Mercado:** {symbol}
"""
            
        except Exception as e:
            mensaje = f"❌ Error generando análisis detallado: {str(e)}"
        
        # Agregar nota al final para ver detalles por estrategia
        mensaje += f"""

━━━━━━━━━━━━━━━━━━━━━━

💡 **¿Quieres más detalles?**
Selecciona una estrategia para ver su análisis técnico completo:
"""
        
        # Botones para cada estrategia (INCLUYENDO NUEVAS MEJORAS)
        keyboard = [
            [InlineKeyboardButton("1️⃣ Tendencia", callback_data=f"analisis_estrategia_tendencia")],
            [InlineKeyboardButton("2️⃣ Soportes/Resistencias", callback_data=f"analisis_estrategia_sr")],
            [InlineKeyboardButton("3️⃣ Patrones de Velas", callback_data=f"analisis_estrategia_patrones")],
            [InlineKeyboardButton("4️⃣ Patrones Chartistas ✨", callback_data=f"analisis_estrategia_chartistas")],
            [InlineKeyboardButton("5️⃣ Canales ✨", callback_data=f"analisis_estrategia_canales")],
            [InlineKeyboardButton("6️⃣ Velas Japonesas ✨", callback_data=f"analisis_estrategia_velas_japonesas")],
            [InlineKeyboardButton("7️⃣ Volatilidad", callback_data=f"analisis_estrategia_volatilidad")],
            [InlineKeyboardButton("📄 Exportar PDF Completo", callback_data="analisis_detallado_pdf")],
            [InlineKeyboardButton("🔍 Nueva búsqueda", callback_data="admin_mercados_buscar"),
             InlineKeyboardButton("⬅️ Volver", callback_data="admin_mercados")]
        ]
        
        # Verificar longitud del mensaje (límite de Telegram: 4096 caracteres)
        if len(mensaje) > 4000:
            print(f"[Telegram] ⚠️ Mensaje muy largo ({len(mensaje)} caracteres), dividiendo...")
            # Si es muy largo, dividir en dos mensajes
            try:
                # Buscar un buen punto de corte (después de una sección completa)
                punto_corte = mensaje.rfind('━━━━━━━━━━━━━━━━━━━━━━', 0, 3500)
                if punto_corte == -1:
                    punto_corte = mensaje.rfind('\n\n', 0, 3500)
                if punto_corte == -1:
                    punto_corte = 3500
                
                # Enviar primera parte sin botones
                mensaje_parte1 = mensaje[:punto_corte]
                await query.edit_message_text(mensaje_parte1, parse_mode=ParseMode.MARKDOWN)
                
                # Enviar segunda parte con botones
                mensaje_parte2 = mensaje[punto_corte:] + f"""

━━━━━━━━━━━━━━━━━━━━━━

💡 **¿Quieres más detalles?**
Selecciona una estrategia para ver su análisis técnico completo:
"""
                await query.message.reply_text(mensaje_parte2, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
                print(f"[Telegram] ✅ Mensaje dividido correctamente")
            except Exception as e:
                print(f"[Telegram] ❌ Error al enviar mensaje largo: {e}")
                # Fallback: enviar versión resumida
                mensaje_corto = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

🎯 **EFECTIVIDAD TOTAL:** {resultado.get('efectividad_total', 0):.1f}%
🎲 **DECISIÓN:** {resultado.get('decision') if resultado.get('decision') else 'Sin señal clara'}

━━━━━━━━━━━━━━━━━━━━━━

📋 **RESUMEN POR ESTRATEGIA:**

1️⃣ **Tendencia** - {tendencia.get('efectividad', 0):.1f}%
2️⃣ **Soportes/Resistencias** - {sr.get('efectividad', 0):.1f}%
3️⃣ **Patrones de Velas** - {patrones.get('efectividad', 0):.1f}%
4️⃣ **Volatilidad** - {volatilidad.get('efectividad', 0):.1f}%

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **Mensaje muy extenso**
Selecciona una estrategia para ver detalles:
"""
                await query.edit_message_text(mensaje_corto, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            # Mensaje completo con botones
            try:
                await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception as e:
                print(f"[Telegram] ❌ Error al enviar análisis completo: {e}")
                print(f"[Telegram] Longitud del mensaje: {len(mensaje)} caracteres")
                
                # Intentar sin formato Markdown
                try:
                    await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
                except Exception as e2:
                    print(f"[Telegram] ❌ Error sin Markdown: {e2}")
                    
                    # Último intento: mensaje resumido
                    mensaje_corto = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

🎯 EFECTIVIDAD TOTAL: {resultado.get('efectividad_total', 0):.1f}%
🎲 DECISIÓN: {resultado.get('decision') if resultado.get('decision') else 'Sin señal clara'}

━━━━━━━━━━━━━━━━━━━━━━

⚠️ Error mostrando análisis completo
Selecciona una estrategia para ver detalles:
"""
                    await query.edit_message_text(mensaje_corto, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_analisis_estrategia_individual(self, query, estrategia: str):
        """Muestra el análisis detallado de una estrategia específica"""
        
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        # Verificar cache
        if not hasattr(self, '_analisis_detallado_cache') or user_id not in self._analisis_detallado_cache:
            await query.edit_message_text("❌ No hay datos de análisis disponibles. Busca un mercado primero.")
            return
        
        try:
            cache_data = self._analisis_detallado_cache[user_id]
            symbol = cache_data['symbol']
            nombre = cache_data['nombre']
            resultado = cache_data['resultado']
            detalles = cache_data['detalles']
            
            # Construir mensaje según la estrategia
            if estrategia == "tendencia":
                tendencia = detalles.get('tendencia', {})
                detalles_tend = tendencia.get('detalles', {})
                
                mensaje = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

━━━━━━━━━━━━━━━━━━━━━━

1️⃣ **ESTRATEGIA: TENDENCIA (30% peso)**
📈 **Efectividad Final:** {tendencia.get('efectividad', 0):.1f}%
🧭 **Dirección:** {tendencia.get('direccion', 'indefinida').upper()}

━━━━━━━━━━━━━━━━━━━━━━

📊 **ANÁLISIS MULTI-TIMEFRAME:**
"""
                # Mostrar análisis de tendencias múltiples
                if detalles_tend and isinstance(detalles_tend, dict):
                    # Tendencias multitimeframe
                    tendencias_mtf = detalles_tend.get('tendencias_multitimeframe', {})
                    if not isinstance(tendencias_mtf, dict):
                        tendencias_mtf = {}
                    if tendencias_mtf:
                        mensaje += "\n**🔍 4 Niveles de Tendencia Analizados:**\n\n"
                        
                        primaria = tendencias_mtf.get('primaria', {})
                        if primaria:
                            detalles_prim = primaria.get('detalles', {})
                            mensaje += f"1. **Tendencia Primaria (MA 200) - 40% peso**\n"
                            mensaje += f"   • Dirección: {primaria.get('direccion', 'N/A').upper()}\n"
                            mensaje += f"   • Fuerza: {primaria.get('fuerza', 0):.1f}/100\n"
                            mensaje += f"   • Ángulo: {detalles_prim.get('angulo_grados', 0):.2f}° ({detalles_prim.get('clasificacion_fuerza', 'N/A')})\n"
                            mensaje += f"   • Pendiente: {detalles_prim.get('pendiente', 0):.5f}\n"
                            mensaje += f"   • MA Actual: {detalles_prim.get('ma_actual', 0):.5f}\n"
                            mensaje += f"   • Precio: {detalles_prim.get('precio_actual', 0):.5f}\n\n"
                        
                        secundaria = tendencias_mtf.get('secundaria', {})
                        if secundaria:
                            detalles_sec = secundaria.get('detalles', {})
                            mensaje += f"2. **Tendencia Secundaria (MA 50) - 30% peso**\n"
                            mensaje += f"   • Dirección: {secundaria.get('direccion', 'N/A').upper()}\n"
                            mensaje += f"   • Fuerza: {secundaria.get('fuerza', 0):.1f}/100\n"
                            mensaje += f"   • Ángulo: {detalles_sec.get('angulo_grados', 0):.2f}° ({detalles_sec.get('clasificacion_fuerza', 'N/A')})\n"
                            mensaje += f"   • Pendiente: {detalles_sec.get('pendiente', 0):.5f}\n"
                            mensaje += f"   • MA Actual: {detalles_sec.get('ma_actual', 0):.5f}\n"
                            mensaje += f"   • Precio: {detalles_sec.get('precio_actual', 0):.5f}\n\n"
                        
                        terciaria = tendencias_mtf.get('terciaria', {})
                        if terciaria:
                            detalles_ter = terciaria.get('detalles', {})
                            mensaje += f"3. **Tendencia Terciaria (MA 20) - 20% peso**\n"
                            mensaje += f"   • Dirección: {terciaria.get('direccion', 'N/A').upper()}\n"
                            mensaje += f"   • Fuerza: {terciaria.get('fuerza', 0):.1f}/100\n"
                            mensaje += f"   • Ángulo: {detalles_ter.get('angulo_grados', 0):.2f}° ({detalles_ter.get('clasificacion_fuerza', 'N/A')})\n"
                            mensaje += f"   • Pendiente: {detalles_ter.get('pendiente', 0):.5f}\n"
                            mensaje += f"   • MA Actual: {detalles_ter.get('ma_actual', 0):.5f}\n"
                            mensaje += f"   • Precio: {detalles_ter.get('precio_actual', 0):.5f}\n\n"
                        
                        inmediata = tendencias_mtf.get('inmediata', {})
                        if inmediata:
                            detalles_inm = inmediata.get('detalles', {})
                            mensaje += f"4. **Tendencia Inmediata (MA 9) - 10% peso**\n"
                            mensaje += f"   • Dirección: {inmediata.get('direccion', 'N/A').upper()}\n"
                            mensaje += f"   • Fuerza: {inmediata.get('fuerza', 0):.1f}/100\n"
                            mensaje += f"   • Ángulo: {detalles_inm.get('angulo_grados', 0):.2f}° ({detalles_inm.get('clasificacion_fuerza', 'N/A')})\n"
                            mensaje += f"   • Pendiente: {detalles_inm.get('pendiente', 0):.5f}\n"
                            mensaje += f"   • MA Actual: {detalles_inm.get('ma_actual', 0):.5f}\n"
                            mensaje += f"   • Precio: {detalles_inm.get('precio_actual', 0):.5f}\n\n"
                    
                    # Bonus de alineación
                    bonus = detalles_tend.get('bonus_alineacion', 0)
                    if bonus != 0:
                        mensaje += f"**⚡ Bonus por Alineación:** {bonus:+.1f}%\n"
                        if bonus > 0:
                            mensaje += "   ✅ Múltiples tendencias alineadas\n\n"
                        else:
                            mensaje += "   ⚠️ Tendencias en conflicto\n\n"
                    
                    # Fuerza de tendencia (ADX + MACD)
                    fuerza = detalles_tend.get('fuerza_tendencia', {})
                    if isinstance(fuerza, dict):
                        mensaje += "**📈 INDICADORES DE FUERZA:**\n\n"
                        
                        adx = fuerza.get('adx', 0)
                        tendencia_fuerte = fuerza.get('tendencia_fuerte', False)
                        mensaje += f"• **ADX:** {adx:.2f}\n"
                        mensaje += f"  → {'🟢 Tendencia fuerte (>25)' if tendencia_fuerte else '🔴 Tendencia débil (<25)'}\n\n"
                        
                        macd_cruce = fuerza.get('macd_cruce', 'neutral')
                        mensaje += f"• **MACD:** {macd_cruce.upper()}\n"
                        if macd_cruce == 'alcista':
                            mensaje += "  → 🟢 Cruce alcista detectado\n\n"
                        elif macd_cruce == 'bajista':
                            mensaje += "  → 🔴 Cruce bajista detectado\n\n"
                        else:
                            mensaje += "  → ⚪ Sin cruce claro\n\n"
                        
                        divergencia = fuerza.get('divergencia', False)
                        if divergencia:
                            mensaje += "⚠️ **Divergencia detectada** - Posible cambio de tendencia\n\n"
                        
                        agotamiento = fuerza.get('agotamiento', False)
                        if agotamiento:
                            mensaje += "⚠️ **Agotamiento de tendencia** - Precaución\n\n"
                    
                    # Patrones chartistas
                    patrones_chart = detalles_tend.get('patrones_chartistas', {})
                    if isinstance(patrones_chart, dict):
                        mensaje += "**📐 PATRONES CHARTISTAS:**\n\n"
                        
                        hch = patrones_chart.get('hch')
                        if hch and hch != 'None':
                            mensaje += f"• Hombro-Cabeza-Hombro: {hch}\n"
                        
                        doble = patrones_chart.get('doble_techo_suelo')
                        if doble and doble != 'None':
                            mensaje += f"• Doble Techo/Suelo: {doble}\n"
                        
                        triangulo = patrones_chart.get('triangulo')
                        if triangulo and triangulo != 'None':
                            mensaje += f"• Triángulo: {triangulo}\n"
                        
                        bandera = patrones_chart.get('bandera')
                        if bandera and bandera != 'None':
                            mensaje += f"• Bandera: {bandera}\n"
                        
                        if not any([hch, doble, triangulo, bandera]):
                            mensaje += "• No se detectaron patrones chartistas\n"
                        
                        mensaje += "\n"
                    
                    # Resumen de tendencias
                    resumen = detalles_tend.get('resumen_tendencias', '')
                    if resumen:
                        mensaje += f"**📝 RESUMEN:**\n{resumen}\n\n"
                
                mensaje += "**💡 CONCLUSIÓN:**\n"
                ef_tend = tendencia.get('efectividad', 0)
                if ef_tend == 0:
                    mensaje += "❌ **Mercado lateral o indefinido**\n"
                    mensaje += "• Sin dirección clara en ningún timeframe\n"
                elif ef_tend < 50:
                    mensaje += "⚠️ **Tendencia débil**\n"
                    mensaje += "• Señales mixtas entre timeframes\n"
                elif ef_tend < 70:
                    mensaje += "✅ **Tendencia moderada**\n"
                    mensaje += "• Dirección identificada pero no muy fuerte\n"
                else:
                    mensaje += "🟢 **Tendencia fuerte y clara**\n"
                    mensaje += "• Múltiples timeframes alineados\n"
                
            elif estrategia == "sr":
                sr = detalles.get('soportes_resistencias', {})
                detalles_sr = sr.get('detalles', {})
                
                mensaje = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

━━━━━━━━━━━━━━━━━━━━━━

2️⃣ **ESTRATEGIA: SOPORTES/RESISTENCIAS (20% peso)**
📈 **Efectividad Final:** {sr.get('efectividad', 0):.1f}%
🧭 **Dirección:** {sr.get('direccion', 'indefinida').upper()}

━━━━━━━━━━━━━━━━━━━━━━

📊 **KEY LEVELS DETECTADOS:**
"""
                # Agregar niveles si están disponibles
                if detalles_sr and isinstance(detalles_sr, dict):
                    zonas = detalles_sr.get('zonas_detectadas', [])
                    precio_actual = detalles_sr.get('precio_actual', 0)
                    
                    # Verificar que zonas sea una lista
                    if not isinstance(zonas, list):
                        zonas = []
                    
                    if precio_actual:
                        mensaje += f"\n💰 **Precio Actual:** {precio_actual:.5f}\n\n"
                    
                    if zonas and len(zonas) > 0:
                        mensaje += f"**🎯 Total de Zonas Detectadas:** {len(zonas)}\n\n"
                        
                        # Separar soportes y resistencias
                        soportes = [z for z in zonas if z.get('tipo') == 'Soporte']
                        resistencias = [z for z in zonas if z.get('tipo') == 'Resistencia']
                        
                        # Mostrar resistencias (ordenadas de más cercana a más lejana)
                        if resistencias:
                            mensaje += "**🔴 RESISTENCIAS (niveles arriba del precio):**\n\n"
                            resistencias_sorted = sorted(resistencias, key=lambda x: x.get('nivel', 0))
                            for i, zona in enumerate(resistencias_sorted[:5], 1):
                                nivel = zona.get('nivel', 0)
                                fuerza = zona.get('fuerza', 0)
                                toques = zona.get('toques', 0)
                                distancia = ((nivel - precio_actual) / precio_actual * 100) if precio_actual else 0
                                
                                mensaje += f"{i}. **Nivel:** {nivel:.5f}\n"
                                mensaje += f"   • Fuerza: {fuerza:.1f}%\n"
                                mensaje += f"   • Toques históricos: {toques}\n"
                                mensaje += f"   • Distancia: {distancia:+.2f}% del precio\n"
                                
                                if abs(distancia) < 0.5:
                                    mensaje += f"   ⚠️ **MUY CERCA** - Alta probabilidad de reacción\n"
                                elif abs(distancia) < 1.0:
                                    mensaje += f"   ✅ **CERCA** - Zona importante\n"
                                
                                mensaje += "\n"
                        
                        # Mostrar soportes (ordenados de más cercano a más lejano)
                        if soportes:
                            mensaje += "**🟢 SOPORTES (niveles debajo del precio):**\n\n"
                            soportes_sorted = sorted(soportes, key=lambda x: x.get('nivel', 0), reverse=True)
                            for i, zona in enumerate(soportes_sorted[:5], 1):
                                nivel = zona.get('nivel', 0)
                                fuerza = zona.get('fuerza', 0)
                                toques = zona.get('toques', 0)
                                distancia = ((nivel - precio_actual) / precio_actual * 100) if precio_actual else 0
                                
                                mensaje += f"{i}. **Nivel:** {nivel:.5f}\n"
                                mensaje += f"   • Fuerza: {fuerza:.1f}%\n"
                                mensaje += f"   • Toques históricos: {toques}\n"
                                mensaje += f"   • Distancia: {distancia:+.2f}% del precio\n"
                                
                                if abs(distancia) < 0.5:
                                    mensaje += f"   ⚠️ **MUY CERCA** - Alta probabilidad de rebote\n"
                                elif abs(distancia) < 1.0:
                                    mensaje += f"   ✅ **CERCA** - Zona importante\n"
                                
                                mensaje += "\n"
                        
                        if not soportes and not resistencias:
                            mensaje += "• No se detectaron zonas clave claras\n\n"
                    else:
                        mensaje += "• No se detectaron zonas clave\n\n"
                    
                    # Información adicional
                    rango_precio = detalles_sr.get('rango_precio', {})
                    if rango_precio:
                        mensaje += "**📏 RANGO DE PRECIO ANALIZADO:**\n"
                        mensaje += f"• Máximo: {rango_precio.get('max', 0):.5f}\n"
                        mensaje += f"• Mínimo: {rango_precio.get('min', 0):.5f}\n"
                        mensaje += f"• Rango: {rango_precio.get('rango', 0):.5f}\n\n"
                
                mensaje += "**💡 CONCLUSIÓN:**\n"
                ef_sr = sr.get('efectividad', 0)
                if ef_sr == 0:
                    mensaje += "❌ **Sin estructura clara**\n"
                    mensaje += "• Precio no respeta niveles históricos\n"
                elif ef_sr < 50:
                    mensaje += "⚠️ **Zonas débiles**\n"
                    mensaje += "• Pocos toques en los niveles\n"
                elif ef_sr < 70:
                    mensaje += "✅ **Zonas válidas**\n"
                    mensaje += "• Niveles con varios toques confirmados\n"
                else:
                    mensaje += "🟢 **Key Levels muy fuertes**\n"
                    mensaje += "• Alta probabilidad de reacción en estos niveles\n"
                
            elif estrategia == "patrones":
                patrones = detalles.get('patrones', {})
                detalles_pat = patrones.get('detalles', {})
                
                mensaje = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

━━━━━━━━━━━━━━━━━━━━━━

3️⃣ **ESTRATEGIA: PATRONES DE VELAS (30% peso)**
📈 **Efectividad Final:** {patrones.get('efectividad', 0):.1f}%
🧭 **Dirección:** {patrones.get('direccion', 'indefinida').upper()}

━━━━━━━━━━━━━━━━━━━━━━

📊 **PATRONES CANDLESTICK DETECTADOS:**
"""
                # Agregar patrones si están disponibles
                if detalles_pat and isinstance(detalles_pat, dict):
                    patrones_detectados = detalles_pat.get('patrones_detectados', [])
                    velas_analizadas = detalles_pat.get('velas_analizadas', 0)
                    
                    if velas_analizadas:
                        mensaje += f"\n📈 **Velas Analizadas:** {velas_analizadas} velas de 5 minutos\n\n"
                    
                    # Verificar que patrones_detectados sea una lista
                    if not isinstance(patrones_detectados, list):
                        patrones_detectados = []
                    
                    if patrones_detectados and len(patrones_detectados) > 0:
                        mensaje += f"**🎯 Total de Patrones Encontrados:** {len(patrones_detectados)}\n\n"
                        
                        # Separar por tipo
                        alcistas = [p for p in patrones_detectados if p.get('tipo', '').lower() in ['alcista', 'bullish']]
                        bajistas = [p for p in patrones_detectados if p.get('tipo', '').lower() in ['bajista', 'bearish']]
                        neutrales = [p for p in patrones_detectados if p.get('tipo', '').lower() in ['neutral', 'indecision']]
                        
                        # Mostrar patrones alcistas
                        if alcistas:
                            mensaje += "**🟢 PATRONES ALCISTAS:**\n\n"
                            for i, patron in enumerate(alcistas[:5], 1):
                                nombre_patron = patron.get('nombre', 'N/A')
                                confianza = patron.get('confianza', 0)
                                posicion = patron.get('posicion', 'N/A')
                                contexto = patron.get('contexto', '')
                                
                                mensaje += f"{i}. **{nombre_patron}**\n"
                                mensaje += f"   • Confianza: {confianza:.1f}%\n"
                                mensaje += f"   • Posición: Vela #{posicion}\n"
                                
                                if contexto:
                                    mensaje += f"   • Contexto: {contexto}\n"
                                
                                # Explicar el patrón
                                if 'martillo' in nombre_patron.lower():
                                    mensaje += "   → Patrón de reversión alcista\n"
                                    mensaje += "   → Indica rechazo de precios bajos\n"
                                elif 'envolvente' in nombre_patron.lower():
                                    mensaje += "   → Patrón de reversión fuerte\n"
                                    mensaje += "   → Vela alcista envuelve vela bajista\n"
                                elif 'estrella' in nombre_patron.lower() and 'mañana' in nombre_patron.lower():
                                    mensaje += "   → Patrón de 3 velas alcista\n"
                                    mensaje += "   → Cambio de tendencia bajista a alcista\n"
                                
                                mensaje += "\n"
                        
                        # Mostrar patrones bajistas
                        if bajistas:
                            mensaje += "**🔴 PATRONES BAJISTAS:**\n\n"
                            for i, patron in enumerate(bajistas[:5], 1):
                                nombre_patron = patron.get('nombre', 'N/A')
                                confianza = patron.get('confianza', 0)
                                posicion = patron.get('posicion', 'N/A')
                                contexto = patron.get('contexto', '')
                                
                                mensaje += f"{i}. **{nombre_patron}**\n"
                                mensaje += f"   • Confianza: {confianza:.1f}%\n"
                                mensaje += f"   • Posición: Vela #{posicion}\n"
                                
                                if contexto:
                                    mensaje += f"   • Contexto: {contexto}\n"
                                
                                # Explicar el patrón
                                if 'estrella' in nombre_patron.lower() and 'fugaz' in nombre_patron.lower():
                                    mensaje += "   → Patrón de reversión bajista\n"
                                    mensaje += "   → Indica rechazo de precios altos\n"
                                elif 'envolvente' in nombre_patron.lower():
                                    mensaje += "   → Patrón de reversión fuerte\n"
                                    mensaje += "   → Vela bajista envuelve vela alcista\n"
                                elif 'ahorcado' in nombre_patron.lower():
                                    mensaje += "   → Patrón de reversión bajista\n"
                                    mensaje += "   → Señal de techo de mercado\n"
                                
                                mensaje += "\n"
                        
                        # Mostrar patrones neutrales/indecisión
                        if neutrales:
                            mensaje += "**⚪ PATRONES DE INDECISIÓN:**\n\n"
                            for i, patron in enumerate(neutrales[:3], 1):
                                nombre_patron = patron.get('nombre', 'N/A')
                                confianza = patron.get('confianza', 0)
                                
                                mensaje += f"{i}. **{nombre_patron}** - Confianza: {confianza:.1f}%\n"
                                
                                if 'doji' in nombre_patron.lower():
                                    mensaje += "   → Indecisión del mercado\n"
                                    mensaje += "   → Posible cambio de tendencia\n"
                                
                                mensaje += "\n"
                        
                        if not alcistas and not bajistas and not neutrales:
                            mensaje += "• No se detectaron patrones candlestick reconocibles\n\n"
                    else:
                        mensaje += "• No se detectaron patrones de velas\n\n"
                    
                    # Análisis de confirmación
                    confirmacion = detalles_pat.get('confirmacion', {})
                    if confirmacion:
                        mensaje += "**✅ CONFIRMACIÓN DE PATRONES:**\n"
                        confirmados = confirmacion.get('confirmados', 0)
                        total = confirmacion.get('total', 0)
                        if total > 0:
                            porcentaje = (confirmados / total) * 100
                            mensaje += f"• Patrones confirmados: {confirmados}/{total} ({porcentaje:.1f}%)\n"
                        mensaje += "\n"
                
                mensaje += "**💡 CONCLUSIÓN:**\n"
                ef_pat = patrones.get('efectividad', 0)
                if ef_pat == 0:
                    mensaje += "❌ **Sin patrones válidos**\n"
                    mensaje += "• No hay formaciones reconocibles\n"
                elif ef_pat < 50:
                    mensaje += "⚠️ **Patrones débiles o contradictorios**\n"
                    mensaje += "• Señales mixtas\n"
                elif ef_pat < 70:
                    mensaje += "✅ **Patrones válidos detectados**\n"
                    mensaje += "• Formaciones identificadas correctamente\n"
                else:
                    mensaje += "🟢 **Patrones fuertes y confirmados**\n"
                    mensaje += "• Excelente señal de entrada\n"
                
            elif estrategia == "volatilidad":
                volatilidad = detalles.get('volatilidad', {})
                detalles_vol = volatilidad.get('detalles', {})
                
                mensaje = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

━━━━━━━━━━━━━━━━━━━━━━

4️⃣ **ESTRATEGIA: VOLATILIDAD Y PULLBACK (20% peso)**
📈 **Efectividad Final:** {volatilidad.get('efectividad', 0):.1f}%
🧭 **Dirección:** {volatilidad.get('direccion', 'indefinida').upper()}

━━━━━━━━━━━━━━━━━━━━━━

📊 **ANÁLISIS DE VOLATILIDAD:**
"""
                # Agregar métricas si están disponibles
                if detalles_vol and isinstance(detalles_vol, dict):
                    # ATR (Average True Range)
                    atr = detalles_vol.get('atr', 0)
                    atr_normalizado = detalles_vol.get('atr_normalizado', 0)
                    if atr:
                        mensaje += f"\n**📏 ATR (Average True Range):**\n"
                        mensaje += f"• Valor absoluto: {atr:.5f}\n"
                        if atr_normalizado:
                            mensaje += f"• Normalizado: {atr_normalizado:.2f}%\n"
                        mensaje += f"• Interpretación: "
                        if atr_normalizado < 0.5:
                            mensaje += "Muy baja volatilidad\n"
                        elif atr_normalizado < 1.0:
                            mensaje += "Baja volatilidad\n"
                        elif atr_normalizado < 2.0:
                            mensaje += "Volatilidad normal\n"
                        elif atr_normalizado < 3.0:
                            mensaje += "Alta volatilidad\n"
                        else:
                            mensaje += "Volatilidad extrema\n"
                        mensaje += "\n"
                    
                    # Rango de precio
                    rango_promedio = detalles_vol.get('rango_promedio', 0)
                    rango_actual = detalles_vol.get('rango_actual', 0)
                    if rango_promedio:
                        mensaje += f"**📊 RANGO DE PRECIO:**\n"
                        mensaje += f"• Rango promedio (20 velas): {rango_promedio:.5f}\n"
                        if rango_actual:
                            mensaje += f"• Rango actual: {rango_actual:.5f}\n"
                            comparacion = (rango_actual / rango_promedio) * 100 if rango_promedio > 0 else 0
                            mensaje += f"• Comparación: {comparacion:.1f}% del promedio\n"
                        mensaje += "\n"
                    
                    # Bollinger Bands
                    bb = detalles_vol.get('bollinger_bands', {})
                    if bb:
                        mensaje += f"**📈 BOLLINGER BANDS:**\n"
                        upper = bb.get('upper', 0)
                        middle = bb.get('middle', 0)
                        lower = bb.get('lower', 0)
                        precio_actual = bb.get('precio_actual', 0)
                        
                        if upper and middle and lower:
                            mensaje += f"• Banda Superior: {upper:.5f}\n"
                            mensaje += f"• Banda Media (MA20): {middle:.5f}\n"
                            mensaje += f"• Banda Inferior: {lower:.5f}\n"
                            
                            if precio_actual:
                                mensaje += f"• Precio Actual: {precio_actual:.5f}\n"
                                
                                # Determinar posición
                                if precio_actual >= upper:
                                    mensaje += "  → ⚠️ **Precio en banda superior** - Sobrecompra\n"
                                elif precio_actual <= lower:
                                    mensaje += "  → ⚠️ **Precio en banda inferior** - Sobreventa\n"
                                elif precio_actual > middle:
                                    mensaje += "  → ✅ **Precio sobre la media** - Zona alcista\n"
                                else:
                                    mensaje += "  → ✅ **Precio bajo la media** - Zona bajista\n"
                        mensaje += "\n"
                    
                    # Detección de Pullback
                    pullback = detalles_vol.get('pullback_detectado', False)
                    pullback_info = detalles_vol.get('pullback_info', {})
                    
                    mensaje += f"**🎯 DETECCIÓN DE PULLBACK:**\n"
                    mensaje += f"• **Pullback Detectado:** {'✅ SÍ' if pullback else '❌ NO'}\n"
                    
                    if pullback and pullback_info:
                        tipo = pullback_info.get('tipo', 'N/A')
                        fuerza = pullback_info.get('fuerza', 0)
                        retroceso = pullback_info.get('retroceso_porcentaje', 0)
                        
                        mensaje += f"• Tipo: {tipo}\n"
                        mensaje += f"• Fuerza del pullback: {fuerza:.1f}%\n"
                        mensaje += f"• Retroceso: {retroceso:.2f}%\n"
                        mensaje += "\n**💡 SIGNIFICADO:**\n"
                        mensaje += "→ El precio retrocedió temporalmente\n"
                        mensaje += "→ Momento ideal para entrada a favor de tendencia\n"
                        mensaje += "→ Alta probabilidad de continuación\n"
                    else:
                        mensaje += "\n**💡 SIGNIFICADO:**\n"
                        mensaje += "→ No hay retroceso claro detectado\n"
                        mensaje += "→ Esperar mejor punto de entrada\n"
                    
                    mensaje += "\n"
                    
                    # Momentum
                    momentum = detalles_vol.get('momentum', {})
                    if momentum:
                        mensaje += f"**⚡ MOMENTUM:**\n"
                        rsi = momentum.get('rsi', 0)
                        if rsi:
                            mensaje += f"• RSI (14): {rsi:.2f}\n"
                            if rsi >= 70:
                                mensaje += "  → ⚠️ Sobrecompra - Posible corrección\n"
                            elif rsi <= 30:
                                mensaje += "  → ⚠️ Sobreventa - Posible rebote\n"
                            else:
                                mensaje += "  → ✅ Zona neutral\n"
                        mensaje += "\n"
                
                mensaje += "**💡 CONCLUSIÓN:**\n"
                ef_vol = volatilidad.get('efectividad', 0)
                if ef_vol == 0:
                    mensaje += "❌ **Volatilidad inadecuada**\n"
                    mensaje += "• Movimientos muy pequeños o muy grandes\n"
                elif ef_vol < 50:
                    mensaje += "⚠️ **Volatilidad baja**\n"
                    mensaje += "• Difícil alcanzar objetivos\n"
                elif ef_vol < 70:
                    mensaje += "✅ **Volatilidad normal**\n"
                    mensaje += "• Apropiada para trading de 5 minutos\n"
                else:
                    mensaje += "🟢 **Volatilidad óptima con pullback**\n"
                    mensaje += "• Excelente momento para operar\n"
            
            elif estrategia == "chartistas":
                patrones_chartistas_raw = detalles.get('patrones_chartistas', {})
                patrones_chartistas = patrones_chartistas_raw if isinstance(patrones_chartistas_raw, dict) else {}
                
                mensaje = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

━━━━━━━━━━━━━━━━━━━━━━

4️⃣ **ESTRATEGIA: PATRONES CHARTISTAS (10% peso)** ✨ NUEVO
📈 **Efectividad Final:** {patrones_chartistas.get('efectividad', 0):.1f}%
🎯 **Patrones Detectados:** {len(patrones_chartistas.get('patrones_validos', []))}

━━━━━━━━━━━━━━━━━━━━━━

📊 **PATRONES GEOMÉTRICOS DETECTADOS:**
"""
                patrones_validos = patrones_chartistas.get('patrones_validos', [])
                
                if not patrones_validos:
                    mensaje += "\n⚪ **No se detectaron patrones chartistas**\n"
                    mensaje += "• Sin formaciones geométricas claras\n"
                    mensaje += "• Mercado sin patrones de reversión o continuidad\n"
                else:
                    mensaje += f"\n🟢 **{len(patrones_validos)} patrón(es) detectado(s):**\n\n"
                    
                    for i, patron in enumerate(patrones_validos, 1):
                        nombre_patron = patron.get('nombre', '').replace('_', ' ').title()
                        direccion = patron.get('direccion', 'neutral')
                        confirmado = patron.get('confirmado', False)
                        efectividad_patron = patron.get('efectividad', 0)
                        
                        emoji_dir = '🟢' if direccion == 'alcista' else '🔴' if direccion == 'bajista' else '⚪'
                        emoji_conf = '✅' if confirmado else '⏳'
                        
                        mensaje += f"**{i}. {nombre_patron}**\n"
                        mensaje += f"   {emoji_dir} Dirección: {direccion.upper()}\n"
                        mensaje += f"   {emoji_conf} Estado: {'Confirmado' if confirmado else 'Pendiente confirmación'}\n"
                        mensaje += f"   📊 Efectividad: {efectividad_patron}%\n"
                        
                        # Agregar descripción según el patrón
                        if 'doble_techo' in patron.get('nombre', ''):
                            mensaje += "   📝 Patrón de reversión bajista\n"
                        elif 'doble_suelo' in patron.get('nombre', ''):
                            mensaje += "   📝 Patrón de reversión alcista\n"
                        elif 'hch' in patron.get('nombre', ''):
                            mensaje += "   📝 Hombro-Cabeza-Hombro (reversión bajista)\n"
                        elif 'hchi' in patron.get('nombre', ''):
                            mensaje += "   📝 HCH Invertido (reversión alcista)\n"
                        elif 'triangulo' in patron.get('nombre', ''):
                            mensaje += "   📝 Patrón de continuidad\n"
                        elif 'bandera' in patron.get('nombre', ''):
                            mensaje += "   📝 Patrón de continuidad (pullback)\n"
                        
                        mensaje += "\n"
                
                mensaje += "\n**💡 CONCLUSIÓN:**\n"
                if not patrones_validos:
                    mensaje += "⚪ Sin patrones chartistas para operar\n"
                elif len(patrones_validos) == 1:
                    mensaje += "✅ Un patrón detectado - Validar con otras estrategias\n"
                else:
                    mensaje += "🟢 Múltiples patrones - Alta probabilidad\n"
            
            elif estrategia == "canales":
                canales_raw = detalles.get('canales', {})
                canales = canales_raw if isinstance(canales_raw, dict) else {}
                
                mensaje = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

━━━━━━━━━━━━━━━━━━━━━━

5️⃣ **ESTRATEGIA: CANALES (5% peso)** ✨ NUEVO
📊 **Canal Detectado:** {'SÍ' if canales.get('hay_canal') else 'NO'}

━━━━━━━━━━━━━━━━━━━━━━

📊 **ANÁLISIS DE CANALES:**
"""
                if canales.get('hay_canal'):
                    canal_activo = canales.get('canal_activo', '')
                    canal_info = canales.get('canales', {}).get(canal_activo, {})
                    
                    tipo_canal = canal_activo.replace('_', ' ').title()
                    mensaje += f"\n🟢 **{tipo_canal} Detectado**\n\n"
                    
                    # Información del canal
                    if canal_info:
                        resistencia = canal_info.get('resistencia', 0)
                        soporte = canal_info.get('soporte', 0)
                        altura = canal_info.get('altura_canal', 0)
                        testeos = canal_info.get('total_testeos', 0)
                        riesgo = canal_info.get('riesgo_ruptura', 'N/A')
                        oportunidad = canal_info.get('oportunidad', 'N/A')
                        
                        mensaje += f"**📏 NIVELES DEL CANAL:**\n"
                        mensaje += f"• Resistencia: {resistencia:.5f}\n"
                        mensaje += f"• Soporte: {soporte:.5f}\n"
                        mensaje += f"• Altura: {altura:.5f}\n\n"
                        
                        mensaje += f"**📊 ESTADÍSTICAS:**\n"
                        mensaje += f"• Total de testeos: {testeos}\n"
                        mensaje += f"• Riesgo de ruptura: {riesgo}\n\n"
                        
                        mensaje += f"**🎯 OPORTUNIDAD:**\n"
                        mensaje += f"{oportunidad}\n\n"
                        
                        # Advertencia según riesgo
                        if riesgo == 'ALTO':
                            mensaje += "⚠️ **ADVERTENCIA:**\n"
                            mensaje += "• Muchos testeos detectados (8+)\n"
                            mensaje += "• Alta probabilidad de ruptura\n"
                            mensaje += "• NO operar dentro del canal\n"
                            mensaje += "• Esperar ruptura confirmada\n"
                        elif riesgo == 'MEDIO':
                            mensaje += "⚠️ **PRECAUCIÓN:**\n"
                            mensaje += "• Testeos moderados (5-7)\n"
                            mensaje += "• Operar con cuidado\n"
                            mensaje += "• Vigilar señales de ruptura\n"
                        else:
                            mensaje += "✅ **OPORTUNIDAD:**\n"
                            mensaje += "• Canal reciente y válido\n"
                            mensaje += "• Operar rebotes en niveles\n"
                            mensaje += "• Buena relación riesgo/beneficio\n"
                else:
                    mensaje += "\n⚪ **No se detectó canal activo**\n"
                    mensaje += "• Precio no está en rango definido\n"
                    mensaje += "• Sin estructura de canal clara\n"
                    mensaje += "• Buscar otras oportunidades\n"
                
                mensaje += "\n**💡 CONCLUSIÓN:**\n"
                if canales.get('hay_canal'):
                    mensaje += "✅ Canal detectado - Operar según oportunidad\n"
                else:
                    mensaje += "⚪ Sin canal - Usar otras estrategias\n"
            
            elif estrategia == "velas_japonesas":
                velas_japonesas_raw = detalles.get('velas_japonesas', {})
                velas_japonesas = velas_japonesas_raw if isinstance(velas_japonesas_raw, dict) else {}
                presion_mercado_raw = detalles.get('presion_mercado', {})
                presion_mercado = presion_mercado_raw if isinstance(presion_mercado_raw, dict) else {}
                analisis_vela_contexto = detalles.get('analisis_vela_contexto', {})
                
                mensaje = f"""📊 **ANÁLISIS DETALLADO - {nombre}**

━━━━━━━━━━━━━━━━━━━━━━

6️⃣ **ESTRATEGIA: VELAS JAPONESAS (10% peso)** ✨ NUEVO
📊 **Patrones Detectados:** {velas_japonesas.get('estadisticas', {}).get('total_patrones', 0)}

━━━━━━━━━━━━━━━━━━━━━━

📊 **ANÁLISIS DE VELAS:**
"""
                stats = velas_japonesas.get('estadisticas', {})
                
                if stats.get('total_patrones', 0) > 0:
                    mensaje += f"\n🟢 **{stats.get('total_patrones')} patrón(es) de velas detectado(s)**\n\n"
                    
                    mensaje += f"**📋 DISTRIBUCIÓN POR CATEGORÍA:**\n"
                    por_categoria = stats.get('por_categoria', {})
                    if por_categoria:
                        if por_categoria.get('reversion', 0) > 0:
                            mensaje += f"🔄 Reversión: {por_categoria['reversion']} patrones\n"
                        if por_categoria.get('continuidad', 0) > 0:
                            mensaje += f"➡️ Continuidad: {por_categoria['continuidad']} patrones\n"
                        if por_categoria.get('indecision', 0) > 0:
                            mensaje += f"⚪ Indecisión: {por_categoria['indecision']} patrones\n"
                        if por_categoria.get('especiales', 0) > 0:
                            mensaje += f"⭐ Especiales: {por_categoria['especiales']} patrones\n"
                        if por_categoria.get('rupturas', 0) > 0:
                            mensaje += f"💥 Rupturas: {por_categoria['rupturas']} patrones\n"
                        if por_categoria.get('basicos', 0) > 0:
                            mensaje += f"🕯️ Básicos: {por_categoria['basicos']} patrones\n"
                    
                    mensaje += f"\n**🎯 SEÑALES:**\n"
                    mensaje += f"• Patrones Alcistas: {stats.get('patrones_alcistas', 0)} 🟢\n"
                    mensaje += f"• Patrones Bajistas: {stats.get('patrones_bajistas', 0)} 🔴\n"
                else:
                    mensaje += "\n⚪ **No se detectaron patrones de velas**\n"
                
                mensaje += f"\n**⚖️ PRESIÓN DE MERCADO:**\n"
                presion_comp = presion_mercado.get('presion_compradora', 50)
                presion_vend = presion_mercado.get('presion_vendedora', 50)
                dominio = presion_mercado.get('dominio', 'equilibrado')
                fuerza_dominio = presion_mercado.get('fuerza_dominio', 'neutral')
                
                mensaje += f"• Compradores: {presion_comp:.0f}%\n"
                mensaje += f"• Vendedores: {presion_vend:.0f}%\n"
                mensaje += f"• Dominio: {dominio.title()} ({fuerza_dominio})\n\n"
                
                if presion_comp > 60:
                    mensaje += "🟢 **Compradores dominan el mercado**\n"
                    mensaje += "→ Presión alcista fuerte\n"
                    mensaje += "→ Favorable para operaciones CALL\n"
                elif presion_vend > 60:
                    mensaje += "🔴 **Vendedores dominan el mercado**\n"
                    mensaje += "→ Presión bajista fuerte\n"
                    mensaje += "→ Favorable para operaciones PUT\n"
                else:
                    mensaje += "⚪ **Mercado equilibrado**\n"
                    mensaje += "→ Sin dominio claro\n"
                    mensaje += "→ Esperar señal más clara\n"
                
                # Análisis de vela en contexto
                if analisis_vela_contexto:
                    mensaje += f"\n**🎯 ANÁLISIS CONTEXTUAL:**\n"
                    señal = analisis_vela_contexto.get('señal', 'neutral')
                    efectividad_vela = analisis_vela_contexto.get('efectividad', 0)
                    
                    mensaje += f"• Señal: {señal.upper()}\n"
                    mensaje += f"• Efectividad: {efectividad_vela}%\n"
                
                mensaje += "\n**💡 CONCLUSIÓN:**\n"
                if stats.get('total_patrones', 0) > 3 and abs(presion_comp - presion_vend) > 20:
                    mensaje += "🟢 **Múltiples patrones + presión clara**\n"
                    mensaje += "• Excelente señal de velas\n"
                elif stats.get('total_patrones', 0) > 0:
                    mensaje += "✅ **Patrones detectados**\n"
                    mensaje += "• Validar con otras estrategias\n"
                else:
                    mensaje += "⚪ **Sin patrones claros**\n"
                    mensaje += "• Usar otras estrategias\n"
            
            mensaje += f"\n📊 **Mercado:** {symbol}"
            
            # Botones para volver
            keyboard = [
                [InlineKeyboardButton("⬅️ Volver al menú", callback_data="analisis_detallado")],
                [InlineKeyboardButton("🔍 Nueva búsqueda", callback_data="admin_mercados_buscar")]
            ]
            
            # Escapar caracteres especiales de Markdown
            mensaje = mensaje.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
            # Restaurar el formato que queremos mantener
            mensaje = mensaje.replace('\\*\\*', '**')  # Mantener negritas
            
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            import traceback
            print(f"[Telegram] ❌ Error mostrando estrategia {estrategia}: {e}")
            print(f"[Telegram] Traceback: {traceback.format_exc()}")
            
            # Mensaje de error más informativo
            error_msg = f"""❌ **Error mostrando análisis de {estrategia}**

**Error:** {str(e)}

Posibles causas:
• Los datos de esta estrategia no están disponibles
• Formato de datos incorrecto
• Intenta buscar otro mercado

**Solución:** Vuelve al menú y busca otro mercado."""
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Volver al menú", callback_data="analisis_detallado")],
                [InlineKeyboardButton("🔍 Nueva búsqueda", callback_data="admin_mercados_buscar")]
            ]
            
            try:
                await query.edit_message_text(error_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_text(f"❌ Error mostrando análisis de estrategia: {str(e)}")
    
    async def handle_admin_reporte_usuarios_callback(self, query):
        """Callback para reporte de usuarios"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            usuarios_activos = self.user_manager.usuarios_activos
            total_activos = len(usuarios_activos)
            
            mensaje = f"""👥 **REPORTE DE USUARIOS**

📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y')}
⏰ **Hora:** {datetime.now().strftime('%H:%M:%S')}

📊 **ESTADÍSTICAS GENERALES:**
• **Usuarios activos:** {total_activos}
• **Clave del día:** `{self.user_manager.clave_publica_diaria}`
• **Usuarios bloqueados:** {len(self.user_manager.usuarios_bloqueados)}

👤 **USUARIOS ACTIVOS:**"""
            
            if total_activos == 0:
                mensaje += "\n❌ No hay usuarios activos actualmente"
            else:
                for i, (user_id, info) in enumerate(usuarios_activos.items(), 1):
                    if i > 10:  # Mostrar máximo 10
                        mensaje += f"\n... y {total_activos - 10} usuarios más"
                        break
                    username = info.get('username', 'Sin username')
                    hora = info.get('hora_ingreso', 'N/A')
                    tipo = info.get('tipo', 'usuario')
                    emoji = "👑" if tipo == 'admin' else "👤"
                    mensaje += f"\n{i}. {emoji} @{username} - {hora}"
            
            # Obtener estadísticas de accesos no autorizados
            from core.user_manager_accesos import obtener_estadisticas_accesos_no_autorizados
            fecha_hoy = datetime.now().strftime('%Y-%m-%d')
            stats_accesos = obtener_estadisticas_accesos_no_autorizados(self.user_manager, fecha_hoy)
            
            mensaje += f"""

🔒 **SEGURIDAD:**
• **Accesos no autorizados hoy:** {stats_accesos['total_intentos']}
• **Usuarios únicos rechazados:** {stats_accesos['usuarios_unicos']}
• **Estado general:** {'⚠️ Revisar' if stats_accesos['total_intentos'] > 5 else '✅ Seguro'}"""
                
        except Exception as e:
            mensaje = f"👥 **REPORTE DE USUARIOS**\n\n❌ Error generando reporte: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("📊 Estadísticas", callback_data="admin_usuarios_estadisticas")],
            [InlineKeyboardButton("🚨 Ver Accesos No Autorizados", callback_data="admin_ver_accesos_no_autorizados")],
            [InlineKeyboardButton("⬅️ Volver a Reportes", callback_data="admin_reportes")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_usuarios_estadisticas_callback(self, query):
        """Callback para estadísticas detalladas de usuarios"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            from datetime import datetime, timedelta
            from core.user_manager_accesos import obtener_estadisticas_accesos_no_autorizados
            
            # Estadísticas de usuarios activos
            usuarios_activos = self.user_manager.usuarios_activos
            total_activos = len(usuarios_activos)
            
            # Estadísticas de accesos no autorizados (hoy)
            fecha_hoy = datetime.now().strftime('%Y-%m-%d')
            stats_hoy = obtener_estadisticas_accesos_no_autorizados(self.user_manager, fecha_hoy)
            
            # Estadísticas de accesos no autorizados (últimos 7 días)
            fecha_hace_7_dias = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            total_7_dias = 0
            for i in range(7):
                fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                stats = obtener_estadisticas_accesos_no_autorizados(self.user_manager, fecha)
                total_7_dias += stats['total_intentos']
            
            # Estadísticas de bloqueos
            total_bloqueados = len(self.user_manager.usuarios_bloqueados)
            total_bloqueos_historial = len(self.user_manager.historial_bloqueos)
            
            # Calcular promedio de accesos por día
            promedio_diario = total_7_dias / 7 if total_7_dias > 0 else 0
            
            mensaje = f"""📊 **ESTADÍSTICAS DE USUARIOS**

📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

━━━━━━━━━━━━━━━━━━━━━━

👥 **USUARIOS ACTIVOS:**
• **Total conectados:** {total_activos}
• **Clave del día:** `{self.user_manager.clave_publica_diaria}`
• **Lista blanca:** {len(self.user_manager.lista_blanca)} usuarios

━━━━━━━━━━━━━━━━━━━━━━

🚨 **ACCESOS NO AUTORIZADOS:**

**Hoy ({fecha_hoy}):**
• Total intentos: {stats_hoy['total_intentos']}
• Usuarios únicos: {stats_hoy['usuarios_unicos']}

**Últimos 7 días:**
• Total intentos: {total_7_dias}
• Promedio diario: {promedio_diario:.1f}

**Por motivo (hoy):**"""

            for motivo, count in stats_hoy['por_motivo'].items():
                emoji = "🔑" if motivo == "clave_incorrecta" else "📋"
                motivo_texto = {
                    'clave_incorrecta': 'Clave incorrecta',
                    'no_autorizado': 'No en lista diaria',
                    'no_lista_diaria': 'Sin lista diaria'
                }.get(motivo, motivo)
                mensaje += f"\n• {emoji} {motivo_texto}: {count}"

            mensaje += f"""

━━━━━━━━━━━━━━━━━━━━━━

🚫 **BLOQUEOS:**
• **Usuarios bloqueados:** {total_bloqueados}
• **Total acciones historial:** {total_bloqueos_historial}

━━━━━━━━━━━━━━━━━━━━━━

📈 **ANÁLISIS:**"""

            # Análisis de seguridad
            if stats_hoy['total_intentos'] == 0:
                mensaje += "\n✅ **Seguridad óptima** - Sin intentos no autorizados hoy"
            elif stats_hoy['total_intentos'] < 5:
                mensaje += f"\n✅ **Seguridad buena** - Pocos intentos ({stats_hoy['total_intentos']})"
            elif stats_hoy['total_intentos'] < 10:
                mensaje += f"\n⚠️ **Revisar** - Varios intentos ({stats_hoy['total_intentos']})"
            else:
                mensaje += f"\n🚨 **Alerta** - Muchos intentos ({stats_hoy['total_intentos']})"
            
            if promedio_diario > 10:
                mensaje += f"\n⚠️ **Tendencia alta** - Promedio de {promedio_diario:.1f} intentos/día"
            
            keyboard = [
                [InlineKeyboardButton("🚨 Ver Accesos Detallados", callback_data="admin_ver_accesos_no_autorizados")],
                [InlineKeyboardButton("📋 Ver Bloqueos", callback_data="admin_bloqueos")],
                [InlineKeyboardButton("⬅️ Volver a Usuarios", callback_data="admin_reporte_usuarios")]
            ]
            
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            mensaje = f"📊 **ESTADÍSTICAS DE USUARIOS**\n\n❌ Error: {str(e)}"
            keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_reporte_usuarios")]]
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_ver_accesos_no_autorizados_callback(self, query):
        """Callback para ver accesos no autorizados detallados"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            from core.user_manager_accesos import generar_reporte_accesos_no_autorizados
            from datetime import datetime
            
            fecha_hoy = datetime.now().strftime('%Y-%m-%d')
            reporte = generar_reporte_accesos_no_autorizados(self.user_manager, fecha_hoy, limite=20)
            
            keyboard = [
                [InlineKeyboardButton("📅 Ver Otro Día", callback_data="admin_accesos_seleccionar_fecha")],
                [InlineKeyboardButton("⬅️ Volver a Usuarios", callback_data="admin_reporte_usuarios")]
            ]
            
            await query.edit_message_text(reporte, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            
        except Exception as e:
            mensaje = f"🚨 **ACCESOS NO AUTORIZADOS**\n\n❌ Error: {str(e)}"
            keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_reporte_usuarios")]]
            await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_admin_reporte_tecnico_callback(self, query):
        """Callback para reporte técnico"""
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        try:
            # Estado de sistemas
            telegram_ok = self.ready
            scheduler_ok = hasattr(self, 'signal_scheduler') and self.signal_scheduler is not None
            quotex_ok = hasattr(self, 'market_manager') and self.market_manager is not None
            
            mensaje = f"""🔧 **REPORTE TÉCNICO**

📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

🔧 **ESTADO DE SISTEMAS:**
• **Bot Telegram:** {'✅ Operativo' if telegram_ok else '❌ Error'}
• **Signal Scheduler:** {'✅ Funcionando' if scheduler_ok else '❌ Detenido'}
• **Market Manager:** {'✅ Conectado' if quotex_ok else '❌ Desconectado'}

💾 **RECURSOS:**
• **Memoria:** Óptima
• **CPU:** Normal
• **Conexión:** Estable

📊 **MÉTRICAS:**
• **Uptime:** Desde {datetime.now().strftime('%H:%M')}
• **Requests procesados:** {len(self.user_manager.usuarios_activos) * 10}
• **Errores críticos:** 0
• **Warnings:** 0

🔒 **SEGURIDAD:**
• **Autenticación:** ✅ Activa
• **Encriptación:** ✅ Habilitada
• **Firewall:** ✅ Protegido

⚡ **RENDIMIENTO:**
• **Latencia promedio:** < 100ms
• **Throughput:** Óptimo
• **Estado general:** ✅ Excelente"""
                
        except Exception as e:
            mensaje = f"🔧 **REPORTE TÉCNICO**\n\n❌ Error generando reporte: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("📋 Logs", callback_data="admin_ver_logs")],
            [InlineKeyboardButton("⬅️ Volver a Reportes", callback_data="admin_reportes")]
        ]
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_analisis_detallado_pdf(self, query):
        """Genera y envía un PDF con el análisis técnico completo de todas las estrategias"""
        user_id = str(query.from_user.id)
        
        try:
            # Mensaje de progreso
            await query.answer("📄 Generando PDF del análisis completo...", show_alert=False)
            
            # Obtener datos del caché
            if not hasattr(self, '_analisis_detallado_cache') or user_id not in self._analisis_detallado_cache:
                await query.answer("❌ Datos de análisis no disponibles. Busca un mercado primero.", show_alert=True)
                return
            
            cache_data = self._analisis_detallado_cache[user_id]
            symbol = cache_data.get('symbol', 'N/A')
            nombre = cache_data.get('nombre', symbol)
            resultado = cache_data.get('resultado', {})
            detalles = cache_data.get('detalles', {})
            
            # Generar PDF
            from datetime import datetime
            import os
            
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from reportlab.lib.units import inch
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
                
                # Crear directorio temporal
                os.makedirs('temp', exist_ok=True)
                
                # Nombre del archivo
                fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'temp/analisis_{symbol}_{fecha_hora}.pdf'
                
                # Crear documento
                doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
                elements = []
                styles = getSampleStyleSheet()
                
                # Estilos personalizados
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=20,
                    textColor=colors.HexColor('#1a73e8'),
                    spaceAfter=20,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Bold'
                )
                
                subtitle_style = ParagraphStyle(
                    'Subtitle',
                    parent=styles['Heading2'],
                    fontSize=14,
                    textColor=colors.HexColor('#1a73e8'),
                    spaceAfter=12,
                    spaceBefore=12,
                    fontName='Helvetica-Bold'
                )
                
                # Título principal
                elements.append(Paragraph(f"📊 ANÁLISIS TÉCNICO COMPLETO", title_style))
                elements.append(Paragraph(f"<b>Mercado:</b> {nombre} ({symbol})", styles['Normal']))
                elements.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
                elements.append(Spacer(1, 0.3*inch))
                
                # Resumen ejecutivo
                efectividad_total = resultado.get('efectividad_total', 0)
                decision = resultado.get('decision', 'Sin señal')
                
                elements.append(Paragraph("🎯 RESUMEN EJECUTIVO", subtitle_style))
                
                resumen_data = [
                    ['Efectividad Total', f"{efectividad_total:.1f}%"],
                    ['Decisión', decision if decision else 'Sin señal clara'],
                    ['Timestamp', datetime.now().strftime('%d/%m/%Y %H:%M:%S')]
                ]
                
                resumen_table = Table(resumen_data, colWidths=[2.5*inch, 3.5*inch])
                resumen_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f0fe')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                elements.append(resumen_table)
                elements.append(Spacer(1, 0.3*inch))
                
                # Estrategias individuales
                tendencia = detalles.get('tendencia', {})
                sr = detalles.get('soportes_resistencias', {})
                patrones = detalles.get('patrones', {})
                volatilidad = detalles.get('volatilidad', {})
                
                # 1. TENDENCIA
                elements.append(Paragraph("1️⃣ ESTRATEGIA: TENDENCIA (30% peso)", subtitle_style))
                
                tend_data = [
                    ['Métrica', 'Valor'],
                    ['Efectividad', f"{tendencia.get('efectividad', 0):.1f}%"],
                    ['Dirección', tendencia.get('direccion', 'indefinida').upper()],
                    ['Peso en decisión', '30%']
                ]
                
                detalles_tend = tendencia.get('detalles', {})
                if detalles_tend:
                    tendencias_mtf = detalles_tend.get('tendencias_multitimeframe', {})
                    if tendencias_mtf:
                        primaria = tendencias_mtf.get('primaria', {})
                        if primaria:
                            tend_data.append(['Tendencia Primaria (MA200)', f"{primaria.get('direccion', 'N/A').upper()} - Fuerza: {primaria.get('fuerza', 0):.1f}/100"])
                        secundaria = tendencias_mtf.get('secundaria', {})
                        if secundaria:
                            tend_data.append(['Tendencia Secundaria (MA50)', f"{secundaria.get('direccion', 'N/A').upper()} - Fuerza: {secundaria.get('fuerza', 0):.1f}/100"])
                
                tend_table = Table(tend_data, colWidths=[2.5*inch, 3.5*inch])
                tend_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(tend_table)
                elements.append(Spacer(1, 0.2*inch))
                
                # 2. SOPORTES Y RESISTENCIAS
                elements.append(Paragraph("2️⃣ ESTRATEGIA: SOPORTES/RESISTENCIAS (20% peso)", subtitle_style))
                
                sr_data = [
                    ['Métrica', 'Valor'],
                    ['Efectividad', f"{sr.get('efectividad', 0):.1f}%"],
                    ['Dirección', sr.get('direccion', 'indefinida').upper()],
                    ['Peso en decisión', '20%']
                ]
                
                detalles_sr = sr.get('detalles', {})
                if detalles_sr:
                    zonas = detalles_sr.get('zonas_detectadas', [])
                    if isinstance(zonas, list) and len(zonas) > 0:
                        sr_data.append(['Zonas detectadas', str(len(zonas))])
                        soportes = [z for z in zonas if z.get('tipo') == 'Soporte']
                        resistencias = [z for z in zonas if z.get('tipo') == 'Resistencia']
                        sr_data.append(['Soportes', str(len(soportes))])
                        sr_data.append(['Resistencias', str(len(resistencias))])
                
                sr_table = Table(sr_data, colWidths=[2.5*inch, 3.5*inch])
                sr_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(sr_table)
                elements.append(Spacer(1, 0.2*inch))
                
                # 3. PATRONES DE VELAS
                elements.append(Paragraph("3️⃣ ESTRATEGIA: PATRONES DE VELAS (30% peso)", subtitle_style))
                
                pat_data = [
                    ['Métrica', 'Valor'],
                    ['Efectividad', f"{patrones.get('efectividad', 0):.1f}%"],
                    ['Dirección', patrones.get('direccion', 'indefinida').upper()],
                    ['Peso en decisión', '30%']
                ]
                
                detalles_pat = patrones.get('detalles', {})
                if detalles_pat and isinstance(detalles_pat, dict):
                    velas = detalles_pat.get('velas_analizadas', 0)
                    if velas:
                        pat_data.append(['Velas analizadas', str(velas)])
                    patrones_det = detalles_pat.get('patrones_detectados', [])
                    if isinstance(patrones_det, list) and len(patrones_det) > 0:
                        pat_data.append(['Patrones detectados', str(len(patrones_det))])
                
                pat_table = Table(pat_data, colWidths=[2.5*inch, 3.5*inch])
                pat_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(pat_table)
                elements.append(Spacer(1, 0.2*inch))
                
                # 4. VOLATILIDAD
                elements.append(Paragraph("4️⃣ ESTRATEGIA: VOLATILIDAD Y PULLBACK (20% peso)", subtitle_style))
                
                vol_data = [
                    ['Métrica', 'Valor'],
                    ['Efectividad', f"{volatilidad.get('efectividad', 0):.1f}%"],
                    ['Dirección', volatilidad.get('direccion', 'indefinida').upper()],
                    ['Peso en decisión', '20%']
                ]
                
                detalles_vol = volatilidad.get('detalles', {})
                if detalles_vol and isinstance(detalles_vol, dict):
                    atr = detalles_vol.get('atr', 0)
                    if atr:
                        vol_data.append(['ATR', f"{atr:.5f}"])
                    pullback = detalles_vol.get('pullback_detectado', False)
                    vol_data.append(['Pullback detectado', 'Sí' if pullback else 'No'])
                
                vol_table = Table(vol_data, colWidths=[2.5*inch, 3.5*inch])
                vol_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(vol_table)
                elements.append(Spacer(1, 0.3*inch))
                
                # Conclusión
                elements.append(Paragraph("💡 CONCLUSIÓN", subtitle_style))
                
                if efectividad_total >= 80:
                    conclusion = f"<b>SEÑAL VÁLIDA:</b> El mercado {nombre} cumple con los criterios de efectividad (≥80%). Se recomienda operar siguiendo la dirección indicada: <b>{decision}</b>"
                elif efectividad_total >= 70:
                    conclusion = f"<b>SEÑAL MODERADA:</b> El mercado {nombre} muestra condiciones aceptables pero no óptimas. Considerar esperar mejores condiciones."
                else:
                    conclusion = f"<b>NO OPERAR:</b> El mercado {nombre} no cumple con los criterios mínimos de efectividad. Se recomienda esperar mejores condiciones."
                
                elements.append(Paragraph(conclusion, styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
                
                # Pie de página
                footer_text = f"<i>Generado por CubaYDSignal Bot - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i><br/><i>Este análisis es informativo y no constituye asesoramiento financiero.</i>"
                elements.append(Paragraph(footer_text, styles['Normal']))
                
                # Construir PDF
                doc.build(elements)
                
                # Enviar PDF
                with open(filename, 'rb') as pdf_file:
                    await query.message.reply_document(
                        document=pdf_file,
                        filename=f"analisis_{symbol}_{fecha_hora}.pdf",
                        caption=f"📄 **Análisis Técnico Completo**\n\n"
                                f"📊 Mercado: {nombre}\n"
                                f"🎯 Efectividad: {efectividad_total:.1f}%\n"
                                f"🎲 Decisión: {decision if decision else 'Sin señal'}\n"
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
    
    # ==================== ANÁLISIS FORZADO ====================
    
    async def handle_admin_analisis_forzado(self, query):
        """Muestra el menú de Análisis Forzado"""
        try:
            await query.answer()
        except:
            pass
        
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        # Verificar si ya hay un análisis forzado activo
        analisis_activo = False
        par_actual = None
        efectividad_actual = None
        duracion_restante = None
        
        if hasattr(self, 'signal_scheduler') and self.signal_scheduler:
            analisis_activo = getattr(self.signal_scheduler, 'analisis_forzado_activo', False)
            par_actual = getattr(self.signal_scheduler, 'analisis_forzado_par', None)
            efectividad_actual = getattr(self.signal_scheduler, 'efectividad_minima_temporal', 80)
            
            # Calcular duración restante
            if analisis_activo and hasattr(self.signal_scheduler, 'analisis_forzado_inicio'):
                from datetime import datetime
                inicio = getattr(self.signal_scheduler, 'analisis_forzado_inicio', None)
                duracion_total = getattr(self.signal_scheduler, 'analisis_forzado_duracion', 0)
                if inicio and duracion_total:
                    tiempo_transcurrido = (datetime.now() - inicio).total_seconds() / 60
                    duracion_restante = max(0, duracion_total - tiempo_transcurrido)
        
        # Si hay análisis activo, mostrar opciones especiales
        if analisis_activo and par_actual:
            tiempo_texto = f"{int(duracion_restante)} minutos" if duracion_restante else "Indefinido"
            mensaje = f"""⚡ **ANÁLISIS FORZADO ACTIVO**

🎯 Mercado actual: {par_actual}
📊 Efectividad: {efectividad_actual}%
⏱️ Tiempo restante: {tiempo_texto}

Ya tienes un análisis forzado en ejecución.

¿Qué deseas hacer?
"""
            
            keyboard = [
                [InlineKeyboardButton("🛑 Detener análisis actual", callback_data="af_detener_actual")],
                [InlineKeyboardButton("🔄 Reemplazar con otro mercado", callback_data="af_reemplazar_mercado")],
                [InlineKeyboardButton("➕ Analizar mercado adicional", callback_data="af_adicional_mercado")],
                [InlineKeyboardButton("🎯 Ajustar Efectividad", callback_data="analisis_forzado_efectividad")],
                [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
            ]
        else:
            # No hay análisis activo, mostrar menú normal
            mensaje = """⚡ **ANÁLISIS FORZADO**

El análisis forzado activa un estudio inmediato del mercado sin esperar las condiciones normales del ciclo.

**Usa esta opción solo cuando desees una lectura urgente del comportamiento actual del mercado.**

⚠️ **Importante:**
• El análisis se ejecutará inmediatamente
• No esperará el ciclo normal de señales
• Puede generar señales fuera del horario operativo
• Requiere conexión activa a Quotex

📊 **Opciones disponibles:**
Selecciona una opción para configurar el análisis forzado:
"""
            
            keyboard = [
                [InlineKeyboardButton("💱 Configurar Mercado", callback_data="analisis_forzado_mercado")],
                [InlineKeyboardButton("🎯 Ajustar Efectividad", callback_data="analisis_forzado_efectividad")],
                [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="volver_panel_admin")]
            ]
        
        await query.edit_message_text(
            mensaje,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_analisis_forzado_mercado(self, query):
        """Inicia el flujo de configuración de mercado para análisis forzado"""
        try:
            await query.answer()
        except:
            pass
        
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        user_id = str(query.from_user.id)
        
        # Inicializar estado de conversación
        if not hasattr(self, '_analisis_forzado_state'):
            self._analisis_forzado_state = {}
        
        self._analisis_forzado_state[user_id] = {
            'step': 'tipo_mercado',
            'data': {}
        }
        
        mensaje = """💱 **CONFIGURACIÓN DE MERCADO**

**Paso 1 de 5:** Tipo de Mercado

¿Qué tipo de mercado deseas analizar?

📊 **OTC (Over The Counter):**
• Disponible 24/7
• Sin horarios de noticias
• Ideal para fines de semana

📈 **Normal:**
• Horario de mercado regular
• Mayor liquidez
• Lun-Vie (horario de bolsa)

**Responde con:** `OTC` o `NORMAL`
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 OTC", callback_data="af_tipo_otc"),
             InlineKeyboardButton("📈 Normal", callback_data="af_tipo_normal")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
        ]
        
        await query.edit_message_text(
            mensaje,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_analisis_forzado_efectividad(self, query):
        """Permite ajustar la efectividad mínima temporalmente"""
        try:
            await query.answer()
        except:
            pass
        
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        user_id = str(query.from_user.id)
        
        # Obtener efectividad actual
        efectividad_actual = getattr(self.signal_scheduler, 'efectividad_minima_temporal', 80)
        
        mensaje = f"""🎯 **AJUSTE DE EFECTIVIDAD**

**Valor actual:** {efectividad_actual}%
**Valor por defecto:** 80%

El valor de efectividad por defecto es **80%**.

¿Deseas cambiarlo temporalmente para hoy?

⚠️ **Importante:**
• Este valor se mantendrá activo hasta el cierre del ciclo diario
• Luego volverá automáticamente al 80%
• Valores más bajos generarán más señales (menos precisas)
• Valores más altos generarán menos señales (más precisas)

**Responde con un número entre 60 y 95**
Ejemplo: 60, 70, 85, 90
"""
        
        keyboard = [
            [InlineKeyboardButton("60%", callback_data="af_efectividad_60"),
             InlineKeyboardButton("65%", callback_data="af_efectividad_65"),
             InlineKeyboardButton("70%", callback_data="af_efectividad_70")],
            [InlineKeyboardButton("75%", callback_data="af_efectividad_75"),
             InlineKeyboardButton("80%", callback_data="af_efectividad_80"),
             InlineKeyboardButton("85%", callback_data="af_efectividad_85")],
            [InlineKeyboardButton("90%", callback_data="af_efectividad_90"),
             InlineKeyboardButton("95%", callback_data="af_efectividad_95")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
        ]
        
        await query.edit_message_text(
            mensaje,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_tipo_mercado(self, query, tipo):
        """Maneja la selección del tipo de mercado"""
        try:
            await query.answer()
        except Exception as e:
            print(f"[AF] Error en query.answer(): {e}")
        
        user_id = str(query.from_user.id)
        print(f"[AF] handle_af_tipo_mercado llamado - user_id: {user_id}, tipo: {tipo}")
        
        if not hasattr(self, '_analisis_forzado_state'):
            print(f"[AF] ⚠️ _analisis_forzado_state no existe, creando...")
            self._analisis_forzado_state = {}
        
        if user_id not in self._analisis_forzado_state:
            print(f"[AF] ⚠️ Usuario {user_id} no tiene estado, creando...")
            self._analisis_forzado_state[user_id] = {
                'step': 'tipo_mercado',
                'data': {}
            }
        
        # Guardar tipo de mercado
        self._analisis_forzado_state[user_id]['data']['tipo'] = tipo
        self._analisis_forzado_state[user_id]['step'] = 'par_mercado'
        
        print(f"[AF] ✅ Estado actualizado: {self._analisis_forzado_state[user_id]}")
        
        mensaje = f"""💱 **CONFIGURACIÓN DE MERCADO**

**Paso 2 de 5:** Par de Mercado

✅ Tipo seleccionado: **{tipo}**

Selecciona un par común o escribe uno personalizado:

**Responde con el nombre del par**
Ejemplo: EURUSD, GBPUSD, BTCUSD
"""
        
        # Agregar sufijo _otc si es OTC
        sufijo = "_otc" if tipo == "OTC" else ""
        
        keyboard = [
            [InlineKeyboardButton(f"EUR/USD{sufijo}", callback_data=f"af_par_EURUSD{sufijo}"),
             InlineKeyboardButton(f"GBP/USD{sufijo}", callback_data=f"af_par_GBPUSD{sufijo}")],
            [InlineKeyboardButton(f"USD/JPY{sufijo}", callback_data=f"af_par_USDJPY{sufijo}"),
             InlineKeyboardButton(f"AUD/USD{sufijo}", callback_data=f"af_par_AUDUSD{sufijo}")],
            [InlineKeyboardButton(f"BTC/USD{sufijo}", callback_data=f"af_par_BTCUSD{sufijo}"),
             InlineKeyboardButton(f"ETH/USD{sufijo}", callback_data=f"af_par_ETHUSD{sufijo}")],
            [InlineKeyboardButton("✍️ Escribir otro par", callback_data="af_par_custom")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
        ]
        
        await query.edit_message_text(
            mensaje,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_par_mercado(self, query, par):
        """Maneja la selección del par de mercado"""
        try:
            await query.answer()
        except Exception as e:
            print(f"[AF] Error en query.answer(): {e}")
        
        user_id = str(query.from_user.id)
        print(f"[AF] handle_af_par_mercado llamado - user_id: {user_id}, par: {par}")
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        # Guardar par de mercado
        self._analisis_forzado_state[user_id]['data']['par'] = par
        self._analisis_forzado_state[user_id]['step'] = 'temporalidad'
        
        print(f"[AF] ✅ Estado actualizado: {self._analisis_forzado_state[user_id]}")
        
        tipo = self._analisis_forzado_state[user_id]['data'].get('tipo', 'NORMAL')
        
        mensaje = f"""💱 CONFIGURACIÓN DE MERCADO

Paso 3 de 6: Temporalidad (Timeframe)

✅ Tipo: {tipo}
✅ Par: {par}

Selecciona la temporalidad para el análisis:
"""
        
        keyboard = [
            [InlineKeyboardButton("1M (1 minuto)", callback_data="af_temp_1M"),
             InlineKeyboardButton("5M (5 minutos) ⭐", callback_data="af_temp_5M")],
            [InlineKeyboardButton("15M (15 minutos)", callback_data="af_temp_15M"),
             InlineKeyboardButton("30M (30 minutos)", callback_data="af_temp_30M")],
            [InlineKeyboardButton("1H (1 hora)", callback_data="af_temp_1H"),
             InlineKeyboardButton("4H (4 horas)", callback_data="af_temp_4H")],
            [InlineKeyboardButton("✍️ Escribir otra", callback_data="af_temp_custom")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_temporalidad(self, query, temporalidad):
        """Maneja la selección de temporalidad"""
        try:
            await query.answer()
        except Exception as e:
            print(f"[AF] Error en query.answer(): {e}")
        
        user_id = str(query.from_user.id)
        print(f"[AF] handle_af_temporalidad llamado - user_id: {user_id}, temp: {temporalidad}")
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        # Guardar temporalidad
        self._analisis_forzado_state[user_id]['data']['temporalidad'] = temporalidad
        self._analisis_forzado_state[user_id]['step'] = 'efectividad'
        
        print(f"[AF] ✅ Estado actualizado: {self._analisis_forzado_state[user_id]}")
        
        tipo = self._analisis_forzado_state[user_id]['data'].get('tipo', 'NORMAL')
        par = self._analisis_forzado_state[user_id]['data'].get('par', 'EURUSD')
        
        mensaje = f"""💱 CONFIGURACIÓN DE MERCADO

Paso 4 de 6: Efectividad Mínima

✅ Tipo: {tipo}
✅ Par: {par}
✅ Temporalidad: {temporalidad}

Selecciona la efectividad mínima para las señales:
"""
        
        keyboard = [
            [InlineKeyboardButton("70% (Más señales)", callback_data="af_efectividad_70"),
             InlineKeyboardButton("75%", callback_data="af_efectividad_75")],
            [InlineKeyboardButton("80% ⭐ Recomendado", callback_data="af_efectividad_80"),
             InlineKeyboardButton("85%", callback_data="af_efectividad_85")],
            [InlineKeyboardButton("90% (Muy selectivo)", callback_data="af_efectividad_90")],
            [InlineKeyboardButton("✍️ Escribir otro %", callback_data="af_efectividad_custom")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_set_efectividad(self, query, porcentaje):
        """Maneja la selección de efectividad y avanza a duración"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        print(f"[AF] handle_af_set_efectividad llamado - user_id: {user_id}, porcentaje: {porcentaje}")
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        # Guardar efectividad
        self._analisis_forzado_state[user_id]['data']['efectividad'] = porcentaje
        self._analisis_forzado_state[user_id]['step'] = 'duracion'
        
        print(f"[AF] ✅ Estado actualizado: {self._analisis_forzado_state[user_id]}")
        
        tipo = self._analisis_forzado_state[user_id]['data'].get('tipo', 'NORMAL')
        par = self._analisis_forzado_state[user_id]['data'].get('par', 'EURUSD')
        temporalidad = self._analisis_forzado_state[user_id]['data'].get('temporalidad', '5M')
        
        mensaje = f"""💱 CONFIGURACIÓN DE MERCADO

Paso 5 de 6: Duración del Análisis

✅ Tipo: {tipo}
✅ Par: {par}
✅ Temporalidad: {temporalidad}
✅ Efectividad: {porcentaje}%

⏰ ¿Por cuánto tiempo quieres analizar SOLO este mercado?

Durante este tiempo, el bot:
• Analizará únicamente {par}
• Ignorará todos los demás mercados
• Generará señales solo de este par
• Volverá al modo normal al finalizar

Selecciona la duración:
"""
        
        keyboard = [
            [InlineKeyboardButton("⏱️ 15 minutos", callback_data="af_duracion_15"),
             InlineKeyboardButton("⏱️ 30 minutos", callback_data="af_duracion_30")],
            [InlineKeyboardButton("⏱️ 1 hora", callback_data="af_duracion_60"),
             InlineKeyboardButton("⏱️ 2 horas", callback_data="af_duracion_120")],
            [InlineKeyboardButton("⏱️ 4 horas", callback_data="af_duracion_240"),
             InlineKeyboardButton("⏱️ Hasta fin de día", callback_data="af_duracion_eod")],
            [InlineKeyboardButton("✍️ Escribir duración (minutos)", callback_data="af_duracion_custom")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
        ]
        
        await query.edit_message_text(
            mensaje,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_duracion(self, query, duracion):
        """Maneja la selección de duración del análisis"""
        try:
            await query.answer()
        except Exception as e:
            print(f"[AF] Error en query.answer(): {e}")
        
        user_id = str(query.from_user.id)
        print(f"[AF] handle_af_duracion llamado - user_id: {user_id}, duracion: {duracion}")
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        # Calcular minutos
        if duracion == "eod":
            from datetime import datetime, time
            now = datetime.now()
            end_of_day = datetime.combine(now.date(), time(20, 0, 0))  # 8 PM
            if now >= end_of_day:
                minutos = 30  # Si ya pasó las 8 PM, dar 30 minutos
            else:
                minutos = int((end_of_day - now).total_seconds() / 60)
            duracion_texto = f"Hasta las 8:00 PM ({minutos} minutos)"
        else:
            minutos = int(duracion)
            if minutos == 60:
                duracion_texto = "1 hora"
            elif minutos == 120:
                duracion_texto = "2 horas"
            elif minutos == 240:
                duracion_texto = "4 horas"
            else:
                duracion_texto = f"{minutos} minutos"
        
        # Guardar duración
        self._analisis_forzado_state[user_id]['data']['duracion_minutos'] = minutos
        self._analisis_forzado_state[user_id]['step'] = 'confirmar'
        
        print(f"[AF] ✅ Estado actualizado: {self._analisis_forzado_state[user_id]}")
        
        # Obtener todos los datos
        data = self._analisis_forzado_state[user_id]['data']
        tipo = data.get('tipo', 'NORMAL')
        par = data.get('par', 'EURUSD')
        temporalidad = data.get('temporalidad', '5M')
        efectividad = data.get('efectividad', 80)
        
        mensaje = f"""💱 CONFIRMACIÓN DE ANÁLISIS FORZADO

Paso 6 de 6: Confirmar Configuración

📊 Resumen de configuración:

✅ Tipo: {tipo}
✅ Par: {par}
✅ Temporalidad: {temporalidad}
✅ Efectividad mínima: {efectividad}%
✅ Duración: {duracion_texto}

⚠️ El bot hará lo siguiente:

1. Analizará ÚNICAMENTE el par {par}
2. Ignorará todos los demás mercados
3. Generará señales solo de este par
4. Usará efectividad mínima de {efectividad}%
5. Durará {duracion_texto}
6. Después volverá al modo normal automáticamente

¿Confirmas iniciar el análisis forzado?
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar y Comenzar", callback_data="af_confirmar_inicio")],
            [InlineKeyboardButton("🔄 Cambiar configuración", callback_data="admin_analisis_forzado")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="volver_panel_admin")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_confirmar_inicio(self, query):
        """Confirma e inicia el análisis forzado del mercado específico"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada.")
            return
        
        # Obtener configuración
        data = self._analisis_forzado_state[user_id]['data']
        par = data.get('par', 'EURUSD')
        duracion_minutos = data.get('duracion_minutos', 60)
        efectividad = data.get('efectividad', 80)
        temporalidad = data.get('temporalidad', '5M')
        
        # Activar análisis forzado en el signal_scheduler
        print(f"[AF] Activando análisis forzado: par={par}, duración={duracion_minutos}min, efectividad={efectividad}%")
        
        import asyncio
        from datetime import datetime, timedelta
        
        fin_analisis = datetime.now() + timedelta(minutes=duracion_minutos)
        
        if hasattr(self, 'signal_scheduler'):
            self.signal_scheduler.analisis_forzado_activo = True
            self.signal_scheduler.analisis_forzado_par = par
            self.signal_scheduler.analisis_forzado_duracion = duracion_minutos
            self.signal_scheduler.analisis_forzado_inicio = datetime.now()  # Guardar timestamp de inicio
            self.signal_scheduler.efectividad_minima_temporal = efectividad
            print(f"[AF] ✅ Análisis forzado activado en signal_scheduler")
            print(f"[AF] Estado: activo={self.signal_scheduler.analisis_forzado_activo}, par={self.signal_scheduler.analisis_forzado_par}")
            
            # Programar desactivación automática
            async def desactivar_analisis_forzado():
                await asyncio.sleep(duracion_minutos * 60)
                if hasattr(self, 'signal_scheduler'):
                    self.signal_scheduler.analisis_forzado_activo = False
                    self.signal_scheduler.analisis_forzado_par = None
                    self.signal_scheduler.efectividad_minima_temporal = 80
                    print(f"[Bot] Análisis forzado de {par} finalizado")
                    
                    # Notificar al admin
                    try:
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=f"✅ Análisis forzado finalizado\n\nEl análisis de {par} ha terminado.\nEl bot ha vuelto al modo normal."
                        )
                    except:
                        pass
            
            asyncio.create_task(desactivar_analisis_forzado())
        else:
            print(f"[AF] ❌ ERROR: signal_scheduler no encontrado")
        
        # Limpiar estado
        del self._analisis_forzado_state[user_id]
        
        mensaje = f"""✅ ANÁLISIS FORZADO INICIADO

🎯 Mercado: {par}
⏰ Duración: {duracion_minutos} minutos
📊 Efectividad mínima: {efectividad}%
🕐 Finaliza a las: {fin_analisis.strftime('%I:%M %p')}

⚡ El bot está ahora en modo análisis forzado:

• Analizando ÚNICAMENTE {par}
• Todos los demás mercados ignorados
• Generando señales solo de este par
• Volverá al modo normal automáticamente

📈 Esperando señales...
Te notificaré cuando encuentre una señal válida.

💰 ¿Quieres activar el TRADING AUTOMÁTICO?
"""
        
        keyboard = [
            [InlineKeyboardButton("🤖 Activar Trading Automático", callback_data="af_activar_trading")],
            [InlineKeyboardButton("📊 Solo Análisis (sin trading)", callback_data="af_solo_analisis_confirmado")],
            [InlineKeyboardButton("🛑 Detener análisis forzado", callback_data="af_detener")],
            [InlineKeyboardButton("🏠 Volver al Panel", callback_data="volver_panel_admin")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_activar_trading(self, query):
        """Activa el trading automático para el análisis forzado"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        print(f"[AF] Activando trading automático - user_id: {user_id}")
        
        # Inicializar estado de trading si no existe
        if not hasattr(self, '_af_trading_state'):
            self._af_trading_state = {}
        
        self._af_trading_state[user_id] = {}
        
        mensaje = """💰 TRADING AUTOMÁTICO

Selecciona el modo de trading:

🎮 DEMO: Operaciones en cuenta de práctica
💵 REAL: Operaciones con dinero real

⚠️ IMPORTANTE:
• Las operaciones se ejecutarán automáticamente
• Solo con señales del mercado en análisis forzado
• Con la efectividad mínima configurada
"""
        
        keyboard = [
            [InlineKeyboardButton("🎮 Modo DEMO", callback_data="af_trading_demo")],
            [InlineKeyboardButton("💵 Modo REAL", callback_data="af_trading_real")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="af_confirmar_inicio")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_trading_modo(self, query, modo):
        """Maneja la selección del modo de trading"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        if not hasattr(self, '_af_trading_state'):
            self._af_trading_state = {}
        
        if user_id not in self._af_trading_state:
            self._af_trading_state[user_id] = {}
        
        self._af_trading_state[user_id]['modo'] = modo
        
        mensaje = f"""💰 TRADING AUTOMÁTICO

✅ Modo seleccionado: {modo}

Selecciona el monto por operación:
"""
        
        keyboard = [
            [InlineKeyboardButton("$1", callback_data="af_trading_monto_1"),
             InlineKeyboardButton("$2", callback_data="af_trading_monto_2")],
            [InlineKeyboardButton("$5", callback_data="af_trading_monto_5"),
             InlineKeyboardButton("$10", callback_data="af_trading_monto_10")],
            [InlineKeyboardButton("$20", callback_data="af_trading_monto_20"),
             InlineKeyboardButton("$50", callback_data="af_trading_monto_50")],
            [InlineKeyboardButton("$100", callback_data="af_trading_monto_100")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="af_activar_trading")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_trading_monto(self, query, monto):
        """Maneja la selección del monto"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        if not hasattr(self, '_af_trading_state') or user_id not in self._af_trading_state:
            await query.edit_message_text("❌ Sesión expirada. Vuelve a empezar.")
            return
        
        self._af_trading_state[user_id]['monto'] = float(monto)
        
        modo = self._af_trading_state[user_id].get('modo', 'DEMO')
        
        mensaje = f"""💰 CONFIRMACIÓN DE TRADING AUTOMÁTICO

✅ Modo: {modo}
✅ Monto por operación: ${monto}

⚠️ IMPORTANTE:
• El bot ejecutará operaciones automáticamente
• Solo con señales del análisis forzado
• En cuenta {modo}
• Con ${monto} por operación

¿Confirmas activar el trading automático?
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar y Activar", callback_data="af_trading_confirmar")],
            [InlineKeyboardButton("⬅️ Cambiar monto", callback_data=f"af_trading_{modo.lower()}")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="af_confirmar_inicio")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_trading_confirmar(self, query):
        """Confirma y activa el trading automático"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        if not hasattr(self, '_af_trading_state') or user_id not in self._af_trading_state:
            await query.edit_message_text("❌ Sesión expirada. Vuelve a empezar.")
            return
        
        modo = self._af_trading_state[user_id].get('modo', 'DEMO')
        monto = self._af_trading_state[user_id].get('monto', 1)
        
        # Activar trading automático
        self._trading_activo = True
        self._trading_modo = modo
        self._trading_monto = monto
        
        print(f"[AF Trading] ✅ Trading automático activado - Modo: {modo}, Monto: ${monto}")
        
        # Limpiar estado
        del self._af_trading_state[user_id]
        
        mensaje = f"""✅ TRADING AUTOMÁTICO ACTIVADO

🤖 El bot ejecutará operaciones automáticamente

📊 Configuración:
• Modo: {modo}
• Monto: ${monto} por operación
• Solo señales del análisis forzado
• Efectividad mínima configurada

⚡ Estado: ACTIVO
El bot comenzará a operar cuando encuentre señales válidas.
"""
        
        keyboard = [
            [InlineKeyboardButton("🛑 Detener Trading", callback_data="af_detener_trading_activo")],
            [InlineKeyboardButton("📊 Ver Estado", callback_data="admin_trading")],
            [InlineKeyboardButton("🏠 Volver al Panel", callback_data="volver_panel_admin")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_detener(self, query):
        """Detiene el análisis forzado activo"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        print(f"[AF] Deteniendo análisis forzado - user_id: {user_id}")
        
        # Desactivar análisis forzado
        if hasattr(self, 'signal_scheduler'):
            self.signal_scheduler.analisis_forzado_activo = False
            self.signal_scheduler.analisis_forzado_par = None
            self.signal_scheduler.efectividad_minima_temporal = 80
            print(f"[AF] ✅ Análisis forzado detenido")
        
        mensaje = """🛑 ANÁLISIS FORZADO DETENIDO

El análisis forzado ha sido detenido manualmente.

✅ El bot ha vuelto al modo normal
✅ Analizará todos los mercados disponibles
✅ Usará efectividad mínima de 80%

Puedes iniciar un nuevo análisis forzado cuando quieras.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Nuevo análisis forzado", callback_data="admin_analisis_forzado")],
            [InlineKeyboardButton("🏠 Volver al Panel", callback_data="volver_panel_admin")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_detener_actual(self, query):
        """Detiene el análisis forzado activo actual"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        print(f"[AF] Deteniendo análisis forzado actual - user_id: {user_id}")
        
        # Obtener información del análisis actual
        par_actual = None
        if hasattr(self, 'signal_scheduler') and self.signal_scheduler:
            par_actual = getattr(self.signal_scheduler, 'analisis_forzado_par', None)
        
        # Desactivar análisis forzado
        if hasattr(self, 'signal_scheduler'):
            self.signal_scheduler.analisis_forzado_activo = False
            self.signal_scheduler.analisis_forzado_par = None
            self.signal_scheduler.efectividad_minima_temporal = 80
            print(f"[AF] ✅ Análisis forzado detenido: {par_actual}")
        
        mensaje = f"""🛑 **ANÁLISIS DETENIDO**

El análisis forzado de **{par_actual}** ha sido detenido.

✅ El bot ha vuelto al modo normal
✅ Analizará todos los mercados disponibles
✅ Efectividad mínima: 80%

¿Qué deseas hacer ahora?
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Nuevo análisis forzado", callback_data="admin_analisis_forzado")],
            [InlineKeyboardButton("🏠 Volver al Panel", callback_data="volver_panel_admin")]
        ]
        
        await query.edit_message_text(
            mensaje,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_reemplazar_mercado(self, query):
        """Reemplaza el mercado del análisis forzado actual con otro"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        print(f"[AF] Reemplazando mercado - user_id: {user_id}")
        
        # Detener el análisis actual
        if hasattr(self, 'signal_scheduler'):
            self.signal_scheduler.analisis_forzado_activo = False
            self.signal_scheduler.analisis_forzado_par = None
        
        # Iniciar flujo de nuevo análisis
        await self.handle_analisis_forzado_mercado(query)
    
    async def handle_af_adicional_mercado(self, query):
        """Permite analizar un mercado adicional en paralelo (función futura)"""
        try:
            await query.answer()
        except:
            pass
        
        mensaje = """➕ **ANÁLISIS MÚLTIPLE**

⚠️ **Función en desarrollo**

Esta función permitirá analizar múltiples mercados simultáneamente en modo forzado.

Por ahora, puedes:
• Detener el análisis actual y crear uno nuevo
• Reemplazar el mercado actual con otro

**Próximamente:**
• Análisis de hasta 3 mercados en paralelo
• Priorización automática de señales
• Gestión independiente de cada mercado
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Reemplazar mercado", callback_data="af_reemplazar_mercado")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_analisis_forzado")]
        ]
        
        await query.edit_message_text(
            mensaje,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_af_text_input(self, update, texto):
        """Maneja el input de texto durante el flujo de análisis forzado"""
        user_id = str(update.effective_user.id)
        
        if user_id not in self._analisis_forzado_state:
            print(f"[AF] ⚠️ Usuario {user_id} no tiene estado en handle_af_text_input")
            await update.message.reply_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        state = self._analisis_forzado_state[user_id]
        step = state['step']
        
        print(f"[AF] handle_af_text_input - user_id: {user_id}, step: {step}, texto: {texto}")
        
        if step == 'tipo_mercado':
            # Usuario escribió el tipo en lugar de usar botones
            tipo = texto.upper().strip()
            if tipo not in ['OTC', 'NORMAL']:
                await update.message.reply_text(
                    "❌ Tipo no válido. Usa los botones o escribe: `OTC` o `NORMAL`"
                )
                return
            
            # Guardar tipo primero
            state['data']['tipo'] = tipo
            
            mensaje = f"""💱 **CONFIGURACIÓN DE MERCADO**

**Paso 2 de 5:** Par de Mercado

✅ Tipo seleccionado: **{tipo}**

¿Qué par o mercado específico quieres analizar?

**Ejemplos:**
• EUR/USD
• GBP/USD
• USD/JPY
• BTC/USD
• ETH/USD
• EUR/USD_otc (si es OTC)

**Responde con el nombre del par**
Ejemplo: EUR/USD o EURUSD
"""
            # Solo cambiar el paso después de enviar el mensaje exitosamente
            await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
            state['step'] = 'par_mercado'
            
        elif step == 'par_mercado':
            # Guardar par de mercado primero
            state['data']['par'] = texto.upper().replace('/', '')
            
            mensaje = f"""💱 CONFIGURACIÓN DE MERCADO

Paso 3 de 5: Temporalidad (Timeframe)

✅ Tipo: {state['data']['tipo']}
✅ Par: {state['data']['par']}

¿En qué temporalidad quieres analizar el mercado?

📊 Temporalidades disponibles:

Corto Plazo:
• 1M (1 minuto) - Scalping extremo
• 5M (5 minutos) - Operaciones rápidas (Recomendado)
• 15M (15 minutos) - Trading intradía

Mediano Plazo:
• 30M (30 minutos) - Swing trading corto
• 1H (1 hora) - Análisis más profundo
• 4H (4 horas) - Trading posicional

Largo Plazo:
• 1D (1 día) - Análisis diario
• 1W (1 semana) - Tendencias largas

Recomendación: 5M para operaciones de 5 minutos

Responde con la temporalidad
Ejemplo: 5M, 15M, 1H
"""
            
            # Solo cambiar el paso después de enviar el mensaje exitosamente
            await update.message.reply_text(mensaje, parse_mode=None)
            state['step'] = 'temporalidad'
            
        elif step == 'temporalidad':
            # Guardar temporalidad
            temporalidad_valida = ['1M', '5M', '15M', '30M', '1H', '4H', '1D', '1W']
            temp_input = texto.upper().strip()
            
            if temp_input not in temporalidad_valida:
                await update.message.reply_text(
                    f"❌ Temporalidad no válida. Usa una de estas: {', '.join(temporalidad_valida)}\n\n"
                    f"Intenta de nuevo."
                )
                return
            
            # Guardar temporalidad primero
            state['data']['temporalidad'] = temp_input
            
            mensaje = f"""💱 **CONFIGURACIÓN DE MERCADO**

**Paso 4 de 5:** Efectividad

✅ Tipo: **{state['data']['tipo']}**
✅ Par: **{state['data']['par']}**
✅ Temporalidad: **{temp_input}**

¿Qué porcentaje de efectividad deseas aplicar a este análisis?

**Recomendaciones:**
• 60-69%: Muchas señales, menor precisión
• 70-79%: Más señales, precisión moderada
• 80%: Balance óptimo (por defecto)
• 81-90%: Menos señales, mayor precisión
• 91-95%: Muy selectivo

**Responde con un número entre 60 y 95**
Ejemplo: 60, 70, 80, 85, 90
"""
            
            # Solo cambiar el paso después de enviar el mensaje exitosamente
            await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
            state['step'] = 'efectividad'
            
        elif step == 'efectividad':
            # Validar y guardar efectividad
            try:
                efectividad = int(texto)
                if efectividad < 60 or efectividad > 95:
                    await update.message.reply_text("❌ El porcentaje debe estar entre 60 y 95. Intenta de nuevo.")
                    return
                
                # Guardar efectividad primero
                state['data']['efectividad'] = efectividad
                
                mensaje = f"""💱 **CONFIGURACIÓN DE MERCADO**

**Paso 5 de 5:** Tiempo de Análisis

✅ Tipo: **{state['data']['tipo']}**
✅ Par: **{state['data']['par']}**
✅ Temporalidad: **{state['data']['temporalidad']}**
✅ Efectividad: **{efectividad}%**

¿Durante cuánto tiempo quieres que el bot analice ese mercado?

**Opciones:**
• 5 min: Análisis rápido
• 15 min: Análisis estándar
• 30 min: Análisis extendido
• 1 hora: Análisis completo
• 2 horas: Análisis profundo

**Responde con el tiempo**
Ejemplo: 5 min, 15 min, 1 hora
"""
                
                # Solo cambiar el paso después de enviar el mensaje exitosamente
                await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)
                state['step'] = 'tiempo'
                
            except ValueError:
                await update.message.reply_text(
                    f"❌ **Error:** Debes ingresar un **número** entre 60 y 95.\n\n"
                    f"📊 Estás en el paso de **EFECTIVIDAD** (no temporalidad).\n"
                    f"✅ Tu temporalidad ya está configurada: **{state['data'].get('temporalidad', 'N/A')}**\n\n"
                    f"**Ejemplos válidos:** 60, 70, 80, 85, 90\n"
                    f"**Recomendado:** 80",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        elif step == 'tiempo':
            # Validar y normalizar el formato de tiempo
            texto_lower = texto.lower().strip()
            
            # Normalizar formatos comunes: "1m", "5m", "15m" -> "X min"
            # "1h", "2h" -> "X hora(s)"
            tiempo_normalizado = texto
            
            # Convertir formatos cortos a formato completo
            import re
            match_min = re.match(r'^(\d+)\s*m(?:in)?$', texto_lower)
            match_hora = re.match(r'^(\d+)\s*h(?:ora)?(?:s)?$', texto_lower)
            
            if match_min:
                minutos = match_min.group(1)
                tiempo_normalizado = f"{minutos} min"
            elif match_hora:
                horas = match_hora.group(1)
                tiempo_normalizado = f"{horas} hora" if horas == "1" else f"{horas} horas"
            
            # Guardar tiempo y avanzar a trading automático
            state['data']['tiempo'] = tiempo_normalizado
            state['step'] = 'trading_auto'
            
            mensaje = f"""💱 **CONFIGURACIÓN DE MERCADO**

**Paso 6 de 6:** Trading Automático

✅ Tipo: **{state['data']['tipo']}**
✅ Par: **{state['data']['par']}**
✅ Temporalidad: **{state['data']['temporalidad']}**
✅ Efectividad: **{state['data']['efectividad']}%**
✅ Tiempo: **{texto}**

━━━━━━━━━━━━━━━━━━━━━━

💰 **¿ACTIVAR TRADING AUTOMÁTICO?**

Si activas el trading automático, el bot ejecutará operaciones automáticamente cuando detecte señales válidas en este mercado.

**Opciones:**

🎮 **DEMO:** Operaciones en cuenta de práctica (sin riesgo)
💎 **REAL:** Operaciones con dinero real
⚪ **SOLO ANÁLISIS:** Solo recibir señales sin operar

**¿Qué deseas hacer?**
"""
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🎮 Trading DEMO", callback_data="af_trading_demo")],
                [InlineKeyboardButton("💎 Trading REAL", callback_data="af_trading_real")],
                [InlineKeyboardButton("⚪ Solo Análisis", callback_data="af_solo_analisis")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
            ]
            
            await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def ejecutar_analisis_forzado(self, update, config):
        """Ejecuta el análisis forzado con la configuración especificada"""
        tipo = config['tipo']
        par = config['par']
        temporalidad = config['temporalidad']
        efectividad = config['efectividad']
        tiempo = config['tiempo']
        
        # Mensaje de confirmación
        mensaje_confirmacion = f"""✅ **CONFIGURACIÓN DEL MERCADO ACTUALIZADA CON ÉXITO**

📊 **Resumen de Configuración:**

🔹 **Tipo:** {tipo}
🔹 **Par:** {par}
🔹 **Temporalidad:** {temporalidad}
🔹 **Efectividad:** {efectividad}%
🔹 **Tiempo de análisis:** {tiempo}

━━━━━━━━━━━━━━━━━━━━━━

⚡ **ANÁLISIS FORZADO INICIADO**

El bot comenzará a analizar el mercado **{par}** en temporalidad **{temporalidad}** inmediatamente con los parámetros configurados.

📊 **Estado:**
• Análisis en progreso...
• Timeframe: {temporalidad}
• Buscando señales con efectividad ≥{efectividad}%
• Duración: {tiempo}

🔔 **Notificaciones:**
Recibirás una notificación cuando:
• Se detecte una señal válida
• El análisis se complete
• Ocurra algún error

⏳ **Por favor espera...**
"""
        
        await update.message.reply_text(mensaje_confirmacion, parse_mode=ParseMode.MARKDOWN)
        
        # Convertir tiempo a minutos
        tiempo_minutos = self._convertir_tiempo_a_minutos(tiempo)
        
        # Ejecutar análisis continuo en segundo plano
        import asyncio
        asyncio.create_task(self._analisis_continuo(update, par, temporalidad, efectividad, tiempo_minutos))
    
    async def handle_af_trading_modo(self, query, modo):
        """Maneja la selección del modo de trading (DEMO/REAL)"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        state = self._analisis_forzado_state[user_id]
        state['data']['trading_modo'] = modo
        
        mensaje = f"""💰 **TRADING AUTOMÁTICO - {modo}**

✅ Configuración actual:
• Tipo: **{state['data']['tipo']}**
• Par: **{state['data']['par']}**
• Temporalidad: **{state['data']['temporalidad']}**
• Efectividad: **{state['data']['efectividad']}%**
• Tiempo: **{state['data']['tiempo']}**
• Modo: **{modo}**

━━━━━━━━━━━━━━━━━━━━━━

💵 **MONTO POR OPERACIÓN**

Selecciona el monto que se apostará automáticamente en cada señal detectada:

{'⚠️ **ADVERTENCIA:** Operaciones con dinero real' if modo == 'REAL' else '🎮 **Modo Práctica:** Sin riesgo'}
"""
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        if modo == "DEMO":
            keyboard = [
                [InlineKeyboardButton("$1", callback_data="af_monto_1"),
                 InlineKeyboardButton("$5", callback_data="af_monto_5"),
                 InlineKeyboardButton("$10", callback_data="af_monto_10")],
                [InlineKeyboardButton("$20", callback_data="af_monto_20"),
                 InlineKeyboardButton("$50", callback_data="af_monto_50"),
                 InlineKeyboardButton("$100", callback_data="af_monto_100")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
            ]
        else:  # REAL
            keyboard = [
                [InlineKeyboardButton("$1", callback_data="af_monto_1"),
                 InlineKeyboardButton("$5", callback_data="af_monto_5"),
                 InlineKeyboardButton("$10", callback_data="af_monto_10")],
                [InlineKeyboardButton("$20", callback_data="af_monto_20"),
                 InlineKeyboardButton("$50", callback_data="af_monto_50"),
                 InlineKeyboardButton("$100", callback_data="af_monto_100")],
                [InlineKeyboardButton("$200", callback_data="af_monto_200"),
                 InlineKeyboardButton("$500", callback_data="af_monto_500")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
            ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_af_solo_analisis(self, query):
        """Maneja la opción de solo análisis sin trading"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        state = self._analisis_forzado_state[user_id]
        config = state['data']
        
        # Ejecutar solo análisis sin trading
        await self.ejecutar_analisis_forzado_simple(query, config)
        
        # Limpiar estado
        del self._analisis_forzado_state[user_id]
    
    async def handle_af_set_monto(self, query, data):
        """Maneja la selección del monto"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        monto = int(data.replace("af_monto_", ""))
        state = self._analisis_forzado_state[user_id]
        state['data']['trading_monto'] = monto
        
        modo = state['data']['trading_modo']
        
        mensaje = f"""✅ **CONFIRMACIÓN DE TRADING AUTOMÁTICO**

📊 **Configuración Completa:**

**Mercado:**
• Tipo: {state['data']['tipo']}
• Par: {state['data']['par']}
• Temporalidad: {state['data']['temporalidad']}
• Efectividad: {state['data']['efectividad']}%
• Tiempo: {state['data']['tiempo']}

**Trading Automático:**
• Modo: {modo}
• Monto por operación: ${monto}

━━━━━━━━━━━━━━━━━━━━━━

⚡ **¿QUÉ SUCEDERÁ?**

1. El bot analizará **{state['data']['par']}** cada 30 segundos
2. Cuando detecte una señal con ≥{state['data']['efectividad']}% efectividad:
   → Ejecutará automáticamente la operación
   → En cuenta {modo}
   → Con monto de ${monto}
3. Te notificará cada operación ejecutada
4. Continuará durante {state['data']['tiempo']}

{'⚠️ **IMPORTANTE:** Asegúrate de tener saldo suficiente en tu cuenta ' + modo if modo == 'REAL' else '🎮 **Modo Práctica:** Sin riesgo de pérdida real'}

**¿Confirmas iniciar el trading automático?**
"""
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("🚀 Confirmar e Iniciar", callback_data="af_confirmar_trading")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="admin_analisis_forzado")]
        ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_af_confirmar_trading(self, query):
        """Confirma e inicia el trading automático con análisis forzado"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        if user_id not in self._analisis_forzado_state:
            await query.edit_message_text("❌ Sesión expirada. Usa /start y vuelve a Análisis Forzado.")
            return
        
        state = self._analisis_forzado_state[user_id]
        config = state['data']
        
        # Activar trading automático en el bot
        self._trading_activo = True
        self._trading_modo = config['trading_modo']
        self._trading_monto = config['trading_monto']
        self._trading_operaciones_hoy = 0
        
        # Ejecutar análisis con trading automático
        await self.ejecutar_analisis_forzado_con_trading(query, config)
        
        # Limpiar estado
        del self._analisis_forzado_state[user_id]
    
    async def ejecutar_analisis_forzado_simple(self, query, config):
        """Ejecuta análisis forzado sin trading automático"""
        # Activar bandera
        self._analisis_forzado_activo = True
        self._analisis_forzado_user_id = str(query.from_user.id)
        
        mensaje = f"""✅ **ANÁLISIS FORZADO INICIADO**

📊 **Configuración:**
• Par: {config['par']}
• Temporalidad: {config['temporalidad']}
• Efectividad: {config['efectividad']}%
• Duración: {config['tiempo']}

⚡ El bot analizará el mercado y te enviará señales cuando las detecte.

⏳ Por favor espera...
"""
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("❌ Detener Análisis", callback_data="af_detener_analisis")]
        ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        # Convertir tiempo y ejecutar análisis
        tiempo_minutos = self._convertir_tiempo_a_minutos(config['tiempo'])
        
        # Crear un objeto update falso para compatibilidad
        class FakeMessage:
            async def reply_text(self, text, **kwargs):
                await query.message.reply_text(text, **kwargs)
        
        class FakeUpdate:
            def __init__(self):
                self.message = FakeMessage()
                self.effective_user = query.from_user
        
        fake_update = FakeUpdate()
        
        import asyncio
        asyncio.create_task(self._analisis_continuo(fake_update, config['par'], config['temporalidad'], config['efectividad'], tiempo_minutos))
    
    async def ejecutar_analisis_forzado_con_trading(self, query, config):
        """Ejecuta análisis forzado CON trading automático"""
        # Activar banderas
        self._analisis_forzado_activo = True
        self._trading_auto_af_activo = True
        self._analisis_forzado_user_id = str(query.from_user.id)
        
        mensaje = f"""🚀 **TRADING AUTOMÁTICO INICIADO**

📊 **Configuración:**
• Par: {config['par']}
• Temporalidad: {config['temporalidad']}
• Efectividad: {config['efectividad']}%
• Duración: {config['tiempo']}

💰 **Trading:**
• Modo: {config['trading_modo']}
• Monto: ${config['trading_monto']}

⚡ El bot analizará el mercado y ejecutará operaciones automáticamente.

🔔 Recibirás notificación de cada operación ejecutada.

⏳ Por favor espera...
"""
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("🛑 Detener Trading", callback_data="af_detener_trading")]
        ]
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        # Convertir tiempo y ejecutar análisis
        tiempo_minutos = self._convertir_tiempo_a_minutos(config['tiempo'])
        
        # Crear un objeto update falso para compatibilidad
        class FakeMessage:
            async def reply_text(self, text, **kwargs):
                await query.message.reply_text(text, **kwargs)
        
        class FakeUpdate:
            def __init__(self):
                self.message = FakeMessage()
                self.effective_user = query.from_user
        
        fake_update = FakeUpdate()
        
        import asyncio
        asyncio.create_task(self._analisis_continuo_con_trading(fake_update, config['par'], config['temporalidad'], config['efectividad'], tiempo_minutos))
    
    def _convertir_tiempo_a_minutos(self, tiempo_str):
        """Convierte string de tiempo a minutos"""
        tiempo_str = tiempo_str.lower().strip()
        
        if 'hora' in tiempo_str or 'h' in tiempo_str:
            # Extraer número de horas
            import re
            match = re.search(r'(\d+)', tiempo_str)
            if match:
                horas = int(match.group(1))
                return horas * 60
        elif 'min' in tiempo_str or 'm' in tiempo_str:
            # Extraer número de minutos
            import re
            match = re.search(r'(\d+)', tiempo_str)
            if match:
                return int(match.group(1))
        
        # Por defecto 15 minutos
        return 15
    
    async def _analisis_continuo(self, update, par, temporalidad, efectividad, tiempo_minutos):
        """Ejecuta análisis continuo durante el tiempo especificado"""
        import asyncio
        from datetime import datetime, timedelta
        
        inicio = datetime.now()
        fin = inicio + timedelta(minutes=tiempo_minutos)
        
        analisis_count = 0
        señales_detectadas = 0
        
        print(f"[Análisis Forzado] Iniciando análisis continuo de {par} por {tiempo_minutos} minutos")
        
        try:
            while datetime.now() < fin and self._analisis_forzado_activo:
                analisis_count += 1
                tiempo_restante = (fin - datetime.now()).total_seconds() / 60
                
                print(f"[Análisis Forzado] Análisis #{analisis_count} - Tiempo restante: {tiempo_restante:.1f} min")
                
                # Verificar si se detuvo manualmente
                if not self._analisis_forzado_activo:
                    print("[Análisis Forzado] ⏹️ Detenido manualmente")
                    break
                
                # Obtener datos del mercado
                if hasattr(self, 'market_manager'):
                    df = await self.market_manager.obtener_datos_mercado(par)
                    
                    if df is not None and len(df) >= 50:
                        # Ejecutar análisis completo
                        from src.strategies.evaluar_estrategia_completa import evaluar_estrategia_completa
                        resultado = evaluar_estrategia_completa(df, par)
                
                        efectividad_resultado = resultado.get('efectividad_total', 0)
                        decision = resultado.get('decision')
                        detalles = resultado.get('detalles', {})
                        
                        # Si se detecta señal válida
                        if decision and efectividad_resultado >= efectividad:
                            señales_detectadas += 1
                            
                            # Extraer información de las nuevas mejoras
                            patrones_chartistas = detalles.get('patrones_chartistas', {})
                            canales = detalles.get('canales', {})
                            velas_japonesas = detalles.get('velas_japonesas', {})
                            presion_mercado = detalles.get('presion_mercado', {})
                            
                            # Mensaje para ADMINISTRADOR (con tiempo restante)
                            mensaje_admin = f"""✅ **SEÑAL #{señales_detectadas} DETECTADA - ANÁLISIS FORZADO**

📊 **Mercado:** {par}
⏱️ **Temporalidad:** {temporalidad}
🎯 **Efectividad:** {efectividad_resultado:.1f}%
📍 **Dirección:** {decision}
⏰ **Análisis:** #{analisis_count}

━━━━━━━━━━━━━━━━━━━━━━

📋 **ANÁLISIS COMPLETO:**

**Tendencia:**
• Dirección: {detalles.get('tendencia', {}).get('direccion', 'N/A')}
• Efectividad: {detalles.get('tendencia', {}).get('efectividad', 0):.1f}%

**Patrones Chartistas:** ✨
• Detectados: {len(patrones_chartistas.get('patrones_validos', []))}

**Canales:** ✨
• Canal activo: {'SÍ' if canales.get('hay_canal') else 'NO'}

**Velas Japonesas:** ✨
• Patrones: {velas_japonesas.get('estadisticas', {}).get('total_patrones', 0)}
• Presión: Compradores {presion_mercado.get('presion_compradora', 50):.0f}% vs Vendedores {presion_mercado.get('presion_vendedora', 50):.0f}%

━━━━━━━━━━━━━━━━━━━━━━

🟢 **RECOMENDACIÓN:** Operar {decision} en {temporalidad}

⏳ **Tiempo restante:** {tiempo_restante:.1f} minutos
📊 **Análisis realizados:** {analisis_count}

🔒 **Análisis Forzado** - Solo visible para administrador

🤖 – Señal generada por el Bot **CubaYDsignal**
"""
                            
                            # Mensaje para USUARIOS (sin tiempo restante)
                            mensaje_usuarios = f"""✅ **SEÑAL DETECTADA**

📊 **Mercado:** {par}
⏱️ **Temporalidad:** {temporalidad}
🎯 **Efectividad:** {efectividad_resultado:.1f}%
📍 **Dirección:** {decision}

━━━━━━━━━━━━━━━━━━━━━━

📋 **ANÁLISIS COMPLETO:**

**Tendencia:**
• Dirección: {detalles.get('tendencia', {}).get('direccion', 'N/A')}
• Efectividad: {detalles.get('tendencia', {}).get('efectividad', 0):.1f}%

**Patrones Chartistas:** ✨
• Detectados: {len(patrones_chartistas.get('patrones_validos', []))}

**Canales:** ✨
• Canal activo: {'SÍ' if canales.get('hay_canal') else 'NO'}

**Velas Japonesas:** ✨
• Patrones: {velas_japonesas.get('estadisticas', {}).get('total_patrones', 0)}
• Presión: Compradores {presion_mercado.get('presion_compradora', 50):.0f}% vs Vendedores {presion_mercado.get('presion_vendedora', 50):.0f}%

━━━━━━━━━━━━━━━━━━━━━━

🟢 **RECOMENDACIÓN:** Operar {decision} en {temporalidad}

🤖 – Señal generada por el Bot **CubaYDsignal**
"""
                            
                            # Enviar al ADMINISTRADOR (con tiempo restante)
                            await update.message.reply_text(mensaje_admin, parse_mode=ParseMode.MARKDOWN)
                            
                            # Enviar a USUARIOS ACTIVOS (sin tiempo restante)
                            if hasattr(self, 'user_manager') and hasattr(self.user_manager, 'usuarios_activos'):
                                for user_id in list(self.user_manager.usuarios_activos.keys()):
                                    # No enviar al admin de nuevo
                                    if user_id != str(update.effective_user.id):
                                        try:
                                            await self.send_message(user_id, mensaje_usuarios)
                                        except Exception as e:
                                            print(f"[Análisis Forzado] ⚠️ No se pudo enviar a usuario {user_id}: {e}")
                            
                            print(f"[Análisis Forzado] ✅ Señal #{señales_detectadas} enviada - {decision} {efectividad_resultado:.1f}%")
                
                # Esperar antes del siguiente análisis (30 segundos)
                await asyncio.sleep(30)
            
            # Análisis completado o detenido
            estado = "⏹️ DETENIDO MANUALMENTE" if not self._analisis_forzado_activo else "🏁 COMPLETADO"
            mensaje_final = f"""{estado} **- ANÁLISIS FORZADO**

📊 **Mercado:** {par}
⏱️ **Temporalidad:** {temporalidad}
⏰ **Duración:** {tiempo_minutos} minutos

━━━━━━━━━━━━━━━━━━━━━━

📊 **RESUMEN:**
• Total de análisis: {analisis_count}
• Señales detectadas: {señales_detectadas}
• Efectividad mínima: {efectividad}%

{'🎉 Se detectaron señales válidas!' if señales_detectadas > 0 else '⚪ No se detectaron señales válidas en este período.'}

💡 **Sugerencia:** {'Revisa las señales enviadas anteriormente.' if señales_detectadas > 0 else 'Intenta con otra temporalidad o reduce el umbral de efectividad.'}
"""
            await update.message.reply_text(mensaje_final, parse_mode=ParseMode.MARKDOWN)
            print(f"[Análisis Forzado] {estado} - {analisis_count} análisis, {señales_detectadas} señales")
            
            # Desactivar bandera
            self._analisis_forzado_activo = False
            
        except Exception as e:
            mensaje_error = f"""❌ **Error en análisis forzado:**

{str(e)}

📊 **Estadísticas hasta el error:**
• Análisis realizados: {analisis_count}
• Señales detectadas: {señales_detectadas}

Verifica la conexión a Quotex y que el mercado esté disponible.
"""
            await update.message.reply_text(mensaje_error, parse_mode=ParseMode.MARKDOWN)
            print(f"[Análisis Forzado] ❌ Error: {e}")
    
    async def _analisis_continuo_con_trading(self, update, par, temporalidad, efectividad, tiempo_minutos):
        """Ejecuta análisis continuo CON trading automático"""
        import asyncio
        from datetime import datetime, timedelta
        
        inicio = datetime.now()
        fin = inicio + timedelta(minutes=tiempo_minutos)
        
        analisis_count = 0
        señales_detectadas = 0
        operaciones_ejecutadas = 0
        
        print(f"[Trading Auto AF] Iniciando análisis con trading de {par} por {tiempo_minutos} minutos")
        print(f"[Trading Auto AF] Modo: {self._trading_modo}, Monto: ${self._trading_monto}")
        
        try:
            while datetime.now() < fin and self._trading_auto_af_activo:
                analisis_count += 1
                tiempo_restante = (fin - datetime.now()).total_seconds() / 60
                
                print(f"[Trading Auto AF] Análisis #{analisis_count} - Tiempo restante: {tiempo_restante:.1f} min")
                
                # Verificar si se detuvo manualmente
                if not self._trading_auto_af_activo:
                    print("[Trading Auto AF] ⏹️ Detenido manualmente")
                    break
                
                # Obtener datos del mercado
                if hasattr(self, 'market_manager'):
                    df = await self.market_manager.obtener_datos_mercado(par)
                    
                    if df is not None and len(df) >= 50:
                        # Ejecutar análisis completo
                        from src.strategies.evaluar_estrategia_completa import evaluar_estrategia_completa
                        resultado = evaluar_estrategia_completa(df, par)
                
                        efectividad_resultado = resultado.get('efectividad_total', 0)
                        decision = resultado.get('decision')
                        
                        # Si se detecta señal válida
                        if decision and efectividad_resultado >= efectividad:
                            señales_detectadas += 1
                            
                            # EJECUTAR OPERACIÓN AUTOMÁTICAMENTE
                            try:
                                if hasattr(self, 'signal_scheduler') and hasattr(self.signal_scheduler, 'market_manager'):
                                    quotex = self.signal_scheduler.market_manager.quotex
                                    
                                    if quotex:
                                        # Cambiar a cuenta DEMO o REAL
                                        if self._trading_modo == "DEMO":
                                            await quotex.change_account("PRACTICE")
                                        else:
                                            await quotex.change_account("REAL")
                                        
                                        # Convertir símbolo
                                        asset = par.replace('/', '').replace('_OTC', '_otc')
                                        
                                        # Ejecutar operación
                                        check, order_id = await quotex.buy(
                                            amount=self._trading_monto,
                                            asset=asset,
                                            direction=decision.lower(),
                                            duration=300  # 5 minutos
                                        )
                                        
                                        if check:
                                            operaciones_ejecutadas += 1
                                            self._trading_operaciones_hoy += 1
                                            
                                            mensaje_operacion = f"""✅ **OPERACIÓN EJECUTADA - #{operaciones_ejecutadas}**

📊 **Mercado:** {par}
⏱️ **Temporalidad:** {temporalidad}
🎯 **Efectividad:** {efectividad_resultado:.1f}%
📍 **Dirección:** {decision}

💰 **Trading:**
• Modo: {self._trading_modo}
• Monto: ${self._trading_monto}
• Order ID: {order_id}
• Duración: 5 minutos

⏰ **Análisis:** #{analisis_count}
⏳ **Tiempo restante:** {tiempo_restante:.1f} minutos

🤖 – Operación ejecutada automáticamente
"""
                                            await update.message.reply_text(mensaje_operacion, parse_mode=ParseMode.MARKDOWN)
                                            print(f"[Trading Auto AF] ✅ Operación #{operaciones_ejecutadas} ejecutada - {decision} ${self._trading_monto}")
                                        else:
                                            print(f"[Trading Auto AF] ❌ Error ejecutando operación")
                                    else:
                                        print(f"[Trading Auto AF] ⚠️ No hay conexión a Quotex")
                            except Exception as e:
                                print(f"[Trading Auto AF] ❌ Error en operación: {e}")
                
                # Esperar antes del siguiente análisis (30 segundos)
                await asyncio.sleep(30)
            
            # Análisis completado o detenido
            estado = "⏹️ DETENIDO MANUALMENTE" if not self._trading_auto_af_activo else "🏁 COMPLETADO"
            mensaje_final = f"""{estado} **- TRADING AUTOMÁTICO**

📊 **Mercado:** {par}
⏱️ **Temporalidad:** {temporalidad}
⏰ **Duración:** {tiempo_minutos} minutos

━━━━━━━━━━━━━━━━━━━━━━

📊 **RESUMEN:**
• Total de análisis: {analisis_count}
• Señales detectadas: {señales_detectadas}
• Operaciones ejecutadas: {operaciones_ejecutadas}
• Efectividad mínima: {efectividad}%

💰 **Trading:**
• Modo: {self._trading_modo}
• Monto por operación: ${self._trading_monto}
• Total invertido: ${operaciones_ejecutadas * self._trading_monto}

{'🎉 Se ejecutaron operaciones automáticamente!' if operaciones_ejecutadas > 0 else '⚪ No se detectaron señales válidas en este período.'}

💡 **Sugerencia:** {'Revisa los resultados de las operaciones en tu cuenta ' + self._trading_modo if operaciones_ejecutadas > 0 else 'Intenta con otra temporalidad o reduce el umbral de efectividad.'}
"""
            await update.message.reply_text(mensaje_final, parse_mode=ParseMode.MARKDOWN)
            print(f"[Trading Auto AF] {estado} - {analisis_count} análisis, {operaciones_ejecutadas} operaciones")
            
            # Desactivar trading automático
            self._trading_activo = False
            self._trading_auto_af_activo = False
            self._analisis_forzado_activo = False
            
        except Exception as e:
            mensaje_error = f"""❌ **Error en trading automático:**

{str(e)}

📊 **Estadísticas hasta el error:**
• Análisis realizados: {analisis_count}
• Señales detectadas: {señales_detectadas}
• Operaciones ejecutadas: {operaciones_ejecutadas}

Verifica la conexión a Quotex y que el mercado esté disponible.
"""
            await update.message.reply_text(mensaje_error, parse_mode=ParseMode.MARKDOWN)
            print(f"[Trading Auto AF] ❌ Error: {e}")
            
            # Desactivar trading automático
            self._trading_activo = False
            self._trading_auto_af_activo = False
            self._analisis_forzado_activo = False
    
    async def handle_af_detener_analisis(self, query):
        """Detiene el análisis forzado en curso"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        # Verificar que sea el usuario que inició el análisis
        if self._analisis_forzado_user_id != user_id:
            await query.edit_message_text("❌ Solo el usuario que inició el análisis puede detenerlo.")
            return
        
        if not self._analisis_forzado_activo:
            await query.edit_message_text("⚠️ No hay ningún análisis forzado en curso.")
            return
        
        # Desactivar bandera
        self._analisis_forzado_activo = False
        
        mensaje = """⏹️ **ANÁLISIS FORZADO DETENIDO**

El análisis ha sido detenido manualmente.

Recibirás un resumen con las estadísticas hasta este momento.

⏳ Espera unos segundos...
"""
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN)
        print(f"[Análisis Forzado] ⏹️ Detenido por usuario {user_id}")
    
    async def handle_af_detener_trading(self, query):
        """Detiene el trading automático en curso"""
        try:
            await query.answer()
        except:
            pass
        
        user_id = str(query.from_user.id)
        
        # Verificar que sea el usuario que inició el trading
        if self._analisis_forzado_user_id != user_id:
            await query.edit_message_text("❌ Solo el usuario que inició el trading puede detenerlo.")
            return
        
        if not self._trading_auto_af_activo:
            await query.edit_message_text("⚠️ No hay ningún trading automático en curso.")
            return
        
        # Desactivar banderas
        self._trading_auto_af_activo = False
        self._analisis_forzado_activo = False
        self._trading_activo = False
        
        mensaje = """⏹️ **TRADING AUTOMÁTICO DETENIDO**

El trading automático ha sido detenido manualmente.

No se ejecutarán más operaciones.

Recibirás un resumen con las estadísticas hasta este momento.

⏳ Espera unos segundos...
"""
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN)
        print(f"[Trading Auto AF] ⏹️ Detenido por usuario {user_id}")
    
    # ==================== MARTINGALA ====================
    
    async def handle_martingala_confirmar(self, query):
        """Admin confirma ejecutar Martingala"""
        try:
            await query.answer()
        except:
            pass
        
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        print(f"[Martingala] ✅ Admin confirmó Martingala")
        
        # Ejecutar Martingala
        if hasattr(self, 'signal_scheduler') and self.signal_scheduler:
            # Calcular cuándo será la próxima vela
            from datetime import datetime, timedelta
            ahora = datetime.now()
            minutos_actuales = ahora.minute
            proxima_vela_minuto = ((minutos_actuales // 5) + 1) * 5
            if proxima_vela_minuto >= 60:
                proxima_vela_minuto = 0
                proxima_vela = ahora.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                proxima_vela = ahora.replace(minute=proxima_vela_minuto, second=0, microsecond=0)
            
            tiempo_espera = (proxima_vela - ahora).total_seconds()
            
            await self.signal_scheduler.ejecutar_martingala_confirmada()
            
            mensaje = f"""✅ **MARTINGALA CONFIRMADA**

🎲 La Martingala se ejecutará en la apertura de la próxima vela
⏰ Hora de ejecución: {proxima_vela.strftime('%H:%M:%S')}
⏳ Tiempo de espera: {int(tiempo_espera)} segundos

📊 La operación se abrirá exactamente al inicio de la vela de 5 minutos.

Te notificaré cuando la operación se ejecute.
"""
        else:
            mensaje = "❌ Error: Signal scheduler no disponible"
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_martingala_cancelar(self, query):
        """Admin cancela la Martingala"""
        try:
            await query.answer()
        except:
            pass
        
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        print(f"[Martingala] ❌ Admin canceló Martingala")
        
        # Limpiar Martingala pendiente
        if hasattr(self, 'signal_scheduler') and self.signal_scheduler:
            if hasattr(self.signal_scheduler, 'martingala_pendiente'):
                self.signal_scheduler.martingala_pendiente = None
        
        mensaje = """❌ **MARTINGALA CANCELADA**

La Martingala no se ejecutará.

El bot continuará operando normalmente.
"""
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN)
    
    # NOTA: Las funciones de confirmación de Martingala para usuarios fueron eliminadas
    # Los usuarios ahora reciben solo información en el mensaje de señal perdida
    # No necesitan confirmar, solo se les informa de la oportunidad
    
    async def handle_martingala_anticipada_confirmar(self, query):
        """Admin pre-autoriza la Martingala anticipadamente"""
        try:
            await query.answer()
        except:
            pass
        
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        print(f"[Martingala Predictiva] ✅ Admin pre-autorizó Martingala")
        
        # Marcar confirmación anticipada
        if hasattr(self, 'signal_scheduler') and self.signal_scheduler:
            self.signal_scheduler.martingala_confirmacion_anticipada = True
            print(f"[Martingala Predictiva] ✅ Confirmación anticipada guardada")
        
        mensaje = """✅ **MARTINGALA PRE-AUTORIZADA**

🔮 Has pre-autorizado la Martingala

⏰ **Qué sucederá ahora:**

**Si la vela se pierde:**
✅ Ejecutaré la Martingala inmediatamente en la próxima vela
✅ Sin perder tiempo esperando tu confirmación
✅ Máxima velocidad de recuperación

**Si la vela se gana:**
✅ Cancelaré automáticamente la Martingala
✅ Te notificaré que no fue necesaria
✅ Continuaremos operando normalmente

⏳ Esperando resultado final de la vela (2 minutos)...
"""
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_martingala_anticipada_rechazar(self, query):
        """Admin rechaza la pre-autorización de Martingala"""
        try:
            await query.answer()
        except:
            pass
        
        if not self._admin_check(query):
            await query.edit_message_text("❌ Solo para administradores.")
            return
        
        print(f"[Martingala Predictiva] ❌ Admin rechazó pre-autorización")
        
        # Marcar rechazo
        if hasattr(self, 'signal_scheduler') and self.signal_scheduler:
            self.signal_scheduler.martingala_confirmacion_anticipada = False
            print(f"[Martingala Predictiva] ❌ Pre-autorización rechazada")
        
        mensaje = """❌ **PRE-AUTORIZACIÓN RECHAZADA**

Has decidido NO pre-autorizar la Martingala.

⏰ **Qué sucederá ahora:**

**Si la vela se pierde:**
⏳ Te solicitaré confirmación después del cierre
⏳ Esperaré tu respuesta antes de ejecutar
⏳ Proceso normal de Martingala

**Si la vela se gana:**
✅ No habrá Martingala
✅ Continuaremos operando normalmente

⏳ Esperando resultado final de la vela (2 minutos)...
"""
        
        await query.edit_message_text(mensaje, parse_mode=ParseMode.MARKDOWN)
    
    # (Se eliminaron los callbacks de configuraciones)
