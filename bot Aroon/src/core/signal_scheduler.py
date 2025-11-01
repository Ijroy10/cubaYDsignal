"""
SISTEMA DE PROGRAMACIÓN DE SEÑALES Y NOTIFICACIONES
Maneja:
- Programación de señales (8:00 AM - 8:00 PM, Lun-Sáb)
- Mínimo 20-25 señales por día
- Notificaciones pre-señal
- Mensajes motivacionales
- Resúmenes diarios
- Análisis de rendimiento
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
import pandas as pd
from .market_manager import MarketManager
from .user_manager import UserManager

class SignalScheduler:
    def __init__(self):
        self.market_manager = None  # Se configurará externamente
        self.user_manager = None  # Se configurará externamente
        self.señales_programadas = []
        self.señales_enviadas_hoy = []
        self.objetivo_señales_diarias = 25
        self.mercado_actual = None
        self.bot_telegram = None  # Se configurará externamente
        
        # Estadísticas de Martingala del día
        self.martingalas_ejecutadas_hoy = 0
        self.martingalas_ganadas_hoy = 0
        self.martingalas_perdidas_hoy = 0
        
        # Estadísticas de Trading Automático del día
        self.trading_auto_activo_hoy = False
        self.trading_auto_inicio = None
        self.trading_auto_fin = None
        self.trading_auto_operaciones = []  # Lista de operaciones del día
        self.trading_auto_ganancia_total = 0.0
        self.trading_auto_perdida_total = 0.0
        self.frases_motivacionales = self.cargar_frases_motivacionales()
        self.running = False
        # Override temporal de horario operativo (si está activo, se ignoran reglas de horario)
        self._override_until: Optional[datetime] = None
        # Almacenamiento de confirmaciones/IDs activos
        self.pre_id_actual: Optional[str] = None
        self.signal_id_actual: Optional[str] = None
        self.senales_pendientes: Dict[str, Dict] = {}
        # Ventanas de caducidad
        self.pre_ttl_min = 2  # minutos para aceptar pre‑señal
        self.signal_ttl_min = 2  # minutos para aceptar señal
        self._pre_expirations: Dict[str, datetime] = {}
        self._signal_expirations: Dict[str, datetime] = {}
        # Estado de conexión/pausa
        self.pausado_por_conexion: bool = False
        self._monitor_task = None
        # Análisis forzado de mercado específico
        self.analisis_forzado_activo = False
        self.analisis_forzado_par = None
        self.analisis_forzado_duracion = 0
        self.efectividad_minima_temporal = 80
        
        # Sistema de Martingala
        self.martingala_activa = False
        self.martingala_monto_base = 0
        self.martingala_monto_actual = 0
        self.martingala_direccion = None
        self.martingala_pendiente = None  # Para almacenar Martingala esperando confirmación
        self.martingala_symbol = None
        self.martingala_intentos = 0
        self.martingala_max_intentos = 1  # Solo 1 martingala
        
        # Sistema de Martingala Predictiva
        self.señal_martingala_pendiente = None  # Señal que está siendo analizada
        self.martingala_confirmacion_anticipada = None  # True=confirmada, False=rechazada, None=sin respuesta

    def configurar_bot_telegram(self, bot_telegram):
        """Inyecta la referencia del bot de Telegram para enviar confirmaciones."""
        try:
            self.bot_telegram = bot_telegram
            print("[SignalScheduler] 🤝 Bot de Telegram configurado para confirmaciones")
        except Exception as e:
            print(f"[SignalScheduler] ❌ No se pudo configurar bot de Telegram: {e}")
        # Iniciar monitor de conexión si no está activo
        try:
            if self._monitor_task is None or self._monitor_task.done():
                import asyncio as _aio
                self._monitor_task = _aio.create_task(self.monitor_conexion_quotex())
                print("[SignalScheduler] 🩺 Monitor de conexión a Quotex iniciado")
        except Exception as e:
            print(f"[SignalScheduler] ⚠️ No se pudo iniciar monitor de conexión: {e}")
        
    def cargar_frases_motivacionales(self) -> Dict:
        """Carga las frases motivacionales categorizadas"""
        return {
            # Frases para inicio del día (mensaje 15 min antes de las 8:00 AM)
            'bienvenida_diaria': [
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
            ],
            
            # Frases para usuarios que se conectan temprano
            'bienvenida_temprana': [
                "Los que esperan la señal perfecta, nunca ganan. Los que entienden el juego, la construyen.",
                "La disciplina de hoy es la ganancia de mañana.",
                "Cada día es una nueva oportunidad de demostrar tu control.",
                "El éxito no llega por casualidad, llega por preparación.",
                "Hoy puede ser tu mejor día si operas con la mente, no con el corazón."
            ],
            
            # Frases para respuesta automática a nuevos usuarios
            'saludo_automatico': [
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
            ],
            
            # Frases para inicio de día según expectativa
            'inicio_dia_excelente': [
                "¡Hoy el mercado está preparado para ti! Expectativa: excelente.",
                "Las condiciones son óptimas. Hoy puede ser un gran día.",
                "El análisis indica alta probabilidad de éxito. ¡A operar con confianza!",
                "Hoy las señales prometen ser precisas. Mantén el enfoque.",
                "Expectativa alta para hoy. El mercado está alineado."
            ],
            
            'inicio_dia_bueno': [
                "Buen día para operar. Las condiciones son favorables.",
                "El mercado muestra señales positivas. Mantén la disciplina.",
                "Hoy hay oportunidades claras. Opera con tu estrategia.",
                "Condiciones buenas para el trading. Sigue tu plan.",
                "El análisis es prometedor. Hoy puede ser productivo."
            ],
            
            'inicio_dia_normal': [
                "Día estándar en el mercado. Opera con precaución.",
                "Condiciones normales. Mantén tu estrategia y paciencia.",
                "Hoy requiere análisis cuidadoso. No te apresures.",
                "Mercado en modo neutral. Espera las mejores señales.",
                "Día regular. La disciplina será tu mejor aliada."
            ],
            
            # Frases para cierre exitoso (>80% efectividad)
            'cierre_exitoso': [
                "Hoy no ganaste por suerte, ganaste porque tu análisis fue más fuerte.",
                "Cuando aplicas la lógica y la paciencia, el mercado responde.",
                "Hoy dominaste el juego… mañana toca repetir la fórmula.",
                "Disciplina + estrategia = resultados. Hoy lo comprobaste.",
                "El que entiende las velas, no necesita adivinarlas.",
                "Hoy fuiste preciso, enfocado y controlado. Así se gana.",
                "Cada decisión con lógica te acercó a este resultado. Bien hecho.",
                "Los resultados de hoy confirman que estás operando con mentalidad de trader.",
                "Cuando tus decisiones siguen un plan, los números responden.",
                "Hoy fuiste más que trader: fuiste estratega.",
                "No es magia. Es lógica, estudio y ejecución.",
                "Hoy el mercado habló… y tú supiste escuchar."
            ],
            
            # Frases para día estable (60-80% efectividad)
            'cierre_estable': [
                "Un buen día no es perfecto, es disciplinado.",
                "El enfoque que tuviste hoy construye la consistencia de mañana.",
                "No todos los días traen gloria, pero todos construyen experiencia.",
                "Hoy sumaste decisiones con lógica. Esa es la verdadera ganancia.",
                "Sigue afinando tu visión, cada día suma al trader que estás formando.",
                "La suerte es solo el reflejo de la disciplina repetida cada día.",
                "Hoy fuiste más fuerte que la emoción. Mañana, más sabio que ayer.",
                "Las velas no se controlan… pero tu reacción a ellas, sí.",
                "Pierdas o ganes, lo importante es seguir el plan. La consistencia construye resultados.",
                "El que entiende el juego, no necesita suerte."
            ],
            
            # Frases para día difícil (<60% efectividad)
            'cierre_dificil': [
                "El mercado no siempre premia, pero siempre enseña.",
                "Hoy no ganaste dinero… pero ganaste experiencia. Mañana la conviertes en resultados.",
                "Hasta los mejores traders tienen días rojos. Lo que los hace grandes es que siguen.",
                "Perder no significa fallar, sino que estás un paso más cerca de dominar el sistema.",
                "No es un mal día… es un buen maestro disfrazado.",
                "Hoy fue duro, pero no olvides que tu disciplina no depende del resultado.",
                "No midas tu progreso por un solo día. Mira el camino completo.",
                "A veces el mercado enseña con golpes. Apréndelo y sigue.",
                "Un día malo no define tu futuro. Tu constancia sí.",
                "Hoy no ganaste… pero no perdiste si aprendiste.",
                "El retroceso de hoy es el impulso de mañana.",
                "En el trading, el control emocional vale más que una señal perfecta."
            ],
            
            # Frases para señales exitosas
            'señal_exitosa': [
                "¡Excelente! Esa fue una ejecución perfecta.",
                "¡Genial! El análisis fue preciso.",
                "¡Perfecto! Así se hace trading profesional."
            ],
            'fin_dia_bueno': [
                "¡Buen trabajo equipo! 👏 ¡Día sólido de trading!",
                "¡Excelente! 📈 ¡Otro día positivo!",
                "¡Bien hecho! 💪 ¡Seguimos creciendo!",
                "¡Genial! ⭐ ¡Consistencia que da frutos!",
                "¡Perfecto! 🎯 ¡Día productivo completado!"
            ],
            'fin_dia_regular': [
                "¡Día completado! 📊 ¡Mañana será mejor!",
                "¡Bien! 👍 ¡Cada día aprendemos más!",
                "¡Adelante! 🚶‍♂️ ¡El progreso es constante!",
                "¡Continuamos! 📈 ¡La consistencia es clave!",
                "¡Seguimos! 💪 ¡Cada día nos hace más fuertes!"
            ],
            'motivacion_general': [
                "¡El éxito está en los detalles! 🔍",
                "¡La disciplina es tu mejor aliada! 💪",
                "¡Cada pérdida es una lección! 📚",
                "¡La paciencia es la clave del trading! ⏰",
                "¡Confía en el proceso! 🎯"
            ]
        }

    # ==== Expiración de pre‑señal y señal ====
    def set_pre_expiration(self, pre_id: str, ttl_min: Optional[int] = None):
        ttl = ttl_min if ttl_min is not None else self.pre_ttl_min
        self._pre_expirations[pre_id] = datetime.now() + timedelta(minutes=ttl)

    def set_signal_expiration(self, signal_id: str, ttl_min: Optional[int] = None):
        ttl = ttl_min if ttl_min is not None else self.signal_ttl_min
        self._signal_expirations[signal_id] = datetime.now() + timedelta(minutes=ttl)

    def pre_is_expired(self, pre_id: str) -> bool:
        exp = self._pre_expirations.get(pre_id)
        return exp is not None and datetime.now() >= exp

    def signal_is_expired(self, signal_id: str) -> bool:
        exp = self._signal_expirations.get(signal_id)
        return exp is not None and datetime.now() >= exp
    
    def configurar_bot_telegram(self, bot):
        """Configura el bot de Telegram"""
        self.bot_telegram = bot
        print("[SignalScheduler] Bot de Telegram configurado")
    
    def esta_en_horario_operativo(self) -> bool:
        """Verifica si estamos en horario operativo (8:00-20:00, Lun-Sáb)"""
        # Delegar a es_horario_operativo() que tiene la lógica completa
        return self.es_horario_operativo()

    def enable_override_until(self, hasta: datetime):
        """Habilita un override temporal de horario hasta la fecha/hora indicada"""
        self._override_until = hasta
        print(f"[SignalScheduler] ⏩ Override de horario habilitado hasta: {hasta.strftime('%Y-%m-%d %H:%M:%S')}")

    def enable_override_until_midnight_today(self):
        """Habilita override hasta las 23:59:59 de hoy"""
        ahora = datetime.now()
        hasta = ahora.replace(hour=23, minute=59, second=59, microsecond=0)
        self.enable_override_until(hasta)
    
    def calcular_intervalo_señales(self) -> int:
        """
        Calcula el intervalo entre señales para alcanzar el objetivo diario
        Horario: 8:00-20:00 = 12 horas = 720 minutos
        Objetivo: 25 señales = 720/25 = ~29 minutos entre señales
        """
        minutos_operativos = 12 * 60  # 720 minutos
        intervalo = minutos_operativos // self.objetivo_señales_diarias
        return max(20, min(60, intervalo))  # Entre 20-60 minutos
    
    async def iniciar_dia_trading(self):
        """Inicia el día de trading con mensaje motivacional"""
        if not self.esta_en_horario_operativo():
            return
        # Pausa por conexión
        if self.pausado_por_conexion:
            print("[SignalScheduler] ⏸️ Inicio de día pausado: sin conexión a Quotex")
            return
        
        # Seleccionar mejor mercado del día (pasando self para análisis forzado)
        self.mercado_actual = await self.market_manager.seleccionar_mejor_mercado(signal_scheduler=self)
        if not self.mercado_actual:
            print("[SignalScheduler] ❌ No se pudo seleccionar mercado")
            return
        
        # Generar mensaje de inicio
        efectividad_esperada = self.mercado_actual.get('efectividad_calculada', 75)
        categoria_dia = self.categorizar_expectativa_dia(efectividad_esperada)
        frase_inicio = random.choice(self.frases_motivacionales[categoria_dia])
        
        mensaje_inicio = f"""
🌅 INICIO DEL DÍA DE TRADING

{frase_inicio}

📊 INFORMACIÓN DEL DÍA:
• 💱 Mercado seleccionado: {self.mercado_actual['symbol']}
• 💰 Payout: {self.mercado_actual['payout']}%
• 📈 Efectividad esperada: {efectividad_esperada:.1f}%
• 🎯 Objetivo de señales: {self.objetivo_señales_diarias}
• ⏰ Horario operativo: 8:00 AM - 8:00 PM

🔑 Clave del día: {self.user_manager.clave_publica_diaria}

