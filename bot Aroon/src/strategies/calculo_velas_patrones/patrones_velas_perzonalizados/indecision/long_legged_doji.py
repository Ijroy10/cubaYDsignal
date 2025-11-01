import pandas as pd

def detectar_long_legged_doji(df, tolerancia_cuerpo=0.05, min_mecha_ratio=0.4):
    """
    Detecta el patrón Long-Legged Doji (Doji de piernas largas) en un DataFrame.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango_total = df['high'] - df['low']

    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango_total.replace(0, 1)
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']
    mechas_ratio_total = (mecha_superior + mecha_inferior) / rango_total.replace(0, 1)

    # Detectar patrón
    patron_detectado = (
        (rango_total > 0) &
        (cuerpo_ratio <= tolerancia_cuerpo) &
        (mecha_superior > 0) &
        (mecha_inferior > 0) &
        (mechas_ratio_total >= min_mecha_ratio)
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'long_legged_doji', 'accion': 'CALL', 'fuerza': 0.65} for idx in indices_detectados]
    return []
