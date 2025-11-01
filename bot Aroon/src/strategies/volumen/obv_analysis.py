import pandas as pd

def calcular_obv(df: pd.DataFrame) -> pd.Series:
    """
    Calcula el On-Balance Volume (OBV) a partir de un DataFrame con precios de cierre y volumen.

    Parámetros:
        df (pd.DataFrame): Debe tener columnas 'close' y 'volume'

    Retorna:
        pd.Series: Serie de OBV calculado
    """
    obv = [0]
    for i in range(1, len(df)):
        if df['close'][i] > df['close'][i - 1]:
            obv.append(obv[-1] + df['volume'][i])
        elif df['close'][i] < df['close'][i - 1]:
            obv.append(obv[-1] - df['volume'][i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=df.index)

def interpretar_obv(df: pd.DataFrame) -> str:
    """
    Interpreta la dirección del OBV para evaluar la presión compradora o vendedora.

    Parámetros:
        df (pd.DataFrame): DataFrame con columnas 'close' y 'volume'

    Retorna:
        str: Interpretación de la presión de volumen
    """
    obv = calcular_obv(df)

    if len(obv) < 3:
        return "Datos insuficientes para análisis OBV"

    if obv.iloc[-1] > obv.iloc[-2] > obv.iloc[-3]:
        return "OBV en aumento: presión compradora"
    elif obv.iloc[-1] < obv.iloc[-2] < obv.iloc[-3]:
        return "OBV en descenso: presión vendedora"
    else:
        return "OBV lateral: sin presión clara"