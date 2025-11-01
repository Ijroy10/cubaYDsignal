import pandas as pd

def detectar_kicking_pattern(df):
    """
    Detecta el patrón Kicking (alcista y bajista).
    
    Alcista: Vela bajista marubozu seguida por vela alcista marubozu con gap alcista.
    Bajista: Vela alcista marubozu seguida por vela bajista marubozu con gap bajista.

    Args:
        df (DataFrame): Debe contener ['open', 'high', 'low', 'close'].

    Returns:
        List of tuples: (index, 'CALL' o 'SELL') donde se detecta el patrón.
    """
    señales = []

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        # Marubozu: vela sin mechas o muy pequeñas (más del 90% cuerpo)
        def es_marubozu(vela):
            cuerpo = abs(vela['close'] - vela['open'])
            mechas = (vela['high'] - max(vela['open'], vela['close'])) + (min(vela['open'], vela['close']) - vela['low'])
            return cuerpo > 0 and cuerpo / (cuerpo + mechas) > 0.9

        # Verificamos que ambas velas son marubozu
        if es_marubozu(prev) and es_marubozu(curr):
            # Kicking alcista
            if prev['close'] < prev['open'] and curr['close'] > curr['open']:
                if curr['open'] > prev['close']:
                    señales.append((i, 'CALL'))

            # Kicking bajista
            elif prev['close'] > prev['open'] and curr['close'] < curr['open']:
                if curr['open'] < prev['close']:
                    señales.append((i, 'SELL'))

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'kicking_pattern', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []