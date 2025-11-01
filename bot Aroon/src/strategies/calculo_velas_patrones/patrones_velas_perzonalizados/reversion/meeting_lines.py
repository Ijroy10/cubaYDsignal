import pandas as pd

def detectar_patron_meeting_lines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta el patrón de velas Meeting Lines (líneas que se encuentran).
    Agrega una columna 'meeting_lines' con:
    - 'alcista' si hay Meeting Line alcista (tras tendencia bajista)
    - 'bajista' si hay Meeting Line bajista (tras tendencia alcista)
    - None si no se detecta patrón
    """
    df = df.copy()
    df['meeting_lines'] = None

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        # Alcista: vela roja seguida de vela verde que abre con gap abajo pero cierra igual que la anterior
        if prev['close'] < prev['open'] and curr['close'] > curr['open'] and \
           abs(curr['close'] - prev['close']) < 0.0001:  # cierre igual o muy cercano
            df.at[i, 'meeting_lines'] = 'alcista'

        # Bajista: vela verde seguida de vela roja que abre con gap arriba pero cierra igual que la anterior
        elif prev['close'] > prev['open'] and curr['close'] < curr['open'] and \
             abs(curr['close'] - prev['close']) < 0.0001:
            df.at[i, 'meeting_lines'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'meeting_lines', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
