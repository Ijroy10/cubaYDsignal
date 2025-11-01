import pandas as pd

def detectar_tweezer(df: pd.DataFrame) -> list:
    """
    Detecta patrones Tweezer Top y Tweezer Bottom.
    """
    if len(df) < 2:
        return []
    
    resultados = []
    tolerancia = 0.001  # 0.1% de tolerancia
    
    for i in range(1, len(df)):
        try:
            high_prev = df.iloc[i-1]['high']
            high_curr = df.iloc[i]['high']
            low_prev = df.iloc[i-1]['low']
            low_curr = df.iloc[i]['low']
            
            # Tweezer Top (bajista) - máximos similares
            if abs(high_prev - high_curr) / high_prev < tolerancia:
                resultados.append({'indice': df.index[i], 'tipo': 'tweezer_top', 'accion': 'PUT', 'fuerza': 0.7})
            
            # Tweezer Bottom (alcista) - mínimos similares
            elif abs(low_prev - low_curr) / low_prev < tolerancia:
                resultados.append({'indice': df.index[i], 'tipo': 'tweezer_bottom', 'accion': 'CALL', 'fuerza': 0.7})
        except Exception:
            continue
    
    return resultados
