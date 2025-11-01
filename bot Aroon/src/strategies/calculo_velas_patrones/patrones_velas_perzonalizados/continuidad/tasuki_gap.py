import pandas as pd

def detectar_tasuki_gap_alcista(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón 'Bullish Tasuki Gap' (continuación alcista).

    Estructura:
    1. Vela 1: fuerte alcista.
    2. Vela 2: gap al alza respecto al cierre de la vela 1, también alcista.
    3. Vela 3: entra en el gap (cuerpo dentro del gap) y es bajista, pero no cierra el gap.
    """
    o = df['open']
    c = df['close']
    
    # Velas 1 y 2 alcistas
    v1 = c.shift(2) > o.shift(2)
    v2 = c.shift(1) > o.shift(1)
    # Gap alcista de vela 2 sobre cierre de vela 1
    gap_alcista = o.shift(1) > c.shift(2)
    # Vela 3 bajista, con apertura dentro del gap y cierre aún por encima del máximo de vela 1
    v3_bajista = c < o
    dentro_gap = (o > c.shift(2)) & (c > c.shift(2))
    
    # Detectar patrón
    patron_detectado = v1 & v2 & gap_alcista & v3_bajista & dentro_gap
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            # Retornar lista de señales
            return [{'indice': idx, 'tipo': 'tasuki_gap', 'fuerza': 0.8} for idx in indices_detectados]
    return []


def detectar_tasuki_gap_bajista(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón 'Bearish Tasuki Gap' (continuación bajista).

    Estructura:
    1. Vela 1: fuerte bajista.
    2. Vela 2: gap a la baja respecto al cierre de la vela 1, también bajista.
    3. Vela 3: entra en el gap (cuerpo dentro del gap) y es alcista, pero no cierra el gap.
    """
    o = df['open']
    c = df['close']
    
    # Velas 1 y 2 bajistas
    v1 = c.shift(2) < o.shift(2)
    v2 = c.shift(1) < o.shift(1)
    # Gap bajista de vela 2 bajo cierre de vela 1
    gap_bajista = o.shift(1) < c.shift(2)
    # Vela 3 alcista, con apertura dentro del gap y cierre aún por debajo del mínimo de vela 1
    v3_alcista = c > o
    dentro_gap = (o < c.shift(2)) & (c < c.shift(2))
    
    # Detectar patrón
    patron_detectado = v1 & v2 & gap_bajista & v3_alcista & dentro_gap
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            # Retornar lista de señales
            return [{'indice': idx, 'tipo': 'tasuki_gap', 'fuerza': 0.8} for idx in indices_detectados]
    return []