import pandas as pd

def detectar_pullback(df: pd.DataFrame, umbral_retroceso=0.0025) -> pd.DataFrame:
    """
    Detecta posibles pullbacks en una tendencia (alcista o bajista) en base a la dirección del precio.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close', 'tendencia']
        umbral_retroceso (float): Diferencia mínima para considerar un retroceso relevante (en pips)

    Returns:
        df (pd.DataFrame): DataFrame con columna adicional 'posible_pullback' (True/False)
    """
    df = df.copy()
    df['posible_pullback'] = False

    for i in range(2, len(df)):
        tendencia = df.loc[i - 1, 'tendencia']
        retroceso = False

        # En tendencia alcista, el retroceso es una bajada temporal
        if tendencia == 'alcista':
            retroceso = (df.loc[i, 'close'] < df.loc[i - 1, 'close']) and \
                        (df.loc[i - 1, 'close'] - df.loc[i, 'close'] >= umbral_retroceso)

        # En tendencia bajista, el retroceso es una subida temporal
        elif tendencia == 'bajista':
            retroceso = (df.loc[i, 'close'] > df.loc[i - 1, 'close']) and \
                        (df.loc[i, 'close'] - df.loc[i - 1, 'close'] >= umbral_retroceso)

        if retroceso:
            df.loc[i, 'posible_pullback'] = True

    return df
