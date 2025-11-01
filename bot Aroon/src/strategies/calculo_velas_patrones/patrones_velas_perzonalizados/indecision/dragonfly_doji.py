import pandas as pd

def detectar_dragonfly_doji(df, tolerancia_cuerpo=0.1, min_mecha_ratio=2.0):
    """
    Detecta un patrón Dragonfly Doji en un DataFrame.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'].
        tolerancia_cuerpo (float): Proporción máxima del cuerpo respecto al rango para considerar doji.
        min_mecha_ratio (float): Relación mínima entre mecha inferior y cuerpo.

    Returns:
        list: Lista de señales detectadas.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango = df['high'] - df['low']
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)

    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango.replace(0, 1)
    
    # Detectar patrón
    patron_detectado = (
        (rango > 0) &
        (cuerpo_ratio < tolerancia_cuerpo) &
        (mecha_inferior > cuerpo * min_mecha_ratio) &
        (mecha_superior < cuerpo * 0.5)
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'dragonfly_doji', 'accion': 'CALL', 'fuerza': 0.7} for idx in indices_detectados]
    return []
