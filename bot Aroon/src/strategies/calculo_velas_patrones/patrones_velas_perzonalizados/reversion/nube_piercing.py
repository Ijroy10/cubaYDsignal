import pandas as pd

def detectar_patron_nube_piercing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta los patrones de:
    - 'nube_oscura' (Dark Cloud Cover) → señal bajista
    - 'linea_penetrante' (Piercing Line) → señal alcista

    Devuelve un DataFrame con una columna nueva 'nube_piercing' que indica el patrón detectado.
    """
    df = df.copy()
    df['nube_piercing'] = None

    for i in range(1, len(df)):
        vela_1 = df.iloc[i - 1]
        vela_2 = df.iloc[i]

        # Nube Oscura (Dark Cloud Cover) - bajista
        if vela_1['close'] > vela_1['open'] and vela_2['open'] > vela_1['high'] and \
           vela_2['close'] < (vela_1['close'] + vela_1['open']) / 2 and \
           vela_2['close'] > vela_1['open']:
            df.at[i, 'nube_piercing'] = 'nube_oscura'

        # Línea Penetrante (Piercing Line) - alcista
        elif vela_1['close'] < vela_1['open'] and vela_2['open'] < vela_1['low'] and \
             vela_2['close'] > (vela_1['close'] + vela_1['open']) / 2 and \
             vela_2['close'] < vela_1['open']:
            df.at[i, 'nube_piercing'] = 'linea_penetrante'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'nube_piercing', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
