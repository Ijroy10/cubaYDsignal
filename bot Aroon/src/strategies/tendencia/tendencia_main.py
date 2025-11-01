import pandas as pd
from src.strategies.tendencia.tendencia_multitimeframe import analizar_tendencia_multitimeframe
from src.strategies.tendencia.fuerza_tendencia import calcular_fuerza_tendencia
from src.strategies.tendencia.patrones_chartistas import analizar_patrones

def analizar_tendencia_completa(df, otras_estrategias=None):
    """
    ESTRATEGIA 1: ANÁLISIS COMPLETO DE TENDENCIA MULTI-TIMEFRAME
    
    Nueva implementación que analiza tendencias en 3 niveles temporales:
    1. Tendencia Secundaria (MA 50) - 50% peso
    2. Tendencia Terciaria (MA 20) - 30% peso
    3. Tendencia Inmediata (MA 9) - 20% peso
    
    Incluye:
    - Análisis de fuerza por pendiente, consistencia y distancia precio-MA
    - Sistema de alineación con bonus/penalización
    - Integración con otras estrategias para ajuste de efectividad
    - Análisis de patrones chartistas y fuerza de tendencia (ADX/MACD)
    
    Args:
        df: DataFrame con columnas ['time', 'open', 'high', 'low', 'close']
        otras_estrategias: Dict con resultados de otras estrategias (opcional)
    
    Returns:
        dict: Resultado con efectividad total y detalles
    """
    try:
        # ANÁLISIS MULTI-TIMEFRAME (nuevo sistema)
        resultado_multitf = analizar_tendencia_multitimeframe(df, otras_estrategias)
        
        # ANÁLISIS COMPLEMENTARIO: Patrones Chartistas
        try:
            patrones = analizar_patrones(df)
        except Exception as e:
            print(f"[Tendencia] Error en patrones chartistas: {e}")
            patrones = {}
        
        # ANÁLISIS COMPLEMENTARIO: Fuerza de Tendencia (ADX + MACD)
        try:
            fuerza = calcular_fuerza_tendencia(df)
        except Exception as e:
            print(f"[Tendencia] Error en fuerza de tendencia: {e}")
            fuerza = {}
        
        # Ajustar efectividad con información de patrones y fuerza
        efectividad_ajustada = ajustar_con_analisis_complementario(
            resultado_multitf['efectividad'],
            resultado_multitf['direccion'],
            patrones,
            fuerza
        )
        
        return {
            "efectividad": round(efectividad_ajustada, 2),
            "direccion": resultado_multitf['direccion'],
            "detalles": {
                "tendencias_multitimeframe": resultado_multitf['detalles']['tendencias'],
                "efectividad_base": resultado_multitf['detalles']['efectividad_base'],
                "bonus_alineacion": resultado_multitf['detalles']['bonus_alineacion'],
                "resumen_tendencias": resultado_multitf['detalles']['resumen'],
                "patrones_chartistas": patrones,
                "fuerza_tendencia": fuerza
            }
        }
        
    except Exception as e:
        print(f"[Tendencia] Error en análisis completo: {e}")
        return {
            "efectividad": 0,
            "direccion": "indefinida",
            "error": str(e)
        }

def ajustar_con_analisis_complementario(efectividad_base, direccion, patrones, fuerza):
    """
    Ajusta la efectividad con análisis complementarios de patrones y fuerza
    
    Args:
        efectividad_base: Efectividad del análisis multi-timeframe
        direccion: Dirección predominante
        patrones: Resultado de análisis de patrones chartistas
        fuerza: Resultado de análisis de fuerza (ADX/MACD)
    
    Returns:
        float: Efectividad ajustada
    """
    ajuste = 0
    
    # BONUS POR PATRONES CHARTISTAS
    if isinstance(patrones, dict):
        patrones_detectados = sum(1 for v in patrones.values() if v and v != 'None')
        
        if patrones_detectados > 0:
            # Bonus por patrones geométricos importantes
            patrones_geometricos = sum(1 for k, v in patrones.items() 
                                      if k in ['hch', 'doble_techo_suelo', 'triangulo', 'bandera'] 
                                      and v and v != 'None')
            
            if patrones_geometricos > 0:
                ajuste += 5 * patrones_geometricos  # +5 por cada patrón geométrico
    
    # BONUS/PENALIZACIÓN POR FUERZA DE TENDENCIA
    if isinstance(fuerza, dict):
        # Bonus si tendencia es fuerte según ADX
        if fuerza.get('tendencia_fuerte', False):
            ajuste += 8
        
        # Bonus si MACD confirma dirección
        macd_cruce = fuerza.get('macd_cruce')
        if macd_cruce == direccion:
            ajuste += 5
        elif macd_cruce and macd_cruce != direccion and macd_cruce != 'indefinida':
            ajuste -= 10  # Penalización si MACD contradice
        
        # PENALIZACIÓN POR DIVERGENCIAS (señal de reversión)
        divergencia = fuerza.get('divergencia', {})
        if divergencia.get('detectada', False):
            tipo_div = divergencia.get('tipo', '')
            
            if 'bajista' in tipo_div and direccion == 'alcista':
                ajuste -= 12  # Posible reversión
            elif 'alcista' in tipo_div and direccion == 'bajista':
                ajuste -= 12  # Posible reversión
        
        # PENALIZACIÓN POR AGOTAMIENTO
        agotamiento = fuerza.get('agotamiento', {})
        if agotamiento.get('agotamiento_detectado', False):
            fuerza_agotamiento = agotamiento.get('fuerza_total', 0)
            if fuerza_agotamiento > 60:
                ajuste -= 8  # Tendencia puede estar agotándose
    
    # Aplicar ajuste y limitar entre 0 y 100
    efectividad_final = efectividad_base + ajuste
    return max(0, min(100, efectividad_final))

if __name__ == "__main__":
    import pandas as pd

    # Ejemplo con datos ficticios
    data = {
        'time': range(10),
        'open': [100,102,104,103,105,107,108,109,110,111],
        'high': [103,104,105,106,107,109,110,111,112,113],
        'low':  [99,101,102,101,103,105,104,106,107,108],
        'close':[102,103,103,105,106,108,109,110,111,112]
    }

    df = pd.DataFrame(data)

    resultado = analizar_tendencia_completa(df)
    print(resultado)
