import pandas as pd

def evaluar_pullback_confirmado(df: pd.DataFrame) -> pd.DataFrame:
    """
    Marca si un pullback fue confirmado según la vela siguiente (patrón fuerte o rebote).

    Requiere columnas:
    - 'posible_pullback' (bool)
    - 'patron_confirmacion' (str), que puede venir de la detección de patrones.

    Agrega columna:
    - 'pullback_confirmado' (bool)

    Args:
        df (pd.DataFrame): DataFrame con los datos de velas y columnas necesarias.

    Returns:
        pd.DataFrame: DataFrame con columna 'pullback_confirmado' añadida.
    """
    df = df.copy()

    # Verificación de columnas necesarias
    required_cols = ['posible_pullback', 'patron_confirmacion']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Falta la columna requerida: '{col}'")

    # Inicializa la columna de resultado
    df['pullback_confirmado'] = False

    # Evaluación del pullback
    for i in range(1, len(df)):
        anterior_es_pullback = df.loc[i - 1, 'posible_pullback']
        confirmacion = df.loc[i, 'patron_confirmacion']

        patrones_validos = [
            'envolvente_alcista', 'envolvente_bajista',
            'martillo', 'estrella_fugaz',
            'pinbar', 'doji_confirmado'  # puedes agregar más
        ]

        if anterior_es_pullback and confirmacion in patrones_validos:
            df.loc[i, 'pullback_confirmado'] = True

    return df
