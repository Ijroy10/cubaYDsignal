import pandas as pd

def detectar_railway_tracks(df):
    """
    Detecta el patrón Railway Tracks (Pistas de tren), que es un patrón de reversión formado por dos velas consecutivas:
    - La primera vela tiene cuerpo grande y dirección
    - La segunda vela tiene cuerpo grande en dirección opuesta y similar tamaño al primero

    Requiere columnas ['open', 'high', 'low', 'close'].

    Retorna:
        Lista de tuplas (índice de la segunda vela, 'CALL' o 'SELL')
    """
    señales = []

    for i in range(1, len(df)):
        vela1 = df.iloc[i - 1]
        vela2 = df.iloc[i]

        cuerpo1 = abs(vela1['close'] - vela1['open'])
        cuerpo2 = abs(vela2['close'] - vela2['open'])

        # Velas con cuerpo grande (umbral arbitrario, se puede ajustar)
        umbral = (df['high'] - df['low']).mean() * 0.6

        if cuerpo1 < umbral or cuerpo2 < umbral:
            continue  # Cuerpos no suficientemente grandes

        # Dirección de las velas
        alcista1 = vela1['close'] > vela1['open']
        alcista2 = vela2['close'] > vela2['open']

        # Detectar cuerpo similar tamaño (±20%)
        if not (0.8 <= cuerpo2 / cuerpo1 <= 1.2):
            continue

        # Patrón Railway Tracks: velas consecutivas en direcciones opuestas
        if alcista1 and not alcista2:
            señales.append((i, 'SELL'))  # Reversión bajista
        elif not alcista1 and alcista2:
            señales.append((i, 'CALL'))  # Reversión alcista

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'railway_tracks', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
