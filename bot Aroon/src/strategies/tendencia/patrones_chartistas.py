import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def analizar_patrones(df):
    """
    ANÁLISIS COMPLETO DE PATRONES CHARTISTAS
    Detecta:
    1. Patrones de velas (53 patrones personalizados)
    2. Patrones geométricos (HCH, triángulos, banderas)
    
    Args:
        df: DataFrame con columnas ['open', 'high', 'low', 'close']
    
    Returns:
        dict: Patrones detectados con efectividad
    """
    patrones_detectados = {}
    
    # 1. PATRONES DE VELAS (usar sistema completo de 53 patrones)
    patrones_velas = detectar_patrones_velas_completo(df)
    patrones_detectados.update(patrones_velas)
    
    # 2. PATRONES GEOMÉTRICOS
    patrones_geometricos = detectar_patrones_geometricos(df)
    patrones_detectados.update(patrones_geometricos)
    
    return patrones_detectados

def detectar_patrones_velas_completo(df):
    """
    Detecta todos los patrones de velas usando el sistema completo
    """
    try:
        # Importar el detector completo de patrones
        from src.strategies.calculo_velas_patrones.detectar_patrones import detectar_todos_los_patrones
        
        patrones = detectar_todos_los_patrones(df)
        
        # Convertir a formato compatible
        resultado = {}
        for patron in patrones:
            nombre = patron.get('nombre', 'desconocido')
            direccion = patron.get('direccion', 'neutral')
            resultado[nombre] = direccion
        
        return resultado
        
    except ImportError:
        # Fallback: usar detección básica
        return detectar_patrones_basicos(df)

def detectar_patrones_basicos(df):
    """
    Detección básica de patrones de velas (fallback)
    """
    resultados = {
        'engulfing': detectar_patroon_engulfing(df),
        'doji': detectar_patroon_doji(df),
        'martillo': detectar_patroon_martillo(df),
    }
    return resultados

def detectar_patroon_engulfing(df):
    """Detecta patrón Engulfing"""
    if len(df) < 2:
        return None
    
    vela_antes = df.iloc[-2]
    vela_actual = df.iloc[-1]
    
    # Engulfing alcista
    if (vela_antes['close'] < vela_antes['open'] and
        vela_actual['close'] > vela_actual['open'] and
        vela_actual['close'] > vela_antes['open'] and
        vela_actual['open'] < vela_antes['close']):
        return 'alcista'
    
    # Engulfing bajista
    if (vela_antes['close'] > vela_antes['open'] and
        vela_actual['close'] < vela_actual['open'] and
        vela_actual['open'] > vela_antes['close'] and
        vela_actual['close'] < vela_antes['open']):
        return 'bajista'
    
    return None

def detectar_patroon_doji(df, umbral=0.1):
    """Detecta patrón Doji"""
    if len(df) < 1:
        return False
    
    vela = df.iloc[-1]
    cuerpo = abs(vela['close'] - vela['open'])
    rango = vela['high'] - vela['low']
    
    if rango == 0:
        return False
    
    return cuerpo / rango <= umbral

def detectar_patroon_martillo(df, umbral_cuerpo=0.3, umbral_sombra=2.0):
    """Detecta patrón Martillo"""
    if len(df) < 1:
        return False
    
    vela = df.iloc[-1]
    cuerpo = abs(vela['close'] - vela['open'])
    sombra_inferior = min(vela['close'], vela['open']) - vela['low']
    sombra_superior = vela['high'] - max(vela['close'], vela['open'])
    
    if cuerpo == 0:
        return False
    
    if (cuerpo / (vela['high'] - vela['low']) <= umbral_cuerpo and
        sombra_inferior >= umbral_sombra * cuerpo and
        sombra_superior <= cuerpo):
        return True
    
    return False

# ============================================
# PATRONES GEOMÉTRICOS
# ============================================

def detectar_patrones_geometricos(df):
    """
    Detecta patrones geométricos (chartistas):
    - Hombro-Cabeza-Hombro (HCH)
    - Doble Techo / Doble Suelo
    - Triángulos (Ascendente, Descendente, Simétrico)
    - Banderas y Banderines
    """
    patrones = {}
    
    if len(df) < 20:
        return patrones
    
    # Detectar HCH
    hch = detectar_hombro_cabeza_hombro(df)
    if hch:
        patrones['hch'] = hch
    
    # Detectar Doble Techo/Suelo
    doble = detectar_doble_techo_suelo(df)
    if doble:
        patrones['doble_techo_suelo'] = doble
    
    # Detectar Triángulos
    triangulo = detectar_triangulos(df)
    if triangulo:
        patrones['triangulo'] = triangulo
    
    # Detectar Banderas
    bandera = detectar_banderas(df)
    if bandera:
        patrones['bandera'] = bandera
    
    return patrones

