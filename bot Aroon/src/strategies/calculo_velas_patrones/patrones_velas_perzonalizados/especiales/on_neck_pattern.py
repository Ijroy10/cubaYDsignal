import pandas as pd

def detectar_on_neck_pattern(df):
    """
    Detecta el patrón On Neck (solo bajista).

    Patrón On Neck:
    - Primera vela: bajista fuerte (cuerpo largo)
    - Segunda vela: alcista, abre con gap bajista pero cierra casi al mismo nivel del mínimo de la primera vela.

    Args:
        df (DataFrame): Debe contener columnas ['open', 'high', 'low', 'close'].

    Returns:
        List of tuples: (index de la segunda vela, 'SELL')
    """
    señales = []

    for i in range(1, len(df)):
        vela1 = df.iloc[i - 1]
        vela2 = df.iloc[i]

        # Vela 1 bajista fuerte
        cuerpo1 = vela1['open'] - vela1['close']
        rango1 = vela1['high'] - vela1['low']

        # Vela 2 alcista con apertura por debajo del cierre anterior
        es_bajista_fuerte = cuerpo1 > (0.7 * rango1) and vela1['close'] < vela1['open']
        apertura_gap = vela2['open'] < vela1['close']
        cierra_nivel_minimo = abs(vela2['close'] - vela1['low']) <= (0.02 * vela1['low'])  # 2% de margen

        if es_bajista_fuerte and apertura_gap and vela2['close'] > vela2['open'] and cierra_nivel_minimo:
            señales.append((i, 'SELL'))

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'on_neck_pattern', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
