import pandas as pd

def detectar_envolventes(df):
    """
    Detecta patrones de envolvente alcista y bajista en un DataFrame de velas OHLC.
    Retorna una lista de señales con la posición y el tipo de patrón.
    """
    señales = []

    for i in range(1, len(df)):
        vela_anterior = df.iloc[i - 1]
        vela_actual = df.iloc[i]

        # Envolvente Alcista: cuerpo actual verde envuelve completamente el rojo anterior
        if (
            vela_anterior['close'] < vela_anterior['open'] and  # vela anterior bajista
            vela_actual['close'] > vela_actual['open'] and      # vela actual alcista
            vela_actual['open'] < vela_anterior['close'] and
            vela_actual['close'] > vela_anterior['open']
        ):
            señales.append({
                'indice': i,
                'tipo': 'envolvente_alcista',
                'accion': 'CALL'
            })

        # Envolvente Bajista: cuerpo actual rojo envuelve completamente el verde anterior
        elif (
            vela_anterior['close'] > vela_anterior['open'] and  # vela anterior alcista
            vela_actual['close'] < vela_actual['open'] and      # vela actual bajista
            vela_actual['open'] > vela_anterior['close'] and
            vela_actual['close'] < vela_anterior['open']
        ):
            señales.append({
                'indice': i,
                'tipo': 'envolvente_bajista',
                'accion': 'SELL'
            })

    # Detectar patrón
    patron_detectado = señales
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'envolventes', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
