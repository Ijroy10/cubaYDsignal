import pandas as pd

def detectar_dojis(df, tolerancia=0.1):
    """
    Detecta Dojis clásicos en un DataFrame.

    Args:
        df (pd.DataFrame): DataFrame con columnas open, high, low, close.
        tolerancia (float): Proporción máxima del cuerpo respecto al rango para ser considerado doji.

    Returns:
        list: Lista de señales detectadas.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango_total = df['high'] - df['low']
    
    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango_total.replace(0, 1)
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']

    # Detectar dojis básicos
    patron_detectado = (rango_total > 0) & (cuerpo_ratio < tolerancia)
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'doji', 'accion': 'CALL', 'fuerza': 0.6} for idx in indices_detectados]
    return []