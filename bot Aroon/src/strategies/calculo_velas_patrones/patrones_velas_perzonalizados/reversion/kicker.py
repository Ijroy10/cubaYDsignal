import pandas as pd

def detectar_patron_kicker(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta patrones Kicker alcista y bajista.
    Agrega una nueva columna 'kicker' con valores:
    - 'alcista' para patrón Kicker alcista
    - 'bajista' para patrón Kicker bajista
    - None si no se detecta patrón
    """
    df = df.copy()
    df['kicker'] = None

    for i in range(1, len(df)):
        vela_anterior = df.iloc[i - 1]
        vela_actual = df.iloc[i]

        # Kicker alcista
        if vela_anterior['close'] < vela_anterior['open'] and \
           vela_actual['open'] > vela_anterior['open'] and \
           vela_actual['close'] > vela_actual['open']:
            df.at[i, 'kicker'] = 'alcista'

        # Kicker bajista
        elif vela_anterior['close'] > vela_anterior['open'] and \
             vela_actual['open'] < vela_anterior['open'] and \
             vela_actual['close'] < vela_actual['open']:
            df.at[i, 'kicker'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'kicker', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []