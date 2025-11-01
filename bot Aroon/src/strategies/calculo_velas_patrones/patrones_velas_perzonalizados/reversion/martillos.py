import pandas as pd

def detectar_martillos(df: pd.DataFrame) -> list:
    """
    Detecta patrones Martillo (Hammer) y Hombre Colgado (Hanging Man).
    """
    if len(df) < 1:
        return []
    
    resultados = []
    for i in range(len(df)):
        try:
            cuerpo = abs(df.iloc[i]['close'] - df.iloc[i]['open'])
            mecha_superior = df.iloc[i]['high'] - max(df.iloc[i]['close'], df.iloc[i]['open'])
            mecha_inferior = min(df.iloc[i]['close'], df.iloc[i]['open']) - df.iloc[i]['low']

            # Condiciones del martillo/hombre colgado
            if cuerpo > 0 and mecha_inferior > 2 * cuerpo and mecha_superior < cuerpo * 0.3:
                if df.iloc[i]['close'] > df.iloc[i]['open']:
                    resultados.append({'indice': df.index[i], 'tipo': 'martillo', 'accion': 'CALL', 'fuerza': 0.75})
                else:
                    resultados.append({'indice': df.index[i], 'tipo': 'hombre_colgado', 'accion': 'PUT', 'fuerza': 0.75})
        except Exception:
            continue
    
    return resultados
