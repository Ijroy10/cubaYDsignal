import pandas as pd

def detectar_breakout_bar(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Detecta patrones de breakout bar (vela de ruptura).
    
    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'] ordenado por tiempo ascendente.
        window (int): Número de velas anteriores para determinar el rango de consolidación.
    
    Returns:
        pd.DataFrame: El DataFrame original con una columna nueva 'breakout_bar' que puede tener:
                      - 'alcista' para ruptura al alza
                      - 'bajista' para ruptura a la baja
                      - None si no hay patrón detectado
    """
    df = df.copy()
    df['breakout_bar'] = None

    for i in range(window, len(df)):
        rango_anterior = df.iloc[i - window:i]

        max_rango = rango_anterior['high'].max()
        min_rango = rango_anterior['low'].min()

        vela_actual = df.iloc[i]
        
        # Breakout alcista: cuerpo y cierre por encima del máximo del rango anterior
        if vela_actual['close'] > max_rango and vela_actual['open'] < max_rango:
            df.at[i, 'breakout_bar'] = 'alcista'

        # Breakout bajista: cuerpo y cierre por debajo del mínimo del rango anterior
        elif vela_actual['close'] < min_rango and vela_actual['open'] > min_rango:
            df.at[i, 'breakout_bar'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'breakout_bar', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
