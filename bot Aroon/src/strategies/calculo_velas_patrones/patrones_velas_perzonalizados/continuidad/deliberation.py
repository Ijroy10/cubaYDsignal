import pandas as pd

def detectar_deliberation(df: pd.DataFrame) -> pd.Series:
    """
    Detecta el patrón Deliberation (Deliberación) en el gráfico de velas.

    Características del patrón:
    - Tres velas alcistas consecutivas
    - Las dos primeras tienen cuerpos reales largos
    - La tercera es una vela pequeña que muestra indecisión o agotamiento (tipo doji o cuerpo corto)
    - La tercera vela abre con gap alcista y cierra más arriba que la segunda

    Retorna una Serie booleana con True donde se detecta el patrón.
    """
    cuerpo = abs(df['close'] - df['open'])
    cuerpo_anterior_1 = cuerpo.shift(1)
    cuerpo_anterior_2 = cuerpo.shift(2)

    # Condición de velas alcistas
    alcista_1 = df['close'].shift(2) > df['open'].shift(2)
    alcista_2 = df['close'].shift(1) > df['open'].shift(1)
    alcista_3 = df['close'] > df['open']

    # Las dos primeras con cuerpo largo
    cuerpo_largo_1 = cuerpo_anterior_2 > cuerpo_anterior_2.rolling(window=20).mean()
    cuerpo_largo_2 = cuerpo_anterior_1 > cuerpo_anterior_1.rolling(window=20).mean()

    # La tercera con cuerpo corto
    cuerpo_corto_3 = cuerpo < cuerpo.rolling(window=20).mean() * 0.7

    # La tercera abre con gap y cierra más arriba
    gap_entre_2y3 = df['open'] > df['close'].shift(1)
    cierre_mayor_que_anterior = df['close'] > df['close'].shift(1)

    # Detectar patrón
    patron_detectado = (
        alcista_1 & alcista_2 & alcista_3 &
        cuerpo_largo_1 & cuerpo_largo_2 &
        cuerpo_corto_3 &
        gap_entre_2y3 & cierre_mayor_que_anterior
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'deliberation', 'accion': 'CALL', 'fuerza': 0.75} for idx in indices_detectados]
    return []
