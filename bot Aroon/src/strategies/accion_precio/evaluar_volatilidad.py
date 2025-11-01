import pandas as pd

def evaluar_volatilidad(df: pd.DataFrame, umbral_bajo=0.002, umbral_alto=0.006) -> pd.DataFrame:
    """
    Evalúa la volatilidad de cada vela según su tamaño (alto - bajo).
    
    Agrega una columna 'volatilidad' con valores:
        - 'baja'      → vela muy pequeña
        - 'saludable' → vela de tamaño medio
        - 'alta'      → vela grande o impulsiva

    Args:
        df (pd.DataFrame): DataFrame con columnas ['open', 'high', 'low', 'close']
        umbral_bajo (float): diferencia mínima para considerar baja volatilidad (por ejemplo, 0.002)
        umbral_alto (float): diferencia mínima para considerar alta volatilidad (por ejemplo, 0.006)

    Returns:
        pd.DataFrame: DataFrame con columna adicional 'volatilidad'
    """
    df = df.copy()
    df['rango'] = df['high'] - df['low']

    def clasificar_volatilidad(rango):
        if rango < umbral_bajo:
            return 'baja'
        elif rango > umbral_alto:
            return 'alta'
        else:
            return 'saludable'

    df['volatilidad'] = df['rango'].apply(clasificar_volatilidad)
    return df
