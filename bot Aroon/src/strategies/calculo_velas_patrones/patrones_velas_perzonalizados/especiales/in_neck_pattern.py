import pandas as pd

def detectar_in_neck_pattern(df):
    """
    Detecta el patrón In-Neck (cuello interno), que es un patrón de continuación bajista.

    Requisitos:
    - Primera vela: gran vela bajista (roja)
    - Segunda vela: vela alcista (verde) que abre con gap bajista y cierra cerca del cierre de la anterior pero sin superarlo.

    Args:
        df (DataFrame): Debe contener columnas ['open', 'high', 'low', 'close']

    Returns:
        List of tuples: (index, 'SELL') donde se detecta el patrón
    """
    señales = []

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        cuerpo_grande_prev = abs(prev['open'] - prev['close']) > (prev['high'] - prev['low']) * 0.5
        cuerpo_grande_curr = abs(curr['open'] - curr['close']) > (curr['high'] - curr['low']) * 0.5

        # Primera vela bajista fuerte
        if prev['close'] < prev['open'] and cuerpo_grande_prev:
            # Segunda vela verde que abre con gap bajista
            if curr['close'] > curr['open'] and curr['open'] < prev['close']:
                # Cierra cerca del cierre de la anterior (pero no lo supera)
                if curr['close'] <= prev['close'] + 0.1 * abs(prev['open'] - prev['close']):
                    señales.append((i, 'SELL'))

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'in_neck_pattern', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
