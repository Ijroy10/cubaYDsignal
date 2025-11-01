import pandas as pd

def detectar_gap_escape(df: pd.DataFrame) -> list:
    """
    Detecta gaps (huecos) en el precio.
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            curr_high = df.iloc[i]['high']
            curr_low = df.iloc[i]['low']
            curr_close = df.iloc[i]['close']
            curr_open = df.iloc[i]['open']
            
            # Gap alcista (mínimo actual > máximo anterior)
            if curr_low > prev_high:
                resultados.append({'indice': df.index[i], 'tipo': 'gap_alcista', 'accion': 'CALL', 'fuerza': 0.75})
            
            # Gap bajista (máximo actual < mínimo anterior)
            elif curr_high < prev_low:
                resultados.append({'indice': df.index[i], 'tipo': 'gap_bajista', 'accion': 'PUT', 'fuerza': 0.75})
        except Exception:
            continue
    
    return resultados
