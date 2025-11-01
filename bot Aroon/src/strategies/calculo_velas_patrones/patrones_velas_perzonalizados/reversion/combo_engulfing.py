import pandas as pd

def detectar_combo_engulfing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta el patrón Combo Engulfing:
    - Una vela con mecha larga que indica rechazo
    - La siguiente vela es un engulfing (envolvente) en dirección opuesta

    Añade columna 'combo_engulfing' con valores:
    - 'alcista' si el patrón es alcista
    - 'bajista' si el patrón es bajista
    - None si no hay patrón

    Reglas simplificadas:
    - Vela con mecha larga: mecha (sup o inf) > 2x cuerpo
    - Engulfing: cuerpo vela 2 mayor que cuerpo vela 1 y envuelve cuerpo
    """

    df = df.copy()
    df['combo_engulfing'] = None

    for i in range(1, len(df)):
        v1 = df.iloc[i-1]
        v2 = df.iloc[i]

        cuerpo_v1 = abs(v1['close'] - v1['open'])
        mecha_sup_v1 = v1['high'] - max(v1['close'], v1['open'])
        mecha_inf_v1 = min(v1['close'], v1['open']) - v1['low']

        # Detectar mecha larga (sup o inf > 2x cuerpo)
        mecha_larga = (mecha_sup_v1 > 2 * cuerpo_v1) or (mecha_inf_v1 > 2 * cuerpo_v1)

        cuerpo_v2 = abs(v2['close'] - v2['open'])

        # Engulfing alcista
        engulfing_alcista = (
            (v1['close'] < v1['open']) and  # vela 1 bajista
            (v2['close'] > v2['open']) and  # vela 2 alcista
            (v2['open'] < v1['close']) and
            (v2['close'] > v1['open']) and
            (cuerpo_v2 > cuerpo_v1)
        )

        # Engulfing bajista
        engulfing_bajista = (
            (v1['close'] > v1['open']) and  # vela 1 alcista
            (v2['close'] < v2['open']) and  # vela 2 bajista
            (v2['open'] > v1['close']) and
            (v2['close'] < v1['open']) and
            (cuerpo_v2 > cuerpo_v1)
        )

        if mecha_larga and engulfing_alcista:
            df.at[df.index[i], 'combo_engulfing'] = 'alcista'
        elif mecha_larga and engulfing_bajista:
            df.at[df.index[i], 'combo_engulfing'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'combo_engulfing', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
