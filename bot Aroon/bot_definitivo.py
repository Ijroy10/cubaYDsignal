#!/usr/bin/env python3
"""
🤖 CUBAYDSIGNAL BOT DEFINITIVO
✅ Conexión automática con fallback manual
✅ Inicia trading inmediatamente al conectar
✅ Un solo comando, sin complicaciones
"""

import asyncio
import os
import sys
import time
import logging
import random
import requests
from datetime import datetime, time as dt_time
import pytz
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Notificador de Telegram con fallback a HTTP
class TelegramNotifier:
    def __init__(self, token: str | None, chat_id: str | None):
        self.token = token
        self.chat_id = chat_id

    async def send(self, text: str) -> bool:
        if not self.token or not self.chat_id:
            return False
        # Intentar con python-telegram-bot (async)
        try:
            import telegram
            bot = telegram.Bot(token=self.token)
            await bot.send_message(chat_id=self.chat_id, text=text)
            return True
        except Exception:
            # Fallback HTTP sincrónico
            try:
                resp = requests.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    data={"chat_id": self.chat_id, "text": text},
                    timeout=10,
                )
                return resp.ok
            except Exception:
                return False

class BotDefinitivo:
    def __init__(self):
        self.quotex = None
        self.connected = False
        self.trading_active = False
        self.notifier = TelegramNotifier(
            os.getenv('TELEGRAM_BOT_TOKEN'),
            os.getenv('TELEGRAM_CHAT_ID')
        )
        self.telegram_enabled = bool(os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'))
        # Parámetros de estrategia y horario (desde .env)
        self.assets = (os.getenv('ASSETS') or 'EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD').replace(' ', '').split(',')
        try:
            self.effectiveness_threshold = float(os.getenv('EFFECTIVENESS_THRESHOLD') or 80)
        except Exception:
            self.effectiveness_threshold = 80.0
        try:
            self.pre_signal_seconds = int(os.getenv('PRE_SIGNAL_SECONDS') or 60)
        except Exception:
            self.pre_signal_seconds = 60
        try:
            self.trade_amount = float(os.getenv('TRADE_AMOUNT') or 10)
        except Exception:
            self.trade_amount = 10.0
        try:
            self.trade_duration_min = int(os.getenv('TRADE_DURATION_MIN') or 5)
        except Exception:
            self.trade_duration_min = 5
        self.auto_connect = (os.getenv('AUTO_CONNECT') or 'true').lower() == 'true'
        self.auto_trade_demo = (os.getenv('AUTO_TRADE_DEMO') or 'true').lower() == 'true'
        self.tz_name = os.getenv('TIMEZONE') or 'America/Havana'
        self.trading_start = os.getenv('TRADING_START') or '09:00'
        self.trading_end = os.getenv('TRADING_END') or '21:00'
        self._tz = pytz.timezone(self.tz_name)
        # Control de pre-señales pendientes para evitar duplicados por activo
        self.pending_signals = {}
        self.trading_task = None

    def print_banner(self):
        """Banner del bot definitivo."""
        print("\n" + "="*60)
        print("🤖 CUBAYDSIGNAL BOT DEFINITIVO")
        print("⚡ Conexión automática → Manual si falla")
        print("🚀 Trading inmediato al conectar")
        print("💰 Modo DEMO - Sin riesgo")
        print("="*60)

    def _parse_hhmm(self, s: str) -> dt_time:
        try:
            hh, mm = s.split(':')
            return dt_time(int(hh), int(mm))
        except Exception:
            return dt_time(0, 0)

    def is_trading_hours(self) -> bool:
        """Verificar si estamos en ventana horaria operativa (Lun-Vie, start-end)."""
        now = datetime.now(self._tz)
        weekday = now.weekday()  # 0=Lun .. 6=Dom
        if weekday >= 5:
            return False
        start_t = self._parse_hhmm(self.trading_start)
        end_t = self._parse_hhmm(self.trading_end)
        today_start = self._tz.localize(datetime.combine(now.date(), start_t))
        today_end = self._tz.localize(datetime.combine(now.date(), end_t))
        return today_start <= now <= today_end

    async def connect_automatic(self):
        """Intentar conexión automática."""
        try:
            print("🤖 INTENTANDO CONEXIÓN AUTOMÁTICA...")
            await self.notifier.send("🤖 Intentando conexión automática...")

            # Importar quotexpy
            sys.path.append(os.path.join(os.path.dirname(__file__), 'quotexpy'))
            from quotexpy import Quotex

            # Configurar para automático (headless)
            self.quotex = Quotex(
                email=os.getenv('QUOTEX_EMAIL'),
                password=os.getenv('QUOTEX_PASSWORD'),
                headless=True,
                browser="chrome"
            )

            # Intentar conectar con timeout de 2 minutos
            print("⏳ Conectando automáticamente...")
            success = await asyncio.wait_for(self.quotex.connect(), timeout=120)

            if success:
                print("✅ ¡CONEXIÓN AUTOMÁTICA EXITOSA!")
                await self.notifier.send("✅ Conexión automática exitosa")
                self.connected = True
                return True
            else:
                print("❌ Conexión automática falló")
                await self.notifier.send("❌ Conexión automática falló")
                return False

        except asyncio.TimeoutError:
            print("⏰ Timeout en conexión automática")
            await self.notifier.send("⏰ Timeout en conexión automática")
            return False
        except Exception as e:
            print(f"❌ Error en conexión automática: {e}")
            await self.notifier.send(f"❌ Error en conexión automática: {e}")
            return False

    async def connect_manual(self):
        """Conexión manual como fallback."""
        try:
            print("\n🔄 CAMBIANDO A CONEXIÓN MANUAL...")
            print("👤 Se abrirá Chrome - Haz login manualmente")
            await self.notifier.send(
                "🔄 Cambio a conexión MANUAL.\n"
                "🌐 Se abrirá Chrome. Completa el login y navega a /trade."
            )

            # Importar quotexpy si no está importado
            if not hasattr(self, 'quotex') or self.quotex is None:
                sys.path.append(os.path.join(os.path.dirname(__file__), 'quotexpy'))
                from quotexpy import Quotex

            # Configurar para manual (visible)
            self.quotex = Quotex(
                email=os.getenv('QUOTEX_EMAIL'),
                password=os.getenv('QUOTEX_PASSWORD'),
                headless=False,  # Ventana visible
                browser="chrome"
            )

            print("🌐 Abriendo navegador...")
            print("👤 COMPLETA EL LOGIN MANUALMENTE")
            print("⚠️  NO cierres la ventana hasta que veas 'CONEXIÓN EXITOSA'")

            # Dar tiempo extendido para login manual
            success = await asyncio.wait_for(self.quotex.connect(), timeout=300)

            if success:
                print("✅ ¡CONEXIÓN MANUAL EXITOSA!")
                await self.notifier.send("✅ Conexión manual exitosa")
                self.connected = True
                return True
            else:
                print("❌ Conexión manual falló")
                await self.notifier.send("❌ Conexión manual falló")
                return False

        except asyncio.TimeoutError:
            print("⏰ Timeout en conexión manual (5 minutos)")
            await self.notifier.send("⏰ Timeout en conexión manual (5 minutos)")
            return False
        except Exception as e:
            print(f"❌ Error en conexión manual: {e}")
            await self.notifier.send(f"❌ Error en conexión manual: {e}")
            return False

    async def setup_demo_account(self):
        """Configurar cuenta demo."""
        try:
            print("💰 Configurando cuenta DEMO...")

            # Cambiar a modo practice
            await self.quotex.change_balance("PRACTICE")

            # Obtener balance
            balance = await self.quotex.get_balance()
            print(f"💵 Balance DEMO: ${balance}")
            await self.notifier.send(f"💰 Cuenta DEMO configurada. Balance: ${balance}")

            return True

        except Exception as e:
            print(f"⚠️ Advertencia configurando demo: {e}")
            await self.notifier.send(f"⚠️ Advertencia configurando demo: {e}")
            return True  # Continuar aunque falle

    async def start_trading(self):
        """Iniciar estrategia de trading inmediatamente."""
        print("\n🚀 INICIANDO TRADING AUTOMÁTICO...")
        print("📊 Analizando mercados cada 60 segundos")
        print("🎯 Ejecutando operaciones >80% efectividad")
        print("💵 $10 por operación, 5 minutos duración")
        print("🛑 Presiona Ctrl+C para detener")
        await self.notifier.send(
            "🚀 Trading automático iniciado.\n"
            "📊 Analizando cada 60s y operando cuando efectividad ≥80%"
        )

        self.trading_active = True
        assets = self.assets
        operation_count = 0
        # Importar estrategia real
        try:
            from estrategias.evaluar_estrategia_completa import evaluar_estrategia_completa, obtener_datos_del_activo
        except Exception as e:
            print(f"❌ No se pudo importar la estrategia real: {e}")
            await self.notifier.send(f"❌ No se pudo importar la estrategia real: {e}")
            return

        try:
            while self.trading_active:
                for asset in assets:
                    if not self.trading_active:
                        break
                        
                    try:
                        # Verificar si seguimos conectados
                        if not self.quotex or not self.connected:
                            print("❌ Conexión perdida")
                            break
                        
                        print(f"\n📊 Analizando {asset}...")
                        # Obtener datos reales del mercado y evaluar estrategia
                        df = None
                        try:
                            df = obtener_datos_del_activo(asset)
                        except Exception as e:
                            print(f"❌ Error obteniendo datos de {asset}: {e}")
                            await self.notifier.send(f"❌ Error obteniendo datos de {asset}: {e}")
                        if df is None:
                            continue
                        try:
                            result = evaluar_estrategia_completa(df, asset)
                        except Exception as e:
                            print(f"❌ Error evaluando estrategia en {asset}: {e}")
                            await self.notifier.send(f"❌ Error evaluando estrategia en {asset}: {e}")
                            result = None
                        if not result:
                            continue
                        eff = float(result.get('efectividad_total') or 0)
                        decision = result.get('decision')  # 'CALL'/'SELL'/None
                        if decision and eff >= self.effectiveness_threshold:
                            # Evitar duplicados si ya hay una pre-señal pendiente de este activo
                            if self.pending_signals.get(asset):
                                print(f"ℹ️ Ya existe una pre-señal pendiente para {asset}, omitiendo duplicado")
                            else:
                                direction = 'call' if decision.upper() == 'CALL' else 'put'
                                self.pending_signals[asset] = {
                                    'direction': direction,
                                    'eff': eff,
                                    'scheduled_at': time.time() + self.pre_signal_seconds
                                }
                                # Enviar pre-señal inmediata
                                await self.notifier.send(
                                    "📢 PRE-SEÑAL\n"
                                    f"📊 {asset} {decision}\n"
                                    f"⚡ Efectividad: {eff:.1f}%\n"
                                    f"⏱️ Entrada en {self.pre_signal_seconds}s\n"
                                    f"💵 Monto: ${self.trade_amount} | ⏳ {self.trade_duration_min}min"
                                )
                                # Programar señal final y ejecución
                                asyncio.create_task(
                                    self._delayed_execute_signal(asset, direction, eff, self.trade_amount, self.trade_duration_min, self.pre_signal_seconds)
                                )

                        # Pausa entre análisis
                        await asyncio.sleep(30)
                        
                    except Exception as e:
                        print(f"❌ Error analizando {asset}: {e}")
                        continue
                
                # Pausa entre ciclos
                if self.trading_active:
                    print(f"\n⏳ Próximo ciclo en 60 segundos...")
                    await asyncio.sleep(60)

        except KeyboardInterrupt:
            print("\n🛑 Trading detenido por usuario")
            self.trading_active = False
        except Exception as e:
            print(f"❌ Error en trading: {e}")
            self.trading_active = False

    async def _delayed_execute_signal(self, asset: str, direction: str, eff: float, amount: float, duration_min: int, delay_s: int):
        try:
            await asyncio.sleep(delay_s)
            # Limpiar estado pendiente
            try:
                self.pending_signals.pop(asset, None)
            except Exception:
                pass
            if not self.trading_active or not self.connected:
                return
            print(f"🚀 Ejecutando señal en {asset} tras pre-señal ({eff:.1f}%)")
            await self.notifier.send(
                "✅ SEÑAL CONFIRMADA\n"
                f"📊 {asset} {direction.upper()}\n"
                f"⚡ {eff:.1f}%\n"
                f"💵 ${amount} | ⏳ {duration_min}min"
            )
            # Ejecutar en DEMO
            try:
                result = await self.quotex.buy(
                    amount=amount,
                    asset=asset,
                    direction=direction,
                    duration=duration_min
                )
                if result:
                    print("🎯 Operación ejecutada correctamente")
                else:
                    print("❌ Error ejecutando operación")
            except Exception as e:
                print(f"❌ Error ejecutando operación: {e}")
        except Exception as e:
            print(f"❌ Error en _delayed_execute_signal: {e}")
            return

    def check_config(self):
        """Verificar configuración básica."""
        email = os.getenv('QUOTEX_EMAIL')
        password = os.getenv('QUOTEX_PASSWORD')
        if not email or not password:
            print("❌ ERROR: Configura QUOTEX_EMAIL y QUOTEX_PASSWORD en .env")
            return False
        quotex_path = os.path.join(os.path.dirname(__file__), 'quotexpy')
        if not os.path.exists(quotex_path):
            print("❌ ERROR: Carpeta quotexpy no encontrada")
            return False
        # Advertencia si Telegram no está listo
        if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            print("⚠️ Aviso: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados. No se enviarán notificaciones por Telegram.")
        return True

    async def monitor_trading_window(self):
        """Supervisa la ventana horaria y gestiona conexión/trading automáticamente."""
        last_state = None
        while True:
            try:
                in_window = self.is_trading_hours()
                if in_window:
                    if last_state is not True:
                        print("✅ HORARIO OPERATIVO ACTIVO")
                        _ = await self.notifier.send("✅ Horario operativo activo")
                    if self.auto_connect and not self.connected:
                        print("🚀 Iniciando conexión...")
                        _ = await self.notifier.send("🚀 Iniciando conexión...")
                        success = await self.connect_automatic()
                        if not success:
                            print("🔄 Automático falló → Cambiando a MANUAL")
                            _ = await self.notifier.send("🔄 Automático falló → Cambiando a MANUAL")
                            success = await self.connect_manual()
                        if success:
                            await self.setup_demo_account()
                            print("🎉 ¡BOT CONECTADO Y LISTO!")
                            _ = await self.notifier.send("🎉 ¡Bot conectado y listo!")
                    if self.auto_trade_demo and self.connected and not self.trading_active:
                        print("▶️ Iniciando trading automático en DEMO...")
                        _ = await self.notifier.send("▶️ Iniciando trading automático en DEMO...")
                        self.trading_task = asyncio.create_task(self.start_trading())
                    last_state = True
                else:
                    if last_state is not False:
                        print("⏰ FUERA DE HORARIO OPERATIVO")
                        print("📅 Forex opera Lunes a Viernes 24h")
                        _ = await self.notifier.send("⏰ Fuera de horario operativo")
                    if self.trading_active:
                        print("⏹️ Deteniendo trading por fin de ventana horaria...")
                        self.trading_active = False
                        try:
                            if self.trading_task:
                                self.trading_task = None
                        except Exception:
                            pass
                    last_state = False
                await asyncio.sleep(15)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"⚠️ Error en monitor_trading_window: {e}")
                await asyncio.sleep(10)

    async def run(self):
        """Ejecutar bot definitivo (modo servicio con ventana horaria)."""
        self.print_banner()
        if not self.check_config():
            return
        sent = await self.notifier.send("🚀 CUBAYDSIGNAL ACTIVADO. Modo servicio con ventana horaria.")
        if not sent:
            if self.telegram_enabled:
                print("⚠️ Telegram configurado pero el envío falló. Verifica TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.")
            else:
                print("ℹ️ Telegram no configurado. Continúo sin notificaciones.")
        print(f"🕒 Zona horaria: {self.tz_name} | Ventana: {self.trading_start}-{self.trading_end}")
        await self.monitor_trading_window()

# Función principal
async def main():
    bot = BotDefinitivo()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido")
    except Exception as e:
        print(f"❌ Error: {e}")
