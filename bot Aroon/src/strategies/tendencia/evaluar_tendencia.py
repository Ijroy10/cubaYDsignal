def evaluar_tendencia(df):
    resultado = evaluar_tendencia(df)

    # Suponiendo que resultado tiene valores numéricos o strings que podemos interpretar
    principal = resultado['tendencia_principal']  # Ejemplo: 'alcista' o 'bajista' o % fuerza
    secundaria = resultado['tendencia_secundaria']
    fuerza = resultado['fuerza_tendencia']  # Ejemplo: porcentaje 0-100

    # Aquí lógica para decidir porcentaje y dirección
    # Ejemplo básico:

    votos_alcista = sum(1 for x in [principal, secundaria] if x == 'alcista')
    votos_bajista = sum(1 for x in [principal, secundaria] if x == 'bajista')

    if votos_alcista > votos_bajista and fuerza > 60:
        return {'efectividad': fuerza, 'direccion': 'CALL'}
    elif votos_bajista > votos_alcista and fuerza > 60:
        return {'efectividad': fuerza, 'direccion': 'SELL'}
    else:
        return {'efectividad': 0, 'direccion': None}
