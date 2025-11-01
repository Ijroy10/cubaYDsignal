from datetime import datetime, timedelta

def evaluar_fuerza_zonas(df, zonas, tipo='soporte', umbral_distancia=0.002, dias_vigencia=7):
    """
    Evalúa la fuerza de las zonas de soporte o resistencia.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas ['time', 'open', 'high', 'low', 'close'].
        zonas (list): lista de tuplas (timestamp, precio) de soportes o resistencias detectadas.
        tipo (str): 'soporte' o 'resistencia'.
        umbral_distancia (float): distancia relativa (por ejemplo 0.002 = 0.2%) para considerar un toque cercano.
        dias_vigencia (int): número de días atrás para considerar reciente un toque.
    
    Returns:
        lista de dicts con información de cada zona:
        {
            'precio_zona': float,
            'toques': int,
            'ultimo_toque': datetime,
            'fuerza': str ('alta', 'media', 'baja')
        }
    """
    resultados = []
    
    for _, precio_zona in zonas:
        toques = 0
        ultimo_toque = None
        
        for idx, row in df.iterrows():
            # Precio relevante según tipo
            precio_eval = row['low'] if tipo == 'soporte' else row['high']
            
            # Comprobar si precio está dentro del umbral de la zona
            if abs(precio_eval - precio_zona) / precio_zona <= umbral_distancia:
                toques += 1
                tiempo_toque = row['time']
                if (ultimo_toque is None) or (tiempo_toque > ultimo_toque):
                    ultimo_toque = tiempo_toque
        
        # Evaluar fuerza según toques y antigüedad
        fuerza = 'baja'
        if toques >= 3 and ultimo_toque is not None:
            dias_desde_ultimo = (df['time'].max() - ultimo_toque).days
            if dias_desde_ultimo <= dias_vigencia:
                fuerza = 'alta'
            else:
                fuerza = 'media'
        elif toques == 2:
            fuerza = 'media'
        
        resultados.append({
            'precio_zona': precio_zona,
            'toques': toques,
            'ultimo_toque': ultimo_toque,
            'fuerza': fuerza
        })
    
    return resultados
