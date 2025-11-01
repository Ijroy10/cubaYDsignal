import pandas as pd

def detectar_outside_close(df: pd.DataFrame) -> list:
    """
    Detecta outside bars (vela envolvente).
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
            
            # Outside bar alcista
            if curr_high > prev_high and curr_low < prev_low and curr_close > curr_open:
                resultados.append({'indice': df.index[i], 'tipo': 'outside_alcista', 'accion': 'CALL', 'fuerza': 0.75})
            
            # Outside bar bajista
            elif curr_high > prev_high and curr_low < prev_low and curr_close < curr_open:
                resultados.append({'indice': df.index[i], 'tipo': 'outside_bajista', 'accion': 'PUT', 'fuerza': 0.75})
        except Exception:
            continue
    
    return resultados
