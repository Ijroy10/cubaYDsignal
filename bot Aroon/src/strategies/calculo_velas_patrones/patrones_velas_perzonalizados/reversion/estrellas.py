import pandas as pd

def detectar_estrellas(df: pd.DataFrame) -> list:
    """
    Detecta patrones Estrella de la Mañana y Estrella de la Tarde.
    """
    if len(df) < 3:
        return []
    
    resultados = []
    for i in range(2, len(df)):
        try:
            # Velas
            v1_open, v1_close = df.iloc[i-2]['open'], df.iloc[i-2]['close']
            v2_open, v2_close = df.iloc[i-1]['open'], df.iloc[i-1]['close']
            v3_open, v3_close = df.iloc[i]['open'], df.iloc[i]['close']
            
            cuerpo1 = abs(v1_close - v1_open)
            cuerpo2 = abs(v2_close - v2_open)
            cuerpo3 = abs(v3_close - v3_open)
            
            # Estrella de la Mañana (alcista)
            if (v1_close < v1_open and  # Primera bajista
                cuerpo2 < cuerpo1 * 0.3 and  # Segunda pequeña
                v3_close > v3_open and  # Tercera alcista
                v3_close > (v1_open + v1_close) / 2):  # Cierra en mitad superior
                resultados.append({'indice': df.index[i], 'tipo': 'estrella_mañana', 'accion': 'CALL', 'fuerza': 0.8})
            
            # Estrella de la Tarde (bajista)
            elif (v1_close > v1_open and  # Primera alcista
                  cuerpo2 < cuerpo1 * 0.3 and  # Segunda pequeña
                  v3_close < v3_open and  # Tercera bajista
                  v3_close < (v1_open + v1_close) / 2):  # Cierra en mitad inferior
                resultados.append({'indice': df.index[i], 'tipo': 'estrella_tarde', 'accion': 'PUT', 'fuerza': 0.8})
        except Exception:
            continue
    
    return resultados
