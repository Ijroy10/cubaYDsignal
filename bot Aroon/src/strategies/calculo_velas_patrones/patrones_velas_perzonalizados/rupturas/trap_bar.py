import pandas as pd

def detectar_trap_bar(df: pd.DataFrame) -> list:
    """
    Detecta trap bars (velas trampa).
    """
    if len(df) < 3:
        return []
    
    resultados = []
    
    for i in range(2, len(df)):
        try:
            v1_high = df.iloc[i-2]['high']
            v2_high = df.iloc[i-1]['high']
            v3_close = df.iloc[i]['close']
            
            # Trap alcista (nuevo máximo pero cierra abajo)
            if v2_high > v1_high and v3_close < v1_high:
                resultados.append({'indice': df.index[i], 'tipo': 'trap_bajista', 'accion': 'PUT', 'fuerza': 0.7})
        except Exception:
            continue
    
    return resultados
