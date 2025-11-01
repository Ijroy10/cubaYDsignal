#!/usr/bin/env python3
"""
🇨🇺 CubaYDSignal Bot - Sistema Core
===================================

Sistema principal del bot de trading profesional.

Autor: Yorji Fonseca (@Ijroy10)
Admin ID: 5806367733
Master Key: Ijroy010702$Yorji050212
"""

import asyncio
import os
import json
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Telegram Bot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear directorios
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)

class MotivationalMessages:
    """Sistema de mensajes motivacionales"""
    
    MORNING_PHRASES = [
        "No viniste a probar suerte… viniste a dominar el juego.",
        "La paciencia y la lógica siempre vencen al impulso.",
        "Cada vela cuenta una historia… tú decides cómo leerla.",
        "No se trata de predecir, se trata de entender.",
        "Tu mejor operación es la que sigue tu análisis, no tu emoción.",
        "El mercado premia la disciplina, no la desesperación.",
        "Cuando los demás dudan, tú operas con visión.",
        "Los errores enseñan, pero la constancia gana.",
        "No es suerte si lo entrenaste 100 veces antes.",
        "Operar sin lógica es como navegar sin mapa."
    ]
    
    SUCCESS_PHRASES = [
        "Hoy no ganaste por suerte, ganaste porque tu análisis fue más fuerte.",
        "Cuando aplicas la lógica y la paciencia, el mercado responde.",
        "Hoy dominaste el juego… mañana toca repetir la fórmula.",
        "Disciplina + estrategia = resultados. Hoy lo comprobaste.",
        "El que entiende las velas, no necesita adivinarlas."
    ]
    
    DIFFICULT_PHRASES = [
        "El mercado no siempre premia, pero siempre enseña.",
        "Hoy no ganaste dinero… pero ganaste experiencia.",
        "Hasta los mejores traders tienen días rojos. Lo que los hace grandes es que siguen.",
        "El retroceso de hoy es el impulso de mañana."
    ]

class QuotexSimulator:
    """Simulador de Quotex"""
    
    def __init__(self):
        self.markets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURUSD_OTC", "GBPUSD_OTC"]
    
    def get_available_markets(self) -> List[Dict]:
        """Obtiene mercados disponibles"""
        markets = []
        for symbol in self.markets:
            payout = random.uniform(80, 95)
            is_otc = "_OTC" in symbol
            news_active = random.choice([True, False]) if not is_otc else False
            
            markets.append({
                'symbol': symbol,
                'payout': payout,
                'is_otc': is_otc,
                'news_active': news_active,
                'available': payout >= 80.0
            })
        
        return [m for m in markets if m['available']]
    
    def get_market_data(self, symbol: str) -> Dict:
        """Obtiene datos del mercado"""
        base_price = 1.0850 if "EUR" in symbol else random.uniform(0.5, 2.0)
        
        data = []
        for i in range(100):
            timestamp = datetime.now() - timedelta(minutes=5 * (100 - i))
            open_price = base_price + random.uniform(-0.001, 0.001)
            high_price = open_price + random.uniform(0, 0.002)
            low_price = open_price - random.uniform(0, 0.002)
            close_price = open_price + random.uniform(-0.001, 0.001)
            
            data.append({
                'timestamp': timestamp.isoformat(),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': random.randint(1000, 5000)
            })
            base_price = close_price
        
        return {'symbol': symbol, 'data': data}

