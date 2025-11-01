import pandas as pd

def filtrar_operaciones_por_accion_precio(df: pd.DataFrame, umbral_volatilidad=0.0005, umbral_fuerza=1.5) -> pd.DataFrame:
    """
    Filtra operaciones según la acción del precio, combinando:
    - Volatilidad (rango de la vela)
    - Fuerza (cuerpo dominante)

    Agrega columna 'accion_precio_valida':
        - True si hay buena volatilidad + vela fuerte
        - False si el mercado está lento o sin fuerza

    Args:
        df (pd.DataFrame): DataFrame con ['open', 'high', 'low', 'close']
        umbral_volatilidad (float): Valor mínimo de rango (high - low) para considerar buena volatilidad
        umbral_fuerza (float): Ratio mínimo cuerpo/rango para que la vela sea fuerte

    Returns:
        pd.DataFrame: Con columna 'accion_precio_valida'
    """
    df = df.copy()
    df['accion_precio_valida'] = False

    for i in range(len(df)):
        open_ = df.loc[i, 'open']
        close = df.loc[i, 'close']
        high = df.loc[i, 'high']
        low = df.loc[i, 'low']

        cuerpo = abs(close - open_)
        rango = high - low if high - low != 0 else 0.0001
        ratio_fuerza = cuerpo / rango

        # Condiciones: buena volatilidad y fuerza en la vela
        if rango >= umbral_volatilidad and ratio_fuerza >= umbral_fuerza:
            df.loc[i, 'accion_precio_valida'] = True

    return df