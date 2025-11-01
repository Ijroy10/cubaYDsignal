import pandas as pd

def detectar_rising_three(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón 'Rising Three Methods' de continuación alcista.

    Estructura:
    - Vela 1: vela alcista larga
    - Velas 2-4: velas bajistas pequeñas dentro del rango de la Vela 1
    - Vela 5: vela alcista que rompe el cierre de la Vela 1
    """
    o = df['open']
    c = df['close']
    h = df['high']
    l = df['low']

    v1 = c.shift(4) > o.shift(4)
    v2 = c.shift(3) < o.shift(3)
    v3 = c.shift(2) < o.shift(2)
    v4 = c.shift(1) < o.shift(1)
    v5 = c > o

    dentro_rango = (
        (h.shift(3) < h.shift(4)) & (l.shift(3) > l.shift(4)) &
        (h.shift(2) < h.shift(4)) & (l.shift(2) > l.shift(4)) &
        (h.shift(1) < h.shift(4)) & (l.shift(1) > l.shift(4))
    )

    rompe_rango = c > c.shift(4)

    # Detectar patrón
    patron_detectado = v1 & v2 & v3 & v4 & v5 & dentro_rango & rompe_rango
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            # Retornar lista de señales
            return [{'indice': idx, 'tipo': 'rising_falling_three', 'fuerza': 0.8} for idx in indices_detectados]
    return []


def detectar_falling_three(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón 'Falling Three Methods' de continuación bajista.

    Estructura:
    - Vela 1: vela bajista larga
    - Velas 2-4: velas alcistas pequeñas dentro del rango de la Vela 1
    - Vela 5: vela bajista que rompe el cierre de la Vela 1
    """
    o = df['open']
    c = df['close']
    h = df['high']
    l = df['low']

    v1 = c.shift(4) < o.shift(4)
    v2 = c.shift(3) > o.shift(3)
    v3 = c.shift(2) > o.shift(2)
    v4 = c.shift(1) > o.shift(1)
    v5 = c < o

    dentro_rango = (
        (h.shift(3) < h.shift(4)) & (l.shift(3) > l.shift(4)) &
        (h.shift(2) < h.shift(4)) & (l.shift(2) > l.shift(4)) &
        (h.shift(1) < h.shift(4)) & (l.shift(1) > l.shift(4))
    )

    rompe_rango = c < c.shift(4)

    # Detectar patrón
    patron_detectado = v1 & v2 & v3 & v4 & v5 & dentro_rango & rompe_rango
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            # Retornar lista de señales
            return [{'indice': idx, 'tipo': 'rising_falling_three', 'fuerza': 0.8} for idx in indices_detectados]
    return []