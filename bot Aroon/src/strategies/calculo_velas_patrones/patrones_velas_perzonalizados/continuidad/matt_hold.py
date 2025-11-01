import pandas as pd

def detectar_mat_hold(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón Mat Hold (mantener el tapete), un patrón de continuación alcista.

    Estructura típica:
    - Vela 1: fuerte alcista
    - Velas 2-4: consolidación (pueden ser pequeñas velas bajistas o dojis)
    - Vela 5: rompe hacia arriba con fuerza

    Retorna una Serie booleana donde se detecta el patrón.
    """
    o = df['open']
    c = df['close']

    v1 = c.shift(4) > o.shift(4)  # fuerte alcista
    v2 = c.shift(3) < o.shift(3)  # bajista o débil
    v3 = c.shift(2) < o.shift(2)  # bajista o lateral
    v4 = c.shift(1) > o.shift(1)  # ligera recuperación
    v5 = c > o  # fuerte alcista

    consolidacion = (
        (c.shift(3) < c.shift(4)) &
        (c.shift(2) < c.shift(3)) &
        (c.shift(1) > c.shift(2))
    )

    rompe_alcista = c > c.shift(1) and c > c.shift(4)

    # Detectar patrón
    patron_detectado = v1 & v2 & v3 & v4 & v5 & consolidacion & rompe_alcista
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            # Retornar lista de señales
            return [{'indice': idx, 'tipo': 'matt_hold', 'fuerza': 0.8} for idx in indices_detectados]
    return []