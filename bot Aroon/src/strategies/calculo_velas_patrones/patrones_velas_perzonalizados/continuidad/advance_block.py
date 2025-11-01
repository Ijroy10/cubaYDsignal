import pandas as pd

def detectar_advance_block(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón Advance Block en un DataFrame de velas japonesas.

    Condiciones del patrón:
    - Tres velas consecutivas alcistas
    - Cada vela cierra más alto que la anterior
    - El cuerpo real se va acortando progresivamente
    - Las sombras superiores se alargan

    Retorna una Serie booleana: True donde se detecta el patrón.
    """
    cuerpo = abs(df['close'] - df['open'])
    sombra_superior = df[['close', 'open']].max(axis=1) - df['high']

    # Condiciones para las tres velas consecutivas
    cond1 = df['close'].shift(2) > df['open'].shift(2)
    cond2 = df['close'].shift(1) > df['open'].shift(1)
    cond3 = df['close'] > df['open']

    # Cierres ascendentes
    cond4 = df['close'].shift(2) < df['close'].shift(1)
    cond5 = df['close'].shift(1) < df['close']

    # Cuerpos decrecientes
    cond6 = cuerpo.shift(2) > cuerpo.shift(1)
    cond7 = cuerpo.shift(1) > cuerpo

    # Sombras superiores alargadas
    cond8 = sombra_superior.shift(2) < sombra_superior.shift(1)
    cond9 = sombra_superior.shift(1) < sombra_superior

    # Detectar patrón
    patron_detectado = cond1 & cond2 & cond3 & cond4 & cond5 & cond6 & cond7 & cond8 & cond9
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            # Retornar lista de señales
            return [{'indice': idx, 'tipo': 'advance_block', 'fuerza': 0.8} for idx in indices_detectados]
    return []
