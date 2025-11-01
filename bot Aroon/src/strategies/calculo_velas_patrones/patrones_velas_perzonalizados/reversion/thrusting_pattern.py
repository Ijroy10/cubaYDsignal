import pandas as pd

def detectar_thrusting_pattern(df: pd.DataFrame) -> list:
    """
    Detecta patrón Thrusting (empuje).
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
            
            # Thrusting bajista
            if (prev_close < prev_open and  # Primera bajista
                curr_close > curr_open and  # Segunda alcista
                curr_open < prev_close and  # Abre abajo
                curr_close < (prev_open + prev_close) / 2):  # Cierra en mitad inferior
                resultados.append({'indice': df.index[i], 'tipo': 'thrusting_bajista', 'accion': 'PUT', 'fuerza': 0.65})
        except Exception:
            continue
    
    return resultados
