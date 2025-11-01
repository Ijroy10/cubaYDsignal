"""
ARCHIVO PRINCIPAL MEJORADO - CUBAYDSIGNAL BOT
Integra todos los módulos nuevos:
- Gestión de mercados múltiples
- Sistema de autenticación
- Programación de señales
- Bot de Telegram
- Aprendizaje adaptativo
"""

import asyncio
import os
import sys
from datetime import datetime
import logging
from dotenv import load_dotenv
load_dotenv()

# Importar todos los módulos nuevos
from core.market_manager import MarketManager
from core.user_manager import UserManager
from core.signal_scheduler import SignalScheduler
from core.adaptive_learning import AdaptiveLearning
from bot.telegram_bot import CubaYDSignalBot

# Nuevos módulos de IA y efectividad
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'analysis'))
from analysis.ai_intelligence import AIIntelligence
from analysis.effectiveness_guarantee import EffectivenessGuarantee

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cubaydsignal.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CubaYDSignalMain:
    def __init__(self):
        """Inicializa el sistema completo"""
        self.market_manager = MarketManager()
        self.user_manager = UserManager()
        self.signal_scheduler = SignalScheduler()
        self.adaptive_learning = AdaptiveLearning()
        
        # Nuevos módulos de IA y efectividad
        self.ai_intelligence = AIIntelligence()
        self.effectiveness_guarantee = EffectivenessGuarantee()
        
        self.telegram_bot = None
        
        # Configuraciones
        self.quotex_email = os.getenv("QUOTEX_EMAIL", "ijroyquotex@gmail.com")
        self.quotex_password = os.getenv("QUOTEX_PASSWORD", "Yorji.050212")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        # Crear directorio de logs si no existe
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
    def verificar_configuracion(self) -> bool:
        """Verifica que todas las configuraciones estén correctas"""
        logger.info("🔍 Verificando configuración del sistema...")
        
        if not self.telegram_token:
            logger.error("❌ Token de Telegram no configurado. Configura TELEGRAM_BOT_TOKEN")
            return False
        
        if not self.quotex_email or not self.quotex_password:
            logger.error("❌ Credenciales de Quotex no configuradas")
            return False
        
        logger.info("✅ Configuración verificada correctamente")
        return True
    
    async def inicializar_sistema(self) -> bool:
        """Inicializa todos los componentes del sistema"""
        logger.info("🚀 Inicializando CubaYDSignal Bot...")
        try:
            # 1. Inicializar bot de Telegram primero
            logger.info("🤖 Inicializando bot de Telegram...")
            self.telegram_bot = CubaYDSignalBot(self.telegram_token)
            # Enlazar el MarketManager principal al bot para que los comandos consulten el estado real
            try:
                self.telegram_bot.market_manager = self.market_manager
            except Exception:
                pass
            telegram_task = asyncio.create_task(self.ejecutar_telegram_bot())
            # Esperar a que el bot esté listo (polling) antes de proceder con Quotex
            try:
                await asyncio.wait_for(self.telegram_bot.wait_ready(), timeout=30)
                logger.info("[TG] Bot listo. Procediendo a conectar con Quotex…")
            except Exception:
                logger.warning("[TG] No se pudo confirmar readiness del Bot en 30s, se procede igual.")

            # 2. Conectar a Quotex (no bloquear la inicialización si falla o está fuera de horario)
            logger.info("📊 Conectando a Quotex...")
            conectado_qx = await self.market_manager.conectar_quotex(self.quotex_email, self.quotex_password, telegram_bot=self.telegram_bot)
            if not conectado_qx:
                logger.warning("[Init] Quotex no conectado en inicio. Continuando solo con Telegram y servicios auxiliares (se conectará según horario).")
                # Avisar al admin que el bot está en línea pero sin conexión a Quotex
                try:
                    admin_id = str(self.user_manager.admin_id)
                    await self.telegram_bot.application.bot.send_message(chat_id=admin_id, text="ℹ️ Bot activo sin conexión a Quotex (fuera de horario o pendiente). Los comandos funcionan normalmente.")
                except Exception:
                    pass
            else:
                # Notificar al admin la conexión inicial exitosa
                try:
                    admin_id = str(self.user_manager.admin_id)
                    await self.telegram_bot.application.bot.send_message(chat_id=admin_id, text="✅ Quotex conectado en inicio. Sistema listo para operar.")
                except Exception:
                    pass
            
            # 3. Inicializar gestión de usuarios
            logger.info("👥 Inicializando gestión de usuarios...")
            self.user_manager.generar_clave_diaria_si_necesario()
            logger.info(f"🔑 Clave del día: {self.user_manager.clave_publica_diaria}")
            
            # 4. Configurar scheduler de señales
            logger.info("📅 Configurando programador de señales...")
            self.signal_scheduler.market_manager = self.market_manager
            self.signal_scheduler.user_manager = self.user_manager
            self.signal_scheduler.configurar_bot_telegram(self.telegram_bot)
            
            # 5. Cargar configuración optimizada del aprendizaje adaptativo
            logger.info("🧠 Cargando configuración de aprendizaje adaptativo...")
            config_optimizada = self.adaptive_learning.obtener_pesos_optimizados()
            logger.info(f"⚖️ Pesos optimizados cargados: {len(config_optimizada)} estrategias")
            
            logger.info("✅ Sistema inicializado correctamente (Telegram operativo).")
            # Mantener el bot de Telegram activo en paralelo
            await telegram_task
            return True
        except Exception as e:
            logger.error(f"❌ Error inicializando sistema: {e}")
            return False
    
    async def ejecutar_modo_automatico(self):
        """Ejecuta el bot en modo automático completo"""
        logger.info("🔄 Iniciando modo automático...")
        
        try:
            # Crear tareas asíncronas
            tasks = []
            
            # 1. Tarea del bot de Telegram
            telegram_task = asyncio.create_task(self.ejecutar_telegram_bot())
            tasks.append(telegram_task)

            # 2. Tarea de conexión/desconexión de Quotex según horario
            tasks.append(asyncio.create_task(self.gestionar_conexion_quotex()))

            # 3. Tarea del scheduler de señales (si está en horario)
            if self.signal_scheduler.esta_en_horario_operativo():
                scheduler_task = asyncio.create_task(self.signal_scheduler.ejecutar_ciclo_diario())
                tasks.append(scheduler_task)
                logger.info("📈 Ciclo de señales iniciado")
            else:
                logger.info("⏰ Fuera de horario operativo - Solo bot de Telegram activo")
            
            # 4. Tarea de análisis adaptativo (cada hora)
            learning_task = asyncio.create_task(self.ejecutar_aprendizaje_periodico())
            tasks.append(learning_task)
            
            # Ejecutar todas las tareas
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            logger.info("⏹️ Deteniendo sistema por solicitud del usuario...")
        except Exception as e:
            logger.error(f"❌ Error en modo automático: {e}")
        finally:
            logger.info("🏁 Sistema detenido")

    async def gestionar_conexion_quotex(self):
        """Gestiona la conexión y desconexión de Quotex según el horario operativo y días hábiles."""
        import pytz
        tz_cuba = pytz.timezone('America/Havana')
        admin_id = str(self.user_manager.admin_id)
        conectado = False
        while True:
            ahora = datetime.now(tz_cuba)
            weekday = ahora.weekday()  # 0=Lunes ... 5=Sábado, 6=Domingo
            hora = ahora.hour
            minuto = ahora.minute
            # Solo operar de lunes a sábado (domingo no operativo)
            if weekday < 6:
                # En horario operativo: 07:50 a 20:00 hora Cuba
                en_horario = (hora > 7 or (hora == 7 and minuto >= 50)) and (hora < 20)
                if en_horario:
                    # Si no está conectado, reintentar conexión periódicamente
                    if not conectado:
                        logger.info("⏰ Intentando conectar a Quotex (en horario operativo)...")
                        ok = await self.market_manager.conectar_quotex(self.quotex_email, self.quotex_password, telegram_bot=self.telegram_bot)
                        if ok:
                            conectado = True
                            logger.info("✅ Conexión a Quotex activa para la jornada.")
                            try:
                                await self.telegram_bot.application.bot.send_message(chat_id=admin_id, text="✅ Quotex conectado. Listo para operar.")
                            except Exception as e:
                                logger.warning(f"No se pudo notificar al admin por Telegram: {e}")
                        else:
                            logger.warning("❌ Intento de conexión a Quotex fallido. Se reintentará automáticamente.")
                # Fuera de horario: si está conectado y son las 20:00, desconectar
                if hora == 20 and minuto == 0 and conectado:
                    logger.info("⏰ Desconectando de Quotex (20:00, cierre de jornada)...")
                    await self.market_manager.desconectar_quotex()
                    conectado = False
                    try:
                        await self.telegram_bot.application.bot.send_message(chat_id=admin_id, text="🔒 Quotex desconectado (20:00, cierre de jornada).")
                    except Exception as e:
                        logger.warning(f"No se pudo notificar al admin por Telegram: {e}")
            else:
                # Fines de semana: asegurarse de estar desconectado
                if conectado:
                    logger.info("⏰ Desconectando de Quotex (fin de semana)...")
                    await self.market_manager.desconectar_quotex()
                    conectado = False
                    try:
                        await self.telegram_bot.application.bot.send_message(chat_id=admin_id, text="🔒 Quotex desconectado (fin de semana, sin operaciones).")
                    except Exception as e:
                        logger.warning(f"No se pudo notificar al admin por Telegram: {e}")
            await asyncio.sleep(30)  # Reintento/chequeo periódico

    
    async def ejecutar_telegram_bot(self):
        """Ejecuta el bot de Telegram en modo asíncrono"""
        try:
            await self.telegram_bot.run_async()
        except Exception as e:
            logger.error(f"❌ Error en bot de Telegram: {e}")
    
    async def ejecutar_aprendizaje_periodico(self):
        """Ejecuta análisis de aprendizaje adaptativo cada hora"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1 hora
                
                logger.info("🧠 Ejecutando análisis de aprendizaje adaptativo...")
                
                # Analizar resultados del día actual
                analisis = self.adaptive_learning.analizar_resultados_diarios()

                # Ejecutar mejoras automáticas y notificar admin si corresponde
                if self.telegram_bot:
                    await self.adaptive_learning.aplicar_mejoras_automaticas(
                        analisis,
                        notify_admin_callback=self.telegram_bot.notificar_admin_telegram
                    )
                else:
                    await self.adaptive_learning.aplicar_mejoras_automaticas(analisis)

                if analisis.get('recomendaciones'):
                    logger.info(f"💡 {len(analisis['recomendaciones'])} recomendaciones generadas")
                    for rec in analisis['recomendaciones']:
                        logger.info(f"   • {rec}")
                
                # Generar reporte si hay suficientes datos
                if len(self.adaptive_learning.historial_resultados) >= 10:
                    reporte = self.adaptive_learning.generar_reporte_aprendizaje()
                    logger.info("📊 Reporte de aprendizaje generado")
                
            except Exception as e:
                logger.error(f"❌ Error en aprendizaje adaptativo: {e}")
    
    def ejecutar_modo_manual(self):
        """Ejecuta el bot en modo manual con menú interactivo"""
        while True:
            print("\n" + "="*50)
            print("🇨🇺 CUBAYDSIGNAL BOT - PANEL DE CONTROL")
            print("="*50)
            print("1. 🚀 Iniciar modo automático")
            print("2. 📊 Ver estado del sistema")
            print("3. 🔑 Generar nueva clave diaria")
            print("4. 👥 Ver usuarios activos")
            print("5. 📈 Analizar mercados disponibles")
            print("6. 🧠 Ver reporte de aprendizaje")
            print("7. 📋 Generar señal manual")
            print("8. 📊 Estadísticas del día")
            print("9. ⚙️ Configuración")
            print("0. ❌ Salir")
            print("="*50)
            
            opcion = input("Selecciona una opción: ").strip()
            
            if opcion == "1":
                print("🚀 Iniciando modo automático...")
                asyncio.run(self.ejecutar_modo_automatico())
            
            elif opcion == "2":
                self.mostrar_estado_sistema()
            
            elif opcion == "3":
                nueva_clave = self.user_manager.generar_clave_publica_manual()
                print(f"🔑 Nueva clave generada: {nueva_clave}")
            
            elif opcion == "4":
                self.mostrar_usuarios_activos()
            
            elif opcion == "5":
                self.analizar_mercados_manual()
            
            elif opcion == "6":
                reporte = self.adaptive_learning.generar_reporte_aprendizaje()
                print(f"\n{reporte}")
            
            elif opcion == "7":
                asyncio.run(self.generar_señal_manual())
            
            elif opcion == "8":
                self.mostrar_estadisticas_dia()
            
            elif opcion == "9":
                self.mostrar_configuracion()
            
            elif opcion == "0":
                print("👋 ¡Hasta luego!")
                break
            
            else:
                print("❌ Opción no válida")
            
            input("\nPresiona Enter para continuar...")
    
    def mostrar_estado_sistema(self):
        """Muestra el estado actual del sistema"""
        print("\n📊 ESTADO DEL SISTEMA:")
        print(f"⏰ Horario operativo: {'🟢 SÍ' if self.signal_scheduler.esta_en_horario_operativo() else '🔴 NO'}")
        print(f"🔑 Clave del día: {self.user_manager.clave_publica_diaria}")
        print(f"👥 Usuarios activos: {len(self.user_manager.usuarios_activos)}")
        print(f"📈 Señales enviadas hoy: {len(self.signal_scheduler.señales_enviadas_hoy)}")
        
        if self.signal_scheduler.mercado_actual:
            mercado = self.signal_scheduler.mercado_actual
            print(f"💱 Mercado actual: {mercado['symbol']} (Payout: {mercado['payout']}%)")
        else:
            print("💱 Mercado actual: No seleccionado")
    
    def mostrar_usuarios_activos(self):
        """Muestra información de usuarios activos"""
        print("\n👥 USUARIOS ACTIVOS:")
        if not self.user_manager.usuarios_activos:
            print("No hay usuarios activos")
            return
        
        for user_id, info in self.user_manager.usuarios_activos.items():
            print(f"• {info['username']} ({info['tipo']}) - Ingreso: {info['hora_ingreso']}")
    
    def analizar_mercados_manual(self):
        """Analiza mercados disponibles manualmente"""
        print("\n📊 ANALIZANDO MERCADOS...")
        mercados = self.market_manager.obtener_mercados_disponibles()
        
        print(f"Mercados encontrados: {len(mercados)}")
        for mercado in mercados[:10]:  # Mostrar solo los primeros 10
            print(f"• {mercado['symbol']}: {mercado['payout']}% payout ({'OTC' if mercado['otc'] else 'Normal'})")
    
    async def generar_señal_manual(self):
        """Genera una señal manualmente con IA y efectividad garantizada"""
        print("\n🧠 GENERANDO SEÑAL CON IA...")
        
        if not self.signal_scheduler.mercado_actual:
            mejor_mercado = await self.market_manager.seleccionar_mejor_mercado()
            if mejor_mercado:
                self.signal_scheduler.mercado_actual = mejor_mercado
                print(f"💱 Mercado seleccionado: {mejor_mercado['symbol']}")
            else:
                print("❌ No se pudo seleccionar mercado")
                return
        
        # Obtener datos del mercado
        market_data = await self.market_manager.obtener_datos_mercado(self.signal_scheduler.mercado_actual['symbol'])
        if not market_data:
            print("❌ No se pudieron obtener datos del mercado")
            return
            
        # Análisis con IA
        print("🔍 Analizando con inteligencia artificial...")
        ai_analysis = self.ai_intelligence.analyze_market_data(market_data)
        
        # Crear señal base
        señal_base = {
            'symbol': self.signal_scheduler.mercado_actual['symbol'],
            'market': self.signal_scheduler.mercado_actual['symbol'],
            'direccion': ai_analysis['prediction'],
            'payout': self.signal_scheduler.mercado_actual.get('payout', 85),
            'ai_analysis': ai_analysis,
            'strategy_consensus': 0.85,  # Simulado por ahora
            'volatility_analysis': {'score': 0.6}  # Simulado por ahora
        }
        
        # Validar con sistema de efectividad garantizada
        print("🎯 Validando efectividad garantizada...")
        validation = self.effectiveness_guarantee.validate_signal_quality(señal_base)
        
        if validation['approved']:
            print(f"✅ SEÑAL APROBADA (Efectividad: {validation['effectiveness_prediction']:.1%}):")
            print(f"   • Par: {señal_base['symbol']}")
            print(f"   • Dirección: {señal_base['direccion']}")
            print(f"   • Confianza IA: {ai_analysis['confidence']:.1%}")
            print(f"   • Score IA: {ai_analysis['ai_score']:.2f}")
            print(f"   • Payout: {señal_base['payout']}%")
            print(f"   • Efectividad Predicha: {validation['effectiveness_prediction']:.1%}")
            
            # Mostrar análisis detallado de IA
            print("\n🧠 ANÁLISIS DETALLADO DE IA:")
            for key, value in ai_analysis['detailed_analysis'].items():
                if isinstance(value, (int, float)):
                    print(f"   • {key.replace('_', ' ').title()}: {value:.3f}")
                else:
                    print(f"   • {key.replace('_', ' ').title()}: {value}")
                    
            return señal_base
        else:
            print(f"❌ SEÑAL RECHAZADA:")
            print(f"   • Confianza: {validation['confidence_score']:.1%}")
            print(f"   • Razones: {', '.join(validation['rejection_reasons'])}")
            return None
    
    def mostrar_estadisticas_dia(self):
        """Muestra estadísticas del día"""
        stats = self.user_manager.obtener_estadisticas_diarias()
        print("\n📊 ESTADÍSTICAS DEL DÍA:")
        print(f"📅 Fecha: {stats.get('fecha', 'N/A')}")
        print(f"👥 Total usuarios: {stats.get('total_usuarios', 0)}")
        print(f"⏰ Usuarios tardíos: {stats.get('usuarios_tardios', 0)}")
        print(f"📈 Señales enviadas: {stats.get('señales_enviadas', 0)}")
        print(f"🎯 Efectividad promedio: {stats.get('efectividad_promedio', 0):.1f}%")
    
    def mostrar_configuracion(self):
        """Muestra la configuración actual"""
        print("\n⚙️ CONFIGURACIÓN ACTUAL:")
        print(f"📧 Email Quotex: {self.quotex_email}")
        print(f"🤖 Token Telegram: {'Configurado' if self.telegram_token else 'NO CONFIGURADO'}")
        print(f"🎯 Objetivo señales diarias: {self.signal_scheduler.objetivo_señales_diarias}")
        
        # Mostrar pesos de estrategias
        pesos = self.adaptive_learning.obtener_pesos_optimizados()
        print("\n⚖️ PESOS DE ESTRATEGIAS:")
        for estrategia, peso in pesos.items():
            print(f"   • {estrategia.replace('_', ' ').title()}: {peso:.2f}")

def main():
    """Función principal - Arranque automático para producción"""
    print("🇨🇺 Iniciando CubaYDSignal Bot Enhanced...")
    
    # Crear instancia principal
    bot_main = CubaYDSignalMain()
    
    # Verificar configuración
    if not bot_main.verificar_configuracion():
        print("❌ Error en la configuración. Revisa las variables de entorno.")
        return
    
    # Inicializar sistema
    if not asyncio.run(bot_main.inicializar_sistema()):
        print("❌ Error inicializando el sistema.")
        return
    
    # Verificar si hay variable de entorno para modo manual (para desarrollo)
    modo_manual = os.getenv("MANUAL_MODE", "false").lower() == "true"
    
    if modo_manual:
        print("🎮 Ejecutando en modo manual (desarrollo)...")
        bot_main.ejecutar_modo_manual()
    else:
        print("🚀 Ejecutando en modo automático (producción)...")
        print("💡 Para modo manual, configura MANUAL_MODE=true en variables de entorno")
        asyncio.run(bot_main.ejecutar_modo_automatico())

if __name__ == "__main__":
    main()
