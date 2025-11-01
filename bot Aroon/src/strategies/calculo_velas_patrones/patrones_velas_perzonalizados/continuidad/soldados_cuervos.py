import pandas as pd

def detectar_soldados_cuervos(df: pd.DataFrame) -> list:
    """
    Detecta patrones de Tres Soldados Blancos (alcista) y Tres Cuervos Negros (bajista).
    """
    if len(df) < 3:
        return []
    
    o = df['open']
    c = df['close']
    h = df['high']
    l = df['low']
    
    # Tres Soldados Blancos (alcista)
    soldados = (
        (c.shift(2) > o.shift(2)) &
        (c.shift(1) > o.shift(1)) &
        (c > o) &
        (c.shift(1) > c.shift(2)) &
        (c > c.shift(1))
    )
    
    # Tres Cuervos Negros (bajista)
    cuervos = (
        (c.shift(2) < o.shift(2)) &
        (c.shift(1) < o.shift(1)) &
        (c < o) &
        (c.shift(1) < c.shift(2)) &
        (c < c.shift(1))
    )
    
    # Combinar ambos patrones
    patron_detectado = soldados | cuervos
    
    # Convertir a lista
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            resultados = []
            for idx in indices_detectados:
                # Usar .loc en lugar de .iloc para acceder por índice
                if soldados.loc[idx]:
                    resultados.append({'indice': idx, 'tipo': 'tres_soldados_blancos', 'accion': 'CALL', 'fuerza': 0.8})
                else:
                    resultados.append({'indice': idx, 'tipo': 'tres_cuervos_negros', 'accion': 'PUT', 'fuerza': 0.8})
            return resultados
    return []
