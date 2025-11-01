import pandas as pd

def detectar_counterattack_lines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta el patrón Counterattack Lines (líneas de contraataque):
    - Ocurre después de una tendencia previa
    - Dos velas consecutivas con cuerpos opuestos que cierran aproximadamente al mismo nivel
    - Señala posible reversión

    Agrega una columna 'counterattack_lines' con valores:
    - 'alcista' si el patrón es alcista
    - 'bajista' si el patrón es bajista
    - None si no hay patrón
    """

    df = df.copy()
    df['counterattack_lines'] = None
    margen_cierre = 0.002  # margen relativo para considerar cierres iguales (0.2%)

    for i in range(1, len(df)):
        v1 = df.iloc[i-1]
        v2 = df.iloc[i]

        # Condiciones para counterattack alcista:
        # 1. Vela 1 bajista, vela 2 alcista
        # 2. Cierres muy cerca (dentro margen)
        # 3. Cierre vela 2 >= cierre vela 1

        cierre_cerca = abs(v1['close'] - v2['close']) / v1['close'] < margen_cierre

        if (v1['close'] < v1['open']) and (v2['close'] > v2['open']) and cierre_cerca:
            df.at[df.index[i], 'counterattack_lines'] = 'alcista'

        # Condiciones para counterattack bajista:
        # 1. Vela 1 alcista, vela 2 bajista
        # 2. Cierres muy cerca (dentro margen)
        # 3. Cierre vela 2 <= cierre vela 1

        elif (v1['close'] > v1['open']) and (v2['close'] < v2['open']) and cierre_cerca:
            df.at[df.index[i], 'counterattack_lines'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'counterattack_lines', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
