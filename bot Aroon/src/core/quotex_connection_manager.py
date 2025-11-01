"""
MÓDULO DE GESTIÓN DE CONEXIÓN MEJORADO PARA QUOTEX
Basado en mejores prácticas de repositorios de referencia como s1d40/telegram-qxbroker-bot
Implementa lógica robusta de conexión, reconexión y detección de estado
"""

import asyncio
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from loguru import logger
import pytz

from quotexpy import Quotex


class QuotexConnectionManager:
    """Gestor mejorado de conexión a Quotex con lógica robusta de reconexión."""
    
    def __init__(self, email: str, password: str, data_dir: str = "data"):
        self.email = email
        self.password = password
        self.data_dir = data_dir
        self.quotex: Optional[Quotex] = None
        self.connected = False
        self.connection_timestamp = None
        self.last_error = None
        self.session_file = Path(data_dir) / "quotex_session.json"
        
        # Configuración de reconexión
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # segundos entre intentos
        self.connection_timeout = 60  # timeout para conexión inicial
        
        # Control de bloqueos 403
        self.last_403_block = None
        self.block_cooldown = 30 * 60  # 30 minutos
        
        # Asegurar que existe el directorio de datos
        Path(data_dir).mkdir(exist_ok=True)
        
        logger.info(f"QuotexConnectionManager inicializado para {email}")

    async def connect(self, telegram_bot=None) -> bool:
        """
        Conecta a Quotex con lógica robusta de reconexión.
        
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario
        """
        if self.connected and self.quotex and await self._verify_connection():
            logger.info("Ya conectado a Quotex y verificado")
            return True
        
        # Verificar si debemos esperar por bloqueo 403 reciente
        if self._should_wait_for_403_cooldown():
            remaining = self._get_403_cooldown_remaining()
            logger.warning(f"Esperando {remaining//60} minutos más por cooldown de bloqueo 403")
            if telegram_bot:
                await telegram_bot.notificar_admin_telegram(
                    f"⏸️ Bot en pausa por bloqueo Cloudflare. Tiempo restante: {remaining//60} minutos"
                )
            return False
        
        logger.info(f"Iniciando conexión a Quotex para {self.email}")
        
        try:
            # Limpiar sesión anterior si existe
            await self._cleanup_session()
            
            # Crear nueva instancia de Quotex
            self.quotex = Quotex(
                email=self.email, 
                password=self.password, 
                headless=False  # Usar modo visible para evitar bloqueos
            )
            
            # Intentar conexión inicial
            success = await self._attempt_connection()
            
            if success:
                await self._on_connection_success(telegram_bot)
                return True
            else:
                # Intentar reconexión con múltiples intentos
                return await self._attempt_reconnection(telegram_bot)
                
        except Exception as e:
            logger.error(f"Error en conexión inicial: {e}")
            await self._handle_connection_error(e, telegram_bot)
            return False

    async def _attempt_connection(self) -> bool:
        """Intenta la conexión inicial a Quotex."""
        try:
            logger.info("Intentando conexión inicial...")
            
            # Conectar usando el método de quotexpy
            check, reason = await self.quotex.connect()
            
            if check:
                logger.info(f"Conexión inicial exitosa: {reason}")
                return await self._verify_connection()
            else:
                logger.warning(f"Conexión inicial falló: {reason}")
                return False
                
        except Exception as e:
            logger.error(f"Error en intento de conexión: {e}")
            return False

    async def _attempt_reconnection(self, telegram_bot=None) -> bool:
        """Intenta reconexión con múltiples intentos."""
        logger.info(f"Iniciando proceso de reconexión (máx. {self.max_reconnect_attempts} intentos)")
        
        for attempt in range(1, self.max_reconnect_attempts + 1):
            logger.info(f"Intento de reconexión {attempt}/{self.max_reconnect_attempts}")
            
            try:
                # Verificar si ya está conectado usando métodos disponibles
                if self.quotex and await self._verify_connection():
                    logger.info("Conexión ya establecida y verificada")
                    await self._on_connection_success(telegram_bot)
                    return True
                
                # Limpiar sesión corrupta
                await self._cleanup_session()
                
                # Crear nueva instancia para reconexión
                self.quotex = Quotex(
                    email=self.email, 
                    password=self.password, 
                    headless=False
                )
                
                # Intentar nueva conexión
                success = await self.quotex.connect()
                
                if success and await self._verify_connection():
                    logger.info(f"Reconexión exitosa en intento {attempt}")
                    await self._on_connection_success(telegram_bot)
                    return True
                else:
                    logger.warning(f"Reconexión falló en intento {attempt}")
                    
            except Exception as e:
                logger.error(f"Error en intento de reconexión {attempt}: {e}")
                
                # Detectar bloqueo 403
                if self._is_403_error(e):
                    await self._handle_403_block(telegram_bot)
                    return False
            
            # Esperar antes del siguiente intento (excepto en el último)
            if attempt < self.max_reconnect_attempts:
                logger.info(f"Esperando {self.reconnect_delay} segundos antes del siguiente intento...")
                await asyncio.sleep(self.reconnect_delay)
        
        logger.error("Todos los intentos de reconexión fallaron")
        await self._handle_connection_failure(telegram_bot)
        return False

    async def _verify_connection(self) -> bool:
        """Verifica que la conexión esté realmente funcional usando métodos disponibles."""
        if not self.quotex:
            logger.debug("No hay instancia de Quotex")
            return False
        
        try:
            # Verificación 1: API interna disponible
            if not hasattr(self.quotex, 'api') or not self.quotex.api:
                logger.debug("API interna no disponible")
                return False
            
            api = self.quotex.api
            
            # Verificación 2: SSID presente (indica autenticación exitosa)
            if not hasattr(api, 'SSID') or not api.SSID:
                logger.debug("SSID no disponible - no autenticado")
                return False
            
            # Verificación 3: Sin errores de WebSocket
            if hasattr(api, 'check_websocket_if_error') and api.check_websocket_if_error:
                error_reason = getattr(api, 'websocket_error_reason', 'Unknown')
                logger.debug(f"WebSocket tiene errores: {error_reason}")
                return False
            
            # Verificación 4: WebSocket conectado
            if hasattr(api, 'check_websocket_if_connect'):
                if api.check_websocket_if_connect is False:
                    logger.debug("WebSocket no conectado")
                    return False
            
            # Verificación 5: Intentar obtener balance como prueba final
            try:
                balance = await self.quotex.get_balance()
                if isinstance(balance, (int, float)):
                    logger.debug(f"Conexión verificada exitosamente. Balance: {balance}")
                    return True
                else:
                    logger.debug("Balance no disponible o inválido")
                    return False
            except Exception as balance_error:
                logger.debug(f"Error obteniendo balance: {balance_error}")
                # Si el balance falla pero otros criterios están OK, aún consideramos conectado
                # porque puede ser un problema temporal
                return True
            
        except Exception as e:
            logger.debug(f"Error en verificación de conexión: {e}")
            return False

    async def _on_connection_success(self, telegram_bot=None):
        """Acciones a realizar tras una conexión exitosa."""
        self.connected = True
        self.connection_timestamp = datetime.now()
        self.last_error = None
        
        # Obtener información de la cuenta
        try:
            balance = await self.quotex.get_balance()
            account_type = "REAL" if hasattr(self.quotex, 'account_type') else "DESCONOCIDO"
            
            success_msg = (
                f"✅ Conexión exitosa a Quotex\n"
                f"📧 Usuario: {self.email}\n"
                f"💰 Balance: ${balance}\n"
                f"🔄 Tipo: {account_type}\n"
                f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            logger.info("Conexión a Quotex establecida exitosamente")
            
            if telegram_bot:
                await telegram_bot.notificar_admin_telegram(success_msg)
                
        except Exception as e:
            logger.warning(f"Error obteniendo información post-conexión: {e}")

    async def _handle_connection_error(self, error: Exception, telegram_bot=None):
        """Maneja errores de conexión."""
        self.connected = False
        self.last_error = str(error)
        
        error_msg = str(error).lower()
        
        if self._is_403_error(error):
            await self._handle_403_block(telegram_bot)
        elif 'ssid' in error_msg or 'token' in error_msg:
            await self._handle_auth_error(telegram_bot)
        else:
            await self._handle_generic_error(error, telegram_bot)

    async def _handle_403_block(self, telegram_bot=None):
        """Maneja bloqueos 403 de Cloudflare."""
        self.last_403_block = datetime.now()
        
        error_msg = (
            f"🚨 BLOQUEO CLOUDFLARE DETECTADO\n"
            f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🚫 Quotex ha bloqueado la conexión WebSocket.\n\n"
            f"🔧 SOLUCIONES RECOMENDADAS:\n"
            f"1️⃣ Cambiar a red residencial (hotspot móvil)\n"
            f"2️⃣ Evitar VPNs de datacenter\n"
            f"3️⃣ Esperar 30-60 minutos antes de reintentar\n"
            f"4️⃣ Usar navegación manual en Quotex por unos minutos\n\n"
            f"⏸️ El bot pausará intentos por 30 minutos."
        )
        
        logger.error("Bloqueo 403 detectado")
        
        if telegram_bot:
            await telegram_bot.notificar_admin_telegram(error_msg)

    async def _handle_auth_error(self, telegram_bot=None):
        """Maneja errores de autenticación."""
        error_msg = (
            f"🔐 ERROR DE AUTENTICACIÓN\n"
            f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"❌ No se pudo obtener el token de sesión.\n\n"
            f"🔧 POSIBLES CAUSAS:\n"
            f"• Credenciales incorrectas\n"
            f"• Cuenta bloqueada temporalmente\n"
            f"• Cambios en la página de login de Quotex\n"
            f"• CAPTCHA requerido\n\n"
            f"✅ SOLUCIONES:\n"
            f"1️⃣ Verificar credenciales en .env\n"
            f"2️⃣ Hacer login manual en quotex.io\n"
            f"3️⃣ Esperar unos minutos y reintentar"
        )
        
        logger.error("Error de autenticación detectado")
        
        if telegram_bot:
            await telegram_bot.notificar_admin_telegram(error_msg)

    async def _handle_generic_error(self, error: Exception, telegram_bot=None):
        """Maneja errores genéricos de conexión."""
        error_msg = (
            f"⚠️ ERROR DE CONEXIÓN\n"
            f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"❌ {str(error)}\n\n"
            f"🔄 El bot intentará reconectar automáticamente."
        )
        
        logger.error(f"Error genérico de conexión: {error}")
        
        if telegram_bot:
            await telegram_bot.notificar_admin_telegram(error_msg)

    async def _handle_connection_failure(self, telegram_bot=None):
        """Maneja fallo total de conexión tras todos los intentos."""
        failure_msg = (
            f"💥 FALLO TOTAL DE CONEXIÓN\n"
            f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"❌ No se pudo establecer conexión tras {self.max_reconnect_attempts} intentos.\n\n"
            f"🔧 ACCIONES REQUERIDAS:\n"
            f"1️⃣ Verificar conexión a internet\n"
            f"2️⃣ Verificar credenciales\n"
            f"3️⃣ Revisar logs para más detalles\n"
            f"4️⃣ Considerar cambio de IP/red\n\n"
            f"🤖 El bot se detendrá hasta intervención manual."
        )
        
        logger.error("Fallo total de conexión")
        
        if telegram_bot:
            await telegram_bot.notificar_admin_telegram(failure_msg)

    async def _cleanup_session(self):
        """Limpia archivos de sesión corruptos."""
        try:
            # Limpiar archivo de sesión local si existe
            if self.session_file.exists():
                self.session_file.unlink()
                logger.debug("Archivo de sesión local eliminado")
            
            # Limpiar sesión de quotexpy si existe
            sessions_path = Path("sessions") / f"{self.email}.json"
            if sessions_path.exists():
                sessions_path.unlink()
                logger.debug("Archivo de sesión de quotexpy eliminado")
                
        except Exception as e:
            logger.warning(f"Error limpiando sesión: {e}")

    def _is_403_error(self, error: Exception) -> bool:
        """Detecta si un error es un bloqueo 403."""
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in [
            '403', 'forbidden', 'cloudflare', 'blocked', 'access denied'
        ])

    def _should_wait_for_403_cooldown(self) -> bool:
        """Verifica si debe esperar por cooldown de bloqueo 403."""
        if not self.last_403_block:
            return False
        
        elapsed = (datetime.now() - self.last_403_block).total_seconds()
        return elapsed < self.block_cooldown

    def _get_403_cooldown_remaining(self) -> int:
        """Obtiene el tiempo restante de cooldown en segundos."""
        if not self.last_403_block:
            return 0
        
        elapsed = (datetime.now() - self.last_403_block).total_seconds()
        remaining = max(0, self.block_cooldown - elapsed)
        return int(remaining)

    async def disconnect(self):
        """Desconecta limpiamente de Quotex."""
        if self.quotex and self.connected:
            logger.info("Desconectando de Quotex...")
            try:
                await self.quotex.disconnect()
            except Exception as e:
                logger.warning(f"Error en desconexión: {e}")
            finally:
                self.quotex = None
                self.connected = False
                self.connection_timestamp = None
                logger.info("Desconexión completada")

    def get_connection_status(self) -> Dict[str, Any]:
        """Obtiene el estado detallado de la conexión."""
        status = {
            "connected": self.connected,
            "email": self.email,
            "connection_timestamp": self.connection_timestamp,
            "last_error": self.last_error,
            "quotex_instance": self.quotex is not None,
            "in_403_cooldown": self._should_wait_for_403_cooldown(),
            "cooldown_remaining": self._get_403_cooldown_remaining()
        }
        
        if self.quotex:
            try:
                status["quotex_check_connect"] = self.quotex.check_connect()
                if hasattr(self.quotex, 'api') and self.quotex.api:
                    api = self.quotex.api
                    status["has_ssid"] = bool(getattr(api, "SSID", None))
                    status["websocket_error"] = getattr(api, "check_websocket_if_error", False)
            except Exception as e:
                status["status_check_error"] = str(e)
        
        return status

    async def ensure_connected(self, telegram_bot=None) -> bool:
        """Asegura que la conexión esté activa, reconectando si es necesario."""
        if self.connected and self.quotex and await self._verify_connection():
            return True
        
        logger.info("Conexión no activa, intentando reconectar...")
        return await self.connect(telegram_bot)

    def is_ready_for_trading(self) -> bool:
        """Verifica si el bot está listo para ejecutar operaciones."""
        if not self.connected or not self.quotex:
            return False
        
        # Verificar que no estemos en cooldown de bloqueo 403
        if self._should_wait_for_403_cooldown():
            return False
        
        # Verificar conexión básica usando métodos disponibles
        try:
            if not hasattr(self.quotex, 'api') or not self.quotex.api:
                return False
            
            api = self.quotex.api
            
            # Verificar SSID presente
            if not hasattr(api, 'SSID') or not api.SSID:
                return False
            
            # Verificar que no haya errores de WebSocket
            if hasattr(api, 'check_websocket_if_error') and api.check_websocket_if_error:
                return False
            
            return True
            
        except Exception:
            return False
