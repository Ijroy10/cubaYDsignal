import pandas as pd

def detectar_stalled_pattern(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón de 'Stalled Pattern' (patrón estancado), que sugiere una posible reversión bajista.

    Requisitos:
    - Tres velas alcistas consecutivas.
    - La primera y segunda vela son fuertes alcistas.
    - La tercera vela es más pequeña, con cuerpo más corto.
    - La tercera vela muestra pérdida de impulso.
    """
    o = df['open']
    c = df['close']
    h = df['high']
    l = df['low']

    cuerpo1 = abs(c.shift(2) - o.shift(2))
    cuerpo2 = abs(c.shift(1) - o.shift(1))
    cuerpo3 = abs(c - o)

    # Detectar patrón
    patron_detectado = (
        (c.shift(2) > o.shift(2)) &  # vela 1 alcista
        (c.shift(1) > o.shift(1)) &  # vela 2 alcista
        (c > o) &                    # vela 3 alcista
        (cuerpo1 > cuerpo2) &
        (cuerpo2 > cuerpo3) &
        (c > c.shift(1)) &          # sigue cerrando más alto
        (cuerpo3 < cuerpo2 * 0.6)   # cuerpo más pequeño = pérdida de fuerza
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'stalled_pattern', 'accion': 'PUT', 'fuerza': 0.7} for idx in indices_detectados]
    return []
