import pandas as pd

def detectar_marubozu(df, umbral=0.9):
    """
    Detecta patrones Marubozu alcistas y bajistas.

    Un Marubozu es una vela con cuerpo completo (sin mechas o muy pequeñas),
    lo que indica decisión total del mercado.

    Args:
        df (DataFrame): Debe contener columnas ['open', 'high', 'low', 'close'].
        umbral (float): Proporción mínima del cuerpo respecto al total de la vela (por defecto 0.9).

    Returns:
        List of tuples: (index, 'CALL' o 'SELL')
    """
    señales = []

    for i in range(len(df)):
        vela = df.iloc[i]

        cuerpo = abs(vela['close'] - vela['open'])
        rango_total = vela['high'] - vela['low']

        if rango_total == 0:
            continue  # evitar división por cero

        proporcion_cuerpo = cuerpo / rango_total

        if proporcion_cuerpo >= umbral:
            if vela['close'] > vela['open']:
                señales.append((i, 'CALL'))  # Marubozu alcista
            elif vela['close'] < vela['open']:
                señales.append((i, 'SELL'))  # Marubozu bajista

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'marubozu', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
