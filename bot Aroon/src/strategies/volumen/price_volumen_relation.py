import pandas as pd
import numpy as np

def evaluar_volumen(df: pd.DataFrame) -> dict:
    """
    Evalúa el volumen y su relación con el precio.
    
    Args:
        df: DataFrame con columnas ['close', 'volume'] o ['close', 'ticks']
    
    Returns:
        dict: Resultado con efectividad, dirección y detalles
    """
    try:
        # Si no hay columna 'volume', usar 'ticks' como proxy
        if 'volume' not in df.columns and 'ticks' in df.columns:
            df = df.copy()
            df['volume'] = df['ticks']
        
        # Si aún no hay volumen, retornar resultado neutro
        if 'volume' not in df.columns or df['volume'].isna().all():
            return {
                'efectividad': 50,
                'direccion': 'neutral',
                'detalles': {
                    'disponible': False,
                    'mensaje': 'Volumen no disponible'
                }
            }
        
        # Calcular OBV (On Balance Volume)
        obv = calcular_obv(df)
        
        # Analizar tendencia del OBV
        obv_ma = obv.rolling(window=10).mean()
        obv_actual = obv.iloc[-1]
        obv_ma_actual = obv_ma.iloc[-1]
        
        # Determinar dirección
        if obv_actual > obv_ma_actual:
            direccion = 'alcista'
            efectividad = 60
        elif obv_actual < obv_ma_actual:
            direccion = 'bajista'
            efectividad = 60
        else:
            direccion = 'neutral'
            efectividad = 50
        
        # Analizar divergencias
        precio_subiendo = df['close'].iloc[-1] > df['close'].iloc[-10]
        obv_subiendo = obv.iloc[-1] > obv.iloc[-10]
        
        if precio_subiendo and obv_subiendo:
            efectividad += 15  # Confirmación alcista
        elif not precio_subiendo and not obv_subiendo:
            efectividad += 15  # Confirmación bajista
        else:
            efectividad -= 10  # Divergencia (señal débil)
        
        return {
            'efectividad': min(max(efectividad, 0), 100),
            'direccion': direccion,
            'detalles': {
                'disponible': True,
                'obv_actual': float(obv_actual),
                'obv_ma': float(obv_ma_actual),
                'divergencia': precio_subiendo != obv_subiendo
            }
        }
        
    except Exception as e:
        return {
            'efectividad': 50,
            'direccion': 'neutral',
            'detalles': {
                'disponible': False,
                'error': str(e)
            }
        }

def calcular_obv(df: pd.DataFrame) -> pd.Series:
    """
    Calcula el On Balance Volume (OBV).
    
    Args:
        df: DataFrame con columnas ['close', 'volume']
    
    Returns:
        pd.Series: Serie con valores de OBV
    """
    obv = [0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.append(obv[-1] + df['volume'].iloc[i])
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.append(obv[-1] - df['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    
    return pd.Series(obv, index=df.index)

def analizar_precio_volumen(df: pd.DataFrame) -> str:
    """
    Analiza la relación entre precio y volumen.
    
    Parámetros:
        df: DataFrame con columnas ['close', 'volume'] o ['close', 'ticks']
    
    Returns:

    Retorna:
        str: Descripción de la fuerza de la tendencia basada en la relación precio-volumen
    """
    if df.shape[0] < 2:
        return "Datos insuficientes para análisis de precio-volumen"

    # Comparar últimas 2 velas
    precio_anterior = df['close'].iloc[-2]
    precio_actual = df['close'].iloc[-1]

    volumen_anterior = df['volume'].iloc[-2]
    volumen_actual = df['volume'].iloc[-1]

    if precio_actual > precio_anterior and volumen_actual > volumen_anterior:
        return "Tendencia alcista fuerte (precio y volumen suben)"
    elif precio_actual > precio_anterior and volumen_actual < volumen_anterior:
        return "Posible agotamiento alcista (precio sube, volumen baja)"
    elif precio_actual < precio_anterior and volumen_actual > volumen_anterior:
        return "Tendencia bajista fuerte (precio baja, volumen sube)"
    elif precio_actual < precio_anterior and volumen_actual < volumen_anterior:
        return "Corrección temporal bajista (precio y volumen bajan)"
    else:
        return "Relación precio-volumen neutral o indefinida"