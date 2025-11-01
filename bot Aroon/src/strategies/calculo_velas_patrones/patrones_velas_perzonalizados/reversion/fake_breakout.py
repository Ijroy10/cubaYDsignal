import pandas as pd

def detectar_fake_breakout(df: pd.DataFrame) -> list:
    """
    Detecta rupturas falsas (precio rompe nivel pero vuelve).
    """
    if len(df) < 20:
        return []
    
    resultados = []
    
    for i in range(20, len(df)):
        try:
            # Calcular resistencia/soporte de últimas 20 velas
            ventana = df.iloc[i-20:i]
            resistencia = ventana['high'].max()
            soporte = ventana['low'].min()
            
            curr_high = df.iloc[i]['high']
            curr_low = df.iloc[i]['low']
            curr_close = df.iloc[i]['close']
            
            # Falsa ruptura alcista (rompe resistencia pero cierra abajo)
            if curr_high > resistencia and curr_close < resistencia:
                resultados.append({'indice': df.index[i], 'tipo': 'fake_breakout_bajista', 'accion': 'PUT', 'fuerza': 0.7})
            
            # Falsa ruptura bajista (rompe soporte pero cierra arriba)
            elif curr_low < soporte and curr_close > soporte:
                resultados.append({'indice': df.index[i], 'tipo': 'fake_breakout_alcista', 'accion': 'CALL', 'fuerza': 0.7})
        except Exception:
            continue
    
    return resultados