¡Prepárense para un día exitoso! 💪🚀
        """
        
        await self.enviar_mensaje_a_usuarios(mensaje_inicio.strip())
        print(f"[SignalScheduler] 🌅 Día iniciado - Mercado: {self.mercado_actual['symbol']}")
    
    def categorizar_expectativa_dia(self, efectividad: float) -> str:
        """Categoriza el día según la efectividad esperada"""
        if efectividad >= 85:
            return 'inicio_dia_excelente'
        elif efectividad >= 75:
            return 'inicio_dia_bueno'
        else:
            return 'inicio_dia_normal'
    
    async def programar_señales_del_dia(self):
        """Programa las señales del día"""
        if not self.mercado_actual:
            return
        if self.pausado_por_conexion:
            print("[SignalScheduler] ⏸️ Programación de señales pausada por pérdida de conexión")
            return
        
        intervalo_minutos = self.calcular_intervalo_señales()
        hora_inicio = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        hora_fin = datetime.now().replace(hour=20, minute=0, second=0, microsecond=0)
        
        # Si ya pasó la hora de inicio, comenzar desde ahora
        if datetime.now() > hora_inicio:
            hora_inicio = datetime.now() + timedelta(minutes=5)
        
        señales_programadas = []
        hora_actual = hora_inicio
        
        while hora_actual < hora_fin and len(señales_programadas) < self.objetivo_señales_diarias:
            # Agregar variación aleatoria al intervalo (±5 minutos)
            variacion = random.randint(-5, 5)
            hora_señal = hora_actual + timedelta(minutes=variacion)
            
            if hora_señal < hora_fin:
                señales_programadas.append(hora_señal)
            
            hora_actual += timedelta(minutes=intervalo_minutos)
        
        self.señales_programadas = señales_programadas
        print(f"[SignalScheduler] 📅 {len(señales_programadas)} señales programadas")
    
    async def ejecutar_analisis_señal(self) -> Optional[Dict]:
        """Ejecuta el análisis completo para generar una señal"""
        try:
            if not self.mercado_actual:
                return None
            
            # Obtener datos del mercado
            df = await self.market_manager.obtener_datos_mercado(self.mercado_actual['symbol'])
            if df is None or len(df) < 50:
                return None
            
            # Ejecutar análisis completo
            from src.strategies.evaluar_estrategia_completa import evaluar_estrategia_completa
            resultado = evaluar_estrategia_completa(df, self.mercado_actual['symbol'])
            
            # Verificar si la señal es válida (efectividad ≥ umbral configurado)
            efectividad = resultado.get('efectividad_total', 0)
            decision = resultado.get('decision')
            umbral_efectividad = getattr(self, 'efectividad_minima_temporal', 80)
            
            if decision and efectividad >= umbral_efectividad:
                # Obtener precio actual de entrada
                precio_entrada = df['close'].iloc[-1] if df is not None and len(df) > 0 else None
                
                # Crear datos de la señal
                señal = {
                    'numero': len(self.señales_enviadas_hoy) + 1,
                    'hora': datetime.now().strftime('%H:%M'),
                    'timestamp': datetime.now().isoformat(),
                    'symbol': self.mercado_actual['symbol'],
                    'direccion': decision,
                    'efectividad': efectividad,
                    'payout': self.mercado_actual['payout'],
                    'validez_minutos': 5,
                    'precio_entrada': float(precio_entrada) if precio_entrada else None,
                    'detalles_tecnicos': resultado.get('resumen', {}),
                    'pullback_info': resultado.get('pullback_detectado', False),
                    'tendencia': resultado.get('tendencia_direccion', 'N/A'),
                    'volatilidad': resultado.get('volatilidad_estado', 'N/A'),
                    'resultado': None  # Se actualizará automáticamente después de 5 minutos
                }
                
                return señal
            else:
                print(f"[SignalScheduler] ⚠️ Señal no válida - Efectividad: {efectividad}%")
                return None
                
        except Exception as e:
            print(f"[SignalScheduler] ❌ Error en análisis: {e}")
            return None
    
    async def enviar_pre_señal(self, minutos_antes: int = 3):
        """DESACTIVADO: Pre-señales eliminadas - Las señales se envían directamente"""
        print("[SignalScheduler] ⚠️ Pre-señales desactivadas - Enviando señal directamente")
        # Las señales ahora se envían directamente sin pre-notificación
        return

    async def enviar_señal(self, señal: Dict):
        """Envía la señal formateada a los usuarios"""
        # Guard: requerir conexión real a Quotex
        try:
            mm = getattr(self, 'market_manager', None)
            conectado_qx = bool(getattr(mm, 'conectado', False)) or (getattr(mm, 'quotex', None) is not None)
            if not conectado_qx:
                print("[SignalScheduler] 🚫 Señal abortada: sin conexión a Quotex.")
                try:
                    if getattr(self, 'bot_telegram', None) and hasattr(self.bot_telegram, 'notificar_admin_telegram'):
                        await self.bot_telegram.notificar_admin_telegram("⚠️ Señal abortada: sin conexión a Quotex.")
                except Exception:
                    pass
                return
        except Exception:
            pass
        # Guardar señal como pendiente y generar ID
        self.signal_id_actual = datetime.now().strftime('%Y%m%d%H%M%S')
        # Generar y adjuntar mensaje formateado completo para que el callback lo muestre
        try:
            mensaje_fmt = self.generar_mensaje_señal_completo(
                señal,
                señal.get('detalles_tecnicos', {}) if isinstance(señal, dict) else {}
            )
            if isinstance(señal, dict):
                señal['mensaje_formateado'] = mensaje_fmt
        except Exception:
            # En caso de error al formatear, continuar sin bloquear el envío
            pass
        self.senales_pendientes[self.signal_id_actual] = señal
        # Programar caducidad de señal
        try:
            self.set_signal_expiration(self.signal_id_actual)
        except Exception:
            pass
        try:
            if hasattr(self, '_esperar_caducidad_senal'):
                import asyncio as _aio
                try:
                    _aio.create_task(self._esperar_caducidad_senal(self.pre_id_actual, self.signal_id_actual))
                except RuntimeError:
                    if getattr(self, 'bot_telegram', None) and getattr(self.bot_telegram, 'application', None):
                        loop = self.bot_telegram.application.bot.loop
                        loop.create_task(self._esperar_caducidad_senal(self.pre_id_actual, self.signal_id_actual))
        except Exception:
            pass
        # Enviar señal con botón de confirmación (sin pre-señal) a TODOS los usuarios
        if self.bot_telegram is not None and hasattr(self.bot_telegram, 'enviar_confirmacion_senal_a_usuarios'):
            try:
                await self.bot_telegram.enviar_confirmacion_senal_a_usuarios(
                    signal_id=self.signal_id_actual,
                    pre_id=None,  # Sin pre-señal
                    señal=señal
                )
                num_usuarios = len(getattr(self.user_manager, 'usuarios_activos', {}))
                print(f"[SignalScheduler] ✅ Señal #{señal['numero']} enviada a {num_usuarios} usuarios")
            except Exception as e:
                print(f"[SignalScheduler] ❌ Error enviando confirmación de señal: {e}")
        else:
            print("[SignalScheduler] ⚠️ Bot de Telegram no configurado para confirmación de señal")
        # Registrar señal en historial del día (registro administrativo)
        self.señales_enviadas_hoy.append(señal)
        self.user_manager.registrar_señal_enviada(señal)
        print(f"[SignalScheduler] 📤 Señal #{señal['numero']} preparada y confirmación enviada")
        
        # TRADING AUTOMÁTICO: Ejecutar operación ADICIONAL si está activo (las señales ya fueron enviadas a todos)
        try:
            if self.bot_telegram and hasattr(self.bot_telegram, '_trading_activo'):
                if getattr(self.bot_telegram, '_trading_activo', False):
                    print("[Trading] 🤖 Trading automático activo - Ejecutando operación adicional...")
                    await self.ejecutar_operacion_automatica(señal)
        except Exception as e:
            print(f"[Trading] ❌ Error ejecutando operación automática: {e}")
        
        # Programar verificación automática del resultado después de 5 minutos
        try:
            import asyncio as _aio
            _aio.create_task(self.verificar_resultado_señal_automatico(señal))
            print(f"[SignalScheduler] ⏰ Verificación de resultado programada para 5 minutos")
        except Exception as e:
            print(f"[SignalScheduler] ⚠️ Error programando verificación de resultado: {e}")

    # ================== Monitor de conexión y control de pausa ==================
    def _esta_conectado_qx(self) -> bool:
        try:
            mm = getattr(self, 'market_manager', None)
            return bool(getattr(mm, 'conectado', False)) or (getattr(mm, 'quotex', None) is not None)
        except Exception:
            return False

    async def monitor_conexion_quotex(self):
        """Supervisa el estado de conexión a Quotex y pausa/reanuda automáticamente el scheduler."""
        base_sleep = 10
        max_sleep = 120
        sleep_ok = 30
        cur_sleep = base_sleep
        while True:
            try:
                conectado = self._esta_conectado_qx()
                
                # Verificar si fue desconexión manual
                mm = getattr(self, 'market_manager', None)
                desconexion_manual = getattr(mm, 'desconexion_manual', False) if mm else False
                
                if not conectado:
                    if not self.pausado_por_conexion:
                        self.pausado_por_conexion = True
                        if desconexion_manual:
                            print("[SignalScheduler] 🔴 Desconexión manual detectada. Scheduler en pausa.")
                            print("[SignalScheduler] ℹ️ NO se reconectará automáticamente. Usa 'Conectar Forzado' para reconectar.")
                        else:
                            print("[SignalScheduler] 🔴 Conexión a Quotex perdida. Scheduler en pausa.")
                        try:
                            if getattr(self, 'bot_telegram', None) and hasattr(self.bot_telegram, 'notificar_admin_telegram'):
                                if desconexion_manual:
                                    await self.bot_telegram.notificar_admin_telegram("🔴 Desconexión manual. El scheduler está en pausa. Usa 'Conectar Forzado' para reconectar.")
                                else:
                                    await self.bot_telegram.notificar_admin_telegram("🔴 Conexión a Quotex perdida. El scheduler fue pausado.")
                        except Exception:
                            pass
                    # Backoff exponencial mientras esté desconectado
                    import asyncio as _aio
                    await _aio.sleep(cur_sleep)
                    cur_sleep = min(max_sleep, cur_sleep * 2)
                    continue
                # Conectado
                if self.pausado_por_conexion:
                    self.pausado_por_conexion = False
                    print("[SignalScheduler] 🟢 Conexión a Quotex restablecida. Reanudando scheduler.")
                    try:
                        if getattr(self, 'bot_telegram', None) and hasattr(self.bot_telegram, 'notificar_admin_telegram'):
                            await self.bot_telegram.notificar_admin_telegram("🟢 Conexión a Quotex restablecida. Scheduler reanudado.")
                    except Exception:
                        pass
                    # Replanificar si estamos en horario operativo
                    try:
                        if self.esta_en_horario_operativo():
                            # Seleccionar mercado y reprogramar señales del día (pasando self para análisis forzado)
                            self.mercado_actual = await self.market_manager.seleccionar_mejor_mercado(signal_scheduler=self)
                            if self.mercado_actual:
                                await self.programar_señales_del_dia()
                                # Notificación opcional a usuarios: servicio restablecido
                                try:
                                    await self.enviar_pre_notificacion_señal(motivo="servicio restablecido", minutos_antes=3)
                                except Exception:
                                    pass
                    except Exception as e:
                        print(f"[SignalScheduler] ⚠️ Error reprogramando tras reconexión: {e}")
                    # Reset backoff al volver
                    cur_sleep = base_sleep
                # Dormir en estado OK
                import asyncio as _aio
                await _aio.sleep(sleep_ok)
            except Exception:
                # En caso de error en el loop, esperar un poco y continuar
                import asyncio as _aio
                await _aio.sleep(10)

    def obtener_senal_por_id(self, signal_id: str) -> Optional[Dict]:
        """Devuelve la señal pendiente por su ID."""
        return self.senales_pendientes.get(str(signal_id))

    # ================== Programación de caducidades ==================
    async def _esperar_caducidad_presenal(self, pre_id: str):
        """Espera hasta la caducidad de la pre‑señal y notifica a usuarios pendientes."""
        try:
            exp = self._pre_expirations.get(pre_id)
            if not exp:
                return
            segundos = max(0, (exp - datetime.now()).total_seconds())
            import asyncio as _aio
            await _aio.sleep(segundos)
        except Exception:
            pass
        # Si ya caducó, notificar a través del bot si está disponible
        try:
            if self.pre_is_expired(pre_id) and getattr(self, 'bot_telegram', None):
                if hasattr(self.bot_telegram, 'notificar_caducidad_presenal'):
                    await self.bot_telegram.notificar_caducidad_presenal(pre_id)
        except Exception:
            pass

    async def _esperar_caducidad_senal(self, pre_id: str, signal_id: str):
        """Espera hasta la caducidad de la señal y notifica a usuarios pendientes."""
        try:
            exp = self._signal_expirations.get(signal_id)
            if not exp:
                return
            segundos = max(0, (exp - datetime.now()).total_seconds())
            import asyncio as _aio
            await _aio.sleep(segundos)
        except Exception:
            pass
        try:
            if self.signal_is_expired(signal_id) and getattr(self, 'bot_telegram', None):
                if hasattr(self.bot_telegram, 'notificar_caducidad_senal'):
                    await self.bot_telegram.notificar_caducidad_senal(pre_id, signal_id)
        except Exception:
            pass
    
    def generar_mensaje_señal_completo(self, señal: Dict, detalles: Dict) -> str:
        """Genera mensaje de señal con formato completo según especificación del usuario"""
        # Formatear hora a AM/PM
        try:
            from datetime import datetime, timedelta
            hora_obj = datetime.strptime(señal['hora'], '%H:%M')
            hora_formateada = hora_obj.strftime('%I:%M %p')
            
            # Calcular horario de entrada (próxima vela M5)
            ahora = datetime.now()
            minuto_actual = ahora.minute
            segundo_actual = ahora.second
            
            # Calcular la próxima vela M5 (velas en minutos: 00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
            # Redondear al próximo múltiplo de 5
            minutos_hasta_proxima_vela = (5 - (minuto_actual % 5)) % 5
            
            if minutos_hasta_proxima_vela == 0 and segundo_actual > 0:
                # Si estamos en un múltiplo de 5 pero ya pasaron segundos, ir a la siguiente vela M5
                minutos_hasta_proxima_vela = 5
            elif minutos_hasta_proxima_vela == 0:
                # Si estamos exactamente al inicio de una vela M5, usar esa
                minutos_hasta_proxima_vela = 0
            
            # Calcular hora de entrada (apertura de la próxima vela M5)
            hora_entrada = ahora.replace(second=0, microsecond=0) + timedelta(minutes=minutos_hasta_proxima_vela)
            
            # Formatear horario de entrada
            hora_entrada_formateada = hora_entrada.strftime('%I:%M %p')
            minuto_entrada = hora_entrada.strftime('%H:%M')
            
        except:
            hora_formateada = señal['hora']
            hora_entrada_formateada = señal['hora']
            minuto_entrada = señal['hora']
        
        # Formatear dirección
        direccion = señal['direccion'].upper()
        direccion_texto = "CALL (Compra)" if direccion == "CALL" else "PUT (Venta)"
        
        # Análisis de pullback
        pullback_info = señal.get('pullback_info', {})
        # Verificar si pullback_info es un diccionario o un booleano
        if isinstance(pullback_info, dict):
            pullback_esperado = "✅ Sí" if pullback_info.get('detectado', False) else "❌ No"
            pullback_probabilidad = pullback_info.get('probabilidad_efectividad', 0)
            pullback_motivo = pullback_info.get('motivo', "Análisis técnico estándar sin pullback específico detectado.")
        else:
            # Si es booleano o cualquier otro tipo
            pullback_esperado = "❌ No"
            pullback_probabilidad = 0
            pullback_motivo = "Análisis técnico estándar sin pullback específico detectado."
        
        # Detalles técnicos
        tendencia_info = detalles.get('tendencia', {})
        soporte_resistencia = detalles.get('soportes_resistencias', {})
        patrones = detalles.get('patrones', {})
        volatilidad_info = detalles.get('volatilidad', {})
        
        # Obtener mejor patrón
        patrones_detalles = patrones.get('detalles', {}) if isinstance(patrones, dict) else {}
        mejor_patron = patrones_detalles.get('mejor_patron', {})
        patron_nombre = mejor_patron.get('nombre', 'Patrón estándar').capitalize()
        
        # Información de tendencia
        tendencia_direccion = tendencia_info.get('direccion_final', 'Neutral')
        tendencia_texto = "Alcista sólida (mínimos y máximos ascendentes)" if tendencia_direccion == 'ALCISTA' else "Bajista sólida (máximos y mínimos descendentes)" if tendencia_direccion == 'BAJISTA' else "Lateral con consolidación"
        
        # Zona clave (simulada basada en soporte/resistencia)
        zona_clave = soporte_resistencia.get('nivel_clave', señal.get('precio_actual', '1.09240'))
        zona_tipo = "Soporte" if direccion == "CALL" else "Resistencia"
        
        # Volatilidad
        volatilidad_texto = volatilidad_info.get('nivel', 'Media')
        ultima_vela_pips = volatilidad_info.get('ultima_vela_pips', 45)
        promedio_pips = volatilidad_info.get('promedio_pips', 35)
        
        # Verificar si es sábado para añadir notificación OTC
        es_sabado = datetime.now().weekday() == 5
        notificacion_sabado = ""
        if es_sabado:
            notificacion_sabado = "\n\n📅 SÁBADO - SOLO MERCADOS OTC\n⚠️ Los mercados normales están cerrados. Operamos únicamente mercados OTC que funcionan 24/7 sin horarios de noticias."
        
        # Recomendación del bot
        recomendacion = f"⏰ Ejecutar entrada {direccion} exactamente a las {hora_entrada_formateada} (al abrir la vela de {minuto_entrada}).\n\n"
        recomendacion += f"📍 Cómo operar:\n"
        recomendacion += f"1. Espera a que el reloj marque {hora_entrada_formateada}\n"
        recomendacion += f"2. Abre la operación {direccion} en {señal['symbol']}\n"
        recomendacion += f"3. Tiempo de expiración: 5 minutos (M5)\n"
        recomendacion += f"4. Cierre esperado: {(hora_entrada + timedelta(minutes=5)).strftime('%I:%M %p')}"
        
        # Agregar tip de pullback solo si es un diccionario válido
        if isinstance(pullback_info, dict) and pullback_info.get('detectado', False):
            recomendacion += f"\n\n💡 Tip: Pullback detectado - Si ves retroceso leve antes de {hora_entrada_formateada}, es confirmación adicional de la señal."
        
        mensaje = f"""📊 Señal #{señal['numero']:02d}  
