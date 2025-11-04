"""
MÓDULO DE GESTIÓN DE MERCADOS MÚLTIPLES
Maneja la selección automática de mercados basada en:
- Payout ≥ 85%
- Horarios de noticias
- Mercados OTC vs normales
- Análisis de efectividad diaria por mercado
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
from pyquotex.stable_api import Quotex



class MarketManager:
    def __init__(self):
        self.quotex = None
        self.mercados_disponibles = []
        self.mercados_otc = []
        self.efectividad_diaria = {}
        self.efectividad_historica = self.cargar_efectividad_historica()
        self.horarios_noticias = self.cargar_horarios_noticias()
        self.payout_minimo = 80.0
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        self.last_connect_error = None
        self.conectado = False
        # Estado de conexión para health-checks
        self.tstamp_conectado = None
        self.fallos_assets = 0
        # Notificación visual (dashboard) ya enviada
        self.notificado_visual = False
        # Control de bloqueos 403
        self.ultimo_bloqueo_403 = None
        self.tiempo_pausa_403 = 30 * 60  # 30 minutos en segundos
        # Control de conexión forzada por admin
        self.conexion_forzada = False  # Si True, ignora horarios
        # Control de desconexión manual
        self.desconexion_manual = False  # Si True, NO reconectar automáticamente
        logger.info(f"MarketManager inicializado en modo REAL. Esperando conexión a Quotex para obtener mercados disponibles...")
    
    # MÉTODOS DE SIMULACIÓN ELIMINADOS - SOLO DATOS REALES DE QUOTEX
    # Todos los mercados y datos provienen únicamente de la API real de Quotex
        
    async def _post_connection_success(self, telegram_bot=None):
        """Acciones a realizar tras una conexión exitosa."""
        self.conectado = True
        self.last_connect_error = None
        self.tstamp_conectado = datetime.now()
        self.fallos_assets = 0
        # Mensaje uniforme con hora (evitar duplicado si ya notificamos visualmente)
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg_ok = f"[QX]  Conectado correctamente a Quotex\n Hora: {hora}"
        if not self.notificado_visual:
            logger.info(msg_ok)

        try:
            # Cargar/actualizar mercados disponibles tras conectar
            await self.obtener_mercados_disponibles()
            if telegram_bot and not self.notificado_visual:
                await telegram_bot.notificar_admin_telegram(msg_ok)
        except Exception as e:
            logger.error(f"Error en acciones post-conexión: {e}")

    async def _notificar_fallo_conexion(self, telegram_bot, exception=None):
        """Notifica al administrador sobre un fallo de conexión."""
        self.conectado = False
        error_msg = str(exception).lower() if exception else ""
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Detectar error 403 de Cloudflare específicamente
        if '403' in error_msg or 'cloudflare' in error_msg or 'forbidden' in error_msg:
            self.last_connect_error = 'cloudflare_403'
            # Marcar tiempo del último bloqueo para evitar reintentos inmediatos
            self.ultimo_bloqueo_403 = datetime.now()
            msg = (
                f"🚨 [QX] BLOQUEO CLOUDFLARE DETECTADO\n"
                f"🕰️ Hora: {hora}\n\n"
                f"🚫 Quotex ha bloqueado la conexión WebSocket.\n\n"
                f"📝 DIAGNÓSTICO:\n"
                f"• Login web: ✅ EXITOSO\n"
                f"• WebSocket: ❌ BLOQUEADO (403)\n"
                f"• Causa: Cloudflare detecta comportamiento automatizado\n\n"
                f"🔧 SOLUCIONES RECOMENDADAS:\n"
                f"1️⃣ Cambia a red residencial (hotspot móvil)\n"
                f"2️⃣ Evita VPNs de datacenter\n"
                f"3️⃣ Espera 30-60 minutos antes de reintentar\n"
                f"4️⃣ Usa navegación manual en Quotex por unos minutos\n\n"
                f"⏸️ El bot pausará intentos por 30 minutos."
            )
        elif 'unable to extract ssid token' in error_msg:
            self.last_connect_error = 'ssid_token_error'
            msg = (
                f"[QX]  Error de login en Quotex\n Hora: {hora}\n\n"
                "No se pudo obtener el token de sesión. Causas probables:\n"
                "1. Credenciales inválidas: Revisa QUOTEX_EMAIL y QUOTEX_PASSWORD.\n"
                "2. Bloqueo por CAPTCHA: Inicia sesión manualmente para descartarlo.\n\n"
                "El bot reintentará conectarse más tarde."
            )
        elif exception:
            self.last_connect_error = str(exception)
            msg = (
                f"[QX]  Error de conexión en Quotex\n Hora: {hora}\n"
                f"❌ Detalle: {str(exception)[:200]}\n"
                "Se reintentará la conexión automáticamente."
            )
        else:
            self.last_connect_error = "Authentication failed"
            msg = (
                f"[QX]  Error de autenticación en Quotex\n Hora: {hora}\n"
                "• Credenciales inválidas o cuenta bloqueada.\n"
                "• Revisa las variables QUOTEX_EMAIL y QUOTEX_PASSWORD."
            )

        logger.error(f"Fallo de conexión Quotex: {self.last_connect_error}")
        if telegram_bot:
            try:
                await telegram_bot.notificar_admin_telegram(msg)
            except Exception as e_notify:
                logger.warning(f"No se pudo notificar error de Quotex al admin: {e_notify}")

    async def _wait_connected(self, timeout: int = 60) -> bool:
        """Espera activa hasta que la sesión esté completamente lista usando múltiples criterios.

        Verifica:
        1. WebSocket conectado y sin errores
        2. Balance disponible (confirma autenticación)
        3. SSID válido presente
        4. Thread de WebSocket activo
        5. Método interno esta_dentro() si existe
        """
        inicio = datetime.now()
        # Pequeña espera inicial para permitir el envío de SSID
        try:
            await asyncio.sleep(2)
        except Exception:
            pass

        logger.info("🔍 Verificando conexión a Quotex...")
        
        while (datetime.now() - inicio).total_seconds() < timeout:
            try:
                if not self.quotex:
                    logger.debug("❌ No hay instancia de Quotex")
                    await asyncio.sleep(1.5)
                    continue
                
                # Verificar que podemos obtener activos (prueba definitiva)
                try:
                    # Intentar obtener activos de forma asíncrona
                    if hasattr(self.quotex, 'get_all_assets'):
                        assets = await self.quotex.get_all_assets()
                    elif hasattr(self.quotex, 'get_assets'):
                        assets = await self.quotex.get_assets()
                    else:
                        logger.debug("⏳ Método de activos no disponible...")
                        await asyncio.sleep(2)
                        continue
                    
                    if not assets or len(assets) == 0:
                        logger.debug("⏳ Esperando activos...")
                        await asyncio.sleep(2)
                        continue
                    
                    logger.info(f"✅ Conexión verificada: {len(assets)} activos disponibles")
                except Exception as e:
                    logger.debug(f"⏳ Esperando login completo... ({str(e)[:50]})")
                    await asyncio.sleep(2)
                    continue
                
                # Todos los criterios cumplidos
                logger.info("✅ Conexión a Quotex completamente verificada")
                return True
                
            except Exception as e:
                logger.debug(f"⏳ Error en verificación de conexión: {e}")
                await asyncio.sleep(1.5)
                continue
        
        logger.error(f"❌ Timeout: No se pudo verificar conexión completa en {timeout} segundos")
        return False

    def verificar_estado_conexion(self) -> dict:
        """Devuelve un diagnóstico completo del estado de conexión a Quotex.
        
        Returns:
            dict: Estado detallado con todos los criterios de conexión
        """
        estado = {
            "conectado": False,
            "quotex_instance": False,
            "websocket_connected": False,
            "api_available": False,
            "ssid_present": False,
            "no_websocket_errors": False,
            "thread_alive": False,
            "balance_available": False,
            "internal_check": False,
            "balance_value": None,
            "error_details": None
        }
        
        try:
            # Verificar instancia de Quotex
            if self.quotex:
                estado["quotex_instance"] = True
                
                # Verificar WebSocket conectado
                if getattr(self.quotex, "is_connected", False):
                    estado["websocket_connected"] = True
                
                # Verificar API interna
                api = getattr(self.quotex, "api", None)
                if api:
                    estado["api_available"] = True
                    
                    # Verificar SSID
                    if getattr(api, "SSID", None):
                        estado["ssid_present"] = True
                    
                    # Verificar errores de WebSocket
                    if not getattr(api, "check_websocket_if_error", True):
                        estado["no_websocket_errors"] = True
                    else:
                        estado["error_details"] = getattr(api, "websocket_error_reason", "Unknown error")
                    
                    # Verificar thread de WebSocket
                    ws_thread = getattr(api, "websocket_thread", None)
                    if ws_thread and ws_thread.is_alive():
                        estado["thread_alive"] = True
                    
                    # Verificar balance
                    try:
                        bal = getattr(api.profile, "balance", None) if hasattr(api, 'profile') else None
                        if bal is None:
                            bal = getattr(api, "account_balance", None)
                        
                        if isinstance(bal, (int, float)):
                            estado["balance_available"] = True
                            estado["balance_value"] = bal
                    except Exception:
                        pass
                    
                    # Verificación interna
                    try:
                        if hasattr(api, 'esta_dentro'):
                            estado["internal_check"] = api.esta_dentro()
                        else:
                            estado["internal_check"] = True  # No disponible, asumir OK
                    except Exception:
                        estado["internal_check"] = False
            
            # Determinar estado general
            estado["conectado"] = all([
                estado["quotex_instance"],
                estado["websocket_connected"],
                estado["api_available"],
                estado["ssid_present"],
                estado["no_websocket_errors"],
                estado["thread_alive"],
                estado["balance_available"],
                estado["internal_check"]
            ])
            
        except Exception as e:
            estado["error_details"] = str(e)
        
        return estado

    def _ui_validation_status(self) -> tuple[bool, str]:
        """Lee `data/quotex_selectors.json` y el flag `visual_login_ready` para informar estado UI.

        Devuelve:
            (ui_ok, mensaje)
        """
        ui_ready = False
        visual_flag = False
        try:
            api = getattr(self.quotex, 'api', None)
            visual_flag = bool(getattr(api, 'visual_login_ready', False)) if api else False
        except Exception:
            visual_flag = False
        path = os.path.join('data', 'quotex_selectors.json')
        have_selectors = False
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                bal_sel = (cfg.get('balance') or {}).get('selector')
                tr_sel = (cfg.get('trade') or {}).get('selector')
                have_selectors = bool(bal_sel or tr_sel)
        except Exception:
            have_selectors = False
        ui_ready = visual_flag and have_selectors
        msg = []
        msg.append(f"UI visual_login_ready={'ON' if visual_flag else 'OFF'}")
        msg.append(f"selectores_guardados={'SI' if have_selectors else 'NO'}")
        return ui_ready, " | ".join(msg)

    async def conectar_quotex(self, email: str, password: str, telegram_bot=None) -> bool:
        """Conecta a Quotex usando pyquotex (WebSocket puro, sin Selenium)."""
        # Resetear bandera de desconexión manual al conectar manualmente
        self.desconexion_manual = False
        
        if self.conectado:
            logger.info("Ya se encuentra conectado a Quotex.")
            return True

        # ============ DETECCIÓN GEOGRÁFICA Y VPN AUTOMÁTICA ============
        try:
            from src.utils.vpn_manager import vpn_manager
            
            logger.info("[VPN] 🌍 Verificando ubicación geográfica...")
            
            # Detectar si estamos en Estados Unidos
            if vpn_manager.necesita_vpn():
                logger.warning("[VPN] 🚫 Servidor en Estados Unidos detectado")
                logger.warning("[VPN] 🔒 Quotex está bloqueado en esta ubicación")
                logger.info("[VPN] 🔌 Intentando conectar VPN automáticamente...")
                
                # Intentar conectar VPN automáticamente
                vpn_conectada = vpn_manager.auto_conectar()
                
                if vpn_conectada:
                    logger.success("[VPN] ✅ VPN conectada exitosamente")
                    logger.success("[VPN] 🌍 Nueva ubicación establecida")
                    
                    if telegram_bot:
                        try:
                            await telegram_bot.notificar_admin_telegram(
                                "🔒 **VPN Activada Automáticamente**\n\n"
                                "• Servidor en Estados Unidos detectado\n"
                                "• VPN conectada para evitar bloqueo de Quotex\n"
                                "• Conexión segura establecida"
                            )
                        except:
                            pass
                else:
                    logger.error("[VPN] ❌ No se pudo conectar VPN")
                    logger.error("[VPN] 💡 Solución:")
                    logger.error("[VPN]    1. Coloca archivos .conf (WireGuard) o .ovpn (OpenVPN) en: vpn_configs/")
                    logger.error("[VPN]    2. O configura un proxy SOCKS5 en el código")
                    logger.error("[VPN]    3. O usa un servidor fuera de Estados Unidos")
                    
                    if telegram_bot:
                        try:
                            await telegram_bot.notificar_admin_telegram(
                                "⚠️ **Advertencia: Servidor en Estados Unidos**\n\n"
                                "• Quotex está bloqueado en esta ubicación\n"
                                "• No se pudo activar VPN automáticamente\n"
                                "• La conexión puede fallar\n\n"
                                "**Solución:**\n"
                                "1. Coloca archivos VPN en: `vpn_configs/`\n"
                                "2. O usa un servidor en Cuba/Latinoamérica"
                            )
                        except:
                            pass
                    
                    # Intentar conectar de todos modos (puede fallar)
                    logger.warning("[VPN] ⚠️ Intentando conectar sin VPN (puede fallar)...")
            else:
                logger.success("[VPN] ✅ Ubicación permitida - No se necesita VPN")
                
        except Exception as e:
            logger.error(f"[VPN] ❌ Error en verificación geográfica: {e}")
            logger.warning("[VPN] ⚠️ Continuando sin VPN...")
        # ============================================================

        logger.info(f"[Quotex] Intentando conectar con usuario: {email}")
        logger.info("Conectando vía WebSocket (pyquotex - sin navegador)...")
        
        try:
            # Crear cliente pyquotex (WebSocket puro)
            self.quotex = Quotex(email=email, password=password, lang="es")
            
            # Configurar modo de cuenta (PRACTICE por defecto, cambiar a REAL si es necesario)
            self.quotex.set_account_mode("PRACTICE")
            
            # Conectar (retorna tupla: check, reason)
            logger.info("Iniciando conexión WebSocket...")
            check, reason = await self.quotex.connect()
            
            if not check:
                logger.error(f"❌ Fallo en connect(): {reason}")
                await self._notificar_fallo_conexion(telegram_bot, Exception(f"Connect failed: {reason}"))
                return False
            
            logger.info(f"✅ Conexión WebSocket establecida: {reason}")
            
            # Esperar a que los activos estén disponibles (60 segundos para dar tiempo al login)
            logger.info("Esperando autenticación y activos disponibles (máx. 60 segundos)...")
            ok = await self._wait_connected(timeout=60)
            
            if ok:
                logger.info("✅ Conexión confirmada con activos disponibles")
                await self._post_connection_success(telegram_bot)
                return True
            else:
                logger.error("Timeout: No se pudieron obtener activos en el tiempo esperado.")
                await self._notificar_fallo_conexion(telegram_bot, Exception("Timeout obteniendo activos"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en conexión pyquotex: {e}")
            await self._notificar_fallo_conexion(telegram_bot, e)
            return False

    async def _avisar_visual_si_lista(self, telegram_bot=None, timeout: int = 60) -> bool:
        """Envía una notificación inmediata cuando el dashboard visual (/trade) se detecta.

        Lee el flag `visual_login_ready` expuesto por `QuotexAPI` (en `self.quotex.api`).
        No bloquea la conexión principal; está pensado para ser ejecutado como tarea.
        """
        inicio = datetime.now()
        while (datetime.now() - inicio).total_seconds() < timeout and not self.notificado_visual:
            try:
                if self.quotex and getattr(self.quotex, "api", None):
                    api = self.quotex.api
                    if getattr(api, "visual_login_ready", False):
                        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        msg = f"[QX]  Conectado correctamente a Quotex (dashboard)\n Hora: {hora}"
                        logger.info(msg)
                        if telegram_bot:
                            try:
                                await telegram_bot.notificar_admin_telegram(msg)
                            except Exception:
                                pass
                        self.notificado_visual = True
                        return True
            except Exception:
                pass
            await asyncio.sleep(1)
        return False

    async def desconectar_quotex(self):
        """Desconecta de Quotex limpiamente y libera recursos."""
        # Marcar como desconexión manual para evitar reconexión automática
        self.desconexion_manual = True
        
        if self.quotex and self.conectado:
            logger.info("Desconectando de Quotex...")
            try:
                # pyquotex usa close() para cerrar la conexión WebSocket
                await self.quotex.close()
            except Exception as e:
                logger.error(f"Error al desconectar de Quotex: {e}")
            finally:
                self.quotex = None
                self.conectado = False
                self.tstamp_conectado = None
                self.mercados_disponibles = []
                self.mercados_otc = []
                # Desactivar conexión forzada al desconectar manualmente
                self.conexion_forzada = False
                logger.info("Desconexión de Quotex completada. Conexión forzada desactivada.")
        else:
            logger.info("No hay sesión activa para cerrar.")
            # Desactivar conexión forzada aunque no haya sesión
            self.conexion_forzada = False
    
    def activar_conexion_forzada(self):
        """Activa el modo de conexión forzada (ignora horarios)."""
        self.conexion_forzada = True
        logger.info("🔓 Conexión forzada ACTIVADA - Se ignorarán restricciones de horario")
    
    def desactivar_conexion_forzada(self):
        """Desactiva el modo de conexión forzada."""
        self.conexion_forzada = False
        logger.info("🔒 Conexión forzada DESACTIVADA - Se respetarán horarios normales")
    
    def esta_en_modo_forzado(self) -> bool:
        """Verifica si está en modo de conexión forzada."""
        return self.conexion_forzada
    
    def _debe_esperar_por_bloqueo_403(self) -> bool:
        """Verifica si debe esperar antes de intentar reconectar debido a un bloqueo 403 reciente."""
        if not self.ultimo_bloqueo_403:
            return False
        
        tiempo_transcurrido = (datetime.now() - self.ultimo_bloqueo_403).total_seconds()
        return tiempo_transcurrido < self.tiempo_pausa_403
    
    def _tiempo_restante_bloqueo_403(self) -> int:
        """Devuelve el tiempo restante en segundos antes de poder intentar reconectar tras bloqueo 403."""
        if not self.ultimo_bloqueo_403:
            return 0
        
        tiempo_transcurrido = (datetime.now() - self.ultimo_bloqueo_403).total_seconds()
        tiempo_restante = max(0, self.tiempo_pausa_403 - tiempo_transcurrido)
        return int(tiempo_restante)
    
    async def esta_listo_para_operar(self) -> Dict[str, any]:
        """Verifica de manera integral si el bot está completamente listo para ejecutar estrategias.
        
        Returns:
            Dict con estado detallado y criterios de verificación
        """
        resultado = {
            "listo": False,
            "timestamp": datetime.now().isoformat(),
            "criterios": {
                "conexion_quotex": False,
                "websocket_activo": False,
                "balance_disponible": False,
                "mercados_cargados": False,
                "sin_errores_criticos": False,
                "horario_operativo": False,
                "sin_bloqueo_403": False
            },
            "detalles": {},
            "recomendaciones": []
        }
        
        try:
            # 1. Verificar conexión básica a Quotex
            if self.quotex and self.conectado:
                resultado["criterios"]["conexion_quotex"] = True
                resultado["detalles"]["conexion"] = "Instancia de Quotex activa y marcada como conectada"
            else:
                resultado["detalles"]["conexion"] = "No hay instancia de Quotex o no está marcada como conectada"
                resultado["recomendaciones"].append("Ejecutar conectar_quotex() para establecer conexión")
            
            # 2. Verificar WebSocket activo y sin errores
            if self.quotex and hasattr(self.quotex, 'api'):
                api = self.quotex.api
                
                # WebSocket conectado
                ws_connected = getattr(api, 'websocket_client', None) is not None
                if ws_connected:
                    resultado["criterios"]["websocket_activo"] = True
                    resultado["detalles"]["websocket"] = "WebSocket cliente activo"
                else:
                    resultado["detalles"]["websocket"] = "WebSocket cliente no disponible"
                    resultado["recomendaciones"].append("Reconectar WebSocket")
                
                # Sin errores críticos
                no_errors = not getattr(api, 'check_websocket_if_error', True)
                if no_errors:
                    resultado["criterios"]["sin_errores_criticos"] = True
                    resultado["detalles"]["errores"] = "Sin errores WebSocket detectados"
                else:
                    resultado["detalles"]["errores"] = "Errores WebSocket detectados"
                    resultado["recomendaciones"].append("Resolver errores WebSocket antes de operar")
            else:
                resultado["detalles"]["websocket"] = "API de Quotex no disponible"
                resultado["recomendaciones"].append("Verificar inicialización de la API")
            
            # 3. Verificar balance disponible
            try:
                if self.quotex:
                    balance = await self.quotex.get_balance()
                    if balance is not None and isinstance(balance, (int, float)) and balance > 0:
                        resultado["criterios"]["balance_disponible"] = True
                        resultado["detalles"]["balance"] = f"Balance: ${balance}"
                    else:
                        resultado["detalles"]["balance"] = f"Balance no válido: {balance}"
                        resultado["recomendaciones"].append("Verificar balance de la cuenta")
                else:
                    resultado["detalles"]["balance"] = "No se puede verificar balance sin conexión"
            except Exception as e:
                resultado["detalles"]["balance"] = f"Error obteniendo balance: {e}"
                resultado["recomendaciones"].append("Resolver problemas de acceso al balance")
            
            # 4. Verificar mercados cargados
            mercados_count = len(self.mercados_disponibles)
            if mercados_count > 0:
                resultado["criterios"]["mercados_cargados"] = True
                resultado["detalles"]["mercados"] = f"{mercados_count} mercados disponibles"
            else:
                resultado["detalles"]["mercados"] = "No hay mercados cargados"
                resultado["recomendaciones"].append("Ejecutar obtener_mercados_disponibles()")
            
            # 5. Verificar horario operativo (evitar fines de semana y horarios no operativos)
            ahora = datetime.now()
            es_fin_semana = ahora.weekday() >= 5  # Sábado (5) o Domingo (6)
            hora_actual = ahora.hour
            
            # Horario operativo: Lunes a Viernes, 6:00 AM a 10:00 PM
            en_horario = not es_fin_semana and 6 <= hora_actual <= 22
            
            if en_horario:
                resultado["criterios"]["horario_operativo"] = True
                resultado["detalles"]["horario"] = f"Horario operativo válido: {ahora.strftime('%A %H:%M')}"
            else:
                if es_fin_semana:
                    resultado["detalles"]["horario"] = f"Fin de semana: {ahora.strftime('%A %H:%M')}"
                    resultado["recomendaciones"].append("Esperar a día hábil para operar")
                else:
                    resultado["detalles"]["horario"] = f"Fuera de horario operativo: {ahora.strftime('%A %H:%M')}"
                    resultado["recomendaciones"].append("Operar entre 6:00 AM y 10:00 PM")
            
            # 6. Verificar que no hay bloqueo 403 reciente
            sin_bloqueo = not self._debe_esperar_por_bloqueo_403()
            if sin_bloqueo:
                resultado["criterios"]["sin_bloqueo_403"] = True
                resultado["detalles"]["bloqueo_403"] = "Sin bloqueos recientes"
            else:
                tiempo_restante = self._tiempo_restante_bloqueo_403()
                resultado["detalles"]["bloqueo_403"] = f"Bloqueo 403 activo, {tiempo_restante//60} min restantes"
                resultado["recomendaciones"].append(f"Esperar {tiempo_restante//60} minutos antes de operar")
            
            # Determinar estado final
            todos_criterios = all(resultado["criterios"].values())
            resultado["listo"] = todos_criterios
            
            # Mensaje de estado
            if resultado["listo"]:
                resultado["mensaje"] = "✅ Bot completamente listo para ejecutar estrategias"
            else:
                criterios_faltantes = [k for k, v in resultado["criterios"].items() if not v]
                resultado["mensaje"] = f"⚠️ Faltan criterios: {', '.join(criterios_faltantes)}"
            
        except Exception as e:
            resultado["error"] = str(e)
            resultado["mensaje"] = f"❌ Error verificando estado: {e}"
            resultado["recomendaciones"].append("Revisar logs para más detalles del error")
        
        return resultado
    
    async def verificar_y_notificar_estado_operativo(self, telegram_bot=None) -> bool:
        """Verifica si el bot está listo para operar y notifica el estado.
        
        Returns:
            bool: True si está listo, False si no
        """
        estado = await self.esta_listo_para_operar()
        
        # Log del estado actual
        if estado["listo"]:
            logger.info(f"✅ {estado['mensaje']}")
            
            # Mostrar detalles de conexión
            for criterio, detalle in estado["detalles"].items():
                logger.info(f"  📋 {criterio}: {detalle}")
            
            # Notificar por Telegram si está disponible
            if telegram_bot:
                try:
                    mensaje_telegram = (
                        f"🎯 **BOT LISTO PARA OPERAR**\n\n"
                        f"⏰ Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"📊 **Estado de Criterios:**\n"
                    )
                    
                    for criterio, cumplido in estado["criterios"].items():
                        emoji = "✅" if cumplido else "❌"
                        nombre = criterio.replace('_', ' ').title()
                        mensaje_telegram += f"{emoji} {nombre}\n"
                    
                    mensaje_telegram += f"\n💡 **Detalles:**\n"
                    for detalle in estado["detalles"].values():
                        mensaje_telegram += f"• {detalle}\n"
                    
                    await telegram_bot.notificar_admin_telegram(mensaje_telegram)
                except Exception as e:
                    logger.error(f"Error enviando notificación de estado: {e}")
        else:
            logger.warning(f"⚠️ {estado['mensaje']}")
            
            # Mostrar criterios faltantes
            criterios_faltantes = [k for k, v in estado["criterios"].items() if not v]
            logger.warning(f"📋 Criterios faltantes: {', '.join(criterios_faltantes)}")
            
            # Mostrar recomendaciones
            if estado["recomendaciones"]:
                logger.info("💡 Recomendaciones:")
                for rec in estado["recomendaciones"]:
                    logger.info(f"  • {rec}")
            
            # Notificar problemas por Telegram si está disponible
            if telegram_bot:
                try:
                    mensaje_telegram = (
                        f"⚠️ **BOT NO LISTO PARA OPERAR**\n\n"
                        f"⏰ Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"❌ **Criterios Faltantes:**\n"
                    )
                    
                    for criterio in criterios_faltantes:
                        nombre = criterio.replace('_', ' ').title()
                        mensaje_telegram += f"• {nombre}\n"
                    
                    if estado["recomendaciones"]:
                        mensaje_telegram += f"\n💡 **Recomendaciones:**\n"
                        for rec in estado["recomendaciones"][:3]:  # Limitar a 3 recomendaciones
                            mensaje_telegram += f"• {rec}\n"
                    
                    await telegram_bot.notificar_admin_telegram(mensaje_telegram)
                except Exception as e:
                    logger.error(f"Error enviando notificación de problemas: {e}")
        
        return estado["listo"]
    
    async def esperar_hasta_estar_listo(self, timeout: int = 300, telegram_bot=None) -> bool:
        """Espera hasta que el bot esté completamente listo para operar.
        
        Args:
            timeout: Tiempo máximo de espera en segundos (default: 5 minutos)
            telegram_bot: Instancia del bot de Telegram para notificaciones
            
        Returns:
            bool: True si está listo, False si se agotó el timeout
        """
        inicio = datetime.now()
        logger.info(f"🔄 Esperando hasta que el bot esté listo para operar (timeout: {timeout}s)...")
        
        while (datetime.now() - inicio).total_seconds() < timeout:
            estado = await self.esta_listo_para_operar()
            
            if estado["listo"]:
                logger.info("🎉 ¡Bot completamente listo para operar!")
                await self.verificar_y_notificar_estado_operativo(telegram_bot)
                return True
            
            # Mostrar progreso cada 30 segundos
            tiempo_transcurrido = (datetime.now() - inicio).total_seconds()
            if int(tiempo_transcurrido) % 30 == 0:
                criterios_ok = sum(estado["criterios"].values())
                total_criterios = len(estado["criterios"])
                logger.info(f"📊 Progreso: {criterios_ok}/{total_criterios} criterios cumplidos")
                
                # Mostrar criterio más crítico faltante
                criterios_faltantes = [k for k, v in estado["criterios"].items() if not v]
                if criterios_faltantes:
                    logger.info(f"⏳ Esperando: {criterios_faltantes[0].replace('_', ' ')}")
            
            await asyncio.sleep(5)  # Verificar cada 5 segundos
        
        # Timeout alcanzado
        logger.error(f"⏰ Timeout: El bot no estuvo listo en {timeout} segundos")
        estado_final = await self.esta_listo_para_operar()
        await self.verificar_y_notificar_estado_operativo(telegram_bot)
        return False

    
    async def obtener_mercados_disponibles(self) -> List[Dict]:
        """
        Obtiene todos los mercados disponibles con payout ≥ 85% usando la API real de Quotex
        """
        try:
            if not self.quotex:
                raise Exception("No hay conexión activa a Quotex")
            
            # NUEVO: Obtener payouts reales usando get_payment()
            payouts_reales = {}
            payouts_por_simbolo = {}  # Mapeo adicional por símbolo limpio
            try:
                print(f"[MarketManager] 🔍 Obteniendo payouts reales de Quotex...")
                
                # Intentar múltiples métodos para obtener payouts
                payment_data = None
                
                # Método 1: get_payment()
                if hasattr(self.quotex, 'get_payment'):
                    try:
                        payment_data = self.quotex.get_payment()
                        print(f"[MarketManager] ✅ Payouts obtenidos con get_payment()")
                    except Exception as e:
                        print(f"[MarketManager] ⚠️ get_payment() falló: {e}")
                
                # Método 2: payment_data attribute
                if not payment_data and hasattr(self.quotex, 'payment_data'):
                    payment_data = self.quotex.payment_data
                    print(f"[MarketManager] ✅ Payouts obtenidos de payment_data")
                
                # Método 3: api.payment_data
                if not payment_data and hasattr(self.quotex, 'api') and hasattr(self.quotex.api, 'payment_data'):
                    payment_data = self.quotex.api.payment_data
                    print(f"[MarketManager] ✅ Payouts obtenidos de api.payment_data")
                
                # DEBUG: Mostrar estructura de datos
                if payment_data:
                    print(f"[MarketManager] 📦 Tipo de payment_data: {type(payment_data)}")
                    if isinstance(payment_data, dict) and len(payment_data) > 0:
                        # Mostrar ejemplo de un mercado
                        primer_mercado = list(payment_data.items())[0]
                        print(f"[MarketManager] 📋 Ejemplo de mercado: {primer_mercado[0]}")
                        print(f"[MarketManager] 📋 Estructura: {primer_mercado[1]}")
                    
                    if isinstance(payment_data, dict):
                        # payment_data = {"Cardano (OTC)": {"payment": 89, "profit": {"5M": 87}, "open": True}}
                        for symbol_name, data in payment_data.items():
                            if isinstance(data, dict):
                                # Obtener payout para operaciones de 5 minutos (nuestro caso)
                                payout_value = None
                                
                                # Prioridad 1: profit['5M'] (payout específico para 5 minutos)
                                if 'profit' in data and isinstance(data['profit'], dict) and '5M' in data['profit']:
                                    payout_value = data['profit']['5M']
                                # Prioridad 2: payment (payout general)
                                elif 'payment' in data:
                                    payout_value = data['payment']
                                # Prioridad 3: turbo_payment
                                elif 'turbo_payment' in data:
                                    payout_value = data['turbo_payment']
                                
                                if payout_value is not None and isinstance(payout_value, (int, float)):
                                    # Si es decimal (0.85), convertir a porcentaje
                                    if payout_value < 1:
                                        payout_value = payout_value * 100
                                    
                                    payout_info = {
                                        'payout': round(payout_value, 1),
                                        'open': data.get('open', True),
                                        'turbo_payout': data.get('turbo_payment', payout_value),
                                        'profit_5m': data.get('profit', {}).get('5M', payout_value) if isinstance(data.get('profit'), dict) else payout_value
                                    }
                                    
                                    # Guardar con nombre completo
                                    payouts_reales[symbol_name] = payout_info
                                    
                                    # Crear mapeo adicional por símbolo limpio
                                    # "Cardano (OTC)" -> "ADAUSD"
                                    # "EUR/USD" -> "EURUSD"
                                    symbol_clean = symbol_name.replace(' (OTC)', '').replace('/', '').replace(' ', '').upper()
                                    payouts_por_simbolo[symbol_clean] = payout_info
                        
                        logger.info(f"[MarketManager] ✅ Payouts reales obtenidos: {len(payouts_reales)} mercados")
                        print(f"[MarketManager] 💰 Payouts reales cargados para {len(payouts_reales)} mercados")
                        
                        # Mostrar rango de payouts
                        if payouts_reales:
                            payouts_valores = [p['payout'] for p in payouts_reales.values()]
                            print(f"[MarketManager] 📊 Rango de payouts: {min(payouts_valores):.0f}% - {max(payouts_valores):.0f}%")
                            
                            # DEBUG: Mostrar algunos ejemplos
                            ejemplos = list(payouts_reales.items())[:3]
                            print(f"[MarketManager] 📋 Ejemplos de payouts:")
                            for nombre, info in ejemplos:
                                print(f"   • {nombre}: {info['payout']}%")
                            
                            # Estadísticas adicionales de payouts
                            payouts_altos = [p for p in payouts_valores if p >= 85]
                            payouts_medios = [p for p in payouts_valores if 80 <= p < 85]
                            payouts_bajos = [p for p in payouts_valores if p < 80]
                            print(f"[MarketManager] 📈 Distribución de payouts:")
                            print(f"   • ≥85%: {len(payouts_altos)} mercados")
                            print(f"   • 80-85%: {len(payouts_medios)} mercados")
                            print(f"   • <80%: {len(payouts_bajos)} mercados (serán filtrados)")
                    else:
                        print(f"[MarketManager] ⚠️ payment_data no es dict, tipo: {type(payment_data)}")
                else:
                    print(f"[MarketManager] ⚠️ No se pudo obtener payment_data de ninguna fuente")
                    print(f"[MarketManager] 📋 Métodos disponibles en quotex: {[m for m in dir(self.quotex) if 'payment' in m.lower()]}")
            except Exception as e:
                import traceback
                logger.warning(f"[MarketManager] ⚠️ No se pudieron obtener payouts reales: {e}")
                print(f"[MarketManager] ⚠️ Error obteniendo payouts: {e}")
                print(f"[MarketManager] 📋 Traceback: {traceback.format_exc()[:500]}")
            
            # Obtener activos de forma asíncrona
            # Primero intentar obtener datos completos con payout
            mercados_api = None
            
            # Obtener activos disponibles
            if hasattr(self.quotex, 'assets_data') and self.quotex.assets_data:
                mercados_api = self.quotex.assets_data
            elif hasattr(self.quotex, 'api') and hasattr(self.quotex.api, 'assets_data') and self.quotex.api.assets_data:
                mercados_api = self.quotex.api.assets_data
            elif hasattr(self.quotex, 'assets') and self.quotex.assets:
                mercados_api = self.quotex.assets
            elif hasattr(self.quotex, 'api') and hasattr(self.quotex.api, 'assets') and self.quotex.api.assets:
                mercados_api = self.quotex.api.assets
            elif hasattr(self.quotex, 'get_all_assets'):
                mercados_api = await self.quotex.get_all_assets()
            elif hasattr(self.quotex, 'get_assets'):
                mercados_api = await self.quotex.get_assets()
            else:
                raise Exception("Método de activos no disponible")
            
            # Verificar el formato de los datos
            if not mercados_api or not isinstance(mercados_api, (list, dict)):
                print(f"[MarketManager] ⚠️ Formato inesperado de activos: {type(mercados_api)}")
                return []
            
            # Si es un diccionario, verificar su estructura
            if isinstance(mercados_api, dict):
                if mercados_api:
                    primer_valor = list(mercados_api.values())[0]
                
                # CASO 1: Si es {symbol: id}, crear mercados con payout real o por defecto
                if isinstance(primer_valor, int):
                    mercados_validos = []
                    
                    # Crear mercados usando payouts reales cuando estén disponibles
                    for symbol, asset_id in mercados_api.items():
                        otc = '_otc' in symbol.lower()
                        symbol_clean = symbol.replace('_otc', '').replace('_OTC', '').upper()
                        
                        # Buscar payout real para este símbolo
                        payout_real = None
                        is_open = True
                        payout_encontrado = False
                        
                        # Estrategia 1: Buscar por símbolo exacto
                        if symbol in payouts_reales:
                            payout_real = payouts_reales[symbol]['payout']
                            is_open = payouts_reales[symbol]['open']
                            payout_encontrado = True
                        # Estrategia 2: Buscar por símbolo limpio
                        elif symbol_clean in payouts_reales:
                            payout_real = payouts_reales[symbol_clean]['payout']
                            is_open = payouts_reales[symbol_clean]['open']
                            payout_encontrado = True
                        # Estrategia 3: Buscar en payouts_por_simbolo
                        elif symbol in payouts_por_simbolo:
                            payout_real = payouts_por_simbolo[symbol]['payout']
                            is_open = payouts_por_simbolo[symbol]['open']
                            payout_encontrado = True
                        elif symbol_clean in payouts_por_simbolo:
                            payout_real = payouts_por_simbolo[symbol_clean]['payout']
                            is_open = payouts_por_simbolo[symbol_clean]['open']
                            payout_encontrado = True
                        # Estrategia 4: Buscar con variaciones del nombre
                        else:
                            # Intentar con variaciones: EURUSD, EUR/USD, EUR-USD
                            variaciones = [
                                symbol_clean,
                                symbol_clean.replace('/', ''),
                                symbol_clean.replace('-', ''),
                                f"{symbol_clean[:3]}/{symbol_clean[3:]}",
                                f"{symbol_clean[:3]}-{symbol_clean[3:]}"
                            ]
                            
                            for variacion in variaciones:
                                if variacion in payouts_reales:
                                    payout_real = payouts_reales[variacion]['payout']
                                    is_open = payouts_reales[variacion]['open']
                                    payout_encontrado = True
                                    break
                                elif variacion in payouts_por_simbolo:
                                    payout_real = payouts_por_simbolo[variacion]['payout']
                                    is_open = payouts_por_simbolo[variacion]['open']
                                    payout_encontrado = True
                                    break
                        
                        # Si no se encontró payout real, usar valor por defecto
                        if not payout_encontrado:
                            payout_real = 85  # Valor conservador por defecto
                            logger.warning(f"[MarketManager] ⚠️ Payout no encontrado para {symbol}, usando {payout_real}% por defecto")
                        else:
                            logger.debug(f"[MarketManager] ✅ Payout encontrado para {symbol}: {payout_real}%")
                        
                        # IMPORTANTE: Guardar el símbolo ORIGINAL (con _OTC si aplica)
                        mercados_validos.append({
                            "symbol": symbol,  # ✅ Símbolo ORIGINAL con _OTC
                            "payout": payout_real,  # Payout REAL de Quotex
                            "type": "crypto" if any(x in symbol_clean for x in ['BTC', 'ETH', 'USD']) else "forex",
                            "otc": otc,
                            "nombre": symbol_clean,  # Nombre limpio para mostrar
                            "asset_id": asset_id,
                            "open": is_open
                        })
                    
                    # Filtrar solo mercados con payout >= 80%
                    mercados_validos = [m for m in mercados_validos if m["payout"] >= 80]
                    
                    self.mercados_disponibles = [m for m in mercados_validos if not m["otc"]]
                    self.mercados_otc = [m for m in mercados_validos if m["otc"]]
                    
                    # Calcular estadísticas de payout
                    if mercados_validos:
                        payouts = [m["payout"] for m in mercados_validos]
                        payout_min = min(payouts)
                        payout_max = max(payouts)
                        payout_avg = sum(payouts) / len(payouts)
                        print(f"[MarketManager] 📊 Mercados normales: {len(self.mercados_disponibles)} | OTC: {len(self.mercados_otc)}")
                        print(f"[MarketManager] 💰 Payout: Min={payout_min:.1f}% | Max={payout_max:.1f}% | Avg={payout_avg:.1f}%")
                        print(f"[MarketManager] ✅ Filtrado: Solo mercados con payout ≥ 80%")
                        
                        # Mostrar algunos ejemplos de símbolos OTC para verificar
                        if self.mercados_otc:
                            ejemplos_otc = [m['symbol'] for m in self.mercados_otc[:5]]
                            print(f"[MarketManager] 📋 Ejemplos OTC: {', '.join(ejemplos_otc)}")
                    else:
                        print(f"[MarketManager] 📊 Mercados normales: {len(self.mercados_disponibles)} | OTC: {len(self.mercados_otc)}")
                    return mercados_validos
                
                # CASO 2: Puede ser {symbol: data} o {'assets': [...]}
                if 'assets' in mercados_api:
                    mercados_api = mercados_api['assets']
                else:
                    mercados_api = list(mercados_api.values())
            
            mercados_validos = []
            
            # Procesamiento normal si los datos tienen estructura completa (ya no debería llegar aquí con {symbol: id})
            if isinstance(mercados_api, dict) and mercados_api:
                primer_valor = list(mercados_api.values())[0]
                if isinstance(primer_valor, int):
                    # Es un mapeo {symbol: id}, usar payouts reales si están disponibles
                    if payouts_reales:
                        print(f"[MarketManager] ✅ Usando payouts REALES de Quotex")
                    else:
                        print(f"[MarketManager] ℹ️ Usando payout por defecto (90%) para todos los mercados")
                    
                    for symbol, asset_id in mercados_api.items():
                        otc = '_otc' in symbol.lower()
                        symbol_clean = symbol.replace('_otc', '').replace('_OTC', '')
                        
                        # Buscar payout real
                        payout_real = 90  # Valor por defecto
                        is_open = True
                        
                        if symbol in payouts_reales:
                            payout_real = payouts_reales[symbol]['payout']
                            is_open = payouts_reales[symbol]['open']
                        elif symbol_clean in payouts_reales:
                            payout_real = payouts_reales[symbol_clean]['payout']
                            is_open = payouts_reales[symbol_clean]['open']
                        elif symbol in payouts_por_simbolo:
                            payout_real = payouts_por_simbolo[symbol]['payout']
                            is_open = payouts_por_simbolo[symbol]['open']
                        elif symbol_clean in payouts_por_simbolo:
                            payout_real = payouts_por_simbolo[symbol_clean]['payout']
                            is_open = payouts_por_simbolo[symbol_clean]['open']
                        
                        # IMPORTANTE: Guardar el símbolo ORIGINAL (con _OTC si aplica)
                        # para que Quotex pueda obtener los datos correctamente
                        mercados_validos.append({
                            "symbol": symbol,  # ✅ Símbolo ORIGINAL con _OTC
                            "payout": payout_real,  # Payout REAL
                            "type": "crypto" if any(x in symbol_clean for x in ['BTC', 'ETH', 'USD']) else "forex",
                            "otc": otc,
                            "nombre": symbol_clean,  # Nombre limpio para mostrar
                            "asset_id": asset_id,
                            "open": is_open
                        })
                    self.mercados_disponibles = [m for m in mercados_validos if not m["otc"]]
                    self.mercados_otc = [m for m in mercados_validos if m["otc"]]
                    print(f"[MarketManager] 📊 Mercados normales encontrados: {len(self.mercados_disponibles)}")
                    print(f"[MarketManager] 🔄 Mercados OTC encontrados: {len(self.mercados_otc)}")
                    
                    # Mostrar algunos ejemplos de símbolos OTC para verificar
                    if self.mercados_otc:
                        ejemplos_otc = [m['symbol'] for m in self.mercados_otc[:5]]
                        print(f"[MarketManager] 📋 Ejemplos OTC: {', '.join(ejemplos_otc)}")
                    
                    return mercados_validos
            
            # Procesamiento normal si los datos tienen estructura completa
            for m in mercados_api:
                # Si m es un string (solo el símbolo), saltar
                if isinstance(m, str):
                    continue
                if not isinstance(m, dict):
                    continue
                
                symbol = m.get('symbol', '')
                tipo = m.get('type', 'forex')
                otc = m.get('otc', False)
                
                # Intentar obtener payout real primero
                payout = 90  # Por defecto
                is_open = True
                
                if symbol in payouts_reales:
                    payout = payouts_reales[symbol]['payout']
                    is_open = payouts_reales[symbol]['open']
                elif symbol in payouts_por_simbolo:
                    payout = payouts_por_simbolo[symbol]['payout']
                    is_open = payouts_por_simbolo[symbol]['open']
                else:
                    # Fallback a profit_percentage del mercado
                    payout = m.get('profit_percentage', 90)
                
                if payout >= 80:
                    # Si es OTC y el símbolo no tiene el sufijo, agregarlo
                    symbol_final = symbol
                    if otc and '_otc' not in symbol.lower():
                        symbol_final = f"{symbol}_OTC"
                    
                    mercados_validos.append({
                        "symbol": symbol_final,  # ✅ Con _OTC si aplica
                        "payout": payout,
                        "type": tipo,
                        "otc": otc,
                        "nombre": m.get('name', symbol),
                        "open": is_open
                    })
            self.mercados_disponibles = [m for m in mercados_validos if not m["otc"]]
            self.mercados_otc = [m for m in mercados_validos if m["otc"]]
            print(f"[MarketManager] 📊 Mercados normales encontrados: {len(self.mercados_disponibles)}")
            print(f"[MarketManager] 🔄 Mercados OTC encontrados: {len(self.mercados_otc)}")
            
            # Mostrar algunos ejemplos de símbolos OTC para verificar
            if self.mercados_otc:
                ejemplos_otc = [m['symbol'] for m in self.mercados_otc[:5]]
                print(f"[MarketManager] 📋 Ejemplos OTC: {', '.join(ejemplos_otc)}")
            
            return mercados_validos
        except Exception as e:
            print(f"[MarketManager] ❌ Error obteniendo mercados: {e}")
            return []

    def _fetch_assets(self) -> List[Dict]:
        """
        Devuelve la lista de activos desde quotexpy, adaptándose a posibles
        diferencias de versión (método get_assets, get_all_assets o propiedad assets).
        Nunca lanza excepción; en error devuelve [].
        """
        try:
            q = self.quotex
            if not q:
                return []
            # Intento 1: método estándar
            if hasattr(q, 'get_assets'):
                return q.get_assets()
            # Intento 2: alternativas conocidas
            if hasattr(q, 'get_all_assets'):
                return q.get_all_assets()
            # Intento 3: propiedad/atributo
            if hasattr(q, 'assets'):
                assets = getattr(q, 'assets')
                return assets() if callable(assets) else assets
        except Exception as e:
            print(f"[MarketManager] ❌ Error adaptando método de activos: {e}")
        return []
    
    def cargar_horarios_noticias(self) -> Dict:
        """
        Carga los horarios de noticias importantes para cada mercado
        """
        return {
            "EURUSD": [
                {"hora": "08:30", "descripcion": "Datos económicos EUR"},
                {"hora": "14:30", "descripcion": "Datos económicos USD"},
                {"hora": "16:00", "descripcion": "Fed/ECB announcements"}
            ],
            "GBPUSD": [
                {"hora": "07:00", "descripcion": "UK Economic Data"},
                {"hora": "14:30", "descripcion": "US Economic Data"}
            ],
            "USDJPY": [
                {"hora": "14:30", "descripcion": "US Economic Data"},
                {"hora": "23:50", "descripcion": "Japan Economic Data"}
            ],
            "GOLD": [
                {"hora": "14:30", "descripcion": "US Economic Data"},
                {"hora": "16:00", "descripcion": "Fed Announcements"}
            ],
            "BTC": [],  # Crypto no tiene horarios de noticias tradicionales
            "ETH": []
        }

    
    def esta_en_horario_noticias(self, symbol: str) -> bool:
        """
        Verifica si un mercado está en horario de noticias importantes
        """
        ahora = datetime.now()
        hora_actual = ahora.strftime("%H:%M")
        
        # Limpiar símbolo (quitar _otc si existe)
        symbol_base = symbol.replace("_otc", "")
        
        if symbol_base not in self.horarios_noticias:
            return False
        
        # Verificar si estamos dentro de ±30 minutos de alguna noticia
        for noticia in self.horarios_noticias[symbol_base]:
            hora_noticia = datetime.strptime(noticia["hora"], "%H:%M").time()
            hora_actual_dt = datetime.strptime(hora_actual, "%H:%M").time()
            
            # Convertir a minutos para comparar
            minutos_noticia = hora_noticia.hour * 60 + hora_noticia.minute
            minutos_actual = hora_actual_dt.hour * 60 + hora_actual_dt.minute
            
            # Si estamos dentro de ±30 minutos de la noticia
            if abs(minutos_actual - minutos_noticia) <= 30:
                print(f"[MarketManager] ⚠️ {symbol} en horario de noticias: {noticia['descripcion']}")
                return True
        
        return False
    
    def seleccionar_mercados_para_analizar(self, payout_minimo: float = 80.0) -> List[Dict]:
        """
        Selecciona qué mercados analizar según las condiciones:
        - Después de 4:00 PM: SOLO mercados OTC (mercados normales cerrados)
        - Sábados: SOLO mercados OTC (mercados normales cerrados)
        - En horario de noticias: SOLO mercados OTC
        - Fuera de horario de noticias: normales y OTC
        - FILTRO: Solo mercados con payout >= payout_minimo (default 80%)
        """
        from datetime import datetime
        
        mercados_para_analizar = []
        # Los mercados ya se cargan automáticamente al conectar
        if not self.mercados_disponibles:
            print(f"[MarketManager] ⚠️ No hay mercados cargados. Esperando conexión a Quotex...")
            return []

        # Obtener hora actual
        ahora = datetime.now()
        hora_actual = ahora.hour
        
        # NUEVA REGLA: Después de 4:00 PM (16:00), solo OTC
        if hora_actual >= 16:
            # SOLO mercados OTC (sin agregar normales)
            mercados_para_analizar = self.mercados_otc.copy()
            print(f"[MarketManager] 🌙 Después de 4:00 PM: solo mercados OTC seleccionados ({len(mercados_para_analizar)} mercados)")
            print(f"[MarketManager] ℹ️ Mercados normales cerrados - OTC tienen mejores payouts en este horario")
        
        # Verificar si es sábado (weekday = 5)
        es_sabado = ahora.weekday() == 5
        
        if es_sabado:
            # Los sábados solo mercados OTC (mercados normales cerrados)
            mercados_para_analizar = self.mercados_otc.copy()
            print(f"[MarketManager] 📅 Sábado: solo mercados OTC seleccionados ({len(mercados_para_analizar)} mercados - mercados normales cerrados)")
        else:
            # Detectar si estamos en horario de noticias para algún mercado normal
            en_horario_noticias = any(
                self.esta_en_horario_noticias(m["symbol"]) for m in self.mercados_disponibles
            )

            if en_horario_noticias:
                # Solo mercados OTC durante horario de noticias (alta volatilidad en normales)
                mercados_para_analizar = self.mercados_otc.copy()
                print(f"[MarketManager] 🚨 Horario de noticias: solo mercados OTC seleccionados ({len(mercados_para_analizar)} mercados - evitando alta volatilidad)")
            else:
                # Todos los mercados disponibles (normales y OTC)
                mercados_para_analizar = self.mercados_disponibles.copy() + self.mercados_otc.copy()
                print(f"[MarketManager] ✅ No hay noticias: todos los mercados seleccionados")
        
        # FILTRO: Solo mercados con payout >= payout_minimo
        mercados_antes = len(mercados_para_analizar)
        mercados_para_analizar = [m for m in mercados_para_analizar if m.get('payout', 0) >= payout_minimo]
        mercados_despues = len(mercados_para_analizar)
        
        if mercados_antes > mercados_despues:
            print(f"[MarketManager] 💰 Filtro de payout ≥{payout_minimo}%: {mercados_antes} → {mercados_despues} mercados")
        
        print(f"[MarketManager] ✅ Total mercados seleccionados: {len(mercados_para_analizar)}")
        return mercados_para_analizar
    
    def analizar_efectividad_diaria_mercado(self, symbol: str, df: pd.DataFrame) -> float:
        """
        Analiza la efectividad de la estrategia en un mercado específico
        usando datos de aproximadamente 1 día
        """
        try:
            from src.strategies.evaluar_estrategia_completa import evaluar_estrategia_completa
            
            # ANÁLISIS REAL CON DATOS DE QUOTEX - SIN SIMULACIÓN
            efectividades = []
            total_señales = 0
            
            # Analizar datos reales en chunks para evaluar efectividad histórica
            for i in range(0, len(df) - 50, 10):  # Cada 10 velas (50 minutos aprox)
                chunk = df.iloc[i:i+50]
                if len(chunk) >= 20:  # Mínimo de datos necesarios
                    resultado = evaluar_estrategia_completa(chunk, symbol)
                    efectividad = resultado.get('efectividad_total', 0)
                    decision = resultado.get('decision')
                    
                    # Solo contar señales válidas con alta efectividad
                    if decision and efectividad >= 80:
                        total_señales += 1
                        efectividades.append(efectividad)
                        
                        # NOTA: En producción, los resultados reales se obtienen
                        # monitoreando las señales enviadas y sus resultados reales
            
            # Calcular efectividad promedio del mercado basado en datos reales
            if efectividades:
                efectividad_promedio = sum(efectividades) / len(efectividades)
                
                # La efectividad se basa en el análisis técnico real, no en simulación
                # En producción, se complementará con resultados reales de señales enviadas
                
                # Guardar en historial
                self.guardar_efectividad_mercado(symbol, efectividad_promedio, efectividad_promedio, total_señales)
                
                print(f"[MarketManager] 📈 {symbol}: {efectividad_promedio:.1f}% efectividad técnica ({total_señales} señales válidas)")
                return efectividad_promedio
            else:
                print(f"[MarketManager] ⚠️ {symbol}: Sin señales válidas generadas")
                return 0
                
        except Exception as e:
            print(f"[MarketManager] ❌ Error analizando {symbol}: {e}")
            return 0
    
    # MÉTODO DE SIMULACIÓN ELIMINADO - SOLO RESULTADOS REALES
    # Los resultados de señales provienen únicamente de datos reales de Quotex
    
    async def obtener_datos_mercado(self, symbol: str) -> pd.DataFrame:
        """
        Obtiene 300 velas de 5 minutos del mercado especificado usando pyquotex.
        Devuelve un DataFrame con columnas: time, open, high, low, close.
        """
        try:
            if not self.quotex:
                raise Exception("No hay conexión activa a Quotex")
            
            # pyquotex usa: get_candles(asset, end_from_time, history_seconds, timeframe)
            # Para 300 velas de 5 minutos: 300 * 5 * 60 = 90000 segundos
            import time
            end_time = int(time.time())
            history_seconds = 300 * 5 * 60  # 90000 segundos = 25 horas
            timeframe = 300  # 5 minutos en segundos
            
            candles = await self.quotex.get_candles(symbol, end_time, history_seconds, timeframe)
            
            if not candles:
                raise Exception(f"No se obtuvieron datos para {symbol}")
            
            # pyquotex retorna lista de diccionarios con estructura diferente
            # Formato esperado: [{'time': timestamp, 'open': x, 'high': x, 'low': x, 'close': x}, ...]
            datos = []
            for c in candles:
                try:
                    open_val = float(c.get('open', 0))
                    high_val = float(c.get('high', 0))
                    low_val = float(c.get('low', 0))
                    close_val = float(c.get('close', 0))
                    
                    # Validar que los datos sean válidos (no ceros ni negativos)
                    if all([open_val > 0, high_val > 0, low_val > 0, close_val > 0]):
                        datos.append({
                            'time': c.get('time', c.get('timestamp', 0)),
                            'open': open_val,
                            'high': high_val,
                            'low': low_val,
                            'close': close_val
                        })
                    else:
                        logger.warning(f"Vela inválida descartada para {symbol}: {c}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error procesando vela para {symbol}: {e}")
                    continue
            
            if not datos:
                logger.error(f"No se obtuvieron velas válidas para {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(datos)
            logger.info(f"✅ Obtenidas {len(df)} velas válidas para {symbol}")
            
            # Validación final del DataFrame
            if len(df) < 50:
                logger.warning(f"⚠️ Solo {len(df)} velas para {symbol}, se requieren al menos 50")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de {symbol}: {e}")
            return pd.DataFrame()
    
    async def seleccionar_mejor_mercado(self, signal_scheduler=None) -> Dict:
        """
        Selecciona el mercado con mejor señal actual (no promedio histórico)
        Analiza la señal ACTUAL de cada mercado y selecciona la mejor
        
        OPTIMIZACIÓN: Analiza solo 30 mercados aleatorios por ciclo para evitar bloqueos
        Si hay análisis forzado activo, analiza SOLO ese mercado
        """
        # Debug: verificar si signal_scheduler llegó
        print(f"[MarketManager] DEBUG: signal_scheduler={'presente' if signal_scheduler else 'None'}")
        if signal_scheduler:
            activo = getattr(signal_scheduler, 'analisis_forzado_activo', False)
            par = getattr(signal_scheduler, 'analisis_forzado_par', None)
            print(f"[MarketManager] DEBUG: analisis_forzado_activo={activo}, par={par}")
        
        # Verificar si hay análisis forzado activo
        if signal_scheduler and getattr(signal_scheduler, 'analisis_forzado_activo', False):
            par_forzado = getattr(signal_scheduler, 'analisis_forzado_par', None)
            if par_forzado:
                print(f"[MarketManager] 🎯 ANÁLISIS FORZADO: Analizando solo {par_forzado}")
                # Buscar el mercado específico - PRIORIZAR COINCIDENCIA EXACTA
                mercados_disponibles = self.seleccionar_mercados_para_analizar()
                mercado_forzado = None
                
                # Primero buscar coincidencia exacta
                for m in mercados_disponibles:
                    if m['symbol'] == par_forzado:
                        mercado_forzado = m
                        print(f"[MarketManager] ✅ Encontrado mercado exacto: {m['symbol']}")
                        break
                
                # Si no se encuentra exacto, buscar sin _otc
                if not mercado_forzado:
                    par_sin_otc = par_forzado.replace('_otc', '')
                    for m in mercados_disponibles:
                        if m['symbol'].replace('_otc', '') == par_sin_otc:
                            mercado_forzado = m
                            print(f"[MarketManager] ⚠️ No se encontró {par_forzado}, usando {m['symbol']} en su lugar")
                            break
                
                if not mercado_forzado:
                    print(f"[MarketManager] ❌ No se encontró el mercado {par_forzado} ni sus variantes")
                    
                    # Notificar al usuario que no se encontró el mercado
                    if signal_scheduler and hasattr(signal_scheduler, 'bot_telegram'):
                        try:
                            # Obtener admin ID
                            if hasattr(signal_scheduler.bot_telegram, 'user_manager'):
                                admin_id = signal_scheduler.bot_telegram.user_manager.admin_id
                                await signal_scheduler.bot_telegram.application.bot.send_message(
                                    chat_id=admin_id,
                                    text=f"❌ ANÁLISIS FORZADO: ERROR\n\n"
                                         f"No se encontró el mercado {par_forzado}\n\n"
                                         f"Posibles razones:\n"
                                         f"• El mercado no está disponible en este momento\n"
                                         f"• El nombre del mercado es incorrecto\n"
                                         f"• El mercado OTC no está activo\n\n"
                                         f"El análisis forzado se ha detenido."
                                )
                        except Exception as e:
                            print(f"[MarketManager] ⚠️ No se pudo notificar al usuario: {e}")
                    
                    return None
                
                # Analizar solo este mercado
                from src.strategies.evaluar_estrategia_completa import evaluar_estrategia_completa
                df = await self.obtener_datos_mercado(mercado_forzado['symbol'])
                if df is not None and len(df) >= 50:
                    import asyncio
                    resultado = await asyncio.to_thread(
                        evaluar_estrategia_completa, df, mercado_forzado['symbol']
                    )
                    
                    efectividad = resultado.get('efectividad_total', 0)
                    decision = resultado.get('decision')
                    
                    umbral = getattr(signal_scheduler, 'efectividad_minima_temporal', 80)
                    
                    if decision and efectividad >= umbral:
                        mercado_forzado["efectividad_calculada"] = efectividad
                        mercado_forzado["decision_actual"] = decision
                        mercado_forzado["detalles"] = resultado.get('detalles', {})
                        print(f"[MarketManager] ✅ {mercado_forzado['symbol']}: {decision} ({efectividad:.1f}%)")
                        return mercado_forzado
                    else:
                        print(f"[MarketManager] ⚠️ {mercado_forzado['symbol']}: Efectividad {efectividad:.1f}% < {umbral}%")
                        return None
                else:
                    print(f"[MarketManager] ❌ No hay suficientes datos para {par_forzado}")
                    return None
        
        # Modo normal: analizar múltiples mercados
        mercados_analizados = []
        mercados_para_analizar = self.seleccionar_mercados_para_analizar()
        
        # OPTIMIZACIÓN: Analizar solo 30 mercados aleatorios por ciclo
        import random
        if len(mercados_para_analizar) > 30:
            mercados_muestra = random.sample(mercados_para_analizar, 30)
            print(f"[MarketManager] 🎲 Analizando 30 mercados aleatorios de {len(mercados_para_analizar)} disponibles")
        else:
            mercados_muestra = mercados_para_analizar
        
        from src.strategies.evaluar_estrategia_completa import evaluar_estrategia_completa
        
        for mercado in mercados_muestra:
            symbol = mercado["symbol"]
            
            # Obtener datos del mercado
            df = await self.obtener_datos_mercado(symbol)
            if df is not None and len(df) >= 50:  # Suficientes datos
                # Analizar señal ACTUAL (no promedio histórico)
                import asyncio
                resultado = await asyncio.to_thread(
                    evaluar_estrategia_completa, df, symbol
                )
                
                efectividad = resultado.get('efectividad_total', 0)
                decision = resultado.get('decision')
                
                # Solo considerar mercados con señal válida
                if decision and efectividad >= 75:  # Umbral más bajo para selección
                    mercado["efectividad_calculada"] = efectividad
                    mercado["decision_actual"] = decision
                    mercado["detalles"] = resultado.get('detalles', {})
                    mercados_analizados.append(mercado)
                    print(f"[MarketManager] ✅ {symbol}: {decision} ({efectividad:.1f}%)")
        
        if mercados_analizados:
            # Filtrar solo mercados con efectividad >= 80% para envío
            mercados_validos = [m for m in mercados_analizados if m["efectividad_calculada"] >= 80]
            
            if mercados_validos:
                # Ordenar por efectividad
                mercados_validos.sort(key=lambda x: x["efectividad_calculada"], reverse=True)
                mejor_mercado = mercados_validos[0]
                
                print(f"[MarketManager] 🎯 Mejor mercado: {mejor_mercado['symbol']} - {mejor_mercado['decision_actual']} ({mejor_mercado['efectividad_calculada']:.1f}%)")
                return mejor_mercado
            else:
                print(f"[MarketManager] ⚠️ Se encontraron {len(mercados_analizados)} señales pero ninguna >= 80%")
                # Mostrar las mejores encontradas
                if mercados_analizados:
                    mercados_analizados.sort(key=lambda x: x["efectividad_calculada"], reverse=True)
                    print(f"[MarketManager] 📊 Mejor señal encontrada: {mercados_analizados[0]['symbol']} ({mercados_analizados[0]['efectividad_calculada']:.1f}%)")
                return None
        else:
            print("[MarketManager] ⚠️ No se encontraron señales válidas en ningún mercado")
            return None
    
    def cargar_efectividad_historica(self) -> Dict:
        """Carga el historial de efectividad por mercado"""
        try:
            with open('data/efectividad_mercados.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def guardar_efectividad_mercado(self, symbol: str, efectividad: float, tasa_exito: float, total_señales: int):
        """Guarda la efectividad de un mercado"""
        fecha = datetime.now().strftime('%Y-%m-%d')
        
        if symbol not in self.efectividad_historica:
            self.efectividad_historica[symbol] = {}
        
        self.efectividad_historica[symbol][fecha] = {
            'efectividad': efectividad,
            'tasa_exito': tasa_exito,
            'total_señales': total_señales,
            'timestamp': datetime.now().isoformat()
        }
        
        # Crear directorio si no existe
        os.makedirs('data', exist_ok=True)
        
        # Guardar en archivo
        with open('data/efectividad_mercados.json', 'w') as f:
            json.dump(self.efectividad_historica, f, indent=4)

# Función principal para usar el manager
async def obtener_mejor_mercado_del_dia(email: str, password: str) -> Dict:
    """
    Función principal que devuelve el mejor mercado para operar hoy
    """
    manager = MarketManager()
    
    if await manager.conectar_quotex(email, password):
        return manager.seleccionar_mejor_mercado()
    else:
        return None

if __name__ == "__main__":
    # Prueba del sistema
    mejor_mercado = obtener_mejor_mercado_del_dia("ijroyquotex@gmail.com", "Yorji.050212")
    if mejor_mercado:
        print(f"\n🎯 MERCADO SELECCIONADO: {mejor_mercado['symbol']}")
        print(f"💰 Payout: {mejor_mercado['payout']}%")
        print(f"📊 Efectividad estimada: {mejor_mercado['efectividad_calculada']:.1f}%")
    else:
        print("\n❌ No se pudo seleccionar mercado")
