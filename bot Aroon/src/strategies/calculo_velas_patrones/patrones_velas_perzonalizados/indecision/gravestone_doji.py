import pandas as pd

def detectar_gravestone_doji(df, tolerancia_cuerpo=0.1, min_mecha_ratio=2.0):
    """
    Detecta un patrón Gravestone Doji (Doji Lápida) en un DataFrame.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango = df['high'] - df['low']
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']

    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango.replace(0, 1)
    
    # Detectar patrón
    patron_detectado = (
        (rango > 0) &
        (cuerpo_ratio < tolerancia_cuerpo) &
        (mecha_superior > cuerpo * min_mecha_ratio) &
        (mecha_inferior < cuerpo * 0.5)
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'gravestone_doji', 'accion': 'PUT', 'fuerza': 0.7} for idx in indices_detectados]
    return []
