import pandas as pd

def calcular_tendencia_principal(data, periodo=50):
    """
    Analiza la tendencia principal del mercado usando una media móvil.
    
    Args:
        data (pd.DataFrame): DataFrame con una columna 'close' de precios.
        periodo (int): Periodo de la media móvil (por defecto 50).
    
    Returns:
        str: 'alcista', 'bajista' o 'indefinida'
    """

    if 'close' not in data.columns or len(data) < periodo:
        return 'indefinida'

    data['ma_larga'] = data['close'].rolling(window=periodo).mean()

    # Comparamos los últimos valores
    if data['ma_larga'].iloc[-1] > data['ma_larga'].iloc[-5]:
        return 'alcista'
    elif data['ma_larga'].iloc[-1] < data['ma_larga'].iloc[-5]:
        return 'bajista'
    else:
        return 'indefinida'