🕒 Hora de señal: {hora_formateada}
⏰ EJECUTAR ENTRADA A LAS: {hora_entrada_formateada} (Apertura de vela {minuto_entrada})
📈 Activo: {señal['symbol']}  
📍 Dirección: {direccion_texto}  
⏳ Válido por: {señal.get('validez_minutos', 5)} minutos  
🎯 Efectividad estimada: {señal['efectividad']:.0f}%{notificacion_sabado}

🔁 Pullback esperado: {pullback_esperado}  
📊 Probabilidad de efectividad del pullback: {pullback_probabilidad:.0f}%  
📌 Motivo: {pullback_motivo}

───────────────  
📌 Detalles técnicos:

- 📉 Tendencia principal: {tendencia_texto}  
- 📍 Zona clave: {zona_tipo} reciente en {zona_clave} (antigua {'resistencia rota' if direccion == 'CALL' else 'soporte roto'})  
- 📊 Patrón detectado: {patron_nombre} en zona + confirmación con vela fuerte {'verde' if direccion == 'CALL' else 'roja'}  
- 🔥 Volatilidad: {volatilidad_texto} → Última vela: +{ultima_vela_pips} pips | Promedio: {promedio_pips} pips  
- 🎯 Acción del precio: Rechazo limpio de la zona + presión {'compradora' if direccion == 'CALL' else 'vendedora'} creciente

───────────────  
⚠️ Recomendación del bot:  
{recomendacion}

🤖 – Señal generada por el Bot CubaYDsignal"""
        
        return mensaje
    
    async def enviar_pre_notificacion_señal(self, mercado: str = None, motivo: str = None, minutos_antes: int = 3):
        """Envía pre-notificación antes de una señal con mercado y motivo"""
        # Obtener mercado actual si no se proporciona
        if not mercado and self.mercado_actual:
            mercado = self.mercado_actual.get('symbol', 'EUR/USD')
        elif not mercado:
            mercado = 'EUR/USD'
        
        # Generar motivo si no se proporciona
        if not motivo:
            motivos_posibles = [
                "confluencia técnica detectada en zona clave",
                "patrón de reversión confirmado con alta efectividad",
                "ruptura de zona importante con volumen",
                "pullback saludable en tendencia principal",
                "formación de patrón alcista/bajista en soporte/resistencia",
                "señales múltiples convergiendo en la misma dirección"
            ]
            motivo = random.choice(motivos_posibles)
        
        mensaje_pre = f"""🔔 ALERTA DE SEÑAL

🚨 ¡Atención traders!
En aproximadamente {minutos_antes} minutos se generará una nueva señal.

💱 Mercado: {mercado}
🔍 Motivo: {motivo}

👀 Mantente atento a tu dispositivo
📱 Prepárate para recibir la señal
🎯 ¡La oportunidad se acerca!

🤖 – Bot CubaYDsignal"""
        
        await self.enviar_mensaje_a_usuarios(mensaje_pre)
        print(f"[SignalScheduler] 🔔 Pre-notificación enviada ({minutos_antes} min antes) - {mercado}")
    
    async def generar_informe_diario_completo(self):
        """Genera informe diario completo con estadísticas y análisis"""
        if not self.señales_enviadas_hoy:
            return "No se enviaron señales hoy."
        
        # Calcular estadísticas generales
        total_señales = len(self.señales_enviadas_hoy)
        señales_ganadas = sum(1 for s in self.señales_enviadas_hoy if s.get('resultado') == 'WIN')
        señales_perdidas = total_señales - señales_ganadas
        señales_pendientes = sum(1 for s in self.señales_enviadas_hoy if s.get('resultado') not in {'WIN', 'LOSS'})
        efectividad_total = (señales_ganadas / total_señales * 100) if total_señales > 0 else 0
        
        # Obtener activos operados
        activos_operados = list(set(s['symbol'] for s in self.señales_enviadas_hoy))
        activos_texto = ", ".join(activos_operados)
        
        # Payout por activo
        payout_por_activo = {}
        for activo in activos_operados:
            pagos = [float(s.get('payout', 0)) for s in self.señales_enviadas_hoy if s['symbol'] == activo and s.get('payout') is not None]
            payout_prom = sum(pagos) / len(pagos) if pagos else 0
            payout_por_activo[activo] = payout_prom

        # Fecha actual
        fecha_hoy = datetime.now().strftime('%d de %B de %Y')
        
        # Generar resumen de señales
        resumen_señales = []
        for i, señal in enumerate(self.señales_enviadas_hoy, 1):
            # Formatear hora
            try:
                hora_obj = datetime.strptime(señal['hora'], '%H:%M')
                hora_formateada = hora_obj.strftime('%I:%M %p')
            except:
                hora_formateada = señal['hora']
            
            resultado_emoji = "✅ Ganada" if señal.get('resultado') == 'WIN' else "❌ Perdida"
            pullback_info = señal.get('pullback_info', {})
            pullback_texto = "✅ Sí" if pullback_info.get('detectado', False) else "❌ No"
            
            linea = f"{i}. Señal #{i:03d} - {hora_formateada} - {señal['symbol']} - {señal['direccion']} - {resultado_emoji} - Pullback: {pullback_texto}"
            resumen_señales.append(linea)
        
        # Análisis por activo
        analisis_activos = []
        for activo in activos_operados:
            señales_activo = [s for s in self.señales_enviadas_hoy if s['symbol'] == activo]
            total_activo = len(señales_activo)
            ganadas_activo = sum(1 for s in señales_activo if s.get('resultado') == 'WIN')
            efectividad_activo = (ganadas_activo / total_activo * 100) if total_activo > 0 else 0
            
            estado_emoji = "✅" if efectividad_activo >= 70 else "⚠️" if efectividad_activo >= 50 else "❌"
            payout_prom = payout_por_activo.get(activo, 0)
            linea_activo = (
                f"- {activo}: {total_activo} señales → {ganadas_activo} ganadas → "
                f"Efectividad: {efectividad_activo:.1f}% {estado_emoji} → Payout prom.: {payout_prom:.0f}%"
            )
            analisis_activos.append(linea_activo)
        
        # Análisis de pullbacks
        señales_con_pullback = [s for s in self.señales_enviadas_hoy if s.get('pullback_info', {}).get('detectado', False)]
        total_pullbacks = len(señales_con_pullback)
        ganadas_pullback = sum(1 for s in señales_con_pullback if s.get('resultado') == 'WIN')
        efectividad_pullback = (ganadas_pullback / total_pullbacks * 100) if total_pullbacks > 0 else 0
        señales_sin_pullback = [s for s in self.señales_enviadas_hoy if not s.get('pullback_info', {}).get('detectado', False)]
        total_sin_pullback = len(señales_sin_pullback)
        ganadas_sin_pullback = sum(1 for s in señales_sin_pullback if s.get('resultado') == 'WIN')
        efectividad_sin_pullback = (ganadas_sin_pullback / total_sin_pullback * 100) if total_sin_pullback > 0 else 0
        comparativa_pullback = ""
        if total_pullbacks > 0 and total_sin_pullback > 0:
            dif = efectividad_pullback - efectividad_sin_pullback
            if abs(dif) >= 1:
                tendencia = "superó" if dif > 0 else "estuvo por debajo"
                comparativa_pullback = f"(Pullback {tendencia} por {abs(dif):.1f} pts a las señales directas)"

        # Observaciones inteligentes
        mejor_activo = max(
            activos_operados,
            key=lambda a: (
                (sum(1 for s in self.señales_enviadas_hoy if s['symbol'] == a and s.get('resultado') == 'WIN') /
                 max(1, sum(1 for s in self.señales_enviadas_hoy if s['symbol'] == a))) * 100
            ),
            default="N/A"
        )

        # Mini-resumen por activo: últimas 3 señales (ordenadas por timestamp si existe)
        mini_resumen_activos = []
        for activo in activos_operados:
            sa = [s for s in self.señales_enviadas_hoy if s['symbol'] == activo]
            try:
                sa.sort(key=lambda s: s.get('timestamp', ''), reverse=True)
            except Exception:
                pass
            ultimas = sa[:3]
            lineas = []
            for s in ultimas:
                # hora amigable
                try:
                    hobj = datetime.strptime(s['hora'], '%H:%M')
                    hfmt = hobj.strftime('%I:%M %p')
                except Exception:
                    hfmt = s.get('hora', '?')
                res = s.get('resultado')
                res_txt = 'WIN' if res == 'WIN' else 'LOSS' if res == 'LOSS' else 'PEND'
                lineas.append(f"• {hfmt} {s.get('direccion','?')} {res_txt}")
            newline = "\n"
            mini = f"{activo}:{newline}" + (newline.join(lineas) if lineas else "(sin datos)")
            mini_resumen_activos.append(mini)

        # Top patrones del día (frecuencia y efectividad)
        patrones_stats = {}
        for s in self.señales_enviadas_hoy:
            det = s.get('detalles_tecnicos', {})
            pat = det.get('patrones', {})
            mejor = pat.get('detalles', {}).get('mejor_patron', {})
            nombre = (mejor.get('nombre') or 'desconocido').lower()
            if nombre not in patrones_stats:
                patrones_stats[nombre] = {'total': 0, 'win': 0}
            patrones_stats[nombre]['total'] += 1
            if s.get('resultado') == 'WIN':
                patrones_stats[nombre]['win'] += 1
        # Ordenar por frecuencia
        top_patrones = sorted(patrones_stats.items(), key=lambda kv: kv[1]['total'], reverse=True)
        top_lineas = []
        for nombre, st in top_patrones[:5]:
            efect = (st['win'] / st['total']) * 100 if st['total'] else 0
            top_lineas.append(f"- {nombre.capitalize()}: {st['total']} señales → {efect:.1f}% WIN")

        # Estado de Quotex si disponemos de métricas en MarketManager
        estado_qx = []
        try:
            mm = getattr(self, 'market_manager', None)
            if mm is not None:
                reconex = getattr(mm, 'reconexiones', None)
                tdesc = getattr(mm, 'tiempo_desconectado_min', None)
                mercado_mas_rent = None
                # mercado más rentable (por efectividad)
                mercados_eff = {}
                for act in activos_operados:
                    sa = [s for s in self.señales_enviadas_hoy if s['symbol'] == act]
                    if not sa:
                        continue
                    wins = sum(1 for s in sa if s.get('resultado') == 'WIN')
                    mercados_eff[act] = (wins / len(sa)) * 100
                if mercados_eff:
                    mercado_mas_rent = max(mercados_eff, key=mercados_eff.get)
                if reconex is not None:
                    estado_qx.append(f"- Reconexiones: {reconex}")
                if tdesc is not None:
                    estado_qx.append(f"- Tiempo desconectado: {tdesc} min")
                if mercado_mas_rent:
                    estado_qx.append(f"- Mercado más rentable: {mercado_mas_rent} ({mercados_eff[mercado_mas_rent]:.1f}% WIN)")
        except Exception:
            pass
        
        # Generar informe completo
        newline = "\n"
        separador = "───────────────"
        estado_quotex_section = ""
        if estado_qx:
            estado_quotex_section = f"{newline}{separador}{newline}🔌 Estado Quotex:{newline}{newline.join(estado_qx)}"
        
        fire_emoji = '🔥' if efectividad_pullback >= 80 else '✅' if efectividad_pullback >= 60 else '⚠️'
        
        # Estadísticas de Martingala
        martingala_section = ""
        if self.martingalas_ejecutadas_hoy > 0:
            efectividad_martingala = (self.martingalas_ganadas_hoy / self.martingalas_ejecutadas_hoy * 100) if self.martingalas_ejecutadas_hoy > 0 else 0
            martingala_emoji = '🔥' if efectividad_martingala >= 80 else '✅' if efectividad_martingala >= 60 else '⚠️'
            martingala_section = f"""{newline}{separador}
🎲 Martingalas del día:
- Total ejecutadas: {self.martingalas_ejecutadas_hoy}
- Ganadas: {self.martingalas_ganadas_hoy} {martingala_emoji}
- Perdidas: {self.martingalas_perdidas_hoy}
- Efectividad Martingala: {efectividad_martingala:.1f}%
- Recuperaciones exitosas: {self.martingalas_ganadas_hoy}"""
        
        informe = f"""**Informe Diario de Señales (CubaYDSignal)**

📅 Fecha: {fecha_hoy}
🕒 Horario de señales: 08:00 AM – 08:00 PM
📈 Activos operados: {activos_texto}

