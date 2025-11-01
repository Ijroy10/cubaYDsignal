import pandas as pd

def detectar_opening_marubozu(df, margen_mecha=0.02):
    """
    Detecta velas tipo Opening Marubozu (sin mecha inicial).
    
    Características:
    - Alcista: abre en el mínimo y sube con cuerpo largo.
    - Bajista: abre en el máximo y baja con cuerpo largo.
    - Sin mecha en la apertura (o muy pequeña, configurable).

    Args:
        df (DataFrame): Debe contener columnas ['open', 'high', 'low', 'close']
        margen_mecha (float): porcentaje del cuerpo que puede tolerarse como "mecha"

    Returns:
        List of tuples: (index, 'CALL' o 'SELL')
    """
    señales = []

    for i in range(len(df)):
        fila = df.iloc[i]
        open_ = fila['open']
        close = fila['close']
        high = fila['high']
        low = fila['low']
        cuerpo = abs(close - open_)

        if cuerpo == 0:
            continue  # No hay cuerpo real

        if close > open_:
            # Vela alcista
            mecha_inferior = open_ - low
            if mecha_inferior <= cuerpo * margen_mecha:
                señales.append((i, 'CALL'))

        elif close < open_:
            # Vela bajista
            mecha_superior = high - open_
            if mecha_superior <= cuerpo * margen_mecha:
                señales.append((i, 'SELL'))

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'opening_marubozu', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
