import pandas as pd

def evaluar_accion_precio(df: pd.DataFrame,
                          umbral_volatilidad_alta: float = 0.0060,
                          umbral_volatilidad_baja: float = 0.0020) -> pd.DataFrame:
    """
    Evalúa la acción del precio en base a la volatilidad de cada vela y su fuerza.
    Clasifica si el entorno es favorable para operar según criterios básicos.

    Agrega al DataFrame las columnas:
    - 'volatilidad': tamaño de la vela (high - low)
    - 'fuerza_vela': 'alta', 'media' o 'baja'
    - 'accion_precio_valida': True si se considera operable, False si no

    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close']
        umbral_volatilidad_alta (float): valor mínimo para considerar una vela fuerte
        umbral_volatilidad_baja (float): valor máximo para considerar una vela débil

    Returns:
        pd.DataFrame: mismo DataFrame con columnas adicionales
    """
    df = df.copy()

    # Cálculo de la volatilidad por vela (high - low)
    df['volatilidad'] = df['high'] - df['low']

    # Clasificación de la fuerza de la vela
    condiciones_fuerza = []
    for v in df['volatilidad']:
        if v >= umbral_volatilidad_alta:
            condiciones_fuerza.append('alta')
        elif v <= umbral_volatilidad_baja:
            condiciones_fuerza.append('baja')
        else:
            condiciones_fuerza.append('media')
    df['fuerza_vela'] = condiciones_fuerza

    # Evaluar si la vela es operable (evitar consolidaciones)
    df['accion_precio_valida'] = df['fuerza_vela'].apply(lambda f: True if f in ['media', 'alta'] else False)

    return df