def detectar_hombro_cabeza_hombro(df):
    """
    Detecta patrón Hombro-Cabeza-Hombro (HCH)
    """
    try:
        # Buscar máximos locales
        maximos = argrelextrema(df['high'].values, np.greater, order=5)[0]
        
        if len(maximos) < 3:
            return None
        
        # Tomar los últimos 3 máximos
        ultimos_maximos = maximos[-3:]
        
        h1_idx, cabeza_idx, h2_idx = ultimos_maximos
        h1 = df.iloc[h1_idx]['high']
        cabeza = df.iloc[cabeza_idx]['high']
        h2 = df.iloc[h2_idx]['high']
        
        # Verificar patrón HCH: cabeza más alta que hombros
        if (cabeza > h1 * 1.02 and cabeza > h2 * 1.02 and
            abs(h1 - h2) / h1 < 0.03):  # Hombros similares
            return 'bajista'  # HCH es patrón bajista
        
        # HCH invertido (alcista)
        minimos = argrelextrema(df['low'].values, np.less, order=5)[0]
        if len(minimos) >= 3:
            ultimos_minimos = minimos[-3:]
            h1_idx, cabeza_idx, h2_idx = ultimos_minimos
            h1 = df.iloc[h1_idx]['low']
            cabeza = df.iloc[cabeza_idx]['low']
            h2 = df.iloc[h2_idx]['low']
            
            if (cabeza < h1 * 0.98 and cabeza < h2 * 0.98 and
                abs(h1 - h2) / h1 < 0.03):
                return 'alcista'  # HCH invertido es alcista
        
    except Exception as e:
        pass
    
    return None

def detectar_doble_techo_suelo(df):
    """
    Detecta patrón Doble Techo o Doble Suelo
    """
    try:
        # Doble Techo
        maximos = argrelextrema(df['high'].values, np.greater, order=5)[0]
        if len(maximos) >= 2:
            ultimos_2_maximos = maximos[-2:]
            max1 = df.iloc[ultimos_2_maximos[0]]['high']
            max2 = df.iloc[ultimos_2_maximos[1]]['high']
            
            # Máximos similares (±2%)
            if abs(max1 - max2) / max1 < 0.02:
                return 'bajista'  # Doble techo es bajista
        
        # Doble Suelo
        minimos = argrelextrema(df['low'].values, np.less, order=5)[0]
        if len(minimos) >= 2:
            ultimos_2_minimos = minimos[-2:]
            min1 = df.iloc[ultimos_2_minimos[0]]['low']
            min2 = df.iloc[ultimos_2_minimos[1]]['low']
            
            # Mínimos similares (±2%)
            if abs(min1 - min2) / min1 < 0.02:
                return 'alcista'  # Doble suelo es alcista
        
    except Exception as e:
        pass
    
    return None

def detectar_triangulos(df):
    """
    Detecta patrones de triángulos:
    - Ascendente (alcista)
    - Descendente (bajista)
    - Simétrico (neutral)
    """
    try:
        if len(df) < 20:
            return None
        
        ultimas_20 = df.tail(20)
        
        # Calcular líneas de tendencia
        maximos_idx = argrelextrema(ultimas_20['high'].values, np.greater, order=2)[0]
        minimos_idx = argrelextrema(ultimas_20['low'].values, np.less, order=2)[0]
        
        if len(maximos_idx) < 2 or len(minimos_idx) < 2:
            return None
        
        # Pendiente de máximos
        x_max = maximos_idx
        y_max = ultimas_20.iloc[maximos_idx]['high'].values
        pendiente_max = np.polyfit(x_max, y_max, 1)[0]
        
        # Pendiente de mínimos
        x_min = minimos_idx
        y_min = ultimas_20.iloc[minimos_idx]['low'].values
        pendiente_min = np.polyfit(x_min, y_min, 1)[0]
        
        # Triángulo Ascendente: máximos planos, mínimos subiendo
        if abs(pendiente_max) < 0.0001 and pendiente_min > 0.0001:
            return 'alcista'
        
        # Triángulo Descendente: mínimos planos, máximos bajando
        elif abs(pendiente_min) < 0.0001 and pendiente_max < -0.0001:
            return 'bajista'
        
        # Triángulo Simétrico: convergencia
        elif pendiente_max < 0 and pendiente_min > 0:
            return 'neutral'
        
    except Exception as e:
        pass
    
    return None

def detectar_banderas(df):
    """
    Detecta patrones de banderas y banderines
    """
    try:
        if len(df) < 15:
            return None
        
        # Analizar últimas 15 velas
        ultimas_15 = df.tail(15)
        
        # Detectar movimiento fuerte previo (asta de la bandera)
        primeras_5 = ultimas_15.head(5)
        movimiento = (primeras_5.iloc[-1]['close'] - primeras_5.iloc[0]['close']) / primeras_5.iloc[0]['close']
        
        # Requiere movimiento fuerte (>2%)
        if abs(movimiento) < 0.02:
            return None
        
        # Detectar consolidación (bandera)
        ultimas_10 = ultimas_15.tail(10)
        rango_consolidacion = (ultimas_10['high'].max() - ultimas_10['low'].min()) / ultimas_10['close'].mean()
        
        # Consolidación estrecha (<1.5%)
        if rango_consolidacion < 0.015:
            # Bandera alcista: movimiento previo alcista
            if movimiento > 0:
                return 'alcista'
            # Bandera bajista: movimiento previo bajista
            else:
                return 'bajista'
        
    except Exception as e:
        pass
    
    return None
