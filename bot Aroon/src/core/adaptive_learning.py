"""
SISTEMA DE APRENDIZAJE ADAPTATIVO
Analiza los resultados diarios para:
- Mejorar la selección de estrategias
- Optimizar zonas de soporte/resistencia
- Ajustar pesos de efectividad
- Aprender de patrones exitosos
- Adaptar la selección de mercados
"""

import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np
from collections import defaultdict

class AdaptiveLearning:
    def __init__(self):
        self.historial_resultados = self.cargar_historial()
        self.pesos_estrategias = self.cargar_pesos_estrategias()
        self.patrones_exitosos = self.cargar_patrones_exitosos()
        self.mercados_performance = self.cargar_mercados_performance()
        self.zonas_efectivas = self.cargar_zonas_efectivas()
        
    def cargar_historial(self) -> List[Dict]:
        """Carga el historial de resultados de señales"""
        try:
            with open('data/historial_resultados.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def guardar_historial(self):
        """Guarda el historial de resultados"""
        os.makedirs('data', exist_ok=True)
        with open('data/historial_resultados.json', 'w') as f:
            json.dump(self.historial_resultados, f, indent=4)
    
    def cargar_pesos_estrategias(self) -> Dict:
        """Carga los pesos adaptativos de las estrategias"""
        try:
            with open('data/pesos_estrategias.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Pesos iniciales por defecto
            return {
                'tendencia': 0.25,
                'soportes_resistencias': 0.25,
                'patrones_velas': 0.20,
                'volatilidad': 0.15,
                'volumen': 0.10,
                'pullback': 0.05
            }
    
    def guardar_pesos_estrategias(self):
        """Guarda los pesos adaptativos"""
        os.makedirs('data', exist_ok=True)
        with open('data/pesos_estrategias.json', 'w') as f:
            json.dump(self.pesos_estrategias, f, indent=4)
    
    def cargar_patrones_exitosos(self) -> Dict:
        """Carga patrones que han sido más exitosos"""
        try:
            with open('data/patrones_exitosos.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'patrones_velas': {},
                'combinaciones_estrategias': {},
                'horarios_efectivos': {},
                'condiciones_mercado': {}
            }
    
    def guardar_patrones_exitosos(self):
        """Guarda los patrones exitosos identificados"""
        os.makedirs('data', exist_ok=True)
        with open('data/patrones_exitosos.json', 'w') as f:
            json.dump(self.patrones_exitosos, f, indent=4)
    
    def cargar_mercados_performance(self) -> Dict:
        """Carga el rendimiento histórico por mercado"""
        try:
            with open('data/mercados_performance.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def guardar_mercados_performance(self):
        """Guarda el rendimiento por mercado"""
        os.makedirs('data', exist_ok=True)
        with open('data/mercados_performance.json', 'w') as f:
            json.dump(self.mercados_performance, f, indent=4)
    
    def cargar_zonas_efectivas(self) -> Dict:
        """Carga las zonas de soporte/resistencia más efectivas"""
        try:
            with open('data/zonas_efectivas.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def guardar_zonas_efectivas(self):
        """Guarda las zonas más efectivas"""
        os.makedirs('data', exist_ok=True)
        with open('data/zonas_efectivas.json', 'w') as f:
            json.dump(self.zonas_efectivas, f, indent=4)
    
    def registrar_resultado_señal(self, señal_data: Dict, resultado: str, detalles_analisis: Dict):
        """
        Registra el resultado de una señal para aprendizaje
        
        Args:
            señal_data: Datos de la señal enviada
            resultado: 'WIN' o 'LOSS'
            detalles_analisis: Detalles del análisis técnico usado
        """
        registro = {
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M'),
            'timestamp': datetime.now().isoformat(),
            'señal': señal_data,
            'resultado': resultado,
            'analisis': detalles_analisis,
            'efectividad_predicha': señal_data.get('efectividad', 0),
            'mercado': señal_data.get('symbol', ''),
            'direccion': señal_data.get('direccion', ''),
            'exito': resultado == 'WIN'
        }
        
        self.historial_resultados.append(registro)
        self.guardar_historial()
        
        # Analizar inmediatamente para aprendizaje en tiempo real
        self.analizar_resultado_inmediato(registro)
        
        print(f"[AdaptiveLearning] 📊 Resultado registrado: {resultado} - {señal_data.get('symbol', 'N/A')}")
    
    def analizar_resultado_inmediato(self, registro: Dict):
        """Analiza un resultado inmediatamente para ajustes rápidos"""
        analisis = registro['analisis']
        exito = registro['exito']
        
        # 1. Actualizar efectividad de patrones de velas
        patrones_usados = analisis.get('patrones_velas', {}).get('patrones_detectados', [])
        for patron in patrones_usados:
            if patron not in self.patrones_exitosos['patrones_velas']:
                self.patrones_exitosos['patrones_velas'][patron] = {'total': 0, 'exitosos': 0}
            
            self.patrones_exitosos['patrones_velas'][patron]['total'] += 1
            if exito:
                self.patrones_exitosos['patrones_velas'][patron]['exitosos'] += 1
        
        # 2. Actualizar efectividad por horario
        hora = registro['hora'].split(':')[0]  # Solo la hora
        if hora not in self.patrones_exitosos['horarios_efectivos']:
            self.patrones_exitosos['horarios_efectivos'][hora] = {'total': 0, 'exitosos': 0}
        
        self.patrones_exitosos['horarios_efectivos'][hora]['total'] += 1
        if exito:
            self.patrones_exitosos['horarios_efectivos'][hora]['exitosos'] += 1
        
        # 3. Actualizar rendimiento por mercado
        mercado = registro['mercado']
        if mercado not in self.mercados_performance:
            self.mercados_performance[mercado] = {'total': 0, 'exitosos': 0, 'efectividad_promedio': 0}
        
        self.mercados_performance[mercado]['total'] += 1
        if exito:
            self.mercados_performance[mercado]['exitosos'] += 1
        
        # Calcular nueva efectividad promedio
        tasa_exito = self.mercados_performance[mercado]['exitosos'] / self.mercados_performance[mercado]['total']
        self.mercados_performance[mercado]['efectividad_promedio'] = tasa_exito * 100
        
        # Guardar cambios
        self.guardar_patrones_exitosos()
        self.guardar_mercados_performance()
    
    def analizar_resultados_diarios(self, fecha: str = None) -> Dict:
        """
        Analiza los resultados de un día específico para aprendizaje
        """
        if fecha is None:
            fecha = datetime.now().strftime('%Y-%m-%d')
        
        # Filtrar resultados del día
        resultados_dia = [r for r in self.historial_resultados if r['fecha'] == fecha]
        
        if not resultados_dia:
            return {'mensaje': f'No hay resultados para {fecha}'}
        
        # Análisis básico
        total_señales = len(resultados_dia)
        señales_exitosas = len([r for r in resultados_dia if r['exito']])
        tasa_exito = (señales_exitosas / total_señales) * 100
        
        # Análisis por estrategia
        analisis_estrategias = self.analizar_efectividad_estrategias(resultados_dia)
        
        # Análisis de patrones
        analisis_patrones = self.analizar_patrones_exitosos(resultados_dia)
        
        # Análisis temporal
        analisis_temporal = self.analizar_efectividad_temporal(resultados_dia)
        
        # Análisis de mercados
        analisis_mercados = self.analizar_efectividad_mercados(resultados_dia)
        
        # Generar recomendaciones
        recomendaciones = self.generar_recomendaciones(analisis_estrategias, analisis_patrones, analisis_temporal)
        
        resultado_analisis = {
            'fecha': fecha,
            'resumen': {
                'total_señales': total_señales,
                'señales_exitosas': señales_exitosas,
                'tasa_exito': tasa_exito
            },
            'estrategias': analisis_estrategias,
            'patrones': analisis_patrones,
            'temporal': analisis_temporal,
            'mercados': analisis_mercados,
            'recomendaciones': recomendaciones
        }
        
        # Aplicar mejoras automáticamente
        self.aplicar_mejoras_automaticas(resultado_analisis)
        
        return resultado_analisis
    
    def analizar_efectividad_estrategias(self, resultados: List[Dict]) -> Dict:
        """Analiza qué estrategias fueron más efectivas"""
        estrategias_stats = defaultdict(lambda: {'total': 0, 'exitosos': 0, 'efectividad_promedio': 0})
        
        for resultado in resultados:
            analisis = resultado['analisis']
            exito = resultado['exito']
            
            # Analizar cada estrategia
            for estrategia in ['tendencia', 'soportes_resistencias', 'patrones_velas', 'volatilidad']:
                if estrategia in analisis:
                    estrategias_stats[estrategia]['total'] += 1
                    if exito:
                        estrategias_stats[estrategia]['exitosos'] += 1
                    
                    # Acumular efectividad predicha
                    efectividad = analisis[estrategia].get('efectividad', 0)
                    estrategias_stats[estrategia]['efectividad_promedio'] += efectividad
        
        # Calcular promedios
        for estrategia in estrategias_stats:
            total = estrategias_stats[estrategia]['total']
            if total > 0:
                estrategias_stats[estrategia]['tasa_exito'] = (estrategias_stats[estrategia]['exitosos'] / total) * 100
                estrategias_stats[estrategia]['efectividad_promedio'] /= total
        
        return dict(estrategias_stats)
    
    def analizar_patrones_exitosos(self, resultados: List[Dict]) -> Dict:
        """Analiza qué patrones de velas fueron más exitosos"""
        patrones_stats = defaultdict(lambda: {'total': 0, 'exitosos': 0})
        
        for resultado in resultados:
            analisis = resultado['analisis']
            exito = resultado['exito']
            
            patrones_detectados = analisis.get('patrones_velas', {}).get('patrones_detectados', [])
            for patron in patrones_detectados:
                patrones_stats[patron]['total'] += 1
                if exito:
                    patrones_stats[patron]['exitosos'] += 1
        
        # Calcular tasas de éxito
        for patron in patrones_stats:
            total = patrones_stats[patron]['total']
            if total > 0:
                patrones_stats[patron]['tasa_exito'] = (patrones_stats[patron]['exitosos'] / total) * 100
        
        # Ordenar por tasa de éxito
        patrones_ordenados = sorted(patrones_stats.items(), key=lambda x: x[1]['tasa_exito'], reverse=True)
        
        return {
            'patrones_stats': dict(patrones_stats),
            'mejores_patrones': patrones_ordenados[:10]  # Top 10
        }
    
    def analizar_efectividad_temporal(self, resultados: List[Dict]) -> Dict:
        """Analiza la efectividad por horarios"""
        horarios_stats = defaultdict(lambda: {'total': 0, 'exitosos': 0})
        
        for resultado in resultados:
            hora = resultado['hora'].split(':')[0]  # Solo la hora
            exito = resultado['exito']
            
            horarios_stats[hora]['total'] += 1
            if exito:
                horarios_stats[hora]['exitosos'] += 1
        
        # Calcular tasas de éxito
        for hora in horarios_stats:
            total = horarios_stats[hora]['total']
            if total > 0:
                horarios_stats[hora]['tasa_exito'] = (horarios_stats[hora]['exitosos'] / total) * 100
        
        # Encontrar mejores horarios
        mejores_horarios = sorted(horarios_stats.items(), key=lambda x: x[1]['tasa_exito'], reverse=True)
        
        return {
            'horarios_stats': dict(horarios_stats),
            'mejores_horarios': mejores_horarios[:5]  # Top 5
        }
    
    def analizar_efectividad_mercados(self, resultados: List[Dict]) -> Dict:
        """Analiza la efectividad por mercado"""
        mercados_stats = defaultdict(lambda: {'total': 0, 'exitosos': 0})
        
        for resultado in resultados:
            mercado = resultado['mercado']
            exito = resultado['exito']
            
            mercados_stats[mercado]['total'] += 1
            if exito:
                mercados_stats[mercado]['exitosos'] += 1
        
        # Calcular tasas de éxito
        for mercado in mercados_stats:
            total = mercados_stats[mercado]['total']
            if total > 0:
                mercados_stats[mercado]['tasa_exito'] = (mercados_stats[mercado]['exitosos'] / total) * 100
        
        return dict(mercados_stats)
    
    def generar_recomendaciones(self, estrategias: Dict, patrones: Dict, temporal: Dict) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recomendaciones = []
        
        # Recomendaciones de estrategias
        if estrategias:
            mejor_estrategia = max(estrategias.items(), key=lambda x: x[1].get('tasa_exito', 0))
            if mejor_estrategia[1]['tasa_exito'] > 80:
                recomendaciones.append(f"Aumentar peso de {mejor_estrategia[0]} (éxito: {mejor_estrategia[1]['tasa_exito']:.1f}%)")
        
        # Recomendaciones de patrones
        if patrones.get('mejores_patrones'):
            mejor_patron = patrones['mejores_patrones'][0]
            if mejor_patron[1]['tasa_exito'] > 85:
                recomendaciones.append(f"Priorizar patrón {mejor_patron[0]} (éxito: {mejor_patron[1]['tasa_exito']:.1f}%)")
        
        # Recomendaciones temporales
        if temporal.get('mejores_horarios'):
            mejor_horario = temporal['mejores_horarios'][0]
            if mejor_horario[1]['tasa_exito'] > 85:
                recomendaciones.append(f"Concentrar señales en hora {mejor_horario[0]}:XX (éxito: {mejor_horario[1]['tasa_exito']:.1f}%)")
        
        return recomendaciones
    
    async def aplicar_mejoras_automaticas(self, analisis: Dict, notify_admin_callback=None):
        """
        Aplica mejoras automáticas basadas en el análisis y notifica al admin si hay cambios.
        notify_admin_callback: función async para enviar mensajes directos al admin (puede ser None)
        """
        estrategias = analisis.get('estrategias', {})
        cambios = []
        # Ajustar pesos de estrategias
        if estrategias:
            total_peso = sum(self.pesos_estrategias.values())
            for estrategia, stats in estrategias.items():
                if estrategia in self.pesos_estrategias:
                    tasa_exito = stats.get('tasa_exito', 0)
                    peso_anterior = self.pesos_estrategias[estrategia]
                    # Si la tasa de éxito es muy alta, aumentar peso
                    if tasa_exito > 85:
                        self.pesos_estrategias[estrategia] = min(0.4, self.pesos_estrategias[estrategia] * 1.1)
                        if notify_admin_callback:
                            cambios.append((estrategia, peso_anterior, self.pesos_estrategias[estrategia], 'aumentado', tasa_exito))
                    # Si es muy baja, reducir peso
                    elif tasa_exito < 60:
                        self.pesos_estrategias[estrategia] = max(0.05, self.pesos_estrategias[estrategia] * 0.9)
                        if notify_admin_callback:
                            cambios.append((estrategia, peso_anterior, self.pesos_estrategias[estrategia], 'reducido', tasa_exito))
            # Normalizar pesos
            nuevo_total = sum(self.pesos_estrategias.values())
            for estrategia in self.pesos_estrategias:
                self.pesos_estrategias[estrategia] = (self.pesos_estrategias[estrategia] / nuevo_total) * total_peso
        self.guardar_pesos_estrategias()
        print("[AdaptiveLearning] 🧠 Pesos de estrategias actualizados automáticamente")
        # Notificar admin si corresponde
        if notify_admin_callback and cambios:
            for estrategia, anterior, nuevo, accion, tasa in cambios:
                mensaje = (
                    f"🧠 *[Aprendizaje Adaptativo]*\n"
                    f"Estrategia `{estrategia}` {accion} a peso {nuevo:.3f} (antes {anterior:.3f})\n"
                    f"Motivo: tasa de éxito {'alta' if accion=='aumentado' else 'baja'} ({tasa:.1f}%)."
                )
                # Llamada async
                import asyncio
                if asyncio.iscoroutinefunction(notify_admin_callback):
                    asyncio.create_task(notify_admin_callback(mensaje))
                else:
                    notify_admin_callback(mensaje)

    
    def obtener_pesos_optimizados(self) -> Dict:
        """Obtiene los pesos optimizados para las estrategias"""
        return self.pesos_estrategias.copy()
    
    def obtener_mejores_patrones(self, limite: int = 10) -> List[str]:
        """Obtiene los mejores patrones de velas identificados"""
        patrones_con_stats = []
        
        for patron, stats in self.patrones_exitosos['patrones_velas'].items():
            if stats['total'] >= 5:  # Mínimo 5 ocurrencias
                tasa_exito = (stats['exitosos'] / stats['total']) * 100
                patrones_con_stats.append((patron, tasa_exito))
        
        # Ordenar por tasa de éxito
        patrones_con_stats.sort(key=lambda x: x[1], reverse=True)
        
        return [patron[0] for patron in patrones_con_stats[:limite]]
    
    def obtener_mejores_horarios(self) -> List[str]:
        """Obtiene los mejores horarios para señales"""
        horarios_con_stats = []
        
        for hora, stats in self.patrones_exitosos['horarios_efectivos'].items():
            if stats['total'] >= 3:  # Mínimo 3 señales
                tasa_exito = (stats['exitosos'] / stats['total']) * 100
                horarios_con_stats.append((hora, tasa_exito))
        
        # Ordenar por tasa de éxito
        horarios_con_stats.sort(key=lambda x: x[1], reverse=True)
        
        return [f"{hora}:XX" for hora, _ in horarios_con_stats[:5]]
    
    def obtener_mejor_mercado_historico(self) -> Optional[str]:
        """Obtiene el mercado con mejor rendimiento histórico"""
        if not self.mercados_performance:
            return None
        
        mejor_mercado = max(
            self.mercados_performance.items(),
            key=lambda x: x[1]['efectividad_promedio']
        )
        
        return mejor_mercado[0] if mejor_mercado[1]['total'] >= 10 else None
    
    def generar_reporte_aprendizaje(self) -> str:
        """Genera un reporte completo del aprendizaje"""
        reporte = "🧠 **REPORTE DE APRENDIZAJE ADAPTATIVO**\n\n"
        
        # Pesos actuales
        reporte += "⚖️ **PESOS DE ESTRATEGIAS OPTIMIZADOS:**\n"
        for estrategia, peso in self.pesos_estrategias.items():
            reporte += f"• {estrategia.replace('_', ' ').title()}: {peso:.2f} ({peso*100:.1f}%)\n"
        
        # Mejores patrones
        mejores_patrones = self.obtener_mejores_patrones(5)
        if mejores_patrones:
            reporte += f"\n🎯 **MEJORES PATRONES IDENTIFICADOS:**\n"
            for patron in mejores_patrones:
                stats = self.patrones_exitosos['patrones_velas'][patron]
                tasa = (stats['exitosos'] / stats['total']) * 100
                reporte += f"• {patron}: {tasa:.1f}% éxito ({stats['exitosos']}/{stats['total']})\n"
        
        # Mejores horarios
        mejores_horarios = self.obtener_mejores_horarios()
        if mejores_horarios:
            reporte += f"\n⏰ **MEJORES HORARIOS:**\n"
            for horario in mejores_horarios:
                hora = horario.replace(':XX', '')
                stats = self.patrones_exitosos['horarios_efectivos'][hora]
                tasa = (stats['exitosos'] / stats['total']) * 100
                reporte += f"• {horario}: {tasa:.1f}% éxito ({stats['exitosos']}/{stats['total']})\n"
        
        # Mejor mercado
        mejor_mercado = self.obtener_mejor_mercado_historico()
        if mejor_mercado:
            stats = self.mercados_performance[mejor_mercado]
            reporte += f"\n💱 **MEJOR MERCADO:** {mejor_mercado}\n"
            reporte += f"• Efectividad: {stats['efectividad_promedio']:.1f}%\n"
            reporte += f"• Señales: {stats['exitosos']}/{stats['total']}\n"
        
        # Total de datos
        reporte += f"\n📊 **DATOS TOTALES:**\n"
        reporte += f"• Señales analizadas: {len(self.historial_resultados)}\n"
        reporte += f"• Patrones únicos: {len(self.patrones_exitosos['patrones_velas'])}\n"
        reporte += f"• Mercados analizados: {len(self.mercados_performance)}\n"
        
        return reporte

# Función de utilidad
def analizar_dia_completo(fecha: str = None) -> Dict:
    """Analiza un día completo y devuelve recomendaciones"""
    learning = AdaptiveLearning()
    return learning.analizar_resultados_diarios(fecha)

def obtener_configuracion_optimizada() -> Dict:
    """Obtiene la configuración optimizada actual"""
    learning = AdaptiveLearning()
    return {
        'pesos_estrategias': learning.obtener_pesos_optimizados(),
        'mejores_patrones': learning.obtener_mejores_patrones(),
        'mejores_horarios': learning.obtener_mejores_horarios(),
        'mejor_mercado': learning.obtener_mejor_mercado_historico()
    }

if __name__ == "__main__":
    # SISTEMA DE APRENDIZAJE ADAPTATIVO - SOLO DATOS REALES
    # En producción, el sistema registra y analiza únicamente resultados reales
    # de señales enviadas y ejecutadas con datos reales de Quotex
    learning = AdaptiveLearning()
    print("🤖 Sistema de Aprendizaje Adaptativo inicializado - Solo datos reales")
    print("✅ Listo para registrar y analizar resultados reales de señales")
    
    # El sistema está listo para funcionar con datos reales de producción
