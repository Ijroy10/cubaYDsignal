import pandas as pd

def detectar_belt_hold(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta patrones Belt Hold alcista y bajista.
    Añade una columna 'belt_hold' con valores:
    - 'alcista' si se detecta patrón alcista
    - 'bajista' si se detecta patrón bajista
    - None si no se detecta patrón

    Características:
    - Vela con gap de apertura respecto a la anterior
    - Cuerpo largo sin o con pocas mechas (mechas pequeñas en comparación al cuerpo)
    - Para alcista: apertura > cierre anterior, cierre > apertura (vela blanca/verde)
    - Para bajista: apertura < cierre anterior, cierre < apertura (vela negra/roja)
    """

    df = df.copy()
    df['belt_hold'] = None

    for i in range(1, len(df)):
        v_ant = df.iloc[i-1]
        v_act = df.iloc[i]

        cuerpo = abs(v_act['close'] - v_act['open'])
        mecha_sup = v_act['high'] - max(v_act['close'], v_act['open'])
        mecha_inf = min(v_act['close'], v_act['open']) - v_act['low']

        mecha_total = mecha_sup + mecha_inf

        # Relación mechas-cuerpo, queremos mechas muy pequeñas (menos del 10% del cuerpo)
        mechas_pequenas = mecha_total <= 0.1 * cuerpo

        # Vela alcista Belt Hold
        es_alcista = (v_act['open'] > v_ant['close']) and (v_act['close'] > v_act['open']) and mechas_pequenas

        # Vela bajista Belt Hold
        es_bajista = (v_act['open'] < v_ant['close']) and (v_act['close'] < v_act['open']) and mechas_pequenas

        if es_alcista:
            df.at[df.index[i], 'belt_hold'] = 'alcista'
        elif es_bajista:
            df.at[df.index[i], 'belt_hold'] = 'bajista'

    # Detectar patrón
    patron_detectado = df
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'belt_hold', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
