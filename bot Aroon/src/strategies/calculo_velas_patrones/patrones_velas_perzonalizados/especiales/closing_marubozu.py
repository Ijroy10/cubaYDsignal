import pandas as pd

def detectar_closing_marubozu(df, umbral_mecha=0.001):
    """
    Detecta velas tipo Closing Marubozu (alcistas y bajistas).
    Una vela de cuerpo completo que cierra en su máximo o mínimo, sin mecha.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'].
        umbral_mecha (float): Porcentaje permitido de diferencia para considerar una vela sin mecha.
    
    Returns:
        señales (list): Lista de tuplas (índice, tipo) donde tipo puede ser 'CALL' o 'SELL'.
    """
    señales = []

    for i in range(len(df)):
        o = df.iloc[i]['open']
        h = df.iloc[i]['high']
        l = df.iloc[i]['low']
        c = df.iloc[i]['close']
        rango = h - l if h - l != 0 else 1e-6  # evitar división por cero

        # Marubozu alcista
        if c > o:
            sin_mecha_alta = abs(h - c) / rango <= umbral_mecha
            sin_mecha_baja = abs(o - l) / rango > umbral_mecha
            if sin_mecha_alta and not sin_mecha_baja:
                señales.append((i, 'CALL'))

        # Marubozu bajista
        elif o > c:
            sin_mecha_baja = abs(l - c) / rango <= umbral_mecha
            sin_mecha_alta = abs(h - o) / rango > umbral_mecha
            if sin_mecha_baja and not sin_mecha_alta:
                señales.append((i, 'SELL'))

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'closing_marubozu', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
