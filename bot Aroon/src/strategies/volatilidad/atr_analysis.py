import pandas as pd

def calcular_atr(df, periodo=14):
    """
    Calcula el Average True Range (ATR) para medir la volatilidad.

    Parámetros:
    - df: DataFrame con columnas ['high', 'low', 'close']
    - periodo: Periodo para el cálculo del ATR (por defecto 14)

    Retorna:
    - Serie de ATR
    """
    df = df.copy()

    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())

    df['true_range'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['atr'] = df['true_range'].rolling(window=periodo).mean()

    return df['atr']