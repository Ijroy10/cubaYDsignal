import pandas as pd
import ta

def analizar_tendencia(df, periodo_largo=50, periodo_corto=14):
    """
    Analiza la tendencia principal y secundaria usando medias móviles.
    df: DataFrame con columnas ['close']
    """
    df['ma_larga'] = df['close'].rolling(periodo_largo).mean()
    df['ma_corta'] = df['close'].rolling(periodo_corto).mean()
    tendencia_principal = "alcista" if df['ma_larga'].iloc[-1] < df['close'].iloc[-1] else "bajista"
    tendencia_secundaria = "alcista" if df['ma_corta'].iloc[-1] < df['close'].iloc[-1] else "bajista"
    return {
        "tendencia_principal": tendencia_principal,
        "tendencia_secundaria": tendencia_secundaria,
        "ma_larga": df['ma_larga'].iloc[-1],
        "ma_corta": df['ma_corta'].iloc[-1]
    }