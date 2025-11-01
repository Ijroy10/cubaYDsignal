import pandas as pd

def detectar_patron_pinbar(df: pd.DataFrame, factor_mecha=2.0) -> pd.DataFrame:
    """
    Detecta Pin Bars alcistas y bajistas.

    Un Pin Bar tiene:
    - Cuerpo pequeño
    - Mecha larga (superior o inferior al menos X veces el tamaño del cuerpo)

    Devuelve un DataFrame con una columna 'pinbar' que indica:
    - 'alcista' si es un pin bar alcista
    - 'bajista' si es un pin bar bajista
    """
    df = df.copy()
    df['pinbar'] = None

    for i in range(len(df)):
        open_ = df.loc[i, 'open']
        close = df.loc[i, 'close']
        high = df.loc[i, 'high']
        low = df.loc[i, 'low']

        cuerpo = abs(close - open_)
        mecha_superior = high - max(open_, close)
        mecha_inferior = min(open_, close) - low

        if cuerpo == 0:  # Evitar división por cero
            continue

        # Pin bar alcista (rechazo hacia abajo)
        if mecha_inferior > factor_mecha * cuerpo and mecha_superior < cuerpo:
            df.loc[i, 'pinbar'] = 'alcista'

        # Pin bar bajista (rechazo hacia arriba)
        elif mecha_superior > factor_mecha * cuerpo and mecha_inferior < cuerpo:
            df.loc[i, 'pinbar'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'pinbar', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []