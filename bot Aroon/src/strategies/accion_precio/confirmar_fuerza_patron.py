import pandas as pd

def confirmar_vela_fuerte(df: pd.DataFrame, umbral_ratio=1.8) -> pd.DataFrame:
    """
    Marca las velas que son consideradas fuertes (gran cuerpo comparado con el total del rango).
    
    Agrega la columna 'vela_fuerte' con:
        - 'alcista' si es fuerte y verde
        - 'bajista' si es fuerte y roja
        - None si no cumple
    
    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close']
        umbral_ratio (float): Mínimo ratio entre cuerpo y total de la vela para considerarla fuerte
    
    Returns:
        pd.DataFrame: con columna 'vela_fuerte'
    """
    df = df.copy()
    df['vela_fuerte'] = None

    for i in range(len(df)):
        open_ = df.loc[i, 'open']
        close = df.loc[i, 'close']
        high = df.loc[i, 'high']
        low = df.loc[i, 'low']

        cuerpo = abs(close - open_)
        rango_total = high - low if high - low != 0 else 0.0001  # evitar división por cero
        ratio = cuerpo / rango_total

        if ratio >= umbral_ratio:
            df.loc[i, 'vela_fuerte'] = 'alcista' if close > open_ else 'bajista'

    return df