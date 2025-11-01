import pandas as pd

def detectar_three_inside(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta el patrón Three Inside Up y Three Inside Down (3 velas).

    Patrón Alcista (Three Inside Up):
    1. Vela bajista grande.
    2. Vela alcista dentro del cuerpo de la primera.
    3. Tercera vela cierra por encima del cierre de la segunda.

    Patrón Bajista (Three Inside Down):
    1. Vela alcista grande.
    2. Vela bajista dentro del cuerpo de la primera.
    3. Tercera vela cierra por debajo del cierre de la segunda.

    Devuelve un DataFrame con columna 'three_inside':
    - 'alcista' si se detecta el patrón alcista.
    - 'bajista' si se detecta el patrón bajista.
    """
    df = df.copy()
    df['three_inside'] = None

    for i in range(2, len(df)):
        o1, c1 = df.loc[i - 2, 'open'], df.loc[i - 2, 'close']
        o2, c2 = df.loc[i - 1, 'open'], df.loc[i - 1, 'close']
        o3, c3 = df.loc[i, 'open'], df.loc[i, 'close']

        # Three Inside Up (alcista)
        if c1 < o1 and o2 > c1 and c2 < o1 and c3 > c2:
            df.loc[i, 'three_inside'] = 'alcista'

        # Three Inside Down (bajista)
        elif c1 > o1 and o2 < c1 and c2 > o1 and c3 < c2:
            df.loc[i, 'three_inside'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'three_inside_up_down', 'accion': 'PUT', 'fuerza': 0.75} for idx in indices_detectados]
    return []
