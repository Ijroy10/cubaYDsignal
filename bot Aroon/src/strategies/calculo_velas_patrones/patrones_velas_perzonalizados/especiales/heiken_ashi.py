import pandas as pd

def calcular_heiken_ashi(df):
    """
    Convierte velas OHLC normales en velas Heiken Ashi.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'].

    Returns:
        ha_df (pd.DataFrame): DataFrame con columnas Heiken Ashi ['ha_open', 'ha_high', 'ha_low', 'ha_close'].
    """
    ha_df = df.copy()

    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [(df['open'][0] + df['close'][0]) / 2]  # Primer valor

    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha_close[i-1]) / 2)

    ha_high = pd.concat([df['high'], pd.Series(ha_open), ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df['low'], pd.Series(ha_open), ha_close], axis=1).min(axis=1)

    ha_df['ha_open'] = ha_open
    ha_df['ha_close'] = ha_close
    ha_df['ha_high'] = ha_high
    ha_df['ha_low'] = ha_low

    return ha_df


def detectar_cambio_heiken_ashi(df):
    """
    Detecta señales de cambio de tendencia en velas Heiken Ashi:
    - CALL si hay una vela sin mecha inferior tras tendencia bajista
    - SELL si hay una vela sin mecha superior tras tendencia alcista

    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'].

    Returns:
        señales (list): Lista de tuplas (índice, 'CALL' o 'SELL')
    """
    señales = []
    ha_df = calcular_heiken_ashi(df)

    for i in range(1, len(ha_df)):
        ha_candle = ha_df.iloc[i]
        ha_anterior = ha_df.iloc[i - 1]

        # Patrón de cambio alcista (CALL)
        if ha_candle['ha_low'] == min(ha_candle['ha_open'], ha_candle['ha_close']):
            señales.append((i, 'CALL'))

        # Patrón de cambio bajista (SELL)
        elif ha_candle['ha_high'] == max(ha_candle['ha_open'], ha_candle['ha_close']):
            señales.append((i, 'SELL'))

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'heiken_ashi', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