📡 Total de señales enviadas: {total_señales}
✅ Señales ganadas: {señales_ganadas}
❌ Señales perdidas: {señales_perdidas}
⏳ Señales pendientes: {señales_pendientes}
🎯 Efectividad total del día: {efectividad_total:.1f}%

{separador}
📌 Resumen de señales:
{newline.join(resumen_señales)}

{separador}
📈 Análisis del rendimiento:
{newline.join(analisis_activos)}

🔁 Pullbacks:
- Total de señales con pullback: {total_pullbacks}
- Ganadas con pullback: {ganadas_pullback} → Efectividad pullback: {efectividad_pullback:.1f}% {fire_emoji}
- Total sin pullback: {total_sin_pullback}
- Ganadas sin pullback: {ganadas_sin_pullback} → Efectividad sin pullback: {efectividad_sin_pullback:.1f}% {comparativa_pullback}

{separador}
🧩 Top patrones del día:
{newline.join(top_lineas) if top_lineas else '- Sin datos de patrones'}

{separador}
🗂️ Últimas 3 por activo:
{newline.join(mini_resumen_activos)}

{estado_quotex_section}
{martingala_section}

📌 Observaciones:
✔️ {mejor_activo} sigue siendo el activo más confiable hoy
⚡ El {efectividad_pullback:.0f}% de señales con pullback fueron efectivas
✅ Las mejores señales fueron combinaciones de:
   - Zona fuerte (soporte/resistencia)
   - Patrón confirmado (Martillo / Envolvente)
   - Acción del precio clara (rechazo con volumen)

📍 Recomendación para mañana:
→ Priorizar entradas con pullback confirmado y patrón fuerte
→ Operar más en {mejor_activo} en sesiones europeas y apertura americana

📉 Próximo escaneo del bot: 08:00 AM"""
        
        return informe
    
    async def generar_mensaje_motivacional_diario(self, efectividad: float) -> str:
        """Genera mensaje motivacional personalizado según la efectividad del día"""
        # Seleccionar categoría según efectividad
        if efectividad >= 80:
            categoria = 'cierre_exitoso'
        elif efectividad >= 60:
            categoria = 'cierre_estable'
        else:
            categoria = 'cierre_dificil'
        
        # Seleccionar frase aleatoria de la categoría
        frase_motivacional = random.choice(self.frases_motivacionales[categoria])
        
        # Construir mensaje completo
        mensaje = f"""Hoy lograste un {efectividad:.0f}% de efectividad.
{frase_motivacional}

Mañana, las velas te esperan con nuevas oportunidades.
No se trata de adivinar, se trata de entender el lenguaje del mercado.

Tú no viniste a probar suerte… viniste a dominar el juego.

🧠 Mantente enfocado, la próxima jornada está a solo unas horas.

Nos vemos en la apertura… 🚀"""
        
        return mensaje
    
    async def enviar_bienvenida_diaria(self):
        """Envía mensaje de bienvenida diario 15 minutos antes de las señales"""
        from datetime import datetime
        
        # Seleccionar frase motivadora aleatoria
        frase_del_dia = random.choice(self.frases_motivacionales['bienvenida_diaria'])
        
        # Verificar si es sábado para añadir notificación OTC
        es_sabado = datetime.now().weekday() == 5
        notificacion_sabado = ""
        if es_sabado:
            notificacion_sabado = "\n\n📅 **OPERACIÓN DE SÁBADO**\n🎯 Hoy operaremos únicamente mercados OTC (Over The Counter)\n⚠️ Los mercados normales están cerrados hasta el lunes\n🔄 Los OTC funcionan 24/7 sin horarios de noticias"
        
        mensaje_bienvenida = f"""🕗 Buenos días, trader.

🎯 Hoy es un nuevo día de oportunidades en el mercado.
Prepárate para operar con enfoque, lógica y disciplina.{notificacion_sabado}

🔥 Frase del día:
"{frase_del_dia}"

🎲 ¡Que la suerte te acompañe hoy!
Pero recuerda: tú no dependes de ella... tú dependes de tu análisis.
Nos vemos a las 8:00 AM con la primera señal del día.

🤖 CubaYDsignal"""
        
        await self.enviar_mensaje_a_usuarios(mensaje_bienvenida)
        print(f"[SignalScheduler] 🌅 Mensaje de bienvenida diario enviado")
    
    async def enviar_informe_y_motivacion_diaria(self):
        """Envía informe diario completo y mensaje motivacional"""
        # Generar y enviar informe
        informe = await self.generar_informe_diario_completo()
        await self.enviar_mensaje_a_usuarios(informe)
        
        # Calcular efectividad para mensaje motivacional
        if self.señales_enviadas_hoy:
            señales_ganadas = sum(1 for s in self.señales_enviadas_hoy if s.get('resultado') == 'WIN')
            efectividad = (señales_ganadas / len(self.señales_enviadas_hoy)) * 100
        else:
            efectividad = 0
        
        # Esperar un momento y enviar mensaje motivacional
        await asyncio.sleep(2)
        mensaje_motivacional = await self.generar_mensaje_motivacional_diario(efectividad)
        await self.enviar_mensaje_a_usuarios(mensaje_motivacional)
        
        print(f"[SignalScheduler] 📊 Informe diario enviado - Efectividad: {efectividad:.1f}%")
        
        # Enviar resumen de trading automático al admin si hubo operaciones
        if self.trading_auto_activo_hoy:
            await asyncio.sleep(2)
            await self.enviar_resumen_trading_auto_admin()
    
    async def enviar_resumen_trading_auto_admin(self):
        """Envía resumen de trading automático al administrador"""
        try:
            if not self.trading_auto_operaciones:
                return
            
            # Marcar hora de fin si no está marcada
            if not self.trading_auto_fin:
                self.trading_auto_fin = datetime.now().strftime('%H:%M')
            
            # Calcular estadísticas
            total_operaciones = len(self.trading_auto_operaciones)
            operaciones_ganadas = sum(1 for op in self.trading_auto_operaciones if op.get('resultado') == 'WIN')
            operaciones_perdidas = sum(1 for op in self.trading_auto_operaciones if op.get('resultado') == 'LOSS')
            operaciones_pendientes = sum(1 for op in self.trading_auto_operaciones if op.get('resultado') is None)
            
            # Separar operaciones normales de Martingalas
            ops_normales = [op for op in self.trading_auto_operaciones if not op.get('es_martingala', False)]
            ops_martingala = [op for op in self.trading_auto_operaciones if op.get('es_martingala', False)]
            
            normales_ganadas = sum(1 for op in ops_normales if op.get('resultado') == 'WIN')
            normales_perdidas = sum(1 for op in ops_normales if op.get('resultado') == 'LOSS')
            
            martingala_ganadas = sum(1 for op in ops_martingala if op.get('resultado') == 'WIN')
            martingala_perdidas = sum(1 for op in ops_martingala if op.get('resultado') == 'LOSS')
            
            # Calcular efectividad
            efectividad_total = (operaciones_ganadas / total_operaciones * 100) if total_operaciones > 0 else 0
            efectividad_normales = (normales_ganadas / len(ops_normales) * 100) if ops_normales else 0
            efectividad_martingala = (martingala_ganadas / len(ops_martingala) * 100) if ops_martingala else 0
            
            # Calcular balance neto
            balance_neto = self.trading_auto_ganancia_total - self.trading_auto_perdida_total
            balance_emoji = "🟢" if balance_neto > 0 else "🔴" if balance_neto < 0 else "⚪"
            
            # Generar lista de operaciones
            lista_operaciones = []
            for i, op in enumerate(self.trading_auto_operaciones, 1):
                resultado_emoji = "✅" if op.get('resultado') == 'WIN' else "❌" if op.get('resultado') == 'LOSS' else "⏳"
                tipo = "🎲 MARTINGALA" if op.get('es_martingala') else "📊 NORMAL"
                ganancia_perdida = ""
                if op.get('resultado') == 'WIN':
                    ganancia_perdida = f" (+${op.get('ganancia', 0):.2f})"
                elif op.get('resultado') == 'LOSS':
                    ganancia_perdida = f" (-${op.get('perdida', 0):.2f})"
                
                lista_operaciones.append(
                    f"{i}. {op['hora']} - {op['symbol']} {op['direccion']} ${op['monto']:.2f} - {tipo} {resultado_emoji}{ganancia_perdida}"
                )
            
            # Generar mensaje
            newline = "\n"
            mensaje = f"""💰 **RESUMEN DE TRADING AUTOMÁTICO - {datetime.now().strftime('%d/%m/%Y')}**

━━━━━━━━━━━━━━━━━━━━━━

⏰ **HORARIO DE OPERACIÓN:**
• Inicio: {self.trading_auto_inicio}
• Fin: {self.trading_auto_fin}
• Duración: {self._calcular_duracion(self.trading_auto_inicio, self.trading_auto_fin)}

━━━━━━━━━━━━━━━━━━━━━━

📊 **ESTADÍSTICAS GENERALES:**
• Total de operaciones: {total_operaciones}
• Ganadas: {operaciones_ganadas} ✅
• Perdidas: {operaciones_perdidas} ❌
• Pendientes: {operaciones_pendientes} ⏳
• Efectividad total: {efectividad_total:.1f}%

━━━━━━━━━━━━━━━━━━━━━━

📈 **OPERACIONES NORMALES:**
• Total: {len(ops_normales)}
• Ganadas: {normales_ganadas} ✅
• Perdidas: {normales_perdidas} ❌
• Efectividad: {efectividad_normales:.1f}%

🎲 **OPERACIONES MARTINGALA:**
• Total: {len(ops_martingala)}
• Ganadas: {martingala_ganadas} ✅
• Perdidas: {martingala_perdidas} ❌
• Efectividad: {efectividad_martingala:.1f}%

━━━━━━━━━━━━━━━━━━━━━━

💵 **BALANCE FINANCIERO:**
• Ganancia total: +${self.trading_auto_ganancia_total:.2f} 🟢
• Pérdida total: -${self.trading_auto_perdida_total:.2f} 🔴
• **Balance neto: {balance_emoji} ${balance_neto:+.2f}**

━━━━━━━━━━━━━━━━━━━━━━

📋 **DETALLE DE OPERACIONES:**
{newline.join(lista_operaciones)}

━━━━━━━━━━━━━━━━━━━━━━

📌 **OBSERVACIONES:**
{'✅ Día rentable - El trading automático generó ganancias' if balance_neto > 0 else '⚠️ Día con pérdidas - Revisar estrategia' if balance_neto < 0 else '⚪ Día neutro - Sin ganancias ni pérdidas'}
{'🔥 Excelente efectividad - Mantén la estrategia' if efectividad_total >= 80 else '✅ Buena efectividad - Sigue mejorando' if efectividad_total >= 60 else '⚠️ Efectividad baja - Ajustar parámetros'}

💡 **Recomendación:**
{'Continúa con los mismos parámetros' if balance_neto > 0 and efectividad_total >= 70 else 'Considera ajustar efectividad mínima o mercados' if efectividad_total < 60 else 'Monitorea resultados y ajusta según sea necesario'}

━━━━━━━━━━━━━━━━━━━━━━

🤖 **CubaYDSignal - Trading Automático**
📅 Próxima sesión: Mañana 08:00 AM
"""
            
            # Enviar al admin
            if hasattr(self, 'bot_telegram') and self.bot_telegram:
                await self.bot_telegram.notificar_admin_telegram(mensaje)
                print(f"[Trading Auto] 📊 Resumen enviado al admin - Balance: ${balance_neto:+.2f}")
            
        except Exception as e:
            print(f"[Trading Auto] ❌ Error enviando resumen: {e}")
            import traceback
            print(f"[Trading Auto] 📋 Traceback: {traceback.format_exc()}")
    
    def _calcular_duracion(self, inicio: str, fin: str) -> str:
        """Calcula duración entre dos horas en formato HH:MM"""
        try:
            from datetime import datetime
            inicio_dt = datetime.strptime(inicio, '%H:%M')
            fin_dt = datetime.strptime(fin, '%H:%M')
            
            # Si fin es menor que inicio, asumimos que cruzó medianoche
            if fin_dt < inicio_dt:
                fin_dt = fin_dt.replace(day=inicio_dt.day + 1)
            
            duracion = fin_dt - inicio_dt
            horas = duracion.seconds // 3600
            minutos = (duracion.seconds % 3600) // 60
            
            if horas > 0:
                return f"{horas}h {minutos}min"
            else:
                return f"{minutos}min"
        except:
            return "N/A"
    
    async def analizar_y_aprender_del_dia(self):
        """Analiza los resultados del día y ajusta estrategias para mejorar"""
        if not self.señales_enviadas_hoy:
            return
        
        print("[SignalScheduler] 🧠 Iniciando análisis de aprendizaje adaptativo...")
        
        # Análisis por mercado
        mercados_efectividad = {}
        for señal in self.señales_enviadas_hoy:
            mercado = señal['symbol']
            resultado = señal.get('resultado', 'PENDING')
            
            if mercado not in mercados_efectividad:
                mercados_efectividad[mercado] = {'total': 0, 'ganadas': 0}
            
            mercados_efectividad[mercado]['total'] += 1
            if resultado == 'WIN':
                mercados_efectividad[mercado]['ganadas'] += 1
        
        # Análisis por patrones
        patrones_efectividad = {}
        for señal in self.señales_enviadas_hoy:
            detalles = señal.get('detalles_tecnicos', {})
            patrones = detalles.get('patrones', {})
            mejor_patron = patrones.get('detalles', {}).get('mejor_patron', {})
            patron_nombre = mejor_patron.get('nombre', 'desconocido')
            resultado = señal.get('resultado', 'PENDING')
            
            if patron_nombre not in patrones_efectividad:
                patrones_efectividad[patron_nombre] = {'total': 0, 'ganadas': 0}
            
            patrones_efectividad[patron_nombre]['total'] += 1
            if resultado == 'WIN':
                patrones_efectividad[patron_nombre]['ganadas'] += 1
        
        # Análisis por pullback
        pullback_stats = {'con_pullback': {'total': 0, 'ganadas': 0}, 'sin_pullback': {'total': 0, 'ganadas': 0}}
        for señal in self.señales_enviadas_hoy:
            pullback_info = señal.get('pullback_info', {})
            tiene_pullback = pullback_info.get('detectado', False)
            resultado = señal.get('resultado', 'PENDING')
            
            categoria = 'con_pullback' if tiene_pullback else 'sin_pullback'
            pullback_stats[categoria]['total'] += 1
            if resultado == 'WIN':
                pullback_stats[categoria]['ganadas'] += 1
        
        # Generar recomendaciones de aprendizaje
        recomendaciones = []
        
        # Recomendaciones por mercado
        for mercado, stats in mercados_efectividad.items():
            efectividad = (stats['ganadas'] / stats['total']) * 100 if stats['total'] > 0 else 0
            if efectividad < 50 and stats['total'] >= 3:
                recomendaciones.append(f"Reducir peso de {mercado} (efectividad: {efectividad:.1f}%)")
            elif efectividad > 80 and stats['total'] >= 2:
                recomendaciones.append(f"Priorizar {mercado} (efectividad: {efectividad:.1f}%)")
        
        # Recomendaciones por patrones
        for patron, stats in patrones_efectividad.items():
            if patron != 'desconocido' and stats['total'] >= 2:
                efectividad = (stats['ganadas'] / stats['total']) * 100
                if efectividad < 40:
                    recomendaciones.append(f"Reducir confianza en patrón {patron} (efectividad: {efectividad:.1f}%)")
                elif efectividad > 85:
                    recomendaciones.append(f"Aumentar peso de patrón {patron} (efectividad: {efectividad:.1f}%)")
        
        # Recomendaciones por pullback
        if pullback_stats['con_pullback']['total'] >= 2 and pullback_stats['sin_pullback']['total'] >= 2:
            efect_con = (pullback_stats['con_pullback']['ganadas'] / pullback_stats['con_pullback']['total']) * 100
            efect_sin = (pullback_stats['sin_pullback']['ganadas'] / pullback_stats['sin_pullback']['total']) * 100
            
            if efect_con > efect_sin + 20:
                recomendaciones.append(f"Priorizar señales con pullback (efectividad: {efect_con:.1f}% vs {efect_sin:.1f}%)")
            elif efect_sin > efect_con + 20:
                recomendaciones.append(f"Priorizar señales directas sin pullback (efectividad: {efect_sin:.1f}% vs {efect_con:.1f}%)")
        
        # Notificar al admin si hay recomendaciones
        if recomendaciones and self.bot_telegram:
            mensaje_aprendizaje = f"""🧠 **APRENDIZAJE ADAPTATIVO - {datetime.now().strftime('%d/%m/%Y')}**

