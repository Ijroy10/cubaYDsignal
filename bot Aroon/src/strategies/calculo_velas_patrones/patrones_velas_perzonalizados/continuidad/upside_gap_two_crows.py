import pandas as pd

def upside_gap_two_crows(df):
    """
    Detecta el patrón Upside Gap Two Crows en un DataFrame OHLC.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'] ordenado por tiempo ascendente.
                           Debe tener al menos 3 filas.
    
    Returns:
        str: "bajista" si se detecta patrón bajista,
             None si no se detecta patrón.
    """
    if len(df) < 3:
        return None  # No hay suficientes velas

    c1 = df.iloc[-3]  # Primera vela
    c2 = df.iloc[-2]  # Segunda vela
    c3 = df.iloc[-1]  # Tercera vela

    # Condiciones para Upside Gap Two Crows (patrón bajista de reversión)
    cond = (
        # Primera vela alcista grande
        (c1['close'] > c1['open']) and
        # Gap al alza entre la vela 2 y la vela 1
        (c2['open'] > c1['close']) and
        (c2['close'] < c2['open']) and  # Vela 2 bajista
        (c2['close'] > c1['close']) and  # Cierre de vela 2 dentro del gap arriba
        # Vela 3 bajista que cierra dentro del cuerpo de la vela 1 (pero no supera apertura)
        (c3['close'] < c3['open']) and
        (c3['close'] < c2['close']) and
        (c3['close'] > c1['open']) and
        (c3['open'] > c2['close']) and
        # Gap entre vela 3 y vela 2 (la vela 3 abre dentro del gap)
        (c3['open'] < c2['open'])
    )

    if cond:
        return "bajista"
    else:
        return None