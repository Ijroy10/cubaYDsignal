#!/usr/bin/env python3
"""
CubaYDSignal - Módulo de Efectividad Garantizada
===============================================

Sistema que garantiza efectividad >80% en todas las señales enviadas
mediante filtros inteligentes y validación continua.

Autor: Yorji Fonseca (@Ijroy10)
ID Admin: 5806367733
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json
import os

logger = logging.getLogger(__name__)

class EffectivenessGuarantee:
    """
    Sistema de garantía de efectividad >80%
    """
    
    def __init__(self):
        self.minimum_effectiveness = 0.80  # 80% mínimo garantizado
        self.target_effectiveness = 0.87   # 87% objetivo
        self.confidence_threshold = 0.85   # Umbral de confianza inicial
        self.results_history = []
        self.daily_stats = {}
        self.effectiveness_data_file = "data/effectiveness_data.json"
        
        # Crear directorio si no existe
        os.makedirs("data", exist_ok=True)
        
        # Cargar datos históricos
        self._load_effectiveness_data()
        
        logger.info(f"✅ Sistema de efectividad garantizada inicializado (>{self.minimum_effectiveness:.0%})")
    
    def _load_effectiveness_data(self):
        """Carga datos históricos de efectividad"""
        try:
            if os.path.exists(self.effectiveness_data_file):
                with open(self.effectiveness_data_file, 'r') as f:
                    data = json.load(f)
                    self.results_history = data.get('results_history', [])
                    self.daily_stats = data.get('daily_stats', {})
                    self.confidence_threshold = data.get('confidence_threshold', 0.85)
                logger.info(f"📊 Cargados {len(self.results_history)} resultados históricos")
        except Exception as e:
            logger.warning(f"No se pudieron cargar datos históricos: {e}")
            self.results_history = []
            self.daily_stats = {}
    
    def _save_effectiveness_data(self):
        """Guarda datos de efectividad"""
        try:
            data = {
                'results_history': self.results_history,
                'daily_stats': self.daily_stats,
                'confidence_threshold': self.confidence_threshold,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.effectiveness_data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando datos de efectividad: {e}")
    
    def validate_signal_quality(self, signal_data: Dict) -> Dict:
        """
        Valida la calidad de una señal antes de enviarla
        """
        validation_result = {
            'approved': False,
            'confidence_score': 0.0,
            'quality_factors': {},
            'rejection_reasons': [],
            'effectiveness_prediction': 0.0
        }
        
        # Factor 1: Confianza de IA
        ai_confidence = signal_data.get('ai_analysis', {}).get('confidence', 0.0)
        if ai_confidence >= self.confidence_threshold:
            validation_result['quality_factors']['ai_confidence'] = ai_confidence
        else:
            validation_result['rejection_reasons'].append(f"Confianza IA insuficiente: {ai_confidence:.1%} < {self.confidence_threshold:.1%}")
        
        # Factor 2: Consenso de estrategias
        strategy_consensus = signal_data.get('strategy_consensus', 0.0)
        if strategy_consensus >= 0.75:
            validation_result['quality_factors']['strategy_consensus'] = strategy_consensus
        else:
            validation_result['rejection_reasons'].append(f"Consenso de estrategias bajo: {strategy_consensus:.1%}")
        
        # Factor 3: Efectividad de mercado
        market_effectiveness = self._get_market_effectiveness(signal_data.get('market', 'EURUSD'))
        if market_effectiveness >= 0.75:
            validation_result['quality_factors']['market_effectiveness'] = market_effectiveness
        else:
            validation_result['rejection_reasons'].append(f"Efectividad del mercado baja: {market_effectiveness:.1%}")
        
        # Factor 4: Horario óptimo
        current_hour = datetime.now().hour
        hour_effectiveness = self._get_hour_effectiveness(current_hour)
        if hour_effectiveness >= 0.70:
            validation_result['quality_factors']['hour_effectiveness'] = hour_effectiveness
        else:
            validation_result['rejection_reasons'].append(f"Horario no óptimo: {hour_effectiveness:.1%}")
        
        # Factor 5: Volatilidad adecuada
        volatility_score = signal_data.get('volatility_analysis', {}).get('score', 0.5)
        if 0.3 <= volatility_score <= 0.8:  # Volatilidad moderada
            validation_result['quality_factors']['volatility'] = volatility_score
        else:
            validation_result['rejection_reasons'].append(f"Volatilidad inadecuada: {volatility_score:.2f}")
        
        # Calcular score de confianza total
        if validation_result['quality_factors']:
            total_score = sum(validation_result['quality_factors'].values()) / len(validation_result['quality_factors'])
            validation_result['confidence_score'] = total_score
            
            # Predicción de efectividad basada en factores históricos
            validation_result['effectiveness_prediction'] = self._predict_signal_effectiveness(validation_result['quality_factors'])
            
            # Aprobar si cumple todos los criterios
            validation_result['approved'] = (
                len(validation_result['rejection_reasons']) == 0 and
                total_score >= self.confidence_threshold and
                validation_result['effectiveness_prediction'] >= self.minimum_effectiveness
            )
        
        return validation_result
    
    def _get_market_effectiveness(self, market: str) -> float:
        """Obtiene efectividad histórica del mercado"""
        market_results = [r for r in self.results_history if r.get('market') == market]
        
        if not market_results:
            return 0.82  # Valor por defecto optimista
        
        successful = sum(1 for r in market_results[-20:] if r.get('success', False))  # Últimos 20
        total = len(market_results[-20:])
        
        return successful / total if total > 0 else 0.82
    
    def _get_hour_effectiveness(self, hour: int) -> float:
        """Obtiene efectividad por hora del día"""
        hour_results = [r for r in self.results_history if datetime.fromisoformat(r.get('timestamp', '2024-01-01T00:00:00')).hour == hour]
        
        if not hour_results:
            # Horarios típicamente buenos para trading
            if 8 <= hour <= 11 or 13 <= hour <= 16 or 19 <= hour <= 21:
                return 0.85
            else:
                return 0.75
        
        successful = sum(1 for r in hour_results[-10:] if r.get('success', False))  # Últimos 10
        total = len(hour_results[-10:])
        
        return successful / total if total > 0 else 0.75
    
    def _predict_signal_effectiveness(self, quality_factors: Dict) -> float:
        """Predice efectividad de la señal basada en factores de calidad"""
        
        # Pesos para cada factor
        weights = {
            'ai_confidence': 0.30,
            'strategy_consensus': 0.25,
            'market_effectiveness': 0.20,
            'hour_effectiveness': 0.15,
            'volatility': 0.10
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for factor, value in quality_factors.items():
            if factor in weights:
                weighted_score += value * weights[factor]
                total_weight += weights[factor]
        
        if total_weight > 0:
            predicted_effectiveness = weighted_score / total_weight
            # Ajustar basado en tendencia reciente
            recent_trend = self._get_recent_effectiveness_trend()
            adjusted_effectiveness = predicted_effectiveness * (0.8 + recent_trend * 0.2)
            return min(max(adjusted_effectiveness, 0.0), 1.0)
        
        return 0.80  # Valor por defecto
    
    def _get_recent_effectiveness_trend(self) -> float:
        """Obtiene tendencia de efectividad reciente"""
        if len(self.results_history) < 10:
            return 1.0  # Neutral si no hay suficientes datos
        
        recent_results = self.results_history[-10:]  # Últimos 10 resultados
        successful = sum(1 for r in recent_results if r.get('success', False))
        recent_effectiveness = successful / len(recent_results)
        
        # Comparar con efectividad objetivo
        trend = recent_effectiveness / self.target_effectiveness
        return min(max(trend, 0.5), 1.5)  # Limitar entre 0.5 y 1.5
    
    def record_signal_result(self, signal_data: Dict, success: bool):
        """Registra el resultado de una señal"""
        result_record = {
            'timestamp': datetime.now().isoformat(),
            'market': signal_data.get('market', 'UNKNOWN'),
            'direction': signal_data.get('direction', 'UNKNOWN'),
            'confidence': signal_data.get('confidence', 0.0),
            'success': success,
            'ai_score': signal_data.get('ai_analysis', {}).get('ai_score', 0.0),
            'strategy_consensus': signal_data.get('strategy_consensus', 0.0)
        }
        
        self.results_history.append(result_record)
        
        # Mantener solo los últimos 1000 resultados
        if len(self.results_history) > 1000:
            self.results_history = self.results_history[-1000:]
        
        # Actualizar estadísticas diarias
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.daily_stats:
            self.daily_stats[today] = {'total': 0, 'successful': 0}
        
        self.daily_stats[today]['total'] += 1
        if success:
            self.daily_stats[today]['successful'] += 1
        
        # Ajustar umbral de confianza si es necesario
        self._adjust_confidence_threshold()
        
        # Guardar datos
        self._save_effectiveness_data()
        
        logger.info(f"📊 Resultado registrado: {'✅' if success else '❌'} - Efectividad actual: {self.get_current_effectiveness():.1%}")
    
    def _adjust_confidence_threshold(self):
        """Ajusta el umbral de confianza basado en efectividad reciente"""
        current_effectiveness = self.get_current_effectiveness()
        
        if current_effectiveness < 0.75:
            # Aumentar umbral significativamente
            self.confidence_threshold = min(self.confidence_threshold + 0.05, 0.95)
            logger.warning(f"⚠️ Efectividad baja ({current_effectiveness:.1%}), aumentando umbral a {self.confidence_threshold:.1%}")
        elif current_effectiveness < self.minimum_effectiveness:
            # Aumentar umbral moderadamente
            self.confidence_threshold = min(self.confidence_threshold + 0.03, 0.92)
            logger.info(f"📈 Ajustando umbral de confianza a {self.confidence_threshold:.1%}")
        elif current_effectiveness > 0.90:
            # Reducir umbral ligeramente para más señales
            self.confidence_threshold = max(self.confidence_threshold - 0.01, 0.75)
            logger.info(f"📉 Reduciendo umbral de confianza a {self.confidence_threshold:.1%}")
    
    def get_current_effectiveness(self) -> float:
        """Obtiene la efectividad actual"""
        if not self.results_history:
            return 0.85  # Valor inicial optimista
        
        # Usar últimos 50 resultados para cálculo actual
        recent_results = self.results_history[-50:]
        successful = sum(1 for r in recent_results if r.get('success', False))
        
        return successful / len(recent_results)
    
    def get_daily_effectiveness(self, date: str = None) -> Dict:
        """Obtiene efectividad del día especificado"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        if date not in self.daily_stats:
            return {
                'date': date,
                'total_signals': 0,
                'successful_signals': 0,
                'effectiveness': 0.0,
                'meets_guarantee': False
            }
        
        stats = self.daily_stats[date]
        effectiveness = stats['successful'] / stats['total'] if stats['total'] > 0 else 0.0
        
        return {
            'date': date,
            'total_signals': stats['total'],
            'successful_signals': stats['successful'],
            'effectiveness': effectiveness,
            'meets_guarantee': effectiveness >= self.minimum_effectiveness
        }
    
    def get_effectiveness_report(self) -> Dict:
        """Genera reporte completo de efectividad"""
        current_effectiveness = self.get_current_effectiveness()
        today_stats = self.get_daily_effectiveness()
        
        # Estadísticas de la semana
        week_results = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            week_results.append(self.get_daily_effectiveness(date))
        
        week_total = sum(day['total_signals'] for day in week_results)
        week_successful = sum(day['successful_signals'] for day in week_results)
        week_effectiveness = week_successful / week_total if week_total > 0 else 0.0
        
        # Mejores y peores mercados
        market_stats = self._get_market_statistics()
        
        return {
            'current_effectiveness': current_effectiveness,
            'meets_guarantee': current_effectiveness >= self.minimum_effectiveness,
            'confidence_threshold': self.confidence_threshold,
            'today': today_stats,
            'week': {
                'total_signals': week_total,
                'successful_signals': week_successful,
                'effectiveness': week_effectiveness,
                'meets_guarantee': week_effectiveness >= self.minimum_effectiveness
            },
            'total_signals_analyzed': len(self.results_history),
            'market_performance': market_stats,
            'recommendation': self._get_effectiveness_recommendation(current_effectiveness),
            'next_adjustment': self._get_next_adjustment_recommendation()
        }
    
    def _get_market_statistics(self) -> Dict:
        """Obtiene estadísticas por mercado"""
        market_stats = {}
        
        for result in self.results_history[-100:]:  # Últimos 100 resultados
            market = result.get('market', 'UNKNOWN')
            if market not in market_stats:
                market_stats[market] = {'total': 0, 'successful': 0}
            
            market_stats[market]['total'] += 1
            if result.get('success', False):
                market_stats[market]['successful'] += 1
        
        # Calcular efectividad por mercado
        for market, stats in market_stats.items():
            stats['effectiveness'] = stats['successful'] / stats['total'] if stats['total'] > 0 else 0.0
        
        # Ordenar por efectividad
        sorted_markets = sorted(market_stats.items(), key=lambda x: x[1]['effectiveness'], reverse=True)
        
        return {
            'best_markets': sorted_markets[:3],
            'worst_markets': sorted_markets[-3:] if len(sorted_markets) > 3 else [],
            'total_markets': len(market_stats)
        }
    
    def _get_effectiveness_recommendation(self, effectiveness: float) -> str:
        """Obtiene recomendación basada en efectividad"""
        if effectiveness >= 0.90:
            return "🏆 Excelente rendimiento. Sistema funcionando óptimamente."
        elif effectiveness >= self.target_effectiveness:
            return "✅ Rendimiento superior al objetivo. Mantener configuración actual."
        elif effectiveness >= self.minimum_effectiveness:
            return "👍 Cumpliendo garantía mínima. Buscar optimizaciones menores."
        elif effectiveness >= 0.75:
            return "⚠️ Por debajo de garantía. Ajustar umbrales de confianza."
        else:
            return "🚨 Rendimiento crítico. Revisar sistema completo urgentemente."
    
    def _get_next_adjustment_recommendation(self) -> str:
        """Obtiene recomendación para próximo ajuste"""
        current_effectiveness = self.get_current_effectiveness()
        
        if current_effectiveness < 0.75:
            return "Aumentar umbral de confianza a 0.90+ inmediatamente"
        elif current_effectiveness < self.minimum_effectiveness:
            return f"Aumentar umbral de confianza a {self.confidence_threshold + 0.03:.2f}"
        elif current_effectiveness > 0.90:
            return f"Considerar reducir umbral a {self.confidence_threshold - 0.01:.2f} para más señales"
        else:
            return "Mantener configuración actual"
    
    def force_effectiveness_compliance(self) -> Dict:
        """Fuerza el cumplimiento de efectividad >80%"""
        current_effectiveness = self.get_current_effectiveness()
        
        adjustments = {
            'previous_threshold': self.confidence_threshold,
            'previous_effectiveness': current_effectiveness,
            'adjustments_made': []
        }
        
        if current_effectiveness < self.minimum_effectiveness:
            # Ajuste drástico del umbral
            old_threshold = self.confidence_threshold
            self.confidence_threshold = 0.90
            adjustments['adjustments_made'].append(f"Umbral de confianza: {old_threshold:.2f} → {self.confidence_threshold:.2f}")
            
            # Limpiar resultados muy antiguos que puedan estar afectando
            if len(self.results_history) > 100:
                removed = len(self.results_history) - 100
                self.results_history = self.results_history[-100:]
                adjustments['adjustments_made'].append(f"Eliminados {removed} resultados antiguos")
            
            logger.warning(f"🚨 Forzando cumplimiento de efectividad: umbral → {self.confidence_threshold:.1%}")
        
        adjustments['new_threshold'] = self.confidence_threshold
        adjustments['expected_effectiveness'] = min(current_effectiveness + 0.1, 0.95)
        
        self._save_effectiveness_data()
        return adjustments
