"""
ESTRATEGIA COMPLETA DE ANÁLISIS TÉCNICO
Usa la estrategia avanzada implementada en src/strategies/evaluar_estrategia_completa.py

Esta estrategia incluye:
1. Análisis de Tendencia (MA, ADX, MACD)
2. Soportes y Resistencias
3. Patrones de Velas (33+ patrones)
4. Volatilidad y Acción del Precio
5. Análisis de Volumen
"""

from src.strategies.evaluar_estrategia_completa import evaluar_estrategia_completa as estrategia_completa

def evaluar_estrategia_completa(df, symbol):
    """
    Función principal que usa la estrategia completa implementada.
    
    Args:
        df: DataFrame con datos OHLC del mercado
        symbol: Símbolo del mercado (ej: EURUSD)
    
    Returns:
        dict: Resultado con efectividad_total, decision, detalles, resumen
    """
    if df is None or df.empty:
        return {
            "symbol": symbol,
            "error": "No hay datos para analizar",
            "efectividad_total": 0,
            "decision": None
        }
    
    # Usar la estrategia completa implementada en src/strategies
    resultado = estrategia_completa(df, mercado=symbol)
    
    # Formatear respuesta compatible con SignalScheduler
    resumen = resultado.get("resumen", [])
    detalles = resultado.get("detalles", {})
    
    # Detectar pullback desde resumen (es una lista de strings)
    pullback_detectado = False
    if isinstance(resumen, list):
        pullback_detectado = any("pullback" in str(item).lower() for item in resumen)
    
    return {
        "symbol": symbol,
        "efectividad_total": resultado.get("efectividad_total", 0),
        "decision": resultado.get("decision"),
        "tendencia_direccion": detalles.get("tendencia", {}).get("direccion", "neutral"),
        "resumen": resumen,
        "detalles": detalles,
        "pullback_detectado": pullback_detectado,
        "volatilidad_estado": detalles.get("volatilidad", {}).get("detalles", {}).get("volatilidad", {}).get("estado", "media")
    }