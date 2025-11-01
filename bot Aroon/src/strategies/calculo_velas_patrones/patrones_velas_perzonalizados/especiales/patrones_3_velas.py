import pandas as pd

def detectar_patrones_3_velas(df):
    """
    Detecta los patrones de tres velas:
    - Morning Star (Estrella del Amanecer) => CALL
    - Evening Star (Estrella del Atardecer) => SELL

    Requiere que el DataFrame tenga las columnas: ['open', 'high', 'low', 'close']

    Returns:
        List of tuples: (index de la tercera vela, 'CALL' o 'SELL')
    """
    señales = []

    for i in range(2, len(df)):
        vela1 = df.iloc[i - 2]
        vela2 = df.iloc[i - 1]
        vela3 = df.iloc[i]

        cuerpo1 = vela1['close'] - vela1['open']
        cuerpo2 = vela2['close'] - vela2['open']
        cuerpo3 = vela3['close'] - vela3['open']

        # === Morning Star === (CALL)
        if (
            cuerpo1 < 0 and  # Vela 1 bajista
            abs(cuerpo2) < abs(cuerpo1) * 0.5 and  # Vela 2 cuerpo pequeño (doji o indecisión)
            cuerpo3 > 0 and vela3['close'] > (vela1['open'] + vela1['close']) / 2  # Vela 3 fuerte alcista
        ):
            señales.append((i, 'CALL'))

        # === Evening Star === (SELL)
        if (
            cuerpo1 > 0 and  # Vela 1 alcista
            abs(cuerpo2) < abs(cuerpo1) * 0.5 and  # Vela 2 indecisión
            cuerpo3 < 0 and vela3['close'] < (vela1['open'] + vela1['close']) / 2  # Vela 3 fuerte bajista
        ):
            señales.append((i, 'SELL'))

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'patrones_3_velas', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
