import pandas as pd

def detectar_downside_gap_three_methods(df: pd.DataFrame) -> list:
    """
    Detecta el patrón Downside Gap Three Methods en velas japonesas.
    """
    if len(df) < 3:
        return []
    
    open_1 = df['open'].shift(2)
    close_1 = df['close'].shift(2)
    open_2 = df['open'].shift(1)
    close_2 = df['close'].shift(1)
    open_3 = df['open']
    close_3 = df['close']

    bajista_1 = close_1 < open_1
    bajista_2 = close_2 < open_2
    alcista_3 = close_3 > open_3

    gap_bajista = (open_2 < close_1) & (close_2 < close_1)
    tercera_dentro_del_segundo = (open_3 > close_2) & (close_3 < open_2)

    # Detectar patrón
    patron_detectado = bajista_1 & bajista_2 & alcista_3 & gap_bajista & tercera_dentro_del_segundo
    
    # Convertir a lista
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'downside_gap_three_methods', 'accion': 'PUT', 'fuerza': 0.75} for idx in indices_detectados]
    return []
