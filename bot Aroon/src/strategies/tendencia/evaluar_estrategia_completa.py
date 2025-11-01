from strategy.tendencia.tendencia_main import analizar_tendencia_completa

def evaluar_estrategia(activo):
    # Aquí deberías obtener el DataFrame de velas para el activo
    df = obtener_datos_del_activo(activo)  # Implementa esta función según tu fuente de datos

    resultado_tendencia = analizar_tendencia_completa(df)
    # ...aquí puedes seguir con el resto de tus estrategias y sumar efectividades...

    # Ejemplo de resultado combinado:
    return {
        "activo": activo,
        "tendencia": resultado_tendencia,
        # ...otros resultados de estrategias...
        "efectividad": calcular_efectividad_global(resultado_tendencia, ...),  # Implementa tu lógica
        "decision": "CALL"  # o "SELL" según tu análisis
    }