import pandas as pd

def detectar_separating_line_reversal(df: pd.DataFrame) -> list:
    """
    Detecta patrón Separating Lines (líneas de separación).
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            prev_open = df.iloc[i-1]['open']
            prev_close = df.iloc[i-1]['close']
            curr_open = df.iloc[i]['open']
            curr_close = df.iloc[i]['close']
            
            # Alcista: vela bajista seguida de alcista con mismo open
            if (prev_close < prev_open and 
                curr_close > curr_open and 
                abs(curr_open - prev_open) / prev_open < 0.002):
                resultados.append({'indice': df.index[i], 'tipo': 'separating_line_alcista', 'accion': 'CALL', 'fuerza': 0.7})
            
            # Bajista: vela alcista seguida de bajista con mismo open
            elif (prev_close > prev_open and 
                  curr_close < curr_open and 
                  abs(curr_open - prev_open) / prev_open < 0.002):
                resultados.append({'indice': df.index[i], 'tipo': 'separating_line_bajista', 'accion': 'PUT', 'fuerza': 0.7})
        except Exception:
            continue
    
    return resultados
