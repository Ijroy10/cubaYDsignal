import pandas as pd
import pandas_ta as ta

def detectar_divergencias(df):
    resultado = {
        "divergencia_rsi": None,
        "divergencia_obv": None
    }

    if len(df) < 20:
        return resultado

    df = df.copy()
    # Calcular RSI y OBV con pandas-ta
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['OBV'] = ta.obv(df['close'], df['volume'])

    # Validar que no haya NaNs
    if df['RSI'].isna().any() or df['OBV'].isna().any():
        return resultado

    precio_ultimo = df['close'].iloc[-1]
    precio_anterior = df['close'].iloc[-5]

    rsi_ultimo = df['RSI'].iloc[-1]
    rsi_anterior = df['RSI'].iloc[-5]

    obv_ultimo = df['OBV'].iloc[-1]
    obv_anterior = df['OBV'].iloc[-5]

    if precio_ultimo > precio_anterior and rsi_ultimo < rsi_anterior:
        resultado["divergencia_rsi"] = "bajista"
    elif precio_ultimo < precio_anterior and rsi_ultimo > rsi_anterior:
        resultado["divergencia_rsi"] = "alcista"

    if precio_ultimo > precio_anterior and obv_ultimo < obv_anterior:
        resultado["divergencia_obv"] = "bajista"
    elif precio_ultimo < precio_anterior and obv_ultimo > obv_anterior:
        resultado["divergencia_obv"] = "alcista"

    return resultado