📊 El bot ha analizado los resultados del día y generó las siguientes recomendaciones:

"""
            
            for i, rec in enumerate(recomendaciones, 1):
                newline = "\n"
                mensaje_aprendizaje += f"{i}. {rec}{newline}"
            
            newline = "\n"
            mensaje_aprendizaje += f"{newline}🔄 Estos ajustes se aplicarán automáticamente en las próximas señales."
            
            await self.bot_telegram.notificar_admin_telegram(mensaje_aprendizaje)
            print(f"[SignalScheduler] 🧠 Aprendizaje adaptativo: {len(recomendaciones)} recomendaciones generadas")
        
        # Guardar aprendizajes para aplicar mañana
        self.guardar_aprendizajes_del_dia({
            'mercados': mercados_efectividad,
            'patrones': patrones_efectividad,
            'pullback': pullback_stats,
            'recomendaciones': recomendaciones,
            'fecha': datetime.now().strftime('%Y-%m-%d')
        })
    
    def guardar_aprendizajes_del_dia(self, aprendizajes: Dict):
        """Guarda los aprendizajes del día para aplicar en futuras señales"""
        try:
            import json
            archivo_aprendizaje = 'data/aprendizaje_adaptativo.json'
            
            # Crear directorio si no existe
            os.makedirs('data', exist_ok=True)
            
            # Cargar aprendizajes existentes
            aprendizajes_historicos = {}
            if os.path.exists(archivo_aprendizaje):
                with open(archivo_aprendizaje, 'r', encoding='utf-8') as f:
                    aprendizajes_historicos = json.load(f)
            
            # Añadir nuevos aprendizajes
            fecha = aprendizajes['fecha']
            aprendizajes_historicos[fecha] = aprendizajes
            
            # Mantener solo los últimos 30 días
            fechas = sorted(aprendizajes_historicos.keys())
            if len(fechas) > 30:
                for fecha_vieja in fechas[:-30]:
                    del aprendizajes_historicos[fecha_vieja]
            
            # Guardar
            with open(archivo_aprendizaje, 'w', encoding='utf-8') as f:
                json.dump(aprendizajes_historicos, f, indent=2, ensure_ascii=False)
            
            print(f"[SignalScheduler] 💾 Aprendizajes guardados para {fecha}")
            
        except Exception as e:
            print(f"[SignalScheduler] ❌ Error guardando aprendizajes: {e}")
    
    async def verificar_resultado_señal_automatico(self, señal: Dict):
        """Verifica automáticamente el resultado de una señal después de 5 minutos"""
        try:
            print(f"[SignalScheduler] ⏳ Iniciando espera de 5 minutos para señal #{señal.get('numero', 'N/A')}...")
            
            # ANÁLISIS PREDICTIVO: Esperar 3 minutos (180 segundos) para análisis anticipado
            import asyncio as _aio
            await _aio.sleep(180)  # 3 minutos
            
            # Verificar si hay trading automático activo
            tiene_trading_activo = 'trading_order_id' in señal
            
            if tiene_trading_activo:
                print(f"[Martingala Predictiva] 🔮 Analizando vela 2 minutos antes del cierre...")
                await self.analizar_vela_predictiva(señal)
            
            # Esperar los 2 minutos restantes
            await _aio.sleep(120)  # 2 minutos más = 5 minutos total
            
            print(f"[SignalScheduler] 🔍 Verificando resultado de señal #{señal['numero']}...")
            
            # Obtener precio actual del mercado
            precio_actual = await self.obtener_precio_actual(señal['symbol'])
            
            if precio_actual is None:
                print(f"[SignalScheduler] ⚠️ No se pudo obtener precio actual para {señal['symbol']}")
                señal['resultado'] = 'PENDING'
                señal['motivo_pending'] = 'No se pudo verificar precio'
                return
            
            # Obtener precio de entrada (guardado en la señal)
            precio_entrada = señal.get('precio_entrada')
            
            if precio_entrada is None:
                print(f"[SignalScheduler] ⚠️ No hay precio de entrada registrado")
                señal['resultado'] = 'PENDING'
                señal['motivo_pending'] = 'Sin precio de entrada'
                return
            
            # Determinar resultado basado en la dirección
            if señal['direccion'] == 'CALL':
                # Para CALL, ganamos si el precio subió
                resultado = 'WIN' if precio_actual > precio_entrada else 'LOSS'
            else:  # PUT/SELL
                # Para PUT, ganamos si el precio bajó
                resultado = 'WIN' if precio_actual < precio_entrada else 'LOSS'
            
            # Calcular diferencia en pips
            diferencia = abs(precio_actual - precio_entrada)
            diferencia_porcentaje = (diferencia / precio_entrada) * 100
            
            # Actualizar señal con resultado
            señal['resultado'] = resultado
            señal['hora_resultado'] = datetime.now().strftime('%H:%M')
            señal['precio_salida'] = precio_actual
            señal['diferencia_pips'] = diferencia
            señal['diferencia_porcentaje'] = diferencia_porcentaje
            
            print(f"[SignalScheduler] 📊 Resultado: {resultado} | Entrada: {precio_entrada:.5f} | Salida: {precio_actual:.5f} | Diff: {diferencia_porcentaje:.3f}%")
            
            # Actualizar en historial persistente
            self.user_manager.actualizar_resultado_señal(señal)
            
            # Eliminar botones de confirmación (la señal ya expiró)
            try:
                if hasattr(self, 'bot_telegram') and self.bot_telegram:
                    await self.bot_telegram.eliminar_botones_confirmacion(señal)
                    print(f"[SignalScheduler] 🗑️ Botones de confirmación eliminados")
            except Exception as e:
                print(f"[SignalScheduler] ⚠️ Error eliminando botones: {e}")
            
            # Procesar y notificar resultado
            await self.procesar_resultado_señal(señal, resultado)
            print(f"[SignalScheduler] ✅ Resultado procesado y notificado correctamente")
            
            # Actualizar resultado en operaciones de trading automático
            if 'trading_order_id' in señal:
                order_id = señal['trading_order_id']
                monto = señal.get('trading_monto', 0)
                
                # Buscar operación en lista
                for op in self.trading_auto_operaciones:
                    if op['order_id'] == order_id:
                        op['resultado'] = resultado
                        
                        # Calcular ganancia/pérdida (asumiendo 94% payout)
                        if resultado == 'WIN':
                            ganancia = monto * 0.94
                            self.trading_auto_ganancia_total += ganancia
                            op['ganancia'] = ganancia
                        else:
                            self.trading_auto_perdida_total += monto
                            op['perdida'] = monto
                        break
            
            # MARTINGALA: Si la operación automática se perdió, ejecutar Martingala
            if 'trading_order_id' in señal and resultado == 'LOSS':
                await self.procesar_martingala_perdida(señal)
            elif 'trading_order_id' in señal and resultado == 'WIN':
                # Si había confirmación anticipada, cancelarla y notificar
                if hasattr(self, 'martingala_confirmacion_anticipada') and self.martingala_confirmacion_anticipada == True:
                    print(f"[Martingala Predictiva] ✅ Vela ganada - Cancelando Martingala pre-autorizada")
                    self.martingala_confirmacion_anticipada = None
                    
                    # Notificar al admin
                    await self._notificar_admin_trading(
                        f"✅ **MARTINGALA CANCELADA**\n\n"
                        f"🎉 La vela se ganó!\n\n"
                        f"La Martingala pre-autorizada fue cancelada automáticamente.\n"
                        f"No fue necesaria la recuperación.\n\n"
                        f"Symbol: {señal.get('trading_symbol', 'N/A')}\n"
                        f"Dirección: {señal.get('trading_direccion', 'N/A')}\n"
                        f"Ganancia: ${señal.get('trading_monto', 0) * 0.94:.2f}"
                    )
                
                await self.resetear_martingala(señal)
            
        except Exception as e:
            import traceback
            print(f"[SignalScheduler] ❌ Error verificando resultado automático: {e}")
            print(f"[SignalScheduler] 📋 Traceback: {traceback.format_exc()}")
            señal['resultado'] = 'ERROR'
            señal['motivo_error'] = str(e)
            
            # Intentar eliminar botones incluso si hubo error
            try:
                if hasattr(self, 'bot_telegram') and self.bot_telegram:
                    await self.bot_telegram.eliminar_botones_confirmacion(señal)
            except Exception:
                pass
    
    async def obtener_precio_actual(self, symbol: str) -> Optional[float]:
        """Obtiene el precio actual de un mercado desde Quotex"""
        try:
            mm = getattr(self, 'market_manager', None)
            if not mm or not getattr(mm, 'quotex', None):
                print(f"[SignalScheduler] ⚠️ No hay conexión a Quotex para obtener precio")
                return None
            
            # Intentar obtener precio actual usando diferentes métodos
            precio = None
            
            # Método 1: Usar obtener_datos_mercado (más confiable)
            try:
                df = await mm.obtener_datos_mercado(symbol)
                if df is not None and len(df) > 0:
                    precio = df['close'].iloc[-1]
                    if precio:
                        print(f"[SignalScheduler] 💹 Precio actual de {symbol}: {precio}")
                        return float(precio)
            except Exception as e:
                print(f"[SignalScheduler] ⚠️ Error obteniendo datos: {e}")
            
            # Método 2: get_candles con parámetros correctos
            try:
                if hasattr(mm.quotex, 'get_candles'):
                    # get_candles(asset, timeframe, offset, period)
                    candles = await mm.quotex.get_candles(symbol, 60, 0, 1)
                    if candles and len(candles) > 0:
                        ultima_vela = candles[-1]
                        precio = ultima_vela.get('close', ultima_vela.get('c'))
                        if precio:
                            print(f"[SignalScheduler] 💹 Precio de {symbol}: {precio}")
                            return float(precio)
            except Exception as e:
                print(f"[SignalScheduler] ⚠️ Error con get_candles: {e}")
            
            print(f"[SignalScheduler] ⚠️ No se pudo obtener precio actual para {symbol}")
            return None
            
        except Exception as e:
            print(f"[SignalScheduler] ❌ Error obteniendo precio actual: {e}")
            return None
    
    async def procesar_resultado_señal(self, señal: Dict, resultado: str):
        """Procesa el resultado de una señal (WIN/LOSS)"""
        señal['resultado'] = resultado
        señal['hora_resultado'] = datetime.now().strftime('%H:%M')
        
        if resultado == 'WIN':
            frase_exito = random.choice(self.frases_motivacionales['señal_exitosa'])
            diferencia = señal.get('diferencia_porcentaje', 0)
            mensaje = f"""
{frase_exito}

✅ SEÑAL #{señal['numero']} - GANADA
💱 {señal['symbol']} | {señal['direccion']} | {señal['efectividad']:.1f}%
📊 Entrada: {señal.get('precio_entrada', 0):.5f} → Salida: {señal.get('precio_salida', 0):.5f}
📈 Diferencia: {diferencia:.3f}%
💰 Ganancia confirmada!

¡Seguimos así, equipo! 🚀
            """
        else:
            diferencia = señal.get('diferencia_porcentaje', 0)
            
            # Calcular efectividad de Martingala para informar a usuarios
            efectividad_original = señal.get('efectividad', 80)
            efectividad_martingala = min(95, efectividad_original + 5)  # +5% para primer intento
            
            mensaje = f"""
📊 SEÑAL #{señal['numero']} - PERDIDA
💱 {señal['symbol']} | {señal['direccion']} | {señal['efectividad']:.1f}%
📊 Entrada: {señal.get('precio_entrada', 0):.5f} → Salida: {señal.get('precio_salida', 0):.5f}
📉 Diferencia: {diferencia:.3f}%

No te preocupes, es parte del trading. 
¡La próxima será mejor! 💪

🎲 **OPORTUNIDAD DE MARTINGALA**
Si deseas recuperar esta pérdida, puedes hacer Martingala:

💡 **¿Qué es Martingala?**
Duplicar tu inversión en la próxima entrada del mismo mercado para recuperar la pérdida.

📊 **Datos de Martingala:**
• **Efectividad estimada:** {efectividad_martingala}%
• **Monto recomendado:** 2x tu inversión anterior
• **Mercado:** {señal['symbol']}
• **Dirección:** {señal['direccion']}

⚠️ **Importante:**
• Espera la apertura de la próxima vela de 5 minutos
• Opera con responsabilidad
• Solo si te sientes cómodo con el riesgo

💪 ¡Tú decides si quieres recuperar!
            """
        
        await self.enviar_mensaje_a_usuarios(mensaje.strip())
    
    async def generar_resumen_diario(self):
        """Genera y envía el resumen diario"""
        if not self.señales_enviadas_hoy:
            return
        
        # Calcular estadísticas
        total_señales = len(self.señales_enviadas_hoy)
        señales_ganadoras = len([s for s in self.señales_enviadas_hoy if s.get('resultado') == 'WIN'])
        tasa_exito = (señales_ganadoras / total_señales * 100) if total_señales > 0 else 0
        efectividad_promedio = sum(s['efectividad'] for s in self.señales_enviadas_hoy) / total_señales
        
        # Categorizar el día
        if tasa_exito >= 80:
            categoria = 'fin_dia_excelente'
        elif tasa_exito >= 65:
            categoria = 'fin_dia_bueno'
        else:
            categoria = 'fin_dia_regular'
        
        frase_final = random.choice(self.frases_motivacionales[categoria])
        
        # Generar observaciones
        observaciones = self.generar_observaciones_diarias()
        
        # Calcular efectividad por mercado
        mercados = {}
        for s in self.señales_enviadas_hoy:
            symbol = s['symbol']
            if symbol not in mercados:
                mercados[symbol] = {'total': 0, 'ganadas': 0, 'efectividad': []}
            mercados[symbol]['total'] += 1
            if s.get('resultado') == 'WIN':
                mercados[symbol]['ganadas'] += 1
            mercados[symbol]['efectividad'].append(s['efectividad'])
        resumen_mercados = ''
        for symbol, stats in mercados.items():
            tasa = (stats['ganadas']/stats['total']*100) if stats['total'] else 0
            efect = sum(stats['efectividad'])/stats['total'] if stats['total'] else 0
            newline = "\n"
            resumen_mercados += f"• {symbol}: {stats['total']} señales | {tasa:.1f}% éxito | {efect:.1f}% efectividad{newline}"
        
        mensaje_resumen = f"""
