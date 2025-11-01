import pandas as pd

def detectar_doji_confirmacion(df: pd.DataFrame) -> list:
    """
    Detecta Doji con confirmación (siguiente vela confirma dirección).
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            # Vela anterior (posible doji)
            prev_open = df.iloc[i-1]['open']
            prev_close = df.iloc[i-1]['close']
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            prev_cuerpo = abs(prev_close - prev_open)
            prev_rango = prev_high - prev_low
            
            # Vela actual (confirmación)
            curr_open = df.iloc[i]['open']
            curr_close = df.iloc[i]['close']
            curr_cuerpo = abs(curr_close - curr_open)
            
            # Es doji si cuerpo < 10% del rango
            if prev_rango > 0 and prev_cuerpo / prev_rango < 0.1:
                # Confirmación alcista
                if curr_close > curr_open and curr_cuerpo > prev_cuerpo * 2:
                    resultados.append({'indice': df.index[i], 'tipo': 'doji_confirmacion_alcista', 'accion': 'CALL', 'fuerza': 0.75})
                # Confirmación bajista
                elif curr_close < curr_open and curr_cuerpo > prev_cuerpo * 2:
                    resultados.append({'indice': df.index[i], 'tipo': 'doji_confirmacion_bajista', 'accion': 'PUT', 'fuerza': 0.75})
        except Exception:
            continue
    
    return resultados
