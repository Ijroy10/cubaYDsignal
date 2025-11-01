import pandas as pd

# NUEVA ESTRATEGIA: EMA 50/36 + AROON
from .ema_aroon_strategy import evaluar_estrategia_completa as evaluar_ema_aroon

def evaluar_estrategia_completa(df: pd.DataFrame, mercado: str = "EURUSD") -> dict:
    """
    ESTRATEGIA EMA 50/36 + AROON
    
    Estrategia simplificada basada en:
    - Cruces de EMAs (36 y 50)
    - Confirmación con indicador Aroon
    - Rebotes en EMAs
    - Velas consecutivas del mismo color
    
    Args:
        df: DataFrame con columnas ['open', 'high', 'low', 'close']
        mercado: Nombre del mercado (default: EURUSD)
    
    Returns:
        dict: Resultado final con decisión y efectividad
    """
    print(f"[Bot] Ejecutando Estrategia EMA 50/36 + Aroon para {mercado}...")
    return evaluar_ema_aroon(df, mercado)

# Funciones legacy eliminadas - La nueva estrategia EMA + Aroon es autosuficiente
