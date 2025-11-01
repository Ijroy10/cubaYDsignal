import pandas as pd

def detectar_bebe_abandonado(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta el patrón Bebé Abandonado alcista y bajista.
    Agrega una nueva columna 'bebe_abandonado' al DataFrame con valores:
    - 'alcista' si se detecta patrón alcista
    - 'bajista' si se detecta patrón bajista
    - None si no se detecta patrón

    Patrón formado por:
    1ª vela fuerte (en dirección de la tendencia)
    2ª vela Doji con gap (separada de la 1ª y 3ª)
    3ª vela fuerte contraria a la 1ª
    """

    df = df.copy()
    df['bebe_abandonado'] = None

    for i in range(2, len(df)):
        v1 = df.iloc[i-2]
        v2 = df.iloc[i-1]
        v3 = df.iloc[i]

        # Detectar doji en vela 2
        cuerpo_v2 = abs(v2['close'] - v2['open'])
        rango_v2 = v2['high'] - v2['low']
        es_doji = cuerpo_v2 <= (rango_v2 * 0.1)  # cuerpo pequeño comparado con rango

        # Comprobar gaps entre vela1-vela2 y vela2-vela3
        gap_entre_1_2 = (v2['low'] > v1['high']) or (v2['high'] < v1['low'])
        gap_entre_2_3 = (v3['low'] > v2['high']) or (v3['high'] < v2['low'])

        # Vela 1 fuerte alcista o bajista
        cuerpo_v1 = abs(v1['close'] - v1['open'])
        es_v1_alcista = v1['close'] > v1['open'] and cuerpo_v1 > (v1['high'] - v1['low']) * 0.5
        es_v1_bajista = v1['close'] < v1['open'] and cuerpo_v1 > (v1['high'] - v1['low']) * 0.5

        # Vela 3 fuerte en dirección contraria a vela 1
        cuerpo_v3 = abs(v3['close'] - v3['open'])
        es_v3_alcista = v3['close'] > v3['open'] and cuerpo_v3 > (v3['high'] - v3['low']) * 0.5
        es_v3_bajista = v3['close'] < v3['open'] and cuerpo_v3 > (v3['high'] - v3['low']) * 0.5

        if es_doji and gap_entre_1_2 and gap_entre_2_3:
            if es_v1_bajista and es_v3_alcista:
                df.at[df.index[i], 'bebe_abandonado'] = 'alcista'
            elif es_v1_alcista and es_v3_bajista:
                df.at[df.index[i], 'bebe_abandonado'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'bebe_abandonado', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