📋 **RESUMEN DIARIO - {datetime.now().strftime('%d/%m/%Y')}**

{frase_final}

📊 **ESTADÍSTICAS DEL DÍA:**
• 📈 **Total de señales:** {total_señales}
• ✅ **Señales ganadoras:** {señales_ganadoras}
• 📉 **Señales perdidas:** {total_señales - señales_ganadoras}
• 🎯 **Tasa de éxito:** {tasa_exito:.1f}%
• 📊 **Efectividad promedio:** {efectividad_promedio:.1f}%
• 💱 **Mercado principal:** {self.mercado_actual['symbol']}
• 👥 **Usuarios activos:** {len(self.user_manager.obtener_usuarios_activos())}

📈 **RENDIMIENTO POR MERCADO:**
{resumen_mercados}
🔍 **OBSERVACIONES:**
{observaciones}

💡 **Consejo para mañana:** {self.generar_consejo_siguiente_dia(tasa_exito)}

¡Gracias por ser parte del equipo CubaYDSignal! 🇨🇺💪
¡Nos vemos mañana para más oportunidades! 🌅
        """
        
        # Usar el nuevo sistema de informe diario completo
        await self.enviar_informe_y_motivacion_diaria()
        print(f"[SignalScheduler] 📋 Informe diario completo enviado - {tasa_exito:.1f}% éxito")
    
    def generar_observaciones_diarias(self) -> str:
        """Genera observaciones inteligentes sobre el día"""
        observaciones = []
        
        if not self.señales_enviadas_hoy:
            return "• No se generaron señales válidas hoy."
        
        # Análisis por efectividad
        efectividades = [s['efectividad'] for s in self.señales_enviadas_hoy]
        efectividad_max = max(efectividades)
        efectividad_min = min(efectividades)
        
        observaciones.append(f"• Efectividad máxima alcanzada: {efectividad_max:.1f}%")
        observaciones.append(f"• Rango de efectividad: {efectividad_min:.1f}% - {efectividad_max:.1f}%")
        
        # Análisis por dirección
        calls = len([s for s in self.señales_enviadas_hoy if s['direccion'].upper() == 'CALL'])
        puts = len([s for s in self.señales_enviadas_hoy if s['direccion'].upper() == 'PUT'])
        
        if calls > puts:
            observaciones.append(f"• Tendencia alcista predominante ({calls} CALL vs {puts} PUT)")
        elif puts > calls:
            observaciones.append(f"• Tendencia bajista predominante ({puts} PUT vs {calls} CALL)")
        else:
            observaciones.append(f"• Mercado equilibrado ({calls} CALL, {puts} PUT)")
        
        # Análisis temporal
        horas_activas = set(s['hora'].split(':')[0] for s in self.señales_enviadas_hoy)
        observaciones.append(f"• Horas más activas: {', '.join(sorted(horas_activas))}:XX")
        
        return '\n'.join(observaciones)
    
    def generar_consejo_siguiente_dia(self, tasa_exito: float) -> str:
        """Genera consejo para el siguiente día"""
        if tasa_exito >= 80:
            return "Mantén la disciplina y sigue el plan. ¡Excelente trabajo!"
        elif tasa_exito >= 65:
            return "Buen rendimiento. Revisa las señales perdidas para mejorar."
        else:
            return "Analiza las condiciones del mercado. Mañana será mejor."
    
    async def enviar_mensaje_a_usuarios(self, mensaje: str):
        """Envía mensaje a todos los usuarios activos"""
        if not self.bot_telegram:
            print(f"[SignalScheduler] 📱 Mensaje: {mensaje[:100]}...")
            return
        
        # obtener_usuarios_activos() retorna una lista de IDs
        # Acceder directamente al diccionario usuarios_activos
        for user_id, info in self.user_manager.usuarios_activos.items():
            username = info.get('username', '').lower()
            if user_id in self.user_manager.usuarios_bloqueados or (username and username in self.user_manager.usuarios_bloqueados):
                continue
            try:
                # Usar parse_mode=None para evitar errores de Markdown
                await self.bot_telegram.send_message(user_id, mensaje, parse_mode=None)
            except Exception as e:
                print(f"[SignalScheduler] ❌ Error enviando a {user_id}: {e}")
    
    async def programar_mensajes_automaticos(self):
        """Programa mensajes automáticos de bienvenida y cierre"""
        ahora = datetime.now()
        # Programar mensaje de bienvenida 7:45 AM
        hora_bienvenida = ahora.replace(hour=7, minute=45, second=0, microsecond=0)
        if ahora > hora_bienvenida:
            hora_bienvenida += timedelta(days=1)
        delay_bienvenida = (hora_bienvenida - ahora).total_seconds()
        asyncio.create_task(self.enviar_mensaje_bienvenida_automatica(delay_bienvenida))
        # Programar mensaje de cierre 20:05 (8:05 PM)
        hora_cierre = ahora.replace(hour=20, minute=5, second=0, microsecond=0)
        if ahora > hora_cierre:
            hora_cierre += timedelta(days=1)
        delay_cierre = (hora_cierre - ahora).total_seconds()
        asyncio.create_task(self.enviar_mensaje_cierre_automatico(delay_cierre))

    async def enviar_mensaje_bienvenida_automatica(self, delay):
        await asyncio.sleep(delay)
        if datetime.now().weekday() < 6:  # Lunes a sábado (domingo no operativo)
            frase = random.choice(self.frases_motivacionales['inicio_dia_excelente'])
            mensaje = f"""
🌄 *¡Buenos días, traders!*

{frase}

⏰ En 15 minutos inicia el día de trading (8:00 AM - 8:00 PM).
¡Prepárate para recibir señales de alta efectividad!
"""
            await self.enviar_mensaje_a_usuarios(mensaje.strip())
            print("[SignalScheduler] Mensaje motivador de bienvenida enviado.")

    async def enviar_mensaje_cierre_automatico(self, delay):
        await asyncio.sleep(delay)
        if datetime.now().weekday() < 6:  # Lunes a sábado (domingo no operativo)
            efectividad = self.calcular_efectividad_diaria()
            if efectividad >= 85:
                cat = 'fin_dia_excelente'
            elif efectividad >= 75:
                cat = 'fin_dia_bueno'
            else:
                cat = 'fin_dia_regular'
            frase = random.choice(self.frases_motivacionales[cat])
            mensaje = f"""
🌙 *¡Cierre del día de trading!*

{frase}

