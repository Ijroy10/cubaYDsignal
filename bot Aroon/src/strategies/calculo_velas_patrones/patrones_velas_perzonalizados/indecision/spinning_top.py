import pandas as pd

def detectar_spinning_top(df, max_cuerpo_ratio=0.4, min_mecha_ratio=0.3):
    """
    Detecta un patrón Spinning Top (Peonza) en un DataFrame.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango_total = df['high'] - df['low']

    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango_total.replace(0, 1)
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']

    mecha_superior_ratio = mecha_superior / rango_total.replace(0, 1)
    mecha_inferior_ratio = mecha_inferior / rango_total.replace(0, 1)

    # Detectar patrón
    patron_detectado = (
        (rango_total > 0) &
        (cuerpo_ratio <= max_cuerpo_ratio) &
        (mecha_superior_ratio >= min_mecha_ratio) &
        (mecha_inferior_ratio >= min_mecha_ratio)
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'spinning_top', 'accion': 'CALL', 'fuerza': 0.6} for idx in indices_detectados]
    return []