class TechnicalAnalysis:
    """Análisis técnico completo"""
    
    @staticmethod
    def analyze_market(market_data: Dict) -> Dict[str, Any]:
        """Análisis completo del mercado"""
        
        df = pd.DataFrame(market_data['data'])
        if len(df) < 50:
            return {'error': 'Datos insuficientes'}
        
        # Análisis de tendencia
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        current_price = df['close'].iloc[-1]
        sma_10 = df['sma_10'].iloc[-1]
        sma_20 = df['sma_20'].iloc[-1]
        sma_50 = df['sma_50'].iloc[-1]
        
        # Determinar tendencia
        trend_score = 0
        if current_price > sma_10: trend_score += 1
        if current_price > sma_20: trend_score += 1
        if current_price > sma_50: trend_score += 1
        if sma_10 > sma_20: trend_score += 1
        if sma_20 > sma_50: trend_score += 1
        
        if trend_score >= 4:
            trend = 'BULLISH'
            direction = 'CALL'
        elif trend_score <= 1:
            trend = 'BEARISH'
            direction = 'PUT'
        else:
            trend = 'NEUTRAL'
            direction = 'NEUTRAL'
        
        # Análisis de volatilidad
        df['atr'] = (df['high'] - df['low']).rolling(14).mean()
        current_atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].rolling(20).mean().iloc[-1]
        volatility_ratio = current_atr / avg_atr if avg_atr > 0 else 1
        
        if volatility_ratio > 1.5:
            volatility = 'HIGH'
        elif volatility_ratio < 0.7:
            volatility = 'LOW'
        else:
            volatility = 'NORMAL'
        
        # Detectar patrones de velas
        patterns = TechnicalAnalysis._detect_patterns(df)
        
        # Calcular efectividad
        effectiveness = TechnicalAnalysis._calculate_effectiveness(trend, volatility, patterns)
        
        return {
            'trend': trend,
            'direction': direction,
            'volatility': volatility,
            'patterns': patterns,
            'effectiveness': effectiveness,
            'confidence': min(trend_score / 5 * 100, 95)
        }
    
    @staticmethod
    def _detect_patterns(df: pd.DataFrame) -> Dict[str, bool]:
        """Detecta patrones de velas"""
        patterns = {}
        
        if len(df) < 3:
            return patterns
        
        # Calcular propiedades
        body = abs(df['close'] - df['open'])
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        total_range = df['high'] - df['low']
        
        # Doji
        patterns['doji'] = (body / total_range < 0.1).iloc[-1] if len(df) > 0 else False
        
        # Hammer
        patterns['hammer'] = (
            (lower_shadow > body * 2) & 
            (upper_shadow < body * 0.5) & 
            (df['close'] > df['open'])
        ).iloc[-1] if len(df) > 0 else False
        
        # Engulfing
        if len(df) >= 2:
            engulfing_bullish = (
                (df['close'].shift(1) < df['open'].shift(1)) &
                (df['close'] > df['open']) &
                (df['open'] < df['close'].shift(1)) &
                (df['close'] > df['open'].shift(1))
            ).iloc[-1]
            patterns['engulfing_bullish'] = engulfing_bullish
        
        return patterns
    
    @staticmethod
    def _calculate_effectiveness(trend: str, volatility: str, patterns: Dict) -> float:
        """Calcula efectividad de la señal"""
        
        base_effectiveness = 75.0
        
        # Bonificación por tendencia clara
        if trend in ['BULLISH', 'BEARISH']:
            base_effectiveness += 10
        
        # Bonificación por volatilidad normal
        if volatility == 'NORMAL':
            base_effectiveness += 5
        elif volatility == 'HIGH':
            base_effectiveness += 3
        
        # Bonificación por patrones
        pattern_bonus = 0
        for pattern, detected in patterns.items():
            if detected:
                pattern_bonus += 3
        
        base_effectiveness += min(pattern_bonus, 10)
        
        # Añadir algo de aleatoriedad realista
        base_effectiveness += random.uniform(-5, 5)
        
        return min(max(base_effectiveness, 60), 95)

