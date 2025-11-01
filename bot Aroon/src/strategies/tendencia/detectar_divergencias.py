import pandas as pd
import numpy as np
import ta
from scipy.signal import argrelextrema

def detectar_divergencias(df):
    """
    Detecta divergencias entre precio y indicadores (RSI, MACD)
    
    Tipos de divergencias:
    1. Divergencia Alcista Regular: Precio baja, RSI/MACD sube
    2. Divergencia Bajista Regular: Precio sube, RSI/MACD baja
    3. Divergencia Alcista Oculta: Precio sube, RSI/MACD baja (continuación alcista)
    4. Divergencia Bajista Oculta: Precio baja, RSI/MACD sube (continuación bajista)
    
    Args:
        df: DataFrame con columnas ['high', 'low', 'close']
    
    Returns:
        dict: Divergencias detectadas con tipo y fuerza
    """
    if len(df) < 30:
        return {
            'detectada': False,
            'tipo': None,
            'indicador': None,
            'fuerza': 0
        }
    
    divergencias = []
    
    # 1. Detectar divergencias con RSI
    div_rsi = detectar_divergencia_rsi(df)
    if div_rsi['detectada']:
        divergencias.append(div_rsi)
    
    # 2. Detectar divergencias con MACD
    div_macd = detectar_divergencia_macd(df)
    if div_macd['detectada']:
        divergencias.append(div_macd)
    
    # Retornar la divergencia más fuerte
    if divergencias:
        mejor_divergencia = max(divergencias, key=lambda x: x['fuerza'])
        return mejor_divergencia
    
    return {
        'detectada': False,
        'tipo': None,
        'indicador': None,
        'fuerza': 0
    }

def detectar_divergencia_rsi(df, periodo=14):
    """
    Detecta divergencias con RSI
    """
    try:
        # Calcular RSI
        rsi = ta.momentum.RSIIndicator(close=df['close'], window=periodo)
        df_temp = df.copy()
        df_temp['rsi'] = rsi.rsi()
        
        # Buscar mínimos y máximos locales
        minimos_precio_idx = argrelextrema(df_temp['low'].values, np.less, order=5)[0]
        maximos_precio_idx = argrelextrema(df_temp['high'].values, np.greater, order=5)[0]
        
        minimos_rsi_idx = argrelextrema(df_temp['rsi'].values, np.less, order=5)[0]
        maximos_rsi_idx = argrelextrema(df_temp['rsi'].values, np.greater, order=5)[0]
        
        # DIVERGENCIA ALCISTA REGULAR
        # Precio hace mínimos más bajos, RSI hace mínimos más altos
        if len(minimos_precio_idx) >= 2 and len(minimos_rsi_idx) >= 2:
            ultimos_2_min_precio = minimos_precio_idx[-2:]
            ultimos_2_min_rsi = minimos_rsi_idx[-2:]
            
            # Verificar que los índices estén cerca (dentro de 3 velas)
            if abs(ultimos_2_min_precio[0] - ultimos_2_min_rsi[0]) <= 3 and \
               abs(ultimos_2_min_precio[1] - ultimos_2_min_rsi[1]) <= 3:
                
                precio_min1 = df_temp.iloc[ultimos_2_min_precio[0]]['low']
                precio_min2 = df_temp.iloc[ultimos_2_min_precio[1]]['low']
                rsi_min1 = df_temp.iloc[ultimos_2_min_rsi[0]]['rsi']
                rsi_min2 = df_temp.iloc[ultimos_2_min_rsi[1]]['rsi']
                
                # Precio baja, RSI sube
                if precio_min2 < precio_min1 and rsi_min2 > rsi_min1:
                    fuerza = calcular_fuerza_divergencia(precio_min1, precio_min2, rsi_min1, rsi_min2)
                    return {
                        'detectada': True,
                        'tipo': 'alcista_regular',
                        'indicador': 'RSI',
                        'fuerza': fuerza,
                        'descripcion': 'Precio hace mínimos más bajos, RSI hace mínimos más altos'
                    }
        
        # DIVERGENCIA BAJISTA REGULAR
        # Precio hace máximos más altos, RSI hace máximos más bajos
        if len(maximos_precio_idx) >= 2 and len(maximos_rsi_idx) >= 2:
            ultimos_2_max_precio = maximos_precio_idx[-2:]
            ultimos_2_max_rsi = maximos_rsi_idx[-2:]
            
            if abs(ultimos_2_max_precio[0] - ultimos_2_max_rsi[0]) <= 3 and \
               abs(ultimos_2_max_precio[1] - ultimos_2_max_rsi[1]) <= 3:
                
                precio_max1 = df_temp.iloc[ultimos_2_max_precio[0]]['high']
                precio_max2 = df_temp.iloc[ultimos_2_max_precio[1]]['high']
                rsi_max1 = df_temp.iloc[ultimos_2_max_rsi[0]]['rsi']
                rsi_max2 = df_temp.iloc[ultimos_2_max_rsi[1]]['rsi']
                
                # Precio sube, RSI baja
                if precio_max2 > precio_max1 and rsi_max2 < rsi_max1:
                    fuerza = calcular_fuerza_divergencia(precio_max1, precio_max2, rsi_max1, rsi_max2)
                    return {
                        'detectada': True,
                        'tipo': 'bajista_regular',
                        'indicador': 'RSI',
                        'fuerza': fuerza,
                        'descripcion': 'Precio hace máximos más altos, RSI hace máximos más bajos'
                    }
        
    except Exception as e:
        print(f"Error detectando divergencia RSI: {e}")
    
    return {'detectada': False}

