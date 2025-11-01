import pandas as pd

def detectar_hikkake(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """
    Detecta el patrón Hikkake en un DataFrame OHLC.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'] ordenado por tiempo ascendente.
        window (int): Número de velas para analizar la ruptura falsa y confirmación.
    
    Returns:
        pd.DataFrame: DataFrame con una columna nueva 'hikkake' que puede ser:
                      - 'alcista' para patrón hikkake alcista
                      - 'bajista' para patrón hikkake bajista
                      - None si no hay patrón detectado
    """
    df = df.copy()
    df['hikkake'] = None

    for i in range(window, len(df) - 1):
        rango_ventana = df.iloc[i - window:i]
        
        # Detectar ruptura falsa alcista: vela actual rompe máximo previo pero siguiente vela cierra por debajo
        max_prev = rango_ventana['high'].max()
        if (df.loc[i, 'high'] > max_prev and
            df.loc[i + 1, 'close'] < df.loc[i, 'open']):
            df.at[i + 1, 'hikkake'] = 'bajista'

        # Detectar ruptura falsa bajista: vela actual rompe mínimo previo pero siguiente vela cierra por encima
        min_prev = rango_ventana['low'].min()
        if (df.loc[i, 'low'] < min_prev and
            df.loc[i + 1, 'close'] > df.loc[i, 'open']):
            df.at[i + 1, 'hikkake'] = 'alcista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'hikkake_pattern', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
