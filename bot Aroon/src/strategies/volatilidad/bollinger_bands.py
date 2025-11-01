import pandas as pd

def calcular_bollinger_bands(df, periodo=20, num_std=2):
    """
    Calcula las Bandas de Bollinger.
    
    Parámetros:
    - df: DataFrame con columna 'close'
    - periodo: Periodo para la media móvil (por defecto 20)
    - num_std: Número de desviaciones estándar para las bandas (por defecto 2)

    Retorna:
    - DataFrame con columnas: ['bollinger_mid', 'bollinger_upper', 'bollinger_lower']
    """
    df = df.copy()
    df['bollinger_mid'] = df['close'].rolling(window=periodo).mean()
    df['bollinger_std'] = df['close'].rolling(window=periodo).std()

    df['bollinger_upper'] = df['bollinger_mid'] + (num_std * df['bollinger_std'])
    df['bollinger_lower'] = df['bollinger_mid'] - (num_std * df['bollinger_std'])

    return df[['bollinger_mid', 'bollinger_upper', 'bollinger_lower']]