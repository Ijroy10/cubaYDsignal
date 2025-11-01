import pandas as pd

def detectar_inside_fake_breakout(df: pd.DataFrame) -> list:
    """
    Detecta inside bar con falsa ruptura.
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
            
            # Inside bar (actual dentro de anterior)
            if curr_high < prev_high and curr_low > prev_low:
                resultados.append({'indice': df.index[i], 'tipo': 'inside_bar', 'accion': 'CALL', 'fuerza': 0.6})
        except Exception:
            continue
    
    return resultados