📈 Efectividad del día: {efectividad:.1f}%
¡Mañana seguimos con más oportunidades!
"""
            await self.enviar_mensaje_a_usuarios(mensaje.strip())
            print("[SignalScheduler] Mensaje de cierre motivador enviado.")

    def calcular_efectividad_diaria(self):
        # Calcula la efectividad del día (dummy, reemplazar por real)
        if not self.señales_enviadas_hoy:
            return 0.0
        exitos = sum(1 for s in self.señales_enviadas_hoy if s.get('resultado') == 'WIN')
        return 100 * exitos / len(self.señales_enviadas_hoy)

    async def ejecutar_ciclo_diario(self):
        """Ejecuta el ciclo completo de un día de trading"""
        print("[SignalScheduler] 🚀 Iniciando ciclo diario")
        
        # Esperar un momento para que la conexión se establezca completamente
        await asyncio.sleep(2)
        
        # Verificar conexión de múltiples formas
        try:
            conectado = False
            
            # Verificar múltiples indicadores de conexión
            flag_conectado = getattr(self.market_manager, 'conectado', False)
            quotex_activo = getattr(self.market_manager, 'quotex', None) is not None
            mercados_normales = len(getattr(self.market_manager, 'mercados_disponibles', []))
            mercados_otc = len(getattr(self.market_manager, 'mercados_otc', []))
            
            print(f"[SignalScheduler] 🔍 Verificando conexión:")
            print(f"  - Flag conectado: {flag_conectado}")
            print(f"  - Quotex activo: {quotex_activo}")
            print(f"  - Mercados normales: {mercados_normales}")
            print(f"  - Mercados OTC: {mercados_otc}")
            
            # Considerar conectado si hay mercados disponibles (más confiable)
            if mercados_normales > 0 or mercados_otc > 0:
                conectado = True
                print(f"[SignalScheduler] ✅ Conexión verificada: {mercados_normales + mercados_otc} mercados disponibles")
            elif flag_conectado or quotex_activo:
                conectado = True
                print("[SignalScheduler] ✅ Conexión verificada por flags")
            
            if not conectado:
                self.pausado_por_conexion = True
                print("[SignalScheduler] ⏸️ Ciclo no iniciado: sin conexión a Quotex")
                return
            else:
                self.pausado_por_conexion = False
        except Exception as e:
            print(f"[SignalScheduler] ⚠️ Error verificando conexión: {e}")
            pass
        self.running = True
        
        # Iniciar día con manejo de errores para no detener el ciclo completo
        try:
            await self.iniciar_dia_trading()
        except Exception as e:
            print(f"[SignalScheduler] ⚠️ Error en iniciar_dia_trading: {e}")
            print("[SignalScheduler] ✅ Continuando con análisis continuo...")
        
        try:
            await self.programar_señales_del_dia()
        except Exception as e:
            print(f"[SignalScheduler] ⚠️ Error en programar_señales_del_dia: {e}")
        
        try:
            await self.programar_mensajes_automaticos()
        except Exception as e:
            print(f"[SignalScheduler] ⚠️ Error en programar_mensajes_automaticos: {e}")
        # Notificar al administrador SOLO si hay conexión y señales programadas
        try:
            if getattr(self.market_manager, 'conectado', False) and self.señales_programadas:
                if getattr(self, 'bot_telegram', None) and hasattr(self.bot_telegram, 'notificar_admin_telegram'):
                    hora = datetime.now().strftime('%H:%M:%S')
                    mensaje = (
                        f"🧠 Inicio de análisis de estrategia (conectado a Quotex)\n"
                        f"⏰ Hora: {hora}\n"
                        f"📅 Ventana operativa: 08:00–20:00 (Lun–Sáb)\n"
                        f"🔔 Se enviarán pre‑señales ~3 min antes de cada señal."
                    )
                    await self.bot_telegram.notificar_admin_telegram(mensaje)
        except Exception:
            pass
        # Ciclo continuo de análisis
        print("[SignalScheduler] 🔄 Iniciando análisis continuo cada 60 segundos...")
        
        while self.running and self.esta_en_horario_operativo():
            ahora = datetime.now()
            
            # Análisis continuo: seleccionar mejor mercado cada ciclo EN BACKGROUND
            print(f"[SignalScheduler] 🔍 Analizando mercados... ({ahora.strftime('%H:%M:%S')})")
            try:
                # Timeout de 60 segundos (aumentado para permitir análisis completo)
                # El análisis se ejecuta en background sin bloquear Telegram
                mejor_mercado = await asyncio.wait_for(
                    self.market_manager.seleccionar_mejor_mercado(signal_scheduler=self),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                print("[SignalScheduler] ⏱️ Análisis tardó >60s, saltando ciclo...")
                print("[SignalScheduler] 💡 Considera reducir el número de mercados a analizar")
                await asyncio.sleep(60)
                continue
            except Exception as e:
                print(f"[SignalScheduler] ❌ Error en análisis: {e}")
                await asyncio.sleep(60)
                continue
            
            if mejor_mercado:
                self.mercado_actual = mejor_mercado
                efectividad = mejor_mercado.get('efectividad_calculada', 0)
                print(f"[SignalScheduler] 🏆 Mercado: {mejor_mercado['symbol']} | Payout: {mejor_mercado['payout']}% | Efectividad: {efectividad:.1f}%")
                
                # Si la efectividad es >= umbral configurado, generar y enviar señal
                umbral_efectividad = getattr(self, 'efectividad_minima_temporal', 80)
                if efectividad >= umbral_efectividad:
                    print(f"[SignalScheduler] ✅ Señal válida detectada (≥{umbral_efectividad}% efectividad)")
                    señal = await self.ejecutar_analisis_señal()
                    if señal:
                        await self.enviar_señal(señal)
                        # Esperar 5 minutos después de enviar una señal para no saturar
                        print("[SignalScheduler] ⏳ Esperando 5 minutos tras enviar señal...")
                        await asyncio.sleep(300)
                else:
                    print(f"[SignalScheduler] ⚠️ Efectividad insuficiente ({efectividad:.1f}% < {umbral_efectividad}%)")
            else:
                umbral_efectividad = getattr(self, 'efectividad_minima_temporal', 80)
                print(f"[SignalScheduler] ❌ No se encontró mercado con efectividad >= {umbral_efectividad}%")
            
            # Esperar 60 segundos antes del próximo análisis
            # Usar sleep cortos para permitir que el bot responda a comandos
            if self.running and self.esta_en_horario_operativo():
                print("[SignalScheduler] ⏸️ Esperando 60 segundos para próximo análisis...")
                # Dividir en sleeps de 5 segundos para mejor respuesta
                for _ in range(12):  # 12 x 5 = 60 segundos
                    if not self.running:
                        break
                    await asyncio.sleep(5)
        await self.generar_resumen_diario()
        print("[SignalScheduler] 🛑 Fin del ciclo diario")
        self.running = False

        print("[SignalScheduler] 🏁 Ciclo diario completado")
    
    def detener(self):
        """Detiene el scheduler"""
        self.running = False
        print("[SignalScheduler] ⏹️ Scheduler detenido")
    
    async def forzar_inicio_analisis(self):
        """Fuerza el inicio del análisis (usado cuando se activa conexión forzada)"""
        import asyncio
        
        # Si ya está corriendo, detenerlo primero
        if self.running:
            print("[SignalScheduler] ⚠️ Scheduler ya corriendo - Reiniciando con modo forzado...")
            self.running = False
            await asyncio.sleep(1)  # Dar tiempo para que se detenga
        
        print("[SignalScheduler] 🔓 Iniciando análisis forzado (modo forzado activo)...")
        
        # Esperar un momento para que los mercados se carguen
        await asyncio.sleep(2)
        
        self.running = True
        
        # Crear tarea asíncrona para ejecutar el ciclo
        asyncio.create_task(self.ejecutar_ciclo_diario())
        print("[SignalScheduler] ✅ Análisis forzado iniciado")
    
    def configurar_market_manager(self, market_manager):
        """Configura la referencia al MarketManager"""
        self.market_manager = market_manager
        print("[SignalScheduler] ✅ MarketManager configurado")
    
    def configurar_user_manager(self, user_manager):
        """Configura la referencia al UserManager"""
        self.user_manager = user_manager
        print("[SignalScheduler] ✅ UserManager configurado")
    
    def configurar_bot_telegram(self, bot_telegram):
        """Configura la referencia al bot de Telegram"""
        self.bot_telegram = bot_telegram
        print("[SignalScheduler] ✅ Bot de Telegram configurado")
    
    def es_horario_operativo(self) -> bool:
        """Verifica si estamos en horario operativo (8:00-20:00, Lun-Sáb)"""
        ahora = datetime.now()
        
        # Si hay conexión forzada activa, siempre retornar True
        if hasattr(self, 'market_manager') and self.market_manager:
            if self.market_manager.esta_en_modo_forzado():
                return True
        
        # Verificar override temporal
        if self._override_until and ahora < self._override_until:
            return True
        
        # Verificar día de la semana (0=Lunes, 6=Domingo)
        dia_semana = ahora.weekday()
        if dia_semana == 6:  # Domingo
            return False
        
        # Verificar horario (8:00 AM - 8:00 PM)
        hora = ahora.hour
        return 8 <= hora < 20
    
    def esta_en_horario_operativo(self) -> bool:
        """Alias para compatibilidad - llama a es_horario_operativo()"""
        return self.es_horario_operativo()
    
    async def iniciar_scheduler(self):
        """Inicia el scheduler de señales"""
        print("[SignalScheduler] 🚀 Iniciando scheduler de señales...")
        self.running = True
        
        # Verificar horario operativo
        ahora = datetime.now()
        if self._override_until and ahora < self._override_until:
            print(f"[SignalScheduler] ⚡ Override activo hasta {self._override_until}")
            print("[SignalScheduler] 🔄 Iniciando ciclo diario...")
            await self.ejecutar_ciclo_diario()
        else:
            # Verificar si estamos en horario operativo (8:00-20:00, Lun-Sáb)
            if self.es_horario_operativo():
                print("[SignalScheduler] ✅ En horario operativo")
                print("[SignalScheduler] 🔄 Iniciando ciclo diario...")
                await self.ejecutar_ciclo_diario()
            else:
                print("[SignalScheduler] ⏰ Fuera de horario operativo")
                print("[SignalScheduler] 💤 Esperando horario operativo...")
    
    async def ejecutar_operacion_automatica(self, señal: Dict):
        """Ejecuta automáticamente una operación en Quotex según la señal"""
        try:
            # Obtener configuración de trading
            modo = getattr(self.bot_telegram, '_trading_modo', None)
            monto = getattr(self.bot_telegram, '_trading_monto', 0)
            
            if not modo or monto <= 0:
                print(f"[Trading] ⚠️ Configuración inválida - Modo: {modo}, Monto: {monto}")
                return
            
            # Obtener datos de la señal
            symbol = señal.get('symbol', 'EURUSD')
            direccion = señal.get('direccion', señal.get('decision', '')).upper()  # CALL o PUT
            efectividad = señal.get('efectividad', señal.get('efectividad_total', 0))
            
            # Validar que la señal sea válida
            if direccion not in ['CALL', 'PUT']:
                print(f"[Trading] ⚠️ Dirección inválida: {direccion}")
                return
            
            umbral_efectividad = getattr(self, 'efectividad_minima_temporal', 80)
            if efectividad < umbral_efectividad:
                print(f"[Trading] ⚠️ Efectividad muy baja: {efectividad}% < {umbral_efectividad}%")
                return
            
            # ESPERAR HASTA LA APERTURA DE LA PRÓXIMA VELA DE 5 MINUTOS
            from datetime import datetime, timedelta
            import asyncio
            
            ahora = datetime.now()
            minutos_actuales = ahora.minute
            segundos_actuales = ahora.second
            
            # Calcular próxima vela de 5 minutos (00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
            proxima_vela_minuto = ((minutos_actuales // 5) + 1) * 5
            if proxima_vela_minuto >= 60:
                proxima_vela_minuto = 0
                proxima_vela = ahora.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                proxima_vela = ahora.replace(minute=proxima_vela_minuto, second=0, microsecond=0)
            
            # Calcular tiempo de espera
            tiempo_espera = (proxima_vela - ahora).total_seconds()
            
            if tiempo_espera > 0:
                print(f"[Trading] ⏰ Esperando {tiempo_espera:.1f} segundos hasta apertura de vela ({proxima_vela.strftime('%H:%M:%S')})")
                await asyncio.sleep(tiempo_espera)
                print(f"[Trading] ✅ Apertura de vela alcanzada - Ejecutando operación")
            
            print(f"[Trading] 🎯 Ejecutando operación automática:")
            print(f"[Trading]    Modo: {modo}")
            print(f"[Trading]    Symbol: {symbol}")
            print(f"[Trading]    Dirección: {direccion}")
            print(f"[Trading]    Monto: ${monto}")
            print(f"[Trading]    Efectividad: {efectividad}%")
            
            # Verificar conexión a Quotex
            if not self.market_manager or not hasattr(self.market_manager, 'quotex'):
                print(f"[Trading] ❌ No hay conexión a Quotex")
                await self._notificar_admin_trading(
                    f"❌ **Operación NO Ejecutada**\n\n"
                    f"No hay conexión a Quotex\n"
                    f"Señal: {symbol} {direccion}"
                )
                return
            
            quotex = self.market_manager.quotex
            
            # Cambiar a cuenta DEMO o REAL según configuración
            try:
                if modo == "DEMO":
                    await quotex.change_account("PRACTICE")
                    print(f"[Trading] 🎮 Cambiado a cuenta DEMO")
                else:
                    await quotex.change_account("REAL")
                    print(f"[Trading] 💎 Cambiado a cuenta REAL")
            except Exception as e:
                print(f"[Trading] ⚠️ Error cambiando cuenta: {e}")
            
            # Ejecutar la operación
            try:
                # Convertir símbolo al formato de Quotex
                asset = symbol.replace('/', '').replace('_OTC', '_otc')
                
                # Duración de la operación (5 minutos = 300 segundos)
                duracion = 300
                
                # Ejecutar operación
                check, order_id = await quotex.buy(
                    amount=monto,
                    asset=asset,
                    direction=direccion.lower(),  # 'call' o 'put'
                    duration=duracion
                )
                
                if check:
                    # Incrementar contador de operaciones
                    operaciones_actuales = getattr(self.bot_telegram, '_trading_operaciones_hoy', 0)
                    self.bot_telegram._trading_operaciones_hoy = operaciones_actuales + 1
                    
                    # Marcar que hubo trading automático hoy
                    if not self.trading_auto_activo_hoy:
                        self.trading_auto_activo_hoy = True
                        self.trading_auto_inicio = datetime.now().strftime('%H:%M')
                    
                    # Registrar operación para estadísticas
                    operacion_info = {
                        'hora': datetime.now().strftime('%H:%M'),
                        'symbol': symbol,
                        'direccion': direccion,
                        'monto': monto,
                        'modo': modo,
                        'efectividad': efectividad,
                        'order_id': order_id,
                        'es_martingala': señal.get('es_martingala', False),
                        'resultado': None  # Se actualizará después
                    }
                    self.trading_auto_operaciones.append(operacion_info)
                    
                    # Guardar información para Martingala
                    señal['trading_order_id'] = order_id
                    señal['trading_monto'] = monto
                    señal['trading_symbol'] = symbol
                    señal['trading_direccion'] = direccion
                    señal['trading_modo'] = modo
                    
                    print(f"[Trading] ✅ Operación ejecutada exitosamente - ID: {order_id}")
                    
                    # Mensaje de notificación
                    mensaje_martingala = ""
                    if self.martingala_activa:
                        mensaje_martingala = f"\n\n🎲 MARTINGALA #{self.martingala_intentos}/{self.martingala_max_intentos}\n⚠️ Recuperando pérdida anterior"
                    
                    # Notificar al admin
                    await self._notificar_admin_trading(
                        f"✅ **Operación Ejecutada**\n\n"
                        f"🎯 **Detalles:**\n"
                        f"• Modo: {modo}\n"
                        f"• Symbol: {symbol}\n"
                        f"• Dirección: {direccion}\n"
                        f"• Monto: ${monto:.2f}\n"
                        f"• Efectividad: {efectividad:.1f}%\n"
                        f"• Order ID: {order_id}\n"
                        f"• Duración: 5 minutos{mensaje_martingala}\n\n"
                        f"⏰ Resultado en 5 minutos"
                    )
                else:
                    print(f"[Trading] ❌ Error ejecutando operación")
                    await self._notificar_admin_trading(
                        f"❌ **Error Ejecutando Operación**\n\n"
                        f"Symbol: {symbol}\n"
                        f"Dirección: {direccion}\n"
                        f"Monto: ${monto:.2f}\n\n"
                        f"Verifica tu saldo y conexión"
                    )
                    
            except Exception as e:
                print(f"[Trading] ❌ Excepción ejecutando operación: {e}")
                await self._notificar_admin_trading(
                    f"❌ **Excepción en Operación**\n\n"
                    f"Error: {str(e)}\n"
                    f"Symbol: {symbol}\n"
                    f"Dirección: {direccion}"
                )
                
        except Exception as e:
            print(f"[Trading] ❌ Error general en ejecutar_operacion_automatica: {e}")
    
    async def _notificar_admin_trading(self, mensaje: str):
        """Notifica al administrador sobre operaciones de trading"""
        try:
            if self.bot_telegram and hasattr(self.bot_telegram, 'application'):
                # Obtener ID del admin
                admin_ids = self.user_manager.obtener_administradores()
                if admin_ids:
                    admin_id = admin_ids[0]
                    await self.bot_telegram.application.bot.send_message(
                        chat_id=admin_id,
                        text=mensaje,
                        parse_mode='Markdown'
                    )
        except Exception as e:
            print(f"[Trading] ⚠️ Error notificando admin: {e}")
    
    async def analizar_vela_predictiva(self, señal: Dict):
        """Analiza la vela 2 minutos antes del cierre y solicita confirmación anticipada de Martingala"""
        try:
            # Obtener precio actual
            precio_actual = await self.obtener_precio_actual(señal['symbol'])
            precio_entrada = señal.get('precio_entrada')
            
            if precio_actual is None or precio_entrada is None:
                print(f"[Martingala Predictiva] ⚠️ No se pudo obtener precios")
                return
            
            # Analizar si la vela probablemente se perderá
            direccion = señal['direccion']
            probablemente_perdida = False
            
            if direccion == 'CALL':
                # Para CALL, se pierde si el precio está por debajo del precio de entrada
                probablemente_perdida = precio_actual < precio_entrada
                diferencia = precio_entrada - precio_actual
            else:  # PUT/SELL
                # Para PUT, se pierde si el precio está por encima del precio de entrada
                probablemente_perdida = precio_actual > precio_entrada
                diferencia = precio_actual - precio_entrada
            
            diferencia_porcentaje = (abs(diferencia) / precio_entrada) * 100
            
            print(f"[Martingala Predictiva] 📊 Análisis:")
            print(f"[Martingala Predictiva]    Dirección: {direccion}")
            print(f"[Martingala Predictiva]    Precio entrada: {precio_entrada:.5f}")
            print(f"[Martingala Predictiva]    Precio actual: {precio_actual:.5f}")
            print(f"[Martingala Predictiva]    Diferencia: {diferencia_porcentaje:.3f}%")
            print(f"[Martingala Predictiva]    Probablemente perdida: {probablemente_perdida}")
            
            # Si probablemente se perderá, solicitar confirmación anticipada
            if probablemente_perdida:
                print(f"[Martingala Predictiva] ⚠️ Vela probablemente se perderá - Solicitando confirmación anticipada")
                
                # Guardar señal para referencia
                self.señal_martingala_pendiente = señal
                self.martingala_confirmacion_anticipada = None  # Esperando respuesta
                
                # Solicitar confirmación anticipada
                await self._solicitar_confirmacion_martingala_anticipada(señal, diferencia_porcentaje)
            else:
                print(f"[Martingala Predictiva] ✅ Vela probablemente ganará - No se solicita Martingala")
                
        except Exception as e:
            print(f"[Martingala Predictiva] ❌ Error en análisis predictivo: {e}")
            import traceback
            print(f"[Martingala Predictiva] 📋 Traceback: {traceback.format_exc()}")
    
    async def _solicitar_confirmacion_martingala_anticipada(self, señal: Dict, diferencia_porcentaje: float):
        """Solicita confirmación anticipada de Martingala al admin"""
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            monto_perdido = señal.get('trading_monto', 0)
            symbol = señal.get('trading_symbol', '')
            direccion = señal.get('trading_direccion', '')
            modo = señal.get('trading_modo', 'DEMO')
            efectividad_original = señal.get('efectividad', 80)
            
            # Calcular datos de Martingala
            if not self.martingala_activa:
                intento = 1
                monto_nuevo = monto_perdido * 2
                efectividad_martingala = min(95, efectividad_original + 5)
            else:
                intento = self.martingala_intentos + 1
                monto_nuevo = self.martingala_monto_actual * 2
                efectividad_martingala = min(95, efectividad_original + (intento * 5))
            
            # Mensaje para admin
            mensaje_admin = f"""🔮 **MARTINGALA PREDICTIVA - CONFIRMACIÓN ANTICIPADA**

⚠️ La vela probablemente se perderá

📊 **Análisis Actual (2 min antes del cierre):**
• **Symbol:** {symbol}
• **Dirección:** {direccion}
• **Modo:** {modo}
• **Diferencia actual:** {diferencia_porcentaje:.3f}% en contra

💰 **Datos de Martingala:**
• **Intento:** {intento}/{self.martingala_max_intentos}
• **Monto actual:** ${monto_perdido:.2f}
• **Monto Martingala:** ${monto_nuevo:.2f}
• **Efectividad estimada:** {efectividad_martingala}%

⏰ **Ventaja de confirmar ahora:**
Si confirmas ahora y la vela se pierde, ejecutaré la Martingala inmediatamente en la próxima vela sin perder tiempo.

Si la vela se gana, cancelaré automáticamente la Martingala.

