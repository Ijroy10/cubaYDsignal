import pandas as pd

def detectar_concealing_baby_swallow(df):
    """
    Detecta el patrón Concealing Baby Swallow.
    Es un patrón de reversión alcista raro que aparece en tendencias bajistas.
    
    Requiere al menos 4 velas consecutivas:
    - Las 2 primeras son marubozus bajistas.
    - La tercera tiene una pequeña sombra superior y es engullida por la cuarta.
    - La cuarta vela es bajista y engulle completamente a la tercera.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close'].

    Returns:
        señales (list): Lista de tuplas (índice_última_vela, tipo='CALL').
    """
    señales = []

    for i in range(3, len(df)):
        v1 = df.iloc[i - 3]
        v2 = df.iloc[i - 2]
        v3 = df.iloc[i - 1]
        v4 = df.iloc[i]

        # Primeras dos velas: marubozus bajistas
        cond1 = v1['open'] > v1['close'] and (v1['high'] - v1['open']) < 0.002
        cond2 = v2['open'] > v2['close'] and (v2['high'] - v2['open']) < 0.002

        # Tercera vela: pequeña sombra superior
        sombra_sup_3 = v3['high'] - max(v3['open'], v3['close'])
        cuerpo_3 = abs(v3['close'] - v3['open'])
        cond3 = sombra_sup_3 <= cuerpo_3 * 0.3

        # Cuarta vela: bajista y engulle completamente a la tercera
        cond4 = v4['open'] > v4['close'] and v4['open'] >= max(v3['open'], v3['close']) and v4['close'] <= min(v3['open'], v3['close'])

        if cond1 and cond2 and cond3 and cond4:
            señales.append((i, 'CALL'))  # Señal de reversión alcista

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'cocealing_baby_swallow', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
