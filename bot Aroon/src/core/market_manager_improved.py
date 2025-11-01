"""
MARKET MANAGER MEJORADO CON NUEVA LÓGICA DE CONEXIÓN
Integra el QuotexConnectionManager con la funcionalidad existente del MarketManager
Mantiene compatibilidad hacia atrás mientras mejora la robustez de conexión
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
import requests
from loguru import logger
import pytz

from .quotex_connection_manager import QuotexConnectionManager


class MarketManagerImproved:
    """MarketManager mejorado con lógica robusta de conexión."""
    
    def __init__(self):
        self.connection_manager: Optional[QuotexConnectionManager] = None
        self.mercados_disponibles = []
        self.mercados_otc = []
        self.efectividad_diaria = {}
        self.horarios_noticias = self.cargar_horarios_noticias()
        self.payout_minimo = 80.0
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Compatibilidad con código existente
        self.quotex = None
        self.conectado = False
        self.last_connect_error = None
        self.tstamp_conectado = None
        self.fallos_assets = 0
        self.notificado_visual = False
        
        logger.info("MarketManagerImproved inicializado con nueva lógica de conexión")

    async def conectar_quotex(self, email: str, password: str, telegram_bot=None) -> bool:
        """
        Conecta a Quotex usando el nuevo gestor de conexión mejorado.
        Mantiene compatibilidad con la interfaz existente.
        """
        try:
            # Crear gestor de conexión si no existe
            if not self.connection_manager:
                self.connection_manager = QuotexConnectionManager(email, password, self.data_dir)
            
            # Intentar conexión usando el nuevo gestor
            success = await self.connection_manager.connect(telegram_bot)
            
            if success:
                # Actualizar variables de compatibilidad
                self.quotex = self.connection_manager.quotex
                self.conectado = True
                self.last_connect_error = None
                self.tstamp_conectado = datetime.now()
                self.fallos_assets = 0
                
                # Cargar mercados disponibles
                await self._post_connection_success(telegram_bot)
                
                logger.info("Conexión establecida exitosamente con nuevo gestor")
                return True
            else:
                # Actualizar variables de error
                self.conectado = False
                status = self.connection_manager.get_connection_status()
                self.last_connect_error = status.get("last_error", "Unknown error")
                
                logger.error("Fallo en conexión con nuevo gestor")
                return False
                
        except Exception as e:
            logger.error(f"Error en conectar_quotex mejorado: {e}")
            self.conectado = False
            self.last_connect_error = str(e)
            return False

    async def _post_connection_success(self, telegram_bot=None):
        """Acciones post-conexión exitosa."""
        try:
            # Obtener mercados disponibles
            await self.obtener_mercados_disponibles()
            
            # Notificación ya manejada por QuotexConnectionManager
            logger.info("Acciones post-conexión completadas")
            
        except Exception as e:
            logger.error(f"Error en acciones post-conexión: {e}")

    async def ensure_connection(self, telegram_bot=None) -> bool:
        """
        Asegura que la conexión esté activa, reconectando si es necesario.
        Método nuevo que aprovecha la lógica robusta del gestor.
        """
        if not self.connection_manager:
            logger.warning("No hay gestor de conexión inicializado")
            return False
        
        try:
            success = await self.connection_manager.ensure_connected(telegram_bot)
            
            if success:
                # Sincronizar estado
                self.quotex = self.connection_manager.quotex
                self.conectado = True
                self.last_connect_error = None
                if not self.tstamp_conectado:
                    self.tstamp_conectado = datetime.now()
            else:
                self.conectado = False
                status = self.connection_manager.get_connection_status()
                self.last_connect_error = status.get("last_error", "Connection failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error en ensure_connection: {e}")
            self.conectado = False
            self.last_connect_error = str(e)
            return False

    def verificar_estado_conexion(self) -> dict:
        """
        Devuelve un diagnóstico completo del estado de conexión.
        Mejorado con información del nuevo gestor.
        """
        if not self.connection_manager:
            return {
                "conectado": False,
                "quotex_instance": self.quotex is not None,
                "websocket_connected": False,
                "api_available": False,
                "ssid_present": False,
                "no_websocket_errors": False,
                "thread_alive": False,
                "balance_available": False,
                "internal_check": False,
                "balance_value": None,
                "error_details": "No hay gestor de conexión inicializado",
                "legacy_mode": True,
                "manager_version": "improved"
            }
        
        # Obtener estado del gestor
        manager_status = self.connection_manager.get_connection_status()
        
        # Combinar con información legacy para compatibilidad
        estado = {
            "conectado": manager_status["connected"],
            "quotex_instance": manager_status["quotex_instance"],
            "websocket_connected": self._check_websocket_connected(),
            "api_available": self.quotex is not None,
            "ssid_present": manager_status.get("has_ssid", False),
            "no_websocket_errors": not manager_status.get("websocket_error", True),
            "thread_alive": self._check_websocket_thread_alive(),
            "balance_available": False,
            "internal_check": True,
            "balance_value": None,
            "error_details": manager_status.get("last_error"),
            
            # Información adicional del nuevo gestor
            "connection_timestamp": manager_status.get("connection_timestamp"),
            "in_403_cooldown": manager_status.get("in_403_cooldown", False),
            "cooldown_remaining": manager_status.get("cooldown_remaining", 0),
            "email": manager_status.get("email"),
            "manager_version": "improved"
        }
        
        # Intentar obtener balance si está conectado
        if estado["conectado"] and self.quotex:
            try:
                # Esto debe ser llamado de forma asíncrona, pero para compatibilidad
                # lo marcamos como no disponible aquí
                estado["balance_available"] = True
                estado["balance_value"] = "Requiere llamada async"
            except Exception:
                pass
        
        return estado

    def _check_websocket_connected(self) -> bool:
        """Verifica si el WebSocket está conectado usando métodos disponibles."""
        try:
            if not self.quotex or not hasattr(self.quotex, 'api') or not self.quotex.api:
                return False
            
            api = self.quotex.api
            
            # Verificar usando check_websocket_if_connect si está disponible
            if hasattr(api, 'check_websocket_if_connect'):
                return api.check_websocket_if_connect is not False
            
            # Fallback: verificar SSID como indicador de conexión
            return bool(getattr(api, 'SSID', None))
            
        except Exception:
            return False
    
    def _check_websocket_thread_alive(self) -> bool:
        """Verifica si el thread del WebSocket está activo."""
        try:
            if not self.quotex or not hasattr(self.quotex, 'api') or not self.quotex.api:
                return False
            
            api = self.quotex.api
            
            # Verificar thread de WebSocket si está disponible
            if hasattr(api, 'websocket_thread'):
                ws_thread = api.websocket_thread
                return ws_thread and ws_thread.is_alive() if ws_thread else False
            
            # Fallback: asumir que está vivo si hay SSID
            return bool(getattr(api, 'SSID', None))
            
        except Exception:
            return False

    def is_ready_for_trading(self) -> bool:
        """
        Verifica si el bot está listo para ejecutar operaciones de trading.
        Utiliza la lógica mejorada del gestor de conexión.
        """
        if not self.connection_manager:
            return False
        
        return self.connection_manager.is_ready_for_trading()

    async def desconectar_quotex(self):
        """Desconecta limpiamente usando el nuevo gestor."""
        if self.connection_manager:
            await self.connection_manager.disconnect()
        
        # Limpiar variables de compatibilidad
        self.quotex = None
        self.conectado = False
        self.tstamp_conectado = None
        self.mercados_disponibles = []
        self.mercados_otc = []
        
        logger.info("Desconexión completada")

    # Métodos existentes que se mantienen para compatibilidad
    def cargar_horarios_noticias(self) -> dict:
        """Carga horarios de noticias importantes."""
        try:
            # Asegurar que data_dir esté disponible
            data_dir = getattr(self, 'data_dir', 'data')
            noticias_path = os.path.join(data_dir, "horarios_noticias.json")
            if os.path.exists(noticias_path):
                with open(noticias_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error cargando horarios de noticias: {e}")
        
        # Horarios por defecto
        return {
            "high_impact": [
                {"time": "08:30", "description": "US Employment Data"},
                {"time": "10:00", "description": "US ISM Manufacturing"},
                {"time": "14:00", "description": "FOMC Meeting"},
                {"time": "15:30", "description": "US GDP Data"}
            ],
            "medium_impact": [
                {"time": "09:00", "description": "EU Economic Data"},
                {"time": "12:00", "description": "UK Economic Data"}
            ]
        }

    async def obtener_mercados_disponibles(self) -> List[str]:
        """Obtiene mercados disponibles de Quotex."""
        if not self.quotex:
            logger.warning("No hay conexión a Quotex para obtener mercados")
            return []
        
        try:
            # Obtener activos disponibles
            # Nota: Esto depende de la implementación específica de quotexpy
            # Puede necesitar ajustes según la versión de la librería
            
            # Por ahora, usar lista por defecto de mercados principales
            mercados_principales = [
                "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
                "EURJPY", "GBPJPY", "AUDJPY", "NZDUSD", "USDCHF"
            ]
            
            self.mercados_disponibles = mercados_principales
            logger.info(f"Mercados disponibles cargados: {len(self.mercados_disponibles)}")
            
            return self.mercados_disponibles
            
        except Exception as e:
            logger.error(f"Error obteniendo mercados disponibles: {e}")
            return []

    def obtener_mejor_mercado(self) -> Optional[str]:
        """Obtiene el mejor mercado para operar basado en criterios múltiples."""
        if not self.mercados_disponibles:
            return None
        
        # Por ahora, retornar EUR/USD como mercado principal
        # En el futuro, esto puede incluir lógica más sofisticada
        return "EURUSD"

    def esta_en_horario_permitido(self) -> bool:
        """Verifica si estamos en horario permitido para trading."""
        ahora = datetime.now(pytz.timezone('America/New_York'))
        hora_actual = ahora.hour
        
        # Horario de mercado Forex: 17:00 domingo - 17:00 viernes (EST)
        dia_semana = ahora.weekday()  # 0=Lunes, 6=Domingo
        
        # Evitar fines de semana
        if dia_semana == 5 and hora_actual >= 17:  # Viernes después de 17:00
            return False
        if dia_semana == 6:  # Sábado
            return False
        if dia_semana == 0 and hora_actual < 17:  # Domingo antes de 17:00
            return False
        
        # Evitar horarios de noticias de alto impacto
        hora_str = ahora.strftime("%H:%M")
        for noticia in self.horarios_noticias.get("high_impact", []):
            if abs(ahora.hour - int(noticia["time"].split(":")[0])) <= 1:
                logger.info(f"Evitando trading por noticia: {noticia['description']}")
                return False
        
        return True

    async def get_balance_async(self) -> Optional[float]:
        """Obtiene el balance de forma asíncrona."""
        if not self.quotex:
            return None
        
        try:
            balance = await self.quotex.get_balance()
            return balance if isinstance(balance, (int, float)) else None
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            return None

    def get_connection_health_score(self) -> float:
        """
        Calcula un puntaje de salud de la conexión (0.0 - 1.0).
        1.0 = Conexión perfecta, 0.0 = Sin conexión
        """
        if not self.connection_manager:
            return 0.0
        
        status = self.connection_manager.get_connection_status()
        score = 0.0
        
        # Criterios de evaluación
        if status["connected"]:
            score += 0.4
        
        if status["quotex_instance"]:
            score += 0.2
        
        if status.get("quotex_check_connect", False):
            score += 0.2
        
        if status.get("has_ssid", False):
            score += 0.1
        
        if not status.get("websocket_error", True):
            score += 0.1
        
        # Penalizar si está en cooldown
        if status.get("in_403_cooldown", False):
            score *= 0.5
        
        return min(1.0, score)

    def should_attempt_trading(self) -> Tuple[bool, str]:
        """
        Determina si se debe intentar hacer trading ahora.
        
        Returns:
            Tuple[bool, str]: (should_trade, reason)
        """
        # Verificar conexión
        if not self.is_ready_for_trading():
            return False, "No hay conexión activa a Quotex"
        
        # Verificar horario
        if not self.esta_en_horario_permitido():
            return False, "Fuera del horario permitido para trading"
        
        # Verificar mercados disponibles
        if not self.mercados_disponibles:
            return False, "No hay mercados disponibles"
        
        # Verificar salud de conexión
        health_score = self.get_connection_health_score()
        if health_score < 0.7:
            return False, f"Salud de conexión baja: {health_score:.2f}"
        
        return True, "Listo para trading"


# Función de compatibilidad para código existente
async def obtener_mejor_mercado_del_dia(email: str, password: str) -> Optional[str]:
    """
    Función de compatibilidad que usa el nuevo MarketManagerImproved.
    """
    manager = MarketManagerImproved()
    
    try:
        success = await manager.conectar_quotex(email, password)
        if success:
            return manager.obtener_mejor_mercado()
        else:
            logger.error("No se pudo conectar para obtener mercado")
            return None
    except Exception as e:
        logger.error(f"Error en obtener_mejor_mercado_del_dia: {e}")
        return None
    finally:
        await manager.desconectar_quotex()