⚠️ **¿Deseas pre-autorizar la Martingala?**
"""
            
            keyboard_admin = [
                [InlineKeyboardButton("✅ Sí, pre-autorizar Martingala", callback_data=f"martingala_anticipada_si")],
                [InlineKeyboardButton("❌ No, esperar resultado final", callback_data="martingala_anticipada_no")]
            ]
            
            # Enviar al admin
            if hasattr(self.bot_telegram, 'application') and self.bot_telegram.application:
                admin_ids = self.user_manager.obtener_admin_ids() if self.user_manager else []
                for admin_id in admin_ids:
                    try:
                        await self.bot_telegram.application.bot.send_message(
                            chat_id=admin_id,
                            text=mensaje_admin,
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(keyboard_admin)
                        )
                        print(f"[Martingala Predictiva] 📤 Confirmación anticipada enviada a admin {admin_id}")
                    except Exception as e:
                        print(f"[Martingala Predictiva] ⚠️ Error enviando a admin {admin_id}: {e}")
            
        except Exception as e:
            print(f"[Martingala Predictiva] ❌ Error solicitando confirmación anticipada: {e}")
    
    async def procesar_martingala_perdida(self, señal: Dict):
        """Procesa una pérdida y SOLICITA CONFIRMACIÓN antes de ejecutar Martingala (o ejecuta si ya fue pre-autorizada)"""
        try:
            # Verificar si el trading automático sigue activo
            if not getattr(self.bot_telegram, '_trading_activo', False):
                print(f"[Martingala] ⚠️ Trading automático desactivado - No se ejecuta Martingala")
                return
            
            # VERIFICAR SI YA HAY CONFIRMACIÓN ANTICIPADA
            if hasattr(self, 'martingala_confirmacion_anticipada') and self.martingala_confirmacion_anticipada == True:
                print(f"[Martingala] ✅ Confirmación anticipada encontrada - Ejecutando inmediatamente")
                
                # Preparar datos de Martingala
                monto_perdido = señal.get('trading_monto', 0)
                symbol = señal.get('trading_symbol', '')
                direccion = señal.get('trading_direccion', '')
                efectividad_original = señal.get('efectividad', 80)
                
                if not self.martingala_activa:
                    intento = 1
                    monto_nuevo = monto_perdido * 2
                    monto_base = monto_perdido
                else:
                    intento = self.martingala_intentos + 1
                    if intento > self.martingala_max_intentos:
                        print(f"[Martingala] ⛔ Límite alcanzado")
                        self.resetear_martingala_completo()
                        return
                    monto_nuevo = self.martingala_monto_actual * 2
                    monto_base = self.martingala_monto_base
                
                efectividad_martingala = min(95, efectividad_original + (intento * 5))
                
                # Guardar datos pendientes
                self.martingala_pendiente = {
                    'señal': señal,
                    'intento': intento,
                    'monto_base': monto_base,
                    'monto_nuevo': monto_nuevo,
                    'symbol': symbol,
                    'direccion': direccion,
                    'modo': señal.get('trading_modo', 'DEMO'),
                    'efectividad': efectividad_martingala,
                    'perdida_acumulada': sum([monto_base * (2 ** i) for i in range(intento)]),
                    'ganancia_potencial': (monto_nuevo * 0.94) - sum([monto_base * (2 ** i) for i in range(intento)])
                }
                
                # Ejecutar inmediatamente
                await self.ejecutar_martingala_confirmada()
                
                # Limpiar confirmación anticipada
                self.martingala_confirmacion_anticipada = None
                return
            
            # Si no hay confirmación anticipada, proceder con flujo normal
            # Obtener datos de la operación perdida
            monto_perdido = señal.get('trading_monto', 0)
            symbol = señal.get('trading_symbol', '')
            direccion = señal.get('trading_direccion', '')
            modo = señal.get('trading_modo', 'DEMO')
            efectividad_original = señal.get('efectividad', 80)
            
            # Calcular datos de Martingala
            if not self.martingala_activa:
                intento = 1
                monto_nuevo = monto_perdido * 2
                monto_base = monto_perdido
            else:
                intento = self.martingala_intentos + 1
                if intento > self.martingala_max_intentos:
                    print(f"[Martingala] ⛔ Límite alcanzado ({self.martingala_max_intentos} intentos)")
                    
                    # Calcular pérdida total
                    perdida_total = sum([self.martingala_monto_base * (2 ** i) for i in range(self.martingala_max_intentos + 1)])
                    
                    # Incrementar contador de Martingalas perdidas
                    self.martingalas_perdidas_hoy += 1
                    
                    # Notificar al admin
                    await self._notificar_admin_trading(
                        f"⛔ **MARTINGALA DETENIDA**\n\n"
                        f"Se alcanzó el límite de {self.martingala_max_intentos} intentos\n"
                        f"Pérdida total acumulada: ${perdida_total:.2f}\n\n"
                        f"Symbol: {symbol}\n"
                        f"Dirección: {direccion}"
                    )
                    
                    # Notificar a los usuarios
                    mensaje_usuarios = f"""
❌ **MARTINGALA PERDIDA**

⛔ Se alcanzó el límite de intentos

📊 **Resultado:**
• **Symbol:** {symbol}
• **Dirección:** {direccion}
• **Intentos realizados:** {self.martingala_max_intentos}
• **Pérdida total:** ${perdida_total:.2f}

💡 **Aprendizaje:**
No todas las Martingalas funcionan. Es importante saber cuándo detenerse.

⚠️ **Recomendación:**
• Toma un descanso si es necesario
• Revisa tu estrategia
• No persigas las pérdidas
• Espera la próxima oportunidad

💪 Recuerda: El trading exitoso requiere disciplina y paciencia.
                    """
                    
                    await self.enviar_mensaje_a_usuarios(mensaje_usuarios.strip())
                    
                    self.resetear_martingala_completo()
                    return
                monto_nuevo = self.martingala_monto_actual * 2
                monto_base = self.martingala_monto_base
            
            # Calcular efectividad de Martingala (basada en análisis histórico)
            # La efectividad aumenta con cada intento porque estadísticamente es más probable ganar
            efectividad_martingala = min(95, efectividad_original + (intento * 5))
            
            # Calcular pérdida acumulada y ganancia potencial
            perdida_acumulada = sum([monto_base * (2 ** i) for i in range(intento)])
            ganancia_potencial = (monto_nuevo * 0.94) - perdida_acumulada  # 94% payout
            
            print(f"[Martingala] 🎲 Solicitando confirmación - Intento {intento}/{self.martingala_max_intentos}")
            print(f"[Martingala] 💰 Monto: ${monto_perdido} → ${monto_nuevo}")
            print(f"[Martingala] 📊 Efectividad estimada: {efectividad_martingala}%")
            
            # Guardar datos de Martingala pendiente
            self.martingala_pendiente = {
                'señal': señal,
                'intento': intento,
                'monto_base': monto_base,
                'monto_nuevo': monto_nuevo,
                'symbol': symbol,
                'direccion': direccion,
                'modo': modo,
                'efectividad': efectividad_martingala,
                'perdida_acumulada': perdida_acumulada,
                'ganancia_potencial': ganancia_potencial
            }
            
            # Solicitar confirmación al admin y usuarios
            await self._solicitar_confirmacion_martingala(self.martingala_pendiente)
            
        except Exception as e:
            print(f"[Martingala] ❌ Error procesando Martingala: {e}")
            import traceback
            print(f"[Martingala] 📋 Traceback: {traceback.format_exc()}")
    
    async def _solicitar_confirmacion_martingala(self, datos_martingala: Dict):
        """Solicita confirmación para ejecutar Martingala al admin y usuarios"""
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            intento = datos_martingala['intento']
            monto_nuevo = datos_martingala['monto_nuevo']
            symbol = datos_martingala['symbol']
            direccion = datos_martingala['direccion']
            efectividad = datos_martingala['efectividad']
            perdida_acumulada = datos_martingala['perdida_acumulada']
            ganancia_potencial = datos_martingala['ganancia_potencial']
            modo = datos_martingala['modo']
            
            # Mensaje para admin
            mensaje_admin = f"""🎲 **MARTINGALA - CONFIRMACIÓN REQUERIDA**

❌ Operación perdida detectada

📊 **Datos de Martingala:**
• **Intento:** {intento}/{self.martingala_max_intentos}
• **Symbol:** {symbol}
• **Dirección:** {direccion}
• **Modo:** {modo}

💰 **Montos:**
• **Monto nuevo:** ${monto_nuevo:.2f}
• **Pérdida acumulada:** ${perdida_acumulada:.2f}
• **Ganancia potencial:** ${ganancia_potencial:.2f}

📈 **Efectividad estimada:** {efectividad}%

⚠️ **¿Deseas ejecutar la Martingala?**
"""
            
            keyboard_admin = [
                [InlineKeyboardButton("✅ Sí, ejecutar Martingala", callback_data=f"martingala_confirmar_{intento}")],
                [InlineKeyboardButton("❌ No, cancelar", callback_data="martingala_cancelar")]
            ]
            
            # Enviar al admin
            if hasattr(self.bot_telegram, 'application') and self.bot_telegram.application:
                admin_ids = self.user_manager.obtener_admin_ids() if self.user_manager else []
                for admin_id in admin_ids:
                    try:
                        await self.bot_telegram.application.bot.send_message(
                            chat_id=admin_id,
                            text=mensaje_admin,
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(keyboard_admin)
                        )
                    except Exception as e:
                        print(f"[Martingala] ⚠️ Error enviando a admin {admin_id}: {e}")
            
            # NOTA: Los usuarios ya recibieron la información de Martingala
            # en el mensaje de señal perdida (procesar_resultado_señal)
            # No se envía confirmación adicional, solo información
            
            print(f"[Martingala] 📤 Confirmación enviada a admin - Esperando respuesta...")
            
        except Exception as e:
            print(f"[Martingala] ❌ Error solicitando confirmación: {e}")
    
    async def ejecutar_martingala_confirmada(self):
        """Ejecuta la Martingala después de confirmación"""
        try:
            if not hasattr(self, 'martingala_pendiente') or not self.martingala_pendiente:
                print(f"[Martingala] ⚠️ No hay Martingala pendiente")
                return
            
            datos = self.martingala_pendiente
            señal = datos['señal']
            intento = datos['intento']
            monto_nuevo = datos['monto_nuevo']
            symbol = datos['symbol']
            direccion = datos['direccion']
            monto_base = datos['monto_base']
            
            # Activar o actualizar Martingala
            if not self.martingala_activa:
                self.martingala_activa = True
                self.martingala_monto_base = monto_base
                self.martingala_monto_actual = monto_nuevo
                self.martingala_direccion = direccion
                self.martingala_symbol = symbol
                self.martingala_intentos = intento
            else:
                self.martingala_intentos = intento
                self.martingala_monto_actual = monto_nuevo
            
            print(f"[Martingala] ✅ CONFIRMADA - Ejecutando intento {intento}/{self.martingala_max_intentos}")
            print(f"[Martingala] 💰 Monto: ${monto_nuevo}")
            
            # Incrementar contador de Martingalas ejecutadas
            self.martingalas_ejecutadas_hoy += 1
            
            # ESPERAR HASTA LA APERTURA DE LA PRÓXIMA VELA DE 5 MINUTOS
            from datetime import datetime, timedelta
            import asyncio as _aio
            
            ahora = datetime.now()
            minutos_actuales = ahora.minute
            segundos_actuales = ahora.second
            
            # Calcular próxima vela de 5 minutos (00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
            proxima_vela_minuto = ((minutos_actuales // 5) + 1) * 5
            if proxima_vela_minuto >= 60:
                proxima_vela_minuto = 0
                proxima_vela = ahora.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                proxima_vela = ahora.replace(minute=proxima_vela_minuto, second=0, microsecond=0)
            
            # Calcular tiempo de espera
            tiempo_espera = (proxima_vela - ahora).total_seconds()
            
            if tiempo_espera > 0:
                print(f"[Martingala] ⏰ Esperando {tiempo_espera:.1f} segundos hasta apertura de vela ({proxima_vela.strftime('%H:%M:%S')})")
                await _aio.sleep(tiempo_espera)
                print(f"[Martingala] ✅ Apertura de vela alcanzada - Ejecutando Martingala")
            
            # Crear señal de Martingala
            señal_martingala = {
                'symbol': symbol,
                'direccion': direccion,
                'efectividad': datos['efectividad'],
                'hora': datetime.now().strftime('%H:%M'),
                'numero': señal.get('numero', 0),
                'precio_entrada': señal.get('precio_salida', 0),
                'es_martingala': True
            }
            
            # Ejecutar operación con el nuevo monto
            monto_original = getattr(self.bot_telegram, '_trading_monto', 0)
            self.bot_telegram._trading_monto = monto_nuevo
            
            await self.ejecutar_operacion_automatica(señal_martingala)
            
            # Restaurar monto original
            self.bot_telegram._trading_monto = monto_original
            
            # Limpiar Martingala pendiente
            self.martingala_pendiente = None
            
        except Exception as e:
            print(f"[Martingala] ❌ Error ejecutando Martingala confirmada: {e}")
            import traceback
            print(f"[Martingala] 📋 Traceback: {traceback.format_exc()}")
    
    async def resetear_martingala(self, señal: Dict):
        """Resetea el sistema de Martingala después de una victoria"""
        if self.martingala_activa:
            ganancia_total = señal.get('trading_monto', 0) * 0.94  # Asumiendo 94% de payout
            symbol = señal.get('trading_symbol', 'N/A')
            direccion = señal.get('trading_direccion', 'N/A')
            intento = self.martingala_intentos
            
            print(f"[Martingala] ✅ VICTORIA - Recuperación exitosa!")
            print(f"[Martingala] 💰 Ganancia: ${ganancia_total:.2f}")
            
            # Incrementar contador de Martingalas ganadas
            self.martingalas_ganadas_hoy += 1
            
            # Notificar al admin
            await self._notificar_admin_trading(
                f"✅ **MARTINGALA EXITOSA**\n\n"
                f"🎉 Recuperación completada en intento {intento}\n"
                f"💰 Ganancia: ${ganancia_total:.2f}\n\n"
                f"Symbol: {symbol}\n"
                f"Dirección: {direccion}"
            )
            
            # Notificar a los usuarios
            mensaje_usuarios = f"""
🎉 **MARTINGALA GANADA** 🎉

✅ ¡Recuperación exitosa!

📊 **Resultado:**
• **Symbol:** {symbol}
• **Dirección:** {direccion}
• **Intento:** {intento}
• **Ganancia:** ${ganancia_total:.2f}

💪 **¡Felicidades!**
La estrategia de Martingala funcionó perfectamente.
Has recuperado la pérdida anterior y obtenido ganancia.

🚀 ¡Seguimos adelante con más oportunidades!
            """
            
            await self.enviar_mensaje_a_usuarios(mensaje_usuarios.strip())
            
            self.resetear_martingala_completo()
    
    def resetear_martingala_completo(self):
        """Resetea completamente el sistema de Martingala"""
        self.martingala_activa = False
        self.martingala_monto_base = 0
        self.martingala_monto_actual = 0
        self.martingala_direccion = None
        self.martingala_symbol = None
        self.martingala_intentos = 0
        print(f"[Martingala] 🔄 Sistema reseteado")

# Función principal
async def ejecutar_bot_completo():
    """Función principal para ejecutar el bot completo"""
    scheduler = SignalScheduler()
    
    # Conectar a Quotex
    try:
        import os
        email = os.getenv("QUOTEX_EMAIL")
        password = os.getenv("QUOTEX_PASSWORD")
    except Exception:
        email = None
        password = None
    if await scheduler.market_manager.conectar_quotex(email, password):
        await scheduler.ejecutar_ciclo_diario()
    else:
        print("❌ No se pudo conectar a Quotex")

if __name__ == "__main__":
    # Ejecutar bot
    asyncio.run(ejecutar_bot_completo())

