import pandas as pd

def detectar_engaño_volumen(df: pd.DataFrame) -> list:
    """
    Detecta engaños de volumen (requiere columna 'volume').
    Si no hay volumen, retorna lista vacía.
    """
    if len(df) < 2:
        return []
    
    # Verificar si existe columna de volumen
    if 'volume' not in df.columns:
        return []  # Sin volumen, no se puede detectar
    
    # Lógica de detección con volumen
    cuerpo = abs(df['close'] - df['open'])
    volumen_alto = df['volume'] > df['volume'].rolling(window=20).mean() * 1.5
    cuerpo_pequeño = cuerpo < cuerpo.rolling(window=20).mean() * 0.5
    
    # Patrón: volumen alto pero cuerpo pequeño (posible engaño)
    patron_detectado = volumen_alto & cuerpo_pequeño
    
    # Convertir a lista
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'engaño_volumen', 'accion': 'CALL', 'fuerza': 0.65} for idx in indices_detectados]
    return []
