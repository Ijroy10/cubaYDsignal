
#!/usr/bin/env python3
"""
CubaYDSignal Trading Bot - ARCHIVO PRINCIPAL ÚNICO
==================================================

Bot de Trading Profesional para Quotex
Autor: Yorji Fonseca (@Ijroy10)
ID Admin: 5806367733
Versión: 2.0 Professional

🚀 ÚNICA FORMA DE ARRANCAR EL BOT:
   python run_bot.py

Características principales:
- Análisis técnico multi-estrategia
- Gestión inteligente de mercados
- Bot de Telegram integrado
- Sistema de usuarios con lista diaria autorizada
- Bloqueo/desbloqueo de usuarios
- Aprendizaje adaptativo
- Historial completo de acciones
- Señales automáticas 20-25/día
- Notificaciones al admin
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import pytz
import socket
from aiohttp import web

# Configurar el path para imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

_instance_socket = None
_health_runner = None

def ensure_single_instance(port: int = 47653) -> socket.socket:
    """Impide instancias duplicadas del bot enlazando un puerto local.
    Si el puerto ya está en uso, se asume que otra instancia está activa.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s
    except OSError:
        print("❌ Ya hay una instancia del bot ejecutándose. Cierra la otra antes de iniciar.")
        sys.exit(1)

async def iniciar_healthcheck(logger: logging.Logger) -> None:
    global _health_runner
    if _health_runner is not None:
        return
    try:
        port = int(os.getenv("PORT", "8080"))
        app = web.Application()

        async def health(request: web.Request) -> web.Response:
            return web.Response(text="OK")

        app.router.add_get("/health", health)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=port)
        await site.start()
        _health_runner = runner
        logger.info("Healthcheck escuchando en %s", port)
    except Exception as exc:
        logger.error("No se pudo iniciar healthcheck: %s", exc)

def print_banner():
    """Muestra el banner de inicio del bot"""
    banner = f"""
🇨🇺 =============================================== 🇨🇺
    CUBAYDSIGNAL TRADING BOT v2.0 PROFESSIONAL
🇨🇺 =============================================== 🇨🇺

📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
👨‍💻 Desarrollado por: Yorji Fonseca (@Ijroy10)
🆔 Admin ID: 5806367733
🤖 Bot: Señales automáticas de trading

🔧 CARACTERÍSTICAS:
✅ Conexión real a Quotex (sin simulación)
✅ Bot de Telegram integrado
✅ Sistema de lista diaria autorizada
✅ Bloqueo/desbloqueo de usuarios
✅ 20-25 señales diarias (efectividad ≥80%)
✅ Análisis técnico avanzado
✅ Aprendizaje adaptativo
✅ Notificaciones automáticas al admin

🚀 Iniciando sistema...
"""
    print(banner)

def verificar_configuracion():
    """Verifica que todas las variables de entorno estén configuradas"""
    variables_requeridas = [
        'TELEGRAM_BOT_TOKEN',
        'ADMIN_ID', 
        'QUOTEX_EMAIL',
        'QUOTEX_PASSWORD'
    ]
    
    print("🔍 Verificando configuración...")
    
    for var in variables_requeridas:
        if not os.getenv(var):
            print(f"❌ Variable de entorno faltante: {var}")
            return False
        else:
            print(f"✅ {var}: Configurada")
    
    print("✅ Todas las variables de entorno están configuradas")
    return True

def configurar_logging():
    """Configura el sistema de logging"""
    # Crear directorio de logs si no existe
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logs_dir / 'cubaydsignal.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Sistema de logging configurado correctamente")
    return logger

