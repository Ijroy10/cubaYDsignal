import pandas as pd

def detectar_separating_lines_alcista(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón 'Separating Lines' alcista.
    
    Estructura:
    - Vela 1: bajista (roja)
    - Vela 2: alcista (verde) con mismo precio de apertura que la primera vela
    - Cierre de la segunda vela supera el máximo de la primera (confirma continuación alcista)
    """
    o = df['open']
    c = df['close']
    h = df['high']

    v1_bajista = c.shift(1) < o.shift(1)
    v2_alcista = c > o
    misma_apertura = o == o.shift(1)
    cierre_fuerte = c > h.shift(1)

    # Detectar patrón
    patron_detectado = v1_bajista & v2_alcista & misma_apertura & cierre_fuerte
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            # Retornar lista de señales
            return [{'indice': idx, 'tipo': 'separating_lines', 'fuerza': 0.8} for idx in indices_detectados]
    return []


def detectar_separating_lines_bajista(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón 'Separating Lines' bajista.

    Estructura:
    - Vela 1: alcista (verde)
    - Vela 2: bajista (roja) con mismo precio de apertura que la primera vela
    - Cierre de la segunda vela cae por debajo del mínimo de la primera (confirma continuación bajista)
    """
    o = df['open']
    c = df['close']
    l = df['low']

    v1_alcista = c.shift(1) > o.shift(1)
    v2_bajista = c < o
    misma_apertura = o == o.shift(1)
    cierre_fuerte = c < l.shift(1)

    # Detectar patrón
    patron_detectado = v1_alcista & v2_bajista & misma_apertura & cierre_fuerte
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            # Retornar lista de señales
            return [{'indice': idx, 'tipo': 'separating_lines', 'fuerza': 0.8} for idx in indices_detectados]
    return []