def detectar_divergencia_macd(df):
    """
    Detecta divergencias con MACD
    """
    try:
        # Calcular MACD
        macd = ta.trend.MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
        df_temp = df.copy()
        df_temp['macd'] = macd.macd()
        df_temp['macd_signal'] = macd.macd_signal()
        df_temp['macd_hist'] = macd.macd_diff()
        
        # Buscar mínimos y máximos locales
        minimos_precio_idx = argrelextrema(df_temp['low'].values, np.less, order=5)[0]
        maximos_precio_idx = argrelextrema(df_temp['high'].values, np.greater, order=5)[0]
        
        minimos_macd_idx = argrelextrema(df_temp['macd'].values, np.less, order=5)[0]
        maximos_macd_idx = argrelextrema(df_temp['macd'].values, np.greater, order=5)[0]
        
        # DIVERGENCIA ALCISTA REGULAR
        if len(minimos_precio_idx) >= 2 and len(minimos_macd_idx) >= 2:
            ultimos_2_min_precio = minimos_precio_idx[-2:]
            ultimos_2_min_macd = minimos_macd_idx[-2:]
            
            if abs(ultimos_2_min_precio[0] - ultimos_2_min_macd[0]) <= 3 and \
               abs(ultimos_2_min_precio[1] - ultimos_2_min_macd[1]) <= 3:
                
                precio_min1 = df_temp.iloc[ultimos_2_min_precio[0]]['low']
                precio_min2 = df_temp.iloc[ultimos_2_min_precio[1]]['low']
                macd_min1 = df_temp.iloc[ultimos_2_min_macd[0]]['macd']
                macd_min2 = df_temp.iloc[ultimos_2_min_macd[1]]['macd']
                
                # Precio baja, MACD sube
                if precio_min2 < precio_min1 and macd_min2 > macd_min1:
                    fuerza = calcular_fuerza_divergencia(precio_min1, precio_min2, macd_min1, macd_min2)
                    return {
                        'detectada': True,
                        'tipo': 'alcista_regular',
                        'indicador': 'MACD',
                        'fuerza': fuerza,
                        'descripcion': 'Precio hace mínimos más bajos, MACD hace mínimos más altos'
                    }
        
        # DIVERGENCIA BAJISTA REGULAR
        if len(maximos_precio_idx) >= 2 and len(maximos_macd_idx) >= 2:
            ultimos_2_max_precio = maximos_precio_idx[-2:]
            ultimos_2_max_macd = maximos_macd_idx[-2:]
            
            if abs(ultimos_2_max_precio[0] - ultimos_2_max_macd[0]) <= 3 and \
               abs(ultimos_2_max_precio[1] - ultimos_2_max_macd[1]) <= 3:
                
                precio_max1 = df_temp.iloc[ultimos_2_max_precio[0]]['high']
                precio_max2 = df_temp.iloc[ultimos_2_max_precio[1]]['high']
                macd_max1 = df_temp.iloc[ultimos_2_max_macd[0]]['macd']
                macd_max2 = df_temp.iloc[ultimos_2_max_macd[1]]['macd']
                
                # Precio sube, MACD baja
                if precio_max2 > precio_max1 and macd_max2 < macd_max1:
                    fuerza = calcular_fuerza_divergencia(precio_max1, precio_max2, macd_max1, macd_max2)
                    return {
                        'detectada': True,
                        'tipo': 'bajista_regular',
                        'indicador': 'MACD',
                        'fuerza': fuerza,
                        'descripcion': 'Precio hace máximos más altos, MACD hace máximos más bajos'
                    }
        
    except Exception as e:
        print(f"Error detectando divergencia MACD: {e}")
    
    return {'detectada': False}

def calcular_fuerza_divergencia(precio1, precio2, indicador1, indicador2):
    """
    Calcula la fuerza de la divergencia (0-100)
    """
    try:
        # Calcular cambio porcentual en precio
        cambio_precio = abs((precio2 - precio1) / precio1) * 100
        
        # Calcular cambio en indicador
        cambio_indicador = abs((indicador2 - indicador1) / abs(indicador1)) * 100 if indicador1 != 0 else 0
        
        # Fuerza base: promedio de ambos cambios
        fuerza_base = min((cambio_precio + cambio_indicador) / 2, 100)
        
        # Bonus si la divergencia es muy clara (cambios >5%)
        if cambio_precio > 5 and cambio_indicador > 5:
            fuerza_base = min(fuerza_base + 20, 100)
        
        return fuerza_base
        
    except:
        return 50  # Fuerza por defecto

def detectar_agotamiento_tendencia(df):
    """
    Detecta señales de agotamiento de tendencia:
    - Divergencias
    - Volumen decreciente en máximos/mínimos
    - Patrones de agotamiento
    """
    señales_agotamiento = []
    
    # 1. Divergencias
    divergencia = detectar_divergencias(df)
    if divergencia['detectada']:
        señales_agotamiento.append({
            'tipo': 'divergencia',
            'descripcion': divergencia['descripcion'],
            'fuerza': divergencia['fuerza']
        })
    
    # 2. Volumen decreciente (si disponible)
    if 'volume' in df.columns:
        volumen_decreciente = detectar_volumen_decreciente(df)
        if volumen_decreciente:
            señales_agotamiento.append(volumen_decreciente)
    
    # 3. Patrones de agotamiento (velas de indecisión en extremos)
    patron_agotamiento = detectar_patron_agotamiento(df)
    if patron_agotamiento:
        señales_agotamiento.append(patron_agotamiento)
    
    return {
        'agotamiento_detectado': len(señales_agotamiento) > 0,
        'señales': señales_agotamiento,
        'fuerza_total': sum(s['fuerza'] for s in señales_agotamiento) / len(señales_agotamiento) if señales_agotamiento else 0
    }

def detectar_volumen_decreciente(df):
    """
    Detecta volumen decreciente en máximos/mínimos
    """
    try:
        if len(df) < 10:
            return None
        
        ultimas_10 = df.tail(10)
        
        # Buscar máximo/mínimo reciente
        max_precio = ultimas_10['high'].max()
        min_precio = ultimas_10['low'].min()
        
        idx_max = ultimas_10['high'].idxmax()
        idx_min = ultimas_10['low'].idxmin()
        
        # Volumen en el extremo
        volumen_extremo = ultimas_10.loc[idx_max, 'volume'] if idx_max in ultimas_10.index else 0
        volumen_promedio = ultimas_10['volume'].mean()
        
        # Si volumen en extremo es menor que el promedio
        if volumen_extremo < volumen_promedio * 0.7:
            return {
                'tipo': 'volumen_decreciente',
                'descripcion': 'Volumen bajo en máximo/mínimo reciente',
                'fuerza': 70
            }
    
    except:
        pass
    
    return None

def detectar_patron_agotamiento(df):
    """
    Detecta patrones de velas que indican agotamiento
    """
    try:
        if len(df) < 2:
            return None
        
        ultima = df.iloc[-1]
        penultima = df.iloc[-2]
        
        cuerpo = abs(ultima['close'] - ultima['open'])
        rango = ultima['high'] - ultima['low']
        
        # Doji en extremo (indecisión)
        if rango > 0 and cuerpo / rango < 0.1:
            return {
                'tipo': 'doji_extremo',
                'descripcion': 'Doji detectado en posible extremo de tendencia',
                'fuerza': 65
            }
        
        # Vela con mechas largas (rechazo)
        sombra_superior = ultima['high'] - max(ultima['open'], ultima['close'])
        sombra_inferior = min(ultima['open'], ultima['close']) - ultima['low']
        
        if sombra_superior > cuerpo * 2 or sombra_inferior > cuerpo * 2:
            return {
                'tipo': 'rechazo_extremo',
                'descripcion': 'Vela con mecha larga indica rechazo del precio',
                'fuerza': 70
            }
    
    except:
        pass
    
    return None