async def main():
    """Función principal del bot"""
    print_banner()
    global _instance_socket
    # Garantizar instancia única
    _instance_socket = ensure_single_instance()
    
    # Verificar configuración
    if not verificar_configuracion():
        print("❌ Error en la configuración. Revisa el archivo .env")
        return
    
    # Configurar logging
    logger = configurar_logging()
    asyncio.create_task(iniciar_healthcheck(logger))
    
    try:
        # Importar módulos principales
        print("📦 Cargando módulos del sistema...")
        
        from core.market_manager import MarketManager
        from core.user_manager import UserManager
        from core.signal_scheduler import SignalScheduler
        from bot.telegram_bot import CubaYDSignalBot
        
        print("✅ Módulos cargados correctamente")
        
        # Inicializar componentes
        print("🔧 Inicializando componentes...")
        
        market_manager = MarketManager()
        user_manager = UserManager()
        signal_scheduler = SignalScheduler()
        # Aplicar overrides desde .env si están definidos
        try:
            obj_diario = os.getenv('OBJETIVO_SENALES_DIARIAS') or os.getenv('OBJETIVO_SEÑALES_DIARIAS')
            if obj_diario:
                signal_scheduler.objetivo_señales_diarias = max(1, int(obj_diario))
            pre_ttl = os.getenv('PRE_TTL_MIN')
            if pre_ttl:
                signal_scheduler.pre_ttl_min = max(1, int(pre_ttl))
            sig_ttl = os.getenv('SIGNAL_TTL_MIN')
            if sig_ttl:
                signal_scheduler.signal_ttl_min = max(1, int(sig_ttl))
        except Exception:
            pass
        
        # Configurar referencias cruzadas
        signal_scheduler.configurar_market_manager(market_manager)
        signal_scheduler.configurar_user_manager(user_manager)
        
        print("✅ Componentes inicializados")
        
        # Inicializar bot de Telegram
        print("🤖 Iniciando bot de Telegram...")
        
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_bot = CubaYDSignalBot(telegram_token)
        
        # Configurar referencias del bot
        user_manager.configurar_bot_telegram(telegram_bot)
        telegram_bot.configurar_market_manager(market_manager)
        telegram_bot.configurar_signal_scheduler(signal_scheduler)
        
        print("✅ Bot de Telegram configurado")
        
        # Función auxiliar: gestión automática de conexión a Quotex
        async def gestionar_conexion_quotex_auto():
            tz_name = os.getenv('TIMEZONE') or 'America/Havana'
            try:
                tz_local = pytz.timezone(tz_name)
            except Exception:
                tz_local = pytz.timezone('America/Havana')
            admin_id = str(user_manager.admin_id)
            conectado = getattr(market_manager, 'conectado', False)
            email = os.getenv('QUOTEX_EMAIL')
            password = os.getenv('QUOTEX_PASSWORD')
            # flag simple para evitar intentos solapados
            auto_connecting = False
            # backoff exponencial para reintentos fallidos
            backoff_seconds = 5  # inicia en 5s, se duplica hasta 300s
            
            # Horarios aleatorios diarios: conexión (7:30–8:00) y desconexión (20:00–21:00)
            import random as _rand
            from datetime import datetime as _dt
            from datetime import time as _time
            
            daily_connect_dt = None
            daily_disconnect_dt = None
            scheduled_date = None

            def _compute_daily_schedule(now_local):
                nonlocal daily_connect_dt, daily_disconnect_dt, scheduled_date
                scheduled_date = now_local.date()
                # Random connect time between 07:30:00 and 07:59:59
                c_minute = _rand.randint(30, 59)
                c_second = _rand.randint(0, 59)
                daily_connect_dt = now_local.replace(hour=7, minute=c_minute, second=c_second, microsecond=0)
                # Random disconnect time between 20:00:00 and 20:59:59
                d_minute = _rand.randint(0, 59)
                d_second = _rand.randint(0, 59)
                daily_disconnect_dt = now_local.replace(hour=20, minute=d_minute, second=d_second, microsecond=0)
            
            while True:
                try:
                    ahora = datetime.now(tz_local)
                    # Recalcular horarios aleatorios al cambiar el día
                    if scheduled_date is None or ahora.date() != scheduled_date:
                        _compute_daily_schedule(ahora)
                        try:
                            await telegram_bot.application.bot.send_message(
                                chat_id=admin_id,
                                text=(
                                    f"🗓️ Horarios del día configurados:\n"
                                    f"• Conexión aleatoria: {daily_connect_dt.strftime('%H:%M:%S')}\n"
                                    f"• Desconexión aleatoria: {daily_disconnect_dt.strftime('%H:%M:%S')}\n"
                                    "(Estrategia: Lun–Sáb, 8:00–20:00)"
                                )
                            )
                        except Exception:
                            pass
                    weekday = ahora.weekday()  # 0=Lun ... 5=Sáb, 6=Dom
                    hora = ahora.hour
                    minuto = ahora.minute
                    # Estrategia solo 8:00–20:00 Lun–Sáb
                    en_horario = (weekday < 6) and (hora >= 8 and hora < 20)
                    # Ventana de conexión aleatoria (7:30–8:00) antes del horario operativo
                    en_ventana_conexion = (weekday < 6) and (ahora >= daily_connect_dt) and (hora < 20)

                    if en_ventana_conexion:
                        # Si no conectado, intenta conectar (MarketManager ya notifica en éxito)
                        if not getattr(market_manager, 'conectado', False) and not auto_connecting:
                            auto_connecting = True
                            try:
                                try:
                                    await telegram_bot.application.bot.send_message(
                                        chat_id=admin_id,
                                        text="⏳ Conexión automática a Quotex iniciada (ventana aleatoria 7:30–8:00)."
                                    )
                                except Exception:
                                    pass
                                ok = await market_manager.conectar_quotex(email, password, telegram_bot=telegram_bot)
                            finally:
                                auto_connecting = False
                            if ok:
                                conectado = True
                                backoff_seconds = 5
                                # Iniciar estrategia solo si estamos en horario/días válidos
                                try:
                                    if en_horario:
                                        # Si el scheduler no está corriendo, iniciarlo ahora
                                        if not getattr(signal_scheduler, 'running', False):
                                            try:
                                                await signal_scheduler.iniciar_scheduler()
                                            except Exception:
                                                pass
                                        else:
                                            # Si ya corre, iniciar flujo del día y programar señales
                                            try:
                                                await signal_scheduler.iniciar_dia_trading()
                                            except Exception:
                                                pass
                                            try:
                                                await signal_scheduler.programar_señales_del_dia()
                                            except Exception:
                                                pass
                                        # Notificar al admin que la estrategia fue (re)iniciada
                                        try:
                                            await telegram_bot.application.bot.send_message(
                                                chat_id=admin_id,
                                                text="🟢 Estrategia iniciada (en horario) tras conexión a Quotex."
                                            )
                                        except Exception:
                                            pass
                                    else:
                                        # Conectado fuera de horario: no iniciar estrategia
                                        try:
                                            await telegram_bot.application.bot.send_message(
                                                chat_id=admin_id,
                                                text="ℹ️ Quotex conectado fuera de horario. La estrategia NO se iniciará hasta el horario operativo (Lun–Sáb, 8:00–20:00)."
                                            )
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                            else:
                                # notificar y aplicar backoff exponencial
                                try:
                                    # Ajuste especial si hubo bloqueo Cloudflare
                                    last_err = getattr(market_manager, 'last_connect_error', None)
                                    if last_err == 'cloudflare_403':
                                        # Cooldown fuerte de 30 min por bloqueo 403
                                        backoff_seconds = max(backoff_seconds, 1800)
                                        msg = (
                                            "⛔ Bloqueo Cloudflare (403) detectado al conectar a Quotex.\n"
                                            f"Reintentando en {backoff_seconds}s… (cooldown reforzado)\n\n"
                                            "Sugerencias: cambiar de red/IP residencial, evitar VPNs de datacenter, "
                                            "esperar 20–40 minutos y reintentar."
                                        )
                                    else:
                                        msg = f"❌ Falló la conexión automática a Quotex. Reintentando en {backoff_seconds}s…"
                                    await telegram_bot.application.bot.send_message(
                                        chat_id=admin_id,
                                        text=msg
                                    )
                                except Exception:
                                    pass
                                try:
                                    await asyncio.sleep(backoff_seconds)
                                except Exception:
                                    pass
                                backoff_seconds = min(backoff_seconds * 2, 300)
                    elif en_horario:
                        # Si estamos dentro del horario operativo y el bot ha arrancado tarde (después de 8:00), conectamos
                        if not getattr(market_manager, 'conectado', False) and not auto_connecting:
                            auto_connecting = True
                            try:
                                try:
                                    await telegram_bot.application.bot.send_message(
                                        chat_id=admin_id,
                                        text="⏳ Conexión automática a Quotex iniciada (en horario)."
                                    )
                                except Exception:
                                    pass
                                ok = await market_manager.conectar_quotex(email, password, telegram_bot=telegram_bot)
                            finally:
                                auto_connecting = False
                            if ok:
                                conectado = True
                                backoff_seconds = 5
                                # Iniciar estrategia (estamos en horario válido)
                                try:
                                    if not getattr(signal_scheduler, 'running', False):
                                        try:
                                            await signal_scheduler.iniciar_scheduler()
                                        except Exception:
                                            pass
                                    else:
                                        try:
                                            await signal_scheduler.iniciar_dia_trading()
                                        except Exception:
                                            pass
                                        try:
                                            await signal_scheduler.programar_señales_del_dia()
                                        except Exception:
                                            pass
                                    try:
                                        await telegram_bot.application.bot.send_message(
                                            chat_id=admin_id,
                                            text="🟢 Estrategia iniciada (reconexión en horario)."
                                        )
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                            else:
                                try:
                                    await telegram_bot.application.bot.send_message(
                                        chat_id=admin_id,
                                        text="❌ Falló la conexión a Quotex (en horario). Reintentando con backoff…"
                                    )
                                except Exception:
                                    pass
                                backoff_seconds = min(backoff_seconds * 2, 300)

                    # Desconexión aleatoria entre 20:00 y 21:00 si está conectado
                    # PERO NO desconectar si el modo forzado está activo
                    if getattr(market_manager, 'conectado', False) and ahora >= daily_disconnect_dt and hora < 21:
                        if not market_manager.esta_en_modo_forzado():
                            await market_manager.desconectar_quotex()
                            try:
                                await telegram_bot.application.bot.send_message(
                                    chat_id=admin_id,
                                    text=f"🔒 Quotex desconectado (horario aleatorio {daily_disconnect_dt.strftime('%H:%M:%S')})."
                                )
                            except Exception:
                                pass
                        # Chequeo de salud: si conectado, validar acceso a activos con periodo de gracia y tolerancia a fallos
                        # Puede desactivarse temporalmente con DISABLE_HEALTHCHECK=1 para diagnóstico
                        import os as _os
                        if getattr(market_manager, 'conectado', False) and _os.getenv('DISABLE_HEALTHCHECK', '0') != '1':
                            import datetime as _dt
                            try:
                                # Periodo de gracia de 90s tras conexión
                                t0 = getattr(market_manager, 'tstamp_conectado', None)
                                if t0 and (_dt.datetime.now() - t0).total_seconds() < 90:
                                    # Saltar health-check durante warmup
                                    pass
                                else:
                                    import asyncio as _aio
                                    assets = await _aio.to_thread(market_manager._fetch_assets)
                                    if not isinstance(assets, list) or len(assets) == 0:
                                        # Contabilizar fallo y sólo desconectar tras 3 fallos consecutivos
                                        market_manager.fallos_assets = getattr(market_manager, 'fallos_assets', 0) + 1
                                        if market_manager.fallos_assets >= 3:
                                            market_manager.conectado = False
                                            market_manager.fallos_assets = 0
                                            try:
                                                await telegram_bot.application.bot.send_message(
                                                    chat_id=admin_id,
                                                    text="⚠️ Conexión a Quotex no válida (sin activos) tras múltiples intentos. Reintentando…"
                                                )
                                            except Exception:
                                                pass
                                    else:
                                        # Éxito: resetear contador de fallos
                                        market_manager.fallos_assets = 0
                            except Exception:
                                # caída inesperada durante health-check
                                try:
                                    market_manager.fallos_assets = getattr(market_manager, 'fallos_assets', 0) + 1
                                    if market_manager.fallos_assets >= 3:
                                        market_manager.conectado = False
                                        market_manager.fallos_assets = 0
                                        try:
                                            await telegram_bot.application.bot.send_message(
                                                chat_id=admin_id,
                                                text="⚠️ Conexión a Quotex perdida por errores consecutivos. Reintentando…"
                                            )
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                    else:
                        # fuera de horario (y fuera de ventana) o domingo: asegurar desconexión
                        # PERO NO desconectar si el modo forzado está activo
                        if getattr(market_manager, 'conectado', False) and (weekday >= 6 or ahora >= daily_disconnect_dt):
                            # Verificar si está en modo forzado
                            if not market_manager.esta_en_modo_forzado():
                                await market_manager.desconectar_quotex()
                                try:
                                    await telegram_bot.application.bot.send_message(chat_id=admin_id, text="🔒 Quotex desconectado (fuera de horario).")
                                except Exception:
                                    pass
                except Exception as _e:
                    # evitar que el loop muera
                    pass
                await asyncio.sleep(30)
        
        # Mostrar información del sistema
        print(f"🔑 Clave del día: {user_manager.clave_publica_diaria}")
        print(f"📅 Fecha actual: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"⏰ Horario operativo: 8:00 AM - 8:00 PM (Lun-Sáb)")
        
        # Iniciar el bot de Telegram (no bloquear el event loop)
        print("🚀 Iniciando bot de Telegram...")
        tg_task = asyncio.create_task(telegram_bot.run_async())
        
        # Esperar un momento para que el bot esté completamente listo
        await asyncio.sleep(2)
        
        # Notificar al admin que el bot está activo (nuevo formato solicitado)
        try:
            mensaje_inicio = f"""🚀 CUBAYDSIGNAL ACTIVADO 🚀

🔗 Estado del Sistema: Activo ✅ 
 • 🤖 Bot: En línea
 • 📊 Señales: Disponibles

🔑 Clave de Acceso (Hoy): {user_manager.clave_publica_diaria}
📅 Fecha: {datetime.now().strftime('%d/%m/%Y')}

⚡ ¡El mercado te espera, todo listo para operar!"""

            await telegram_bot.notificar_admin_telegram(mensaje_inicio)
            print("✅ Notificación de inicio enviada al administrador")
        except Exception as e:
            print(f"⚠️ No se pudo enviar notificación al admin: {e}")
        
        # Arrancar gestión automática de conexión a Quotex en segundo plano con logging de excepciones
        def _log_task_error(t):
            try:
                exc = t.exception()
                if exc:
                    logger.error(f"[TaskError] Excepción en tarea: {exc}")
            except Exception:
                pass
        t_auto = asyncio.create_task(gestionar_conexion_quotex_auto())
        t_auto.add_done_callback(_log_task_error)

        # Intento de conexión inicial si ya está dentro del horario operativo (no bloqueante)
        try:
            tz_cuba = pytz.timezone('America/Havana')
            ahora = datetime.now(tz_cuba)
            if ahora.weekday() < 6 and ((ahora.hour > 7 or (ahora.hour == 7 and ahora.minute >= 50)) and (ahora.hour < 20)):
                email = os.getenv('QUOTEX_EMAIL')
                password = os.getenv('QUOTEX_PASSWORD')
                # Conectar sin signal_scheduler (el nuevo market_manager.py no lo necesita)
                t_conn = asyncio.create_task(market_manager.conectar_quotex(email, password, telegram_bot=telegram_bot))
                t_conn.add_done_callback(_log_task_error)
        except Exception:
            pass

        # Iniciar el scheduler de señales
        print("📊 Iniciando scheduler de señales...")
        await signal_scheduler.iniciar_scheduler()
        
        print("✅ ¡Bot CubaYDSignal iniciado correctamente!")
        print("📱 El bot de Telegram está activo y listo para recibir comandos")
        print("📈 El sistema de señales está operativo")
        
        # Mantener el proceso corriendo mientras tareas principales sigan activas
        # Nota: Evitamos reiniciar automáticamente el bot de Telegram para prevenir
        # 'This Application is already running!'. Si la tarea termina, solo registramos y seguimos.
        try:
            while True:
                try:
                    if tg_task.done():
                        exc = None
                        try:
                            exc = tg_task.exception()
                        except Exception:
                            pass
                        if exc:
                            logger.error(f"[TelegramTask] terminó con excepción: {exc}")
                        else:
                            logger.info("[TelegramTask] finalizada (no se reinicia automáticamente)")
                        # No reiniciar automáticamente
                except Exception:
                    pass
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️ Deteniendo bot...")
            
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("🔧 Verifica que todos los módulos estén en su lugar")
        logger.error(f"Error de importación: {e}")
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        logger.error(f"Error crítico: {e}")
        
    finally:
        print("👋 Bot detenido. ¡Hasta luego!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)
