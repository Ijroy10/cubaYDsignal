def evaluar_patrones(patrones, tendencia_actual, zonas_relevantes, df):
    """
    Evalúa los patrones detectados según la tendencia y zonas de soporte/resistencia.
    
    Args:
        patrones (dict): Patrones detectados por detectar_patrones_velas
        tendencia_actual (str): 'alcista' o 'bajista'
        zonas_relevantes (dict): {'soporte': [niveles], 'resistencia': [niveles]}
        df (pd.DataFrame): DataFrame original OHLC
    
    Returns:
        patrones_validados (list): Lista de patrones válidos con info de vela y tipo
    """
    patrones_validados = []

    for nombre_patron, df_patron in patrones.items():
        for index, fila in df_patron.iterrows():
            precio_cierre = fila['close']

            # Condición de coincidencia con tendencia
            if nombre_patron == 'hammer' and tendencia_actual == 'bajista':
                tendencia_ok = True
            elif nombre_patron == 'estrella_fugaz' and tendencia_actual == 'alcista':
                tendencia_ok = True
            elif nombre_patron == 'envolvente' or nombre_patron == 'doji':
                tendencia_ok = True  # Neutros, pueden servir en ambos casos
            else:
                tendencia_ok = False

            # Condición de cercanía a zonas de soporte/resistencia
            cerca_de_zona = False
            for nivel in zonas_relevantes.get('soporte', []) + zonas_relevantes.get('resistencia', []):
                if abs(precio_cierre - nivel) <= (0.5 / 100) * precio_cierre:  # ±0.5%
                    cerca_de_zona = True
                    break

            if tendencia_ok and cerca_de_zona:
                patrones_validados.append({
                    'index': index,
                    'patron': nombre_patron,
                    'precio': precio_cierre,
                    'tendencia': tendencia_actual
                })

    return patrones_validados
