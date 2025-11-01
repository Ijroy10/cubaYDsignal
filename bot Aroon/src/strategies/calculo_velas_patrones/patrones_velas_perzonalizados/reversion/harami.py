import pandas as pd

def detectar_patron_harami(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta patrones Harami Alcista y Harami Bajista.
    Agrega una columna 'harami' con los valores:
    - 'alcista' para Harami Alcista
    - 'bajista' para Harami Bajista
    - None si no se detecta ningún patrón
    """
    df = df.copy()
    df['harami'] = None

    for i in range(1, len(df)):
        open_anterior = df.loc[i - 1, 'open']
        close_anterior = df.loc[i - 1, 'close']
        open_actual = df.loc[i, 'open']
        close_actual = df.loc[i, 'close']

        cuerpo_anterior = [min(open_anterior, close_anterior), max(open_anterior, close_anterior)]
        cuerpo_actual = [min(open_actual, close_actual), max(open_actual, close_actual)]

        # Harami Alcista: vela roja grande seguida por vela verde pequeña dentro del cuerpo anterior
        if close_anterior < open_anterior and close_actual > open_actual:
            if cuerpo_actual[0] > cuerpo_anterior[0] and cuerpo_actual[1] < cuerpo_anterior[1]:
                df.loc[i, 'harami'] = 'alcista'

        # Harami Bajista: vela verde grande seguida por vela roja pequeña dentro del cuerpo anterior
        elif close_anterior > open_anterior and close_actual < open_actual:
            if cuerpo_actual[0] > cuerpo_anterior[0] and cuerpo_actual[1] < cuerpo_anterior[1]:
                df.loc[i, 'harami'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'harami', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
