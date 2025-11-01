import pandas as pd
import numpy as np

def calcular_tendencia_secundaria(df: pd.DataFrame, metodo: str = 'media_movil', periodo: int = 9) -> str:
    """
    Calcula la tendencia secundaria (cercana al precio actual).
    
    :param df: DataFrame con columnas ['time', 'open', 'high', 'low', 'close']
    :param metodo: 'media_movil' o 'pendiente'
    :param periodo: número de periodos a considerar
    :return: 'alcista', 'bajista' o 'lateral'
    """
    if df is None or df.empty:
        return "datos insuficientes"

    if metodo == 'media_movil':
        if len(df) < periodo:
            return "datos insuficientes"
        df['media_corta'] = df['close'].rolling(window=periodo).mean()
        if df['media_corta'].iloc[-1] > df['media_corta'].iloc[-2]:
            return 'alcista'
        elif df['media_corta'].iloc[-1] < df['media_corta'].iloc[-2]:
            return 'bajista'
        else:
            return 'lateral'

    elif metodo == 'pendiente':
        if len(df) < periodo:
            return "datos insuficientes"
        # Calcular la pendiente usando regresión lineal
        y = df['close'].tail(periodo).values
        x = np.arange(len(y))
        pendiente = np.polyfit(x, y, 1)[0]
        if pendiente > 0:
            return 'alcista'
        elif pendiente < 0:
            return 'bajista'
        else:
            return 'lateral'

    else:
        return "método inválido"
