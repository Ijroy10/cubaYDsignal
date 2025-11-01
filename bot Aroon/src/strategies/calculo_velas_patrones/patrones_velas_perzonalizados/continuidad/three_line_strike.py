import pandas as pd

def three_line_strike(df):
    """
    Detecta patrón Three Line Strike alcista o bajista en un DataFrame OHLC.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'] ordenado por tiempo ascendente.
                           Debe tener al menos 4 filas.
    
    Returns:
        str: "alcista" si detecta patrón alcista,
             "bajista" si detecta patrón bajista,
             None si no se detecta patrón.
    """
    if len(df) < 4:
        return None  # No hay suficientes velas

    # Extraemos las últimas 4 velas
    c1 = df.iloc[-4]
    c2 = df.iloc[-3]
    c3 = df.iloc[-2]
    c4 = df.iloc[-1]

    # Patrón alcista Three Line Strike
    # 3 velas bajistas consecutivas con cierre descendente
    cond_alcista = (
        (c1['close'] < c1['open']) and
        (c2['close'] < c2['open']) and
        (c3['close'] < c3['open']) and
        (c2['close'] < c1['close']) and
        (c3['close'] < c2['close']) and
        # 4ta vela alcista que abre bajo cierre 3 y cierra arriba de apertura 1
        (c4['close'] > c4['open']) and
        (c4['open'] < c3['close']) and
        (c4['close'] > c1['open'])
    )

    # Patrón bajista Three Line Strike
    # 3 velas alcistas consecutivas con cierre ascendente
    cond_bajista = (
        (c1['close'] > c1['open']) and
        (c2['close'] > c2['open']) and
        (c3['close'] > c3['open']) and
        (c2['close'] > c1['close']) and
        (c3['close'] > c2['close']) and
        # 4ta vela bajista que abre por encima del cierre 3 y cierra por debajo de apertura 1
        (c4['close'] < c4['open']) and
        (c4['open'] > c3['close']) and
        (c4['close'] < c1['open'])
    )

    if cond_alcista:
        return "alcista"
    elif cond_bajista:
        return "bajista"
    else:
        return None