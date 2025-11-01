def clasificar_senal(patrones_validados):
    """
    Clasifica los patrones en CALL o SELL según su tipo.

    Parámetros:
        patrones_validados (list): Lista de patrones confirmados (tuplas con nombre, índice, zona, tendencia)

    Retorna:
        list: Lista de dicts con patrón, tipo de señal y detalles.
    """
    senales = []

    for patron, indice, zona, tendencia in patrones_validados:
        patron = patron.lower()
        zona = zona.lower()

        if patron in ['hammer', 'morningstar', 'engulfingbull'] and zona == 'soporte' and tendencia == 'alcista':
            senales.append({
                "indice": indice,
                "tipo": "CALL",
                "patron": patron,
                "zona": zona,
                "tendencia": tendencia
            })
        elif patron in ['shootingstar', 'eveningstar', 'engulfingbear'] and zona == 'resistencia' and tendencia == 'bajista':
            senales.append({
                "indice": indice,
                "tipo": "SELL",
                "patron": patron,
                "zona": zona,
                "tendencia": tendencia
            })
        # Puedes seguir agregando más lógica para otros patrones aquí...

    return senales