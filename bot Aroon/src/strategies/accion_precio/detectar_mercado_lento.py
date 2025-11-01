import pandas as pd

def detectar_mercado_lento(df: pd.DataFrame, velas_consecutivas=3) -> pd.DataFrame:
    """
    Detecta si hay un mercado lento (consolidación) por baja volatilidad sostenida.
    
    Agrega columna 'mercado_lento' con valores:
        - True  → hay al menos X velas consecutivas con baja volatilidad
        - False → no hay suficiente evidencia de consolidación

    Args:
        df (pd.DataFrame): DataFrame con columna 'volatilidad' previamente generada
        velas_consecutivas (int): cuántas velas consecutivas 'bajas' indican consolidación

    Returns:
        pd.DataFrame: DataFrame con columna adicional 'mercado_lento'
    """
    df = df.copy()
    df['mercado_lento'] = False

    conteo = 0
    for i in range(len(df)):
        if df.loc[i, 'volatilidad'] == 'baja':
            conteo += 1
        else:
            conteo = 0

        if conteo >= velas_consecutivas:
            df.loc[i, 'mercado_lento'] = True

    return df
