import pandas as pd

def detectar_zonas_rebote(df, tipo='soporte', umbral_distancia=0.002, min_rebotes=2):
    """
    Detecta zonas de soporte o resistencia según rebotes de precio.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas ['time', 'open', 'high', 'low', 'close'].
        tipo (str): 'soporte' o 'resistencia'.
        umbral_distancia (float): distancia relativa para considerar que el precio tocó la zona.
        min_rebotes (int): mínimo número de rebotes para considerar zona válida.
    
    Returns:
        lista de tuplas (timestamp, precio_zona) con las zonas detectadas.
    """
    # Elegir la serie relevante para detectar rebotes
    precios = df['low'] if tipo == 'soporte' else df['high']
    
    zonas_candidatas = []
    
    # Buscamos niveles donde el precio rebota (mínimos locales para soportes, máximos locales para resistencias)
    for i in range(1, len(precios) - 1):
        actual = precios.iloc[i]
        prev_ = precios.iloc[i - 1]
        next_ = precios.iloc[i + 1]
        
        if tipo == 'soporte':
            # Mínimo local
            if actual < prev_ and actual < next_:
                zonas_candidatas.append((df['time'].iloc[i], actual))
        else:
            # Resistencia = máximo local
            if actual > prev_ and actual > next_:
                zonas_candidatas.append((df['time'].iloc[i], actual))
    
    # Agrupar zonas cercanas entre sí para no duplicar
    zonas_agregadas = []
    
    for tiempo, precio in zonas_candidatas:
        # Buscar si precio está cercano a alguna zona ya agregada
        agregado = False
        for idx, (t_exist, p_exist) in enumerate(zonas_agregadas):
            if abs(precio - p_exist) / p_exist <= umbral_distancia:
                # Promediar para ajustar zona
                nuevo_precio = (precio + p_exist) / 2
                zonas_agregadas[idx] = (t_exist, nuevo_precio)
                agregado = True
                break
        if not agregado:
            zonas_agregadas.append((tiempo, precio))
    
    # Filtrar zonas con suficientes rebotes
    zonas_validas = []
    for tiempo, precio in zonas_agregadas:
        toques = 0
        for i in range(len(precios)):
            if abs(precios.iloc[i] - precio) / precio <= umbral_distancia:
                toques += 1
        if toques >= min_rebotes:
            zonas_validas.append((tiempo, precio))
    
    return zonas_validas
