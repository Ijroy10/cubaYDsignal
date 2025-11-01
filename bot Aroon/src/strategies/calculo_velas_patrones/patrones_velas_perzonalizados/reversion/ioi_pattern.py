import pandas as pd

def detectar_patron_ioi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta el patrón Inside–Outside–Inside (IOI) en velas japonesas.
    Agrega una columna 'ioi_pattern' al DataFrame con los valores:
    - 'alcista' si se detecta ruptura al alza (CALL)
    - 'bajista' si se detecta ruptura a la baja (SELL)
    - None si no hay patrón
    """
    df = df.copy()
    df['ioi_pattern'] = None

    for i in range(3, len(df)-1):
        v1 = df.iloc[i-3]  # Inside
        v2 = df.iloc[i-2]  # Outside
        v3 = df.iloc[i-1]  # Inside
        v4 = df.iloc[i]    # Vela de ruptura

        inside1 = v1['high'] < v2['high'] and v1['low'] > v2['low']
        outside = v2['high'] > v1['high'] and v2['low'] < v1['low']
        inside2 = v3['high'] < v2['high'] and v3['low'] > v2['low']

        if inside1 and outside and inside2:
            # Verificamos la vela de ruptura
            if v4['close'] > v2['high']:
                df.at[i, 'ioi_pattern'] = 'alcista'
            elif v4['close'] < v2['low']:
                df.at[i, 'ioi_pattern'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'ioi_pattern', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