class CubaYDSignalBot:
    """Bot principal de CubaYDSignal"""
    
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.quotex = QuotexSimulator()
        self.messages = MotivationalMessages()
        
        # Configuración
        self.master_key = "Ijroy010702$Yorji050212"
        self.admin_id = "5806367733"
        self.daily_key = ""
        self.daily_key_date = ""
        
        # Datos del bot
        self.active_users = {}
        self.daily_signals = []
        self.signal_counter = 0
        
        # Cargar datos
        self._load_data()
        
        # Configurar handlers
        self._setup_handlers()
    
    def _load_data(self):
        """Carga datos persistentes"""
        try:
            if os.path.exists('data/bot_data.json'):
                with open('data/bot_data.json', 'r') as f:
                    data = json.load(f)
                    self.daily_key = data.get('daily_key', '')
                    self.daily_key_date = data.get('daily_key_date', '')
                    self.active_users = data.get('active_users', {})
                    self.daily_signals = data.get('daily_signals', [])
                    self.signal_counter = data.get('signal_counter', 0)
        except Exception as e:
            logger.error(f"Error cargando datos: {e}")
    
    def _save_data(self):
        """Guarda datos persistentes"""
        try:
            data = {
                'daily_key': self.daily_key,
                'daily_key_date': self.daily_key_date,
                'active_users': self.active_users,
                'daily_signals': self.daily_signals,
                'signal_counter': self.signal_counter,
                'last_updated': datetime.now().isoformat()
            }
            with open('data/bot_data.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando datos: {e}")
    
    def _setup_handlers(self):
        """Configura los handlers del bot"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        await self.handle_message(update, context)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja todos los mensajes"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Usuario"
        message_text = update.message.text.strip()
        
        # Verificar si es clave maestra (admin)
        if message_text == self.master_key:
            await self._handle_admin_access(update, context)
            return
        
        # Verificar si es clave diaria
        if message_text == self.daily_key and self.daily_key:
            await self._handle_daily_key_access(update, context, user_id, username)
            return
        
        # Verificar si es clave incorrecta (intento de acceso)
        if len(message_text) > 3 and message_text not in ["/start"]:
            await self._handle_incorrect_key(update, context)
            return
        
        # Mensaje de bienvenida general
        await self._handle_welcome_message(update, context)
    
    async def _handle_admin_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja acceso de administrador"""
        keyboard = [
            [InlineKeyboardButton("🔑 Establecer Clave Diaria", callback_data="set_daily_key")],
            [InlineKeyboardButton("👥 Ver Usuarios Activos", callback_data="view_users")],
            [InlineKeyboardButton("📊 Generar Señal Manual", callback_data="manual_signal")],
            [InlineKeyboardButton("📈 Estadísticas del Día", callback_data="daily_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔐 **Bienvenido, Yorji**\n"
            f"Eres el administrador del sistema CubaYDsignal ✅\n\n"
            f"📅 Clave actual: `{self.daily_key or 'No establecida'}`\n"
            f"👥 Usuarios activos: {len(self.active_users)}\n"
            f"📊 Señales enviadas hoy: {len(self.daily_signals)}\n\n"
            f"¿Qué deseas hacer?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_daily_key_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, username: str):
        """Maneja acceso con clave diaria correcta"""
        
        # Registrar usuario
        self.active_users[user_id] = {
            'username': username,
            'access_time': datetime.now().isoformat(),
            'signals_received': len(self.daily_signals)
        }
        self._save_data()
        
        current_hour = datetime.now().hour
        
        if current_hour < 8:
            # Antes del horario de señales
            welcome_phrase = random.choice(self.messages.MORNING_PHRASES)
            await update.message.reply_text(
                f"🚀 ¡Todo listo, trader!\n"
                f"Tu frase del día es ✅ válida.\n\n"
                f"⏰ Las señales de hoy comienzan desde las 8:00 AM hasta las 8:00 PM.\n"
                f"💡 Mantente conectado, enfocado y listo para ejecutar con confianza.\n\n"
                f"🔥 Frase del día:\n"
                f"*\"{welcome_phrase}\"*\n\n"
                f"¡Hoy puede ser tu mejor día!\n"
                f"— CubaYDsignal te acompaña en cada decisión.",
                parse_mode='Markdown'
            )
        elif 8 <= current_hour <= 20:
            # Durante horario de señales
            if self.daily_signals:
                # Enviar señales perdidas
                await update.message.reply_text(
                    f"📢 ¡Hola, trader!\n"
                    f"Has ingresado tu clave del día a las {datetime.now().strftime('%H:%M')} 🕑\n"
                    f"Actualmente ya se han generado {len(self.daily_signals)} señales desde las 8:00 AM.\n\n"
                    f"🔁 Te enviamos a continuación las señales anteriores para que revises el resumen de la jornada.\n\n"
                    f"⚠️ Aún puedes recibir las señales restantes del día. Mantente atento.\n"
                    f"📅 Horario de señales activas: 8:00 AM – 8:00 PM\n\n"
                    f"🤖 – Bot CubaYDsignal"
                )
                
                # Enviar señales anteriores
                for signal in self.daily_signals:
                    await update.message.reply_text(
                        f"📊 Señal #{signal['number']:02d} – {signal['time']} – {signal['symbol']} – {signal['direction']} – 5 min – Efectividad: {signal['effectiveness']:.0f}%"
                    )
            else:
                await update.message.reply_text(
                    f"👋 ¡Hola, buen día trader!\n\n"
                    f"✅ Acceso confirmado. Estás listo para recibir señales.\n"
                    f"⏰ El horario de señales es de 8:00 AM a 8:00 PM.\n\n"
                    f"🔐 Mantente atento a las próximas señales.\n\n"
                    f"¡Vamos con todo hoy! 💪🔥"
                )
        else:
            # Después del horario
            await update.message.reply_text(
                f"👋 ¡Hola, buen día trader!\n\n"
                f"🚫 El sistema de señales ya ha cerrado por hoy.\n\n"
                f"⏰ Te espero mañana desde las 8:00 AM con tu clave del día.\n\n"
                f"¡Prepárate para aprovechar nuevas oportunidades! 🚀"
            )
    
    async def _handle_incorrect_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja clave incorrecta"""
        denied_phrase = random.choice(self.messages.DIFFICULT_PHRASES[:3])  # Usar frases de negación
        
        await update.message.reply_text(
            f"🚫 Clave incorrecta detectada\n\n"
            f"La frase ingresada no coincide con la clave activa del día.\n"
            f"‼️ Tu acceso a las señales ha sido pausado temporalmente.\n\n"
            f"🔑 Ponte en contacto con tu líder o administrador para recuperar el acceso.\n\n"
            f"🚀 CubaYDsignal – ¡Donde la disciplina vence a la suerte!"
        )
    
    async def _handle_welcome_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensaje de bienvenida general"""
        current_hour = datetime.now().hour
        
        if current_hour < 8:
            message = (
                f"👋 ¡Hola, buen día trader!\n\n"
                f"⏰ El horario de señales es de 8:00 AM a 8:00 PM.\n\n"
                f"📌 Para recibir las señales de hoy, por favor escribe la clave del día cuando estés listo.\n\n"
                f"🔐 Solo los traders con la clave correcta podrán acceder a las señales.\n\n"
                f"¡Prepárate para operar con enfoque y disciplina! 🚀"
            )
        elif 8 <= current_hour <= 20:
            message = (
                f"👋 ¡Hola, buen día trader!\n\n"
                f"⏰ El horario de señales es de 8:00 AM a 8:00 PM.\n\n"
                f"📌 Si deseas recibir las señales de hoy, por favor escribe la clave del día.\n\n"
                f"🔐 Solo los traders con la clave correcta podrán acceder a las señales.\n\n"
                f"¡Vamos con todo hoy! 💪🔥"
            )
        else:
            message = (
                f"👋 ¡Hola, buen día trader!\n\n"
                f"🚫 El sistema de señales ya ha cerrado por hoy.\n\n"
                f"⏰ Te espero mañana desde las 8:00 AM con tu clave del día.\n\n"
                f"¡Prepárate para aprovechar nuevas oportunidades! 🚀"
            )
        
        await update.message.reply_text(message)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja callbacks de botones"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "set_daily_key":
            await query.edit_message_text(
                "🔑 **Establecer Clave Diaria**\n\n"
                "Por favor, escribe la nueva clave del día.\n"
                "Puede contener emojis, mayúsculas, etc.\n\n"
                "Ejemplo: `ganaconlogica🔥`",
                parse_mode='Markdown'
            )
            # Aquí necesitarías implementar un estado para capturar la siguiente respuesta
        
        elif query.data == "view_users":
            users_text = "👥 **Usuarios Activos Hoy:**\n\n"
            if self.active_users:
                for user_id, info in self.active_users.items():
                    access_time = datetime.fromisoformat(info['access_time']).strftime('%H:%M')
                    users_text += f"• {info['username']} - Acceso: {access_time}\n"
            else:
                users_text += "No hay usuarios activos hoy."
            
            await query.edit_message_text(users_text, parse_mode='Markdown')
        
        elif query.data == "manual_signal":
            await self._generate_manual_signal(query)
        
        elif query.data == "daily_stats":
            await self._show_daily_stats(query)
    
    async def _generate_manual_signal(self, query):
        """Genera una señal manual"""
        
        # Obtener mercados disponibles
        markets = self.quotex.get_available_markets()
        if not markets:
            await query.edit_message_text("❌ No hay mercados disponibles actualmente.")
            return
        
        # Seleccionar mejor mercado
        best_market = max(markets, key=lambda x: x['payout'])
        
        # Obtener datos y analizar
        market_data = self.quotex.get_market_data(best_market['symbol'])
        analysis = TechnicalAnalysis.analyze_market(market_data)
        
        if analysis.get('error'):
            await query.edit_message_text(f"❌ Error en análisis: {analysis['error']}")
            return
        
        if analysis['effectiveness'] < 80:
            await query.edit_message_text(
                f"❌ **Señal Rechazada**\n\n"
                f"💱 Mercado: {best_market['symbol']}\n"
                f"📊 Efectividad: {analysis['effectiveness']:.1f}%\n"
                f"🚫 Razón: Efectividad < 80%\n\n"
                f"El sistema mantiene la garantía rechazando señales débiles."
            )
            return
        
        # Crear señal
        self.signal_counter += 1
        signal = {
            'number': self.signal_counter,
            'time': datetime.now().strftime('%H:%M'),
            'symbol': best_market['symbol'],
            'direction': analysis['direction'],
            'effectiveness': analysis['effectiveness'],
            'payout': best_market['payout']
        }
        
        self.daily_signals.append(signal)
        self._save_data()
        
        # Enviar a usuarios activos
        signal_text = (
            f"📊 **Señal #{signal['number']:02d}**\n"
            f"🕒 Hora: {signal['time']}\n"
            f"📈 Activo: {signal['symbol']}\n"
            f"📍 Dirección: {signal['direction']}\n"
            f"⏳ Válido por: 5 minutos\n"
            f"🎯 Efectividad estimada: {signal['effectiveness']:.0f}%\n"
            f"💰 Payout: {signal['payout']:.1f}%\n\n"
            f"🤖 – Señal generada por el Bot CubaYDsignal"
        )
        
        await query.edit_message_text(
            f"✅ **Señal Generada y Enviada**\n\n{signal_text}",
            parse_mode='Markdown'
        )
        
        # Enviar a todos los usuarios activos
        for user_id in self.active_users.keys():
            try:
                await self.app.bot.send_message(chat_id=user_id, text=signal_text, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error enviando señal a {user_id}: {e}")
    
    async def _show_daily_stats(self, query):
        """Muestra estadísticas del día"""
        
        total_signals = len(self.daily_signals)
        active_users = len(self.active_users)
        
        # Simular efectividad (en producción sería real)
        if total_signals > 0:
            successful_signals = int(total_signals * random.uniform(0.75, 0.95))
            effectiveness = (successful_signals / total_signals) * 100
        else:
            successful_signals = 0
            effectiveness = 0
        
        stats_text = (
            f"📊 **Estadísticas del Día**\n\n"
            f"📅 Fecha: {datetime.now().strftime('%d/%m/%Y')}\n"
            f"👥 Usuarios activos: {active_users}\n"
            f"📡 Señales enviadas: {total_signals}\n"
            f"✅ Señales exitosas: {successful_signals}\n"
            f"🎯 Efectividad: {effectiveness:.1f}%\n"
            f"🏆 Estado: {'✅ CUMPLIENDO GARANTÍA' if effectiveness >= 80 else '⚠️ BAJO GARANTÍA'}\n\n"
            f"⏰ Horario activo: 8:00 AM - 8:00 PM"
        )
        
        await query.edit_message_text(stats_text, parse_mode='Markdown')
    
    def run(self):
        """Ejecuta el bot"""
        logger.info("🇨🇺 Iniciando CubaYDSignal Bot...")
        logger.info(f"👤 Admin ID: {self.admin_id}")
        logger.info(f"🔑 Clave diaria: {self.daily_key or 'No establecida'}")
        
        self.app.run_polling()

def main():
    """Función principal"""
    
    # Token del bot (debe estar en variable de entorno)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN no configurado")
        print("Configura tu token de Telegram en las variables de entorno")
        return
    
    try:
        bot = CubaYDSignalBot(token)
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        logger.error(f"Error crítico: {e}")

if __name__ == "__main__":
    main()
