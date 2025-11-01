"""
ANÁLISIS DE FIGURAS CHARTISTAS (PATRONES DE REVERSIÓN)

Detecta patrones de cambio de tendencia:
- Doble Techo
- Doble Suelo
- Triple Techo
- Triple Suelo
- Hombro Cabeza Hombro (HCH)
- Hombro Cabeza Hombro Invertido (HCHi)

IMPORTANTE:
- Son figuras de REVERSIÓN (cambio de tendencia)
- Deben darse al FINAL de una tendencia
- Doble Techo: Final de tendencia alcista → Reversión bajista
- Doble Suelo: Final de tendencia bajista → Reversión alcista
- Se confirman al romper el "cuello" (zona de soporte/resistencia)
- Usar como CONFIRMACIÓN adicional, no como única señal
- Aumentan la efectividad cuando se combinan con S/R y tendencia
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def detectar_doble_techo(df: pd.DataFrame, tolerancia: float = 0.01) -> Dict:
    """
    Detecta patrón de Doble Techo
    
    CARACTERÍSTICAS:
    - Dos máximos al mismo nivel (±tolerancia)
    - Comparten un solo mínimo (el "cuello")
    - Se confirma al romper el cuello (soporte)
    - Indica reversión de tendencia alcista a bajista
    
    Args:
        df: DataFrame con OHLC
        tolerancia: Tolerancia para considerar máximos al mismo nivel (1% default)
    
    Returns:
        dict: Información del patrón detectado
    """
    if len(df) < 20:
        return {'detectado': False, 'patron': 'doble_techo'}
    
    # Buscar máximos locales
    maximos = []
    for i in range(5, len(df) - 5):
        ventana = df.iloc[i-5:i+6]
        if df.iloc[i]['high'] == ventana['high'].max():
            maximos.append({
                'indice': i,
                'precio': df.iloc[i]['high']
            })
    
    if len(maximos) < 2:
        return {'detectado': False, 'patron': 'doble_techo'}
    
    # Buscar pares de máximos al mismo nivel
    for i in range(len(maximos) - 1):
        max1 = maximos[i]
        
        for j in range(i + 1, len(maximos)):
            max2 = maximos[j]
            
            # Verificar que estén al mismo nivel (±tolerancia)
            diff_precio = abs(max1['precio'] - max2['precio']) / max1['precio']
            
            if diff_precio <= tolerancia:
                # Buscar el mínimo entre los dos máximos (el cuello)
                rango_entre = df.iloc[max1['indice']:max2['indice']+1]
                precio_cuello = rango_entre['low'].min()
                indice_cuello_relativo = rango_entre['low'].idxmin()
                indice_cuello = max1['indice'] + (indice_cuello_relativo - max1['indice'])
                
                # Verificar si el cuello ha sido roto
                precio_actual = df.iloc[-1]['close']
                cuello_roto = precio_actual < precio_cuello
                
                # Calcular distancia entre máximos
                distancia_velas = max2['indice'] - max1['indice']
                
                return {
                    'detectado': True,
                    'patron': 'doble_techo',
                    'tipo_reversion': 'bajista',
                    'maximo1': {'indice': max1['indice'], 'precio': round(max1['precio'], 5)},
                    'maximo2': {'indice': max2['indice'], 'precio': round(max2['precio'], 5)},
                    'cuello': {'indice': indice_cuello, 'precio': round(precio_cuello, 5)},
                    'cuello_roto': cuello_roto,
                    'confirmado': cuello_roto,
                    'distancia_velas': distancia_velas,
                    'efectividad_patron': 80 if cuello_roto else 60,
                    'descripcion': 'Doble Techo: Reversión de alcista a bajista',
                    'requiere_tendencia': 'alcista'
                }
    
    return {'detectado': False, 'patron': 'doble_techo'}


def detectar_doble_suelo(df: pd.DataFrame, tolerancia: float = 0.01) -> Dict:
    """
    Detecta patrón de Doble Suelo
    
    CARACTERÍSTICAS:
    - Dos mínimos al mismo nivel (±tolerancia)
    - Comparten un solo máximo (el "cuello")
    - Se confirma al romper el cuello (resistencia)
    - Indica reversión de tendencia bajista a alcista
    """
    if len(df) < 20:
        return {'detectado': False, 'patron': 'doble_suelo'}
    
    # Buscar mínimos locales
    minimos = []
    for i in range(5, len(df) - 5):
        ventana = df.iloc[i-5:i+6]
        if df.iloc[i]['low'] == ventana['low'].min():
            minimos.append({
                'indice': i,
                'precio': df.iloc[i]['low']
            })
    
    if len(minimos) < 2:
        return {'detectado': False, 'patron': 'doble_suelo'}
    
    # Buscar pares de mínimos al mismo nivel
    for i in range(len(minimos) - 1):
        min1 = minimos[i]
        
        for j in range(i + 1, len(minimos)):
            min2 = minimos[j]
            
            diff_precio = abs(min1['precio'] - min2['precio']) / min1['precio']
            
            if diff_precio <= tolerancia:
                # Buscar el máximo entre los dos mínimos (el cuello)
                rango_entre = df.iloc[min1['indice']:min2['indice']+1]
                precio_cuello = rango_entre['high'].max()
                indice_cuello_relativo = rango_entre['high'].idxmax()
                indice_cuello = min1['indice'] + (indice_cuello_relativo - min1['indice'])
                
                # Verificar si el cuello ha sido roto
                precio_actual = df.iloc[-1]['close']
                cuello_roto = precio_actual > precio_cuello
                
                distancia_velas = min2['indice'] - min1['indice']
                
                return {
                    'detectado': True,
                    'patron': 'doble_suelo',
                    'tipo_reversion': 'alcista',
                    'minimo1': {'indice': min1['indice'], 'precio': round(min1['precio'], 5)},
                    'minimo2': {'indice': min2['indice'], 'precio': round(min2['precio'], 5)},
                    'cuello': {'indice': indice_cuello, 'precio': round(precio_cuello, 5)},
                    'cuello_roto': cuello_roto,
                    'confirmado': cuello_roto,
                    'distancia_velas': distancia_velas,
                    'efectividad_patron': 80 if cuello_roto else 60,
                    'descripcion': 'Doble Suelo: Reversión de bajista a alcista',
                    'requiere_tendencia': 'bajista'
                }
    
    return {'detectado': False, 'patron': 'doble_suelo'}


def detectar_hombro_cabeza_hombro(df: pd.DataFrame, tolerancia: float = 0.015) -> Dict:
    """
    Detecta patrón Hombro-Cabeza-Hombro (HCH)
    
    CARACTERÍSTICAS:
    - Tres máximos: Hombro1 - Cabeza - Hombro2
    - Cabeza es el máximo más alto
    - Hombros al mismo nivel (±tolerancia)
    - Cuello: línea que une los mínimos entre hombros
    - Se confirma al romper el cuello
    - Indica reversión de alcista a bajista
    """
    if len(df) < 30:
        return {'detectado': False, 'patron': 'hch'}
    
    # Buscar máximos locales
    maximos = []
    for i in range(5, len(df) - 5):
        ventana = df.iloc[i-5:i+6]
        if df.iloc[i]['high'] == ventana['high'].max():
            maximos.append({
                'indice': i,
                'precio': df.iloc[i]['high']
            })
    
    if len(maximos) < 3:
        return {'detectado': False, 'patron': 'hch'}
    
    # Buscar patrón HCH: Hombro1 < Cabeza > Hombro2
    for i in range(len(maximos) - 2):
        hombro1 = maximos[i]
        cabeza = maximos[i + 1]
        hombro2 = maximos[i + 2]
        
        # Verificar que la cabeza sea más alta que los hombros
        if cabeza['precio'] > hombro1['precio'] and cabeza['precio'] > hombro2['precio']:
            # Verificar que los hombros estén al mismo nivel
            diff_hombros = abs(hombro1['precio'] - hombro2['precio']) / hombro1['precio']
            
            if diff_hombros <= tolerancia:
                # Buscar mínimos entre hombro1-cabeza y cabeza-hombro2
                rango1 = df.iloc[hombro1['indice']:cabeza['indice']+1]
                rango2 = df.iloc[cabeza['indice']:hombro2['indice']+1]
                
                min1_precio = rango1['low'].min()
                min2_precio = rango2['low'].min()
                
                # El cuello es el promedio de los dos mínimos
                precio_cuello = (min1_precio + min2_precio) / 2
                
                # Verificar si el cuello ha sido roto
                precio_actual = df.iloc[-1]['close']
                cuello_roto = precio_actual < precio_cuello
                
                return {
                    'detectado': True,
                    'patron': 'hch',
                    'tipo_reversion': 'bajista',
                    'hombro1': {'indice': hombro1['indice'], 'precio': round(hombro1['precio'], 5)},
                    'cabeza': {'indice': cabeza['indice'], 'precio': round(cabeza['precio'], 5)},
                    'hombro2': {'indice': hombro2['indice'], 'precio': round(hombro2['precio'], 5)},
                    'cuello': {'precio': round(precio_cuello, 5)},
                    'cuello_roto': cuello_roto,
                    'confirmado': cuello_roto,
                    'efectividad_patron': 85 if cuello_roto else 65,
                    'descripcion': 'Hombro-Cabeza-Hombro: Reversión de alcista a bajista',
                    'requiere_tendencia': 'alcista'
                }
    
    return {'detectado': False, 'patron': 'hch'}


def detectar_hch_invertido(df: pd.DataFrame, tolerancia: float = 0.015) -> Dict:
    """
    Detecta patrón Hombro-Cabeza-Hombro Invertido (HCHi)
    
    CARACTERÍSTICAS:
    - Tres mínimos: Hombro1 - Cabeza - Hombro2
    - Cabeza es el mínimo más bajo
    - Hombros al mismo nivel (±tolerancia)
    - Cuello: línea que une los máximos entre hombros
    - Se confirma al romper el cuello
    - Indica reversión de bajista a alcista
    """
    if len(df) < 30:
        return {'detectado': False, 'patron': 'hchi'}
    
    # Buscar mínimos locales
    minimos = []
    for i in range(5, len(df) - 5):
        ventana = df.iloc[i-5:i+6]
        if df.iloc[i]['low'] == ventana['low'].min():
            minimos.append({
                'indice': i,
                'precio': df.iloc[i]['low']
            })
    
    if len(minimos) < 3:
        return {'detectado': False, 'patron': 'hchi'}
    
    # Buscar patrón HCHi: Hombro1 > Cabeza < Hombro2
    for i in range(len(minimos) - 2):
        hombro1 = minimos[i]
        cabeza = minimos[i + 1]
        hombro2 = minimos[i + 2]
        
        # Verificar que la cabeza sea más baja que los hombros
        if cabeza['precio'] < hombro1['precio'] and cabeza['precio'] < hombro2['precio']:
            # Verificar que los hombros estén al mismo nivel
            diff_hombros = abs(hombro1['precio'] - hombro2['precio']) / hombro1['precio']
            
            if diff_hombros <= tolerancia:
                # Buscar máximos entre hombro1-cabeza y cabeza-hombro2
                rango1 = df.iloc[hombro1['indice']:cabeza['indice']+1]
                rango2 = df.iloc[cabeza['indice']:hombro2['indice']+1]
                
                max1_precio = rango1['high'].max()
                max2_precio = rango2['high'].max()
                
                # El cuello es el promedio de los dos máximos
                precio_cuello = (max1_precio + max2_precio) / 2
                
                # Verificar si el cuello ha sido roto
                precio_actual = df.iloc[-1]['close']
                cuello_roto = precio_actual > precio_cuello
                
                return {
                    'detectado': True,
                    'patron': 'hchi',
                    'tipo_reversion': 'alcista',
                    'hombro1': {'indice': hombro1['indice'], 'precio': round(hombro1['precio'], 5)},
                    'cabeza': {'indice': cabeza['indice'], 'precio': round(cabeza['precio'], 5)},
                    'hombro2': {'indice': hombro2['indice'], 'precio': round(hombro2['precio'], 5)},
                    'cuello': {'precio': round(precio_cuello, 5)},
                    'cuello_roto': cuello_roto,
                    'confirmado': cuello_roto,
                    'efectividad_patron': 85 if cuello_roto else 65,
                    'descripcion': 'HCH Invertido: Reversión de bajista a alcista',
                    'requiere_tendencia': 'bajista'
                }
    
    return {'detectado': False, 'patron': 'hchi'}


def detectar_todos_patrones_chartistas(df: pd.DataFrame, tendencia_actual: str = None) -> Dict:
    """
    Detecta todos los patrones chartistas (reversión Y continuidad)
    
    PATRONES DE REVERSIÓN:
    - Doble Techo/HCH: Solo si tendencia es alcista
    - Doble Suelo/HCHi: Solo si tendencia es bajista
    
    PATRONES DE CONTINUIDAD:
    - Triángulo Ascendente/Bandera Alcista: Solo si tendencia es alcista
    - Triángulo Descendente/Bandera Bajista: Solo si tendencia es bajista
    
    Args:
        df: DataFrame con OHLC
        tendencia_actual: 'alcista', 'bajista' o None
    
    Returns:
        dict: Todos los patrones detectados con validación contextual
    """
    # Patrones de REVERSIÓN
    patrones_reversion = {
        'doble_techo': detectar_doble_techo(df),
        'doble_suelo': detectar_doble_suelo(df),
        'hch': detectar_hombro_cabeza_hombro(df),
        'hchi': detectar_hch_invertido(df)
    }
    
    # Patrones de CONTINUIDAD
    patrones_continuidad = {
        'triangulo_ascendente': detectar_triangulo_ascendente(df),
        'triangulo_descendente': detectar_triangulo_descendente(df),
        'bandera_alcista': detectar_bandera_alcista(df),
        'bandera_bajista': detectar_bandera_bajista(df)
    }
    
    # Combinar todos los patrones
    patrones = {**patrones_reversion, **patrones_continuidad}
    
    # Filtrar patrones válidos según tendencia
    patrones_validos = []
    patrones_invalidos = []
    
    for nombre, patron in patrones.items():
        if patron['detectado']:
            # Validar contexto de tendencia
            requiere = patron.get('requiere_tendencia')
            
            if tendencia_actual:
                if requiere == tendencia_actual:
                    # Patrón válido: coincide con tendencia requerida
                    patron['valido_contexto'] = True
                    patron['advertencia'] = None
                    patrones_validos.append(patron)
                else:
                    # Patrón inválido: no coincide con tendencia
                    patron['valido_contexto'] = False
                    patron['advertencia'] = f"Patrón requiere tendencia {requiere} pero la actual es {tendencia_actual}"
                    patrones_invalidos.append(patron)
            else:
                # Sin info de tendencia, aceptar con advertencia
                patron['valido_contexto'] = True
                patron['advertencia'] = "No se pudo validar con tendencia actual"
                patrones_validos.append(patron)
    
    # Calcular efectividad total
    if patrones_validos:
        efectividad_promedio = sum(p['efectividad_patron'] for p in patrones_validos) / len(patrones_validos)
        # Bonus si hay múltiples patrones confirmados
        patrones_confirmados = [p for p in patrones_validos if p['confirmado']]
        bonus_confirmacion = len(patrones_confirmados) * 5
        efectividad_total = min(efectividad_promedio + bonus_confirmacion, 100)
    else:
        efectividad_total = 0
    
    return {
        'efectividad': round(efectividad_total, 2),
        'patrones_detectados': len([p for p in patrones.values() if p['detectado']]),
        'patrones_validos': len(patrones_validos),
        'patrones_confirmados': len([p for p in patrones_validos if p.get('confirmado', False)]),
        'detalles_validos': patrones_validos,
        'detalles_invalidos': patrones_invalidos,
        'mejor_patron': max(patrones_validos, key=lambda x: x['efectividad_patron']) if patrones_validos else None
    }


def detectar_triangulo_ascendente(df: pd.DataFrame, ventana: int = 20) -> Dict:
    """
    Detecta patrón de Triángulo Ascendente
    
    CARACTERÍSTICAS:
    - Resistencia fuerte (horizontal)
    - Mínimos cada vez más altos (soporte dinámico ascendente)
    - Indica continuidad de tendencia alcista
    - Se confirma al romper la resistencia
    
    IMPORTANTE:
    - Es un DESCANSO del precio (consolidación)
    - Tras ruptura, precio continúa alcista
    """
    if len(df) < ventana:
        return {'detectado': False, 'patron': 'triangulo_ascendente'}
    
    ultimas_velas = df.tail(ventana)
    
    # Buscar resistencia horizontal (máximos al mismo nivel)
    maximos = []
    for i in range(2, len(ultimas_velas) - 2):
        if ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i-1]['high'] and \
           ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i+1]['high']:
            maximos.append({
                'indice': i,
                'precio': ultimas_velas.iloc[i]['high']
            })
    
    if len(maximos) < 2:
        return {'detectado': False, 'patron': 'triangulo_ascendente'}
    
    # Verificar que los máximos estén al mismo nivel (resistencia horizontal)
    precios_maximos = [m['precio'] for m in maximos]
    resistencia = np.mean(precios_maximos)
    variacion = np.std(precios_maximos) / resistencia
    
    if variacion > 0.01:  # Más de 1% de variación
        return {'detectado': False, 'patron': 'triangulo_ascendente'}
    
    # Buscar mínimos ascendentes
    minimos = []
    for i in range(2, len(ultimas_velas) - 2):
        if ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i-1]['low'] and \
           ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i+1]['low']:
            minimos.append({
                'indice': i,
                'precio': ultimas_velas.iloc[i]['low']
            })
    
    if len(minimos) < 2:
        return {'detectado': False, 'patron': 'triangulo_ascendente'}
    
    # Verificar que los mínimos sean ascendentes
    precios_minimos = [m['precio'] for m in minimos]
    if not all(precios_minimos[i] < precios_minimos[i+1] for i in range(len(precios_minimos)-1)):
        return {'detectado': False, 'patron': 'triangulo_ascendente'}
    
    # Verificar ruptura de resistencia
    precio_actual = df.iloc[-1]['close']
    resistencia_rota = precio_actual > resistencia
    
    return {
        'detectado': True,
        'patron': 'triangulo_ascendente',
        'tipo_continuidad': 'alcista',
        'resistencia': round(resistencia, 5),
        'minimos_ascendentes': len(minimos),
        'resistencia_rota': resistencia_rota,
        'confirmado': resistencia_rota,
        'efectividad_patron': 75 if resistencia_rota else 55,
        'descripcion': 'Triángulo Ascendente: Consolidación antes de continuar alcista',
        'requiere_tendencia': 'alcista',
        'es_descanso': True
    }


def detectar_triangulo_descendente(df: pd.DataFrame, ventana: int = 20) -> Dict:
    """
    Detecta patrón de Triángulo Descendente
    
    CARACTERÍSTICAS:
    - Soporte fuerte (horizontal)
    - Máximos cada vez más bajos (resistencia dinámica descendente)
    - Indica continuidad de tendencia bajista
    - Se confirma al romper el soporte
    """
    if len(df) < ventana:
        return {'detectado': False, 'patron': 'triangulo_descendente'}
    
    ultimas_velas = df.tail(ventana)
    
    # Buscar soporte horizontal (mínimos al mismo nivel)
    minimos = []
    for i in range(2, len(ultimas_velas) - 2):
        if ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i-1]['low'] and \
           ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i+1]['low']:
            minimos.append({
                'indice': i,
                'precio': ultimas_velas.iloc[i]['low']
            })
    
    if len(minimos) < 2:
        return {'detectado': False, 'patron': 'triangulo_descendente'}
    
    # Verificar que los mínimos estén al mismo nivel (soporte horizontal)
    precios_minimos = [m['precio'] for m in minimos]
    soporte = np.mean(precios_minimos)
    variacion = np.std(precios_minimos) / soporte
    
    if variacion > 0.01:
        return {'detectado': False, 'patron': 'triangulo_descendente'}
    
    # Buscar máximos descendentes
    maximos = []
    for i in range(2, len(ultimas_velas) - 2):
        if ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i-1]['high'] and \
           ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i+1]['high']:
            maximos.append({
                'indice': i,
                'precio': ultimas_velas.iloc[i]['high']
            })
    
    if len(maximos) < 2:
        return {'detectado': False, 'patron': 'triangulo_descendente'}
    
    # Verificar que los máximos sean descendentes
    precios_maximos = [m['precio'] for m in maximos]
    if not all(precios_maximos[i] > precios_maximos[i+1] for i in range(len(precios_maximos)-1)):
        return {'detectado': False, 'patron': 'triangulo_descendente'}
    
    # Verificar ruptura de soporte
    precio_actual = df.iloc[-1]['close']
    soporte_roto = precio_actual < soporte
    
    return {
        'detectado': True,
        'patron': 'triangulo_descendente',
        'tipo_continuidad': 'bajista',
        'soporte': round(soporte, 5),
        'maximos_descendentes': len(maximos),
        'soporte_roto': soporte_roto,
        'confirmado': soporte_roto,
        'efectividad_patron': 75 if soporte_roto else 55,
        'descripcion': 'Triángulo Descendente: Consolidación antes de continuar bajista',
        'requiere_tendencia': 'bajista',
        'es_descanso': True
    }


def detectar_bandera_alcista(df: pd.DataFrame, ventana: int = 15) -> Dict:
    """
    Detecta patrón de Bandera Alcista
    
    CARACTERÍSTICAS:
    - Consolidación bajista pequeña (contra tendencia)
    - Dentro de tendencia alcista general
    - Soporte y resistencia dinámicos (inclinados bajista)
    - Es un PULLBACK (retroceso temporal)
    - Tras ruptura de resistencia dinámica, continúa alcista
    """
    if len(df) < ventana + 10:
        return {'detectado': False, 'patron': 'bandera_alcista'}
    
    # Verificar tendencia alcista previa
    velas_previas = df.iloc[-(ventana+10):-ventana]
    precio_inicio = velas_previas.iloc[0]['close']
    precio_antes_consolidacion = velas_previas.iloc[-1]['close']
    
    if precio_antes_consolidacion <= precio_inicio:
        return {'detectado': False, 'patron': 'bandera_alcista'}
    
    # Analizar consolidación (últimas velas)
    consolidacion = df.tail(ventana)
    
    # La consolidación debe ser bajista (contra la tendencia alcista)
    precio_inicio_consol = consolidacion.iloc[0]['close']
    precio_fin_consol = consolidacion.iloc[-1]['close']
    
    if precio_fin_consol >= precio_inicio_consol:
        return {'detectado': False, 'patron': 'bandera_alcista'}
    
    # Buscar canal bajista (S/R dinámicos)
    maximos_consol = consolidacion['high'].values
    minimos_consol = consolidacion['low'].values
    
    # Verificar ruptura de resistencia dinámica
    precio_actual = df.iloc[-1]['close']
    resistencia_dinamica = np.max(maximos_consol[-5:])
    resistencia_rota = precio_actual > resistencia_dinamica
    
    return {
        'detectado': True,
        'patron': 'bandera_alcista',
        'tipo_continuidad': 'alcista',
        'es_pullback': True,
        'resistencia_dinamica': round(resistencia_dinamica, 5),
        'resistencia_rota': resistencia_rota,
        'confirmado': resistencia_rota,
        'efectividad_patron': 70 if resistencia_rota else 50,
        'descripcion': 'Bandera Alcista: Pullback (descanso) antes de continuar alcista',
        'requiere_tendencia': 'alcista',
        'es_descanso': True
    }


def detectar_bandera_bajista(df: pd.DataFrame, ventana: int = 15) -> Dict:
    """
    Detecta patrón de Bandera Bajista
    
    CARACTERÍSTICAS:
    - Consolidación alcista pequeña (contra tendencia)
    - Dentro de tendencia bajista general
    - Soporte y resistencia dinámicos (inclinados alcista)
    - Es un PULLBACK (retroceso temporal)
    - Tras ruptura de soporte dinámico, continúa bajista
    """
    if len(df) < ventana + 10:
        return {'detectado': False, 'patron': 'bandera_bajista'}
    
    # Verificar tendencia bajista previa
    velas_previas = df.iloc[-(ventana+10):-ventana]
    precio_inicio = velas_previas.iloc[0]['close']
    precio_antes_consolidacion = velas_previas.iloc[-1]['close']
    
    if precio_antes_consolidacion >= precio_inicio:
        return {'detectado': False, 'patron': 'bandera_bajista'}
    
    # Analizar consolidación (últimas velas)
    consolidacion = df.tail(ventana)
    
    # La consolidación debe ser alcista (contra la tendencia bajista)
    precio_inicio_consol = consolidacion.iloc[0]['close']
    precio_fin_consol = consolidacion.iloc[-1]['close']
    
    if precio_fin_consol <= precio_inicio_consol:
        return {'detectado': False, 'patron': 'bandera_bajista'}
    
    # Buscar canal alcista (S/R dinámicos)
    minimos_consol = consolidacion['low'].values
    
    # Verificar ruptura de soporte dinámico
    precio_actual = df.iloc[-1]['close']
    soporte_dinamico = np.min(minimos_consol[-5:])
    soporte_roto = precio_actual < soporte_dinamico
    
    return {
        'detectado': True,
        'patron': 'bandera_bajista',
        'tipo_continuidad': 'bajista',
        'es_pullback': True,
        'soporte_dinamico': round(soporte_dinamico, 5),
        'soporte_roto': soporte_roto,
        'confirmado': soporte_roto,
        'efectividad_patron': 70 if soporte_roto else 50,
        'descripcion': 'Bandera Bajista: Pullback (descanso) antes de continuar bajista',
        'requiere_tendencia': 'bajista',
        'es_descanso': True
    }


# Función de integración con otras estrategias
def analizar_patrones_chartistas_con_contexto(df: pd.DataFrame, tendencia_info: Dict = None, zonas_sr: Dict = None) -> Dict:
    """
    Analiza patrones chartistas con contexto completo de tendencia y S/R
    
    Esta función integra los patrones chartistas como confirmación adicional
    para aumentar la efectividad de las señales.
    
    Args:
        df: DataFrame con OHLC
        tendencia_info: Resultado de análisis de tendencia
        zonas_sr: Resultado de análisis de S/R
    
    Returns:
        dict: Análisis completo con bonus de efectividad
    """
    # Obtener tendencia actual
    tendencia_actual = None
    if tendencia_info:
        tendencia_actual = tendencia_info.get('direccion')
    
    # Detectar patrones
    resultado = detectar_todos_patrones_chartistas(df, tendencia_actual)
    
    # Bonus por alineación con zonas S/R
    if zonas_sr and resultado['patrones_validos']:
        for patron in resultado['detalles_validos']:
            if 'cuello' in patron:
                precio_cuello = patron['cuello']['precio']
                
                # Verificar si el cuello coincide con zona S/R
                zonas_soporte = zonas_sr.get('detalles', {}).get('zonas_soporte', [])
                zonas_resistencia = zonas_sr.get('detalles', {}).get('zonas_resistencia', [])
                
                for zona in zonas_soporte + zonas_resistencia:
                    precio_zona = zona.get('precio_medio', 0)
                    if abs(precio_cuello - precio_zona) / precio_zona < 0.005:  # 0.5% tolerancia
                        patron['bonus_sr'] = 10
                        patron['descripcion'] += " + Cuello coincide con zona S/R"
                        resultado['efectividad'] = min(resultado['efectividad'] + 10, 100)
                        break
    
    return resultado


# ============================================================================
# CANALES: LATERALES, ALCISTAS Y BAJISTAS
# ============================================================================

def detectar_canal_lateral(df: pd.DataFrame, ventana: int = 30, tolerancia: float = 0.015) -> Dict:
    """
    Detecta Canal Lateral (Rango)
    
    CARACTERÍSTICAS:
    - Precio atrapado entre resistencia y soporte horizontal
    - Ambos niveles son fuertes y paralelos
    - Oportunidad: Operar rebotes en las zonas
    
    ⚠️ ADVERTENCIA:
    - Mientras más testeos, mayor probabilidad de ruptura
    - Las zonas S/R no son para siempre
    - Cuidado con operar cerca de ruptura
    
    Args:
        df: DataFrame con OHLC
        ventana: Velas a analizar
        tolerancia: % de variación permitida para considerar nivel horizontal
    
    Returns:
        dict: Información del canal lateral
    """
    if len(df) < ventana:
        return {'detectado': False, 'patron': 'canal_lateral'}
    
    ultimas_velas = df.tail(ventana)
    
    # Identificar máximos (resistencia)
    maximos = []
    for i in range(2, len(ultimas_velas) - 2):
        if ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i-1]['high'] and \
           ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i+1]['high']:
            maximos.append(ultimas_velas.iloc[i]['high'])
    
    # Identificar mínimos (soporte)
    minimos = []
    for i in range(2, len(ultimas_velas) - 2):
        if ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i-1]['low'] and \
           ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i+1]['low']:
            minimos.append(ultimas_velas.iloc[i]['low'])
    
    if len(maximos) < 2 or len(minimos) < 2:
        return {'detectado': False, 'patron': 'canal_lateral'}
    
    # Calcular niveles promedio
    resistencia = np.mean(maximos)
    soporte = np.mean(minimos)
    
    # Verificar que sean horizontales (poca variación)
    variacion_resistencia = np.std(maximos) / resistencia
    variacion_soporte = np.std(minimos) / soporte
    
    if variacion_resistencia > tolerancia or variacion_soporte > tolerancia:
        return {'detectado': False, 'patron': 'canal_lateral'}
    
    # Calcular altura del canal
    altura_canal = resistencia - soporte
    altura_porcentaje = (altura_canal / soporte) * 100
    
    # Contar testeos
    testeos_resistencia = len(maximos)
    testeos_soporte = len(minimos)
    total_testeos = testeos_resistencia + testeos_soporte
    
    # ⚠️ Advertencia: Muchos testeos = Mayor probabilidad de ruptura
    riesgo_ruptura = "ALTO" if total_testeos >= 8 else "MEDIO" if total_testeos >= 5 else "BAJO"
    
    # Verificar posición actual del precio
    precio_actual = df.iloc[-1]['close']
    posicion_canal = (precio_actual - soporte) / altura_canal  # 0 = soporte, 1 = resistencia
    
    # Determinar oportunidad de trading
    if posicion_canal <= 0.2:
        oportunidad = "COMPRA cerca de soporte"
        direccion_esperada = "alcista"
    elif posicion_canal >= 0.8:
        oportunidad = "VENTA cerca de resistencia"
        direccion_esperada = "bajista"
    else:
        oportunidad = "ESPERAR - Precio en medio del canal"
        direccion_esperada = "neutral"
    
    return {
        'detectado': True,
        'patron': 'canal_lateral',
        'tipo': 'rango',
        'resistencia': round(resistencia, 5),
        'soporte': round(soporte, 5),
        'altura_canal': round(altura_canal, 5),
        'altura_porcentaje': round(altura_porcentaje, 2),
        'testeos_resistencia': testeos_resistencia,
        'testeos_soporte': testeos_soporte,
        'total_testeos': total_testeos,
        'riesgo_ruptura': riesgo_ruptura,
        'posicion_precio': round(posicion_canal * 100, 1),  # % dentro del canal
        'oportunidad': oportunidad,
        'direccion_esperada': direccion_esperada,
        'descripcion': f'Canal Lateral: Precio atrapado entre {soporte:.5f} y {resistencia:.5f}',
        'advertencia': f'⚠️ {total_testeos} testeos totales - Riesgo de ruptura: {riesgo_ruptura}'
    }


def detectar_canal_alcista(df: pd.DataFrame, ventana: int = 30) -> Dict:
    """
    Detecta Canal Alcista
    
    CARACTERÍSTICAS:
    - Soporte y resistencia dinámicos (inclinados hacia arriba)
    - Ambos niveles son paralelos
    - Indica tendencia alcista controlada
    - Oportunidad: Comprar en rebotes del soporte dinámico
    
    ⚠️ ADVERTENCIA:
    - Mientras más testeos, mayor probabilidad de ruptura
    
    Args:
        df: DataFrame con OHLC
        ventana: Velas a analizar
    
    Returns:
        dict: Información del canal alcista
    """
    if len(df) < ventana:
        return {'detectado': False, 'patron': 'canal_alcista'}
    
    ultimas_velas = df.tail(ventana)
    
    # Identificar máximos y mínimos con sus índices
    maximos = []
    minimos = []
    
    for i in range(2, len(ultimas_velas) - 2):
        if ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i-1]['high'] and \
           ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i+1]['high']:
            maximos.append({'indice': i, 'precio': ultimas_velas.iloc[i]['high']})
        
        if ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i-1]['low'] and \
           ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i+1]['low']:
            minimos.append({'indice': i, 'precio': ultimas_velas.iloc[i]['low']})
    
    if len(maximos) < 2 or len(minimos) < 2:
        return {'detectado': False, 'patron': 'canal_alcista'}
    
    # Calcular pendiente del soporte (mínimos)
    x_minimos = [m['indice'] for m in minimos]
    y_minimos = [m['precio'] for m in minimos]
    pendiente_soporte = np.polyfit(x_minimos, y_minimos, 1)[0]
    
    # Calcular pendiente de la resistencia (máximos)
    x_maximos = [m['indice'] for m in maximos]
    y_maximos = [m['precio'] for m in maximos]
    pendiente_resistencia = np.polyfit(x_maximos, y_maximos, 1)[0]
    
    # Verificar que ambas pendientes sean positivas (alcista)
    if pendiente_soporte <= 0 or pendiente_resistencia <= 0:
        return {'detectado': False, 'patron': 'canal_alcista'}
    
    # Verificar que sean paralelas (pendientes similares)
    diferencia_pendientes = abs(pendiente_soporte - pendiente_resistencia)
    promedio_pendientes = (pendiente_soporte + pendiente_resistencia) / 2
    
    if diferencia_pendientes / promedio_pendientes > 0.5:  # 50% de diferencia máxima
        return {'detectado': False, 'patron': 'canal_alcista'}
    
    # Calcular niveles actuales
    ultimo_indice = len(ultimas_velas) - 1
    soporte_actual = np.polyval([pendiente_soporte, y_minimos[0] - pendiente_soporte * x_minimos[0]], ultimo_indice)
    resistencia_actual = np.polyval([pendiente_resistencia, y_maximos[0] - pendiente_resistencia * x_maximos[0]], ultimo_indice)
    
    # Contar testeos
    testeos_soporte = len(minimos)
    testeos_resistencia = len(maximos)
    total_testeos = testeos_soporte + testeos_resistencia
    
    # Riesgo de ruptura
    riesgo_ruptura = "ALTO" if total_testeos >= 8 else "MEDIO" if total_testeos >= 5 else "BAJO"
    
    # Posición del precio
    precio_actual = df.iloc[-1]['close']
    altura_canal = resistencia_actual - soporte_actual
    posicion_canal = (precio_actual - soporte_actual) / altura_canal
    
    # Oportunidad
    if posicion_canal <= 0.3:
        oportunidad = "COMPRA - Cerca de soporte dinámico"
    elif posicion_canal >= 0.7:
        oportunidad = "ESPERAR - Cerca de resistencia"
    else:
        oportunidad = "NEUTRAL - Precio en medio del canal"
    
    return {
        'detectado': True,
        'patron': 'canal_alcista',
        'tipo': 'tendencia_alcista',
        'soporte_dinamico': round(soporte_actual, 5),
        'resistencia_dinamica': round(resistencia_actual, 5),
        'pendiente_soporte': round(pendiente_soporte, 6),
        'pendiente_resistencia': round(pendiente_resistencia, 6),
        'testeos_soporte': testeos_soporte,
        'testeos_resistencia': testeos_resistencia,
        'total_testeos': total_testeos,
        'riesgo_ruptura': riesgo_ruptura,
        'posicion_precio': round(posicion_canal * 100, 1),
        'oportunidad': oportunidad,
        'descripcion': 'Canal Alcista: Tendencia alcista controlada con S/R dinámicos',
        'advertencia': f'⚠️ {total_testeos} testeos totales - Riesgo de ruptura: {riesgo_ruptura}'
    }


def detectar_canal_bajista(df: pd.DataFrame, ventana: int = 30) -> Dict:
    """
    Detecta Canal Bajista
    
    CARACTERÍSTICAS:
    - Soporte y resistencia dinámicos (inclinados hacia abajo)
    - Ambos niveles son paralelos
    - Indica tendencia bajista controlada
    - Oportunidad: Vender en rebotes de la resistencia dinámica
    
    ⚠️ ADVERTENCIA:
    - Mientras más testeos, mayor probabilidad de ruptura
    
    Args:
        df: DataFrame con OHLC
        ventana: Velas a analizar
    
    Returns:
        dict: Información del canal bajista
    """
    if len(df) < ventana:
        return {'detectado': False, 'patron': 'canal_bajista'}
    
    ultimas_velas = df.tail(ventana)
    
    # Identificar máximos y mínimos con sus índices
    maximos = []
    minimos = []
    
    for i in range(2, len(ultimas_velas) - 2):
        if ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i-1]['high'] and \
           ultimas_velas.iloc[i]['high'] >= ultimas_velas.iloc[i+1]['high']:
            maximos.append({'indice': i, 'precio': ultimas_velas.iloc[i]['high']})
        
        if ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i-1]['low'] and \
           ultimas_velas.iloc[i]['low'] <= ultimas_velas.iloc[i+1]['low']:
            minimos.append({'indice': i, 'precio': ultimas_velas.iloc[i]['low']})
    
    if len(maximos) < 2 or len(minimos) < 2:
        return {'detectado': False, 'patron': 'canal_bajista'}
    
    # Calcular pendiente del soporte (mínimos)
    x_minimos = [m['indice'] for m in minimos]
    y_minimos = [m['precio'] for m in minimos]
    pendiente_soporte = np.polyfit(x_minimos, y_minimos, 1)[0]
    
    # Calcular pendiente de la resistencia (máximos)
    x_maximos = [m['indice'] for m in maximos]
    y_maximos = [m['precio'] for m in maximos]
    pendiente_resistencia = np.polyfit(x_maximos, y_maximos, 1)[0]
    
    # Verificar que ambas pendientes sean negativas (bajista)
    if pendiente_soporte >= 0 or pendiente_resistencia >= 0:
        return {'detectado': False, 'patron': 'canal_bajista'}
    
    # Verificar que sean paralelas (pendientes similares)
    diferencia_pendientes = abs(pendiente_soporte - pendiente_resistencia)
    promedio_pendientes = abs((pendiente_soporte + pendiente_resistencia) / 2)
    
    if diferencia_pendientes / promedio_pendientes > 0.5:  # 50% de diferencia máxima
        return {'detectado': False, 'patron': 'canal_bajista'}
    
    # Calcular niveles actuales
    ultimo_indice = len(ultimas_velas) - 1
    soporte_actual = np.polyval([pendiente_soporte, y_minimos[0] - pendiente_soporte * x_minimos[0]], ultimo_indice)
    resistencia_actual = np.polyval([pendiente_resistencia, y_maximos[0] - pendiente_resistencia * x_maximos[0]], ultimo_indice)
    
    # Contar testeos
    testeos_soporte = len(minimos)
    testeos_resistencia = len(maximos)
    total_testeos = testeos_soporte + testeos_resistencia
    
    # Riesgo de ruptura
    riesgo_ruptura = "ALTO" if total_testeos >= 8 else "MEDIO" if total_testeos >= 5 else "BAJO"
    
    # Posición del precio
    precio_actual = df.iloc[-1]['close']
    altura_canal = resistencia_actual - soporte_actual
    posicion_canal = (precio_actual - soporte_actual) / altura_canal
    
    # Oportunidad
    if posicion_canal >= 0.7:
        oportunidad = "VENTA - Cerca de resistencia dinámica"
    elif posicion_canal <= 0.3:
        oportunidad = "ESPERAR - Cerca de soporte"
    else:
        oportunidad = "NEUTRAL - Precio en medio del canal"
    
    return {
        'detectado': True,
        'patron': 'canal_bajista',
        'tipo': 'tendencia_bajista',
        'soporte_dinamico': round(soporte_actual, 5),
        'resistencia_dinamica': round(resistencia_actual, 5),
        'pendiente_soporte': round(pendiente_soporte, 6),
        'pendiente_resistencia': round(pendiente_resistencia, 6),
        'testeos_soporte': testeos_soporte,
        'testeos_resistencia': testeos_resistencia,
        'total_testeos': total_testeos,
        'riesgo_ruptura': riesgo_ruptura,
        'posicion_precio': round(posicion_canal * 100, 1),
        'oportunidad': oportunidad,
        'descripcion': 'Canal Bajista: Tendencia bajista controlada con S/R dinámicos',
        'advertencia': f'⚠️ {total_testeos} testeos totales - Riesgo de ruptura: {riesgo_ruptura}'
    }


def detectar_todos_canales(df: pd.DataFrame) -> Dict:
    """
    Detecta todos los tipos de canales
    
    Returns:
        dict: Información de todos los canales detectados
    """
    canales = {
        'canal_lateral': detectar_canal_lateral(df),
        'canal_alcista': detectar_canal_alcista(df),
        'canal_bajista': detectar_canal_bajista(df)
    }
    
    # Identificar canal activo
    canal_activo = None
    for nombre, canal in canales.items():
        if canal['detectado']:
            canal_activo = nombre
            break
    
    return {
        'canales': canales,
        'canal_activo': canal_activo,
        'hay_canal': canal_activo is not None
    }


# ============================================================================
# NIVELES OBJETIVO (PROFIT TARGET)
# ============================================================================

def calcular_nivel_objetivo(patron: Dict, df: pd.DataFrame) -> Dict:
    """
    Calcula el Nivel Objetivo de un patrón chartista
    
    CONCEPTO:
    - El nivel objetivo es una zona S/R donde el precio podría llegar tras la ruptura
    - Se calcula midiendo la altura del patrón y proyectándola en dirección de la ruptura
    - Una vez alcanzado, el precio suele hacer PULLBACK (retroceder al patrón)
    - El pullback es la oportunidad del "último beso"
    
    CÁLCULO:
    1. Identificar punto máximo y mínimo del patrón
    2. Calcular altura = máximo - mínimo
    3. Proyectar altura desde el punto de ruptura
    
    ⚠️ ADVERTENCIA:
    - Que exista el nivel NO garantiza que el precio lo alcance
    - Es una zona de PROBABILIDAD, no certeza
    - Usar como referencia para tomar ganancias
    
    Args:
        patron: Diccionario con información del patrón
        df: DataFrame con OHLC
    
    Returns:
        dict: Información del nivel objetivo
    """
    if not patron.get('detectado', False):
        return {'calculado': False, 'razon': 'Patrón no detectado'}
    
    nombre_patron = patron.get('patron', '')
    
    # Extraer puntos clave según el tipo de patrón
    if nombre_patron in ['doble_techo', 'hch']:
        # Patrones de reversión bajista
        punto_maximo = patron.get('techo1', {}).get('precio') or patron.get('cabeza', {}).get('precio')
        punto_minimo = patron.get('cuello', {}).get('precio')
        direccion = 'bajista'
        
    elif nombre_patron in ['doble_suelo', 'hchi']:
        # Patrones de reversión alcista
        punto_maximo = patron.get('cuello', {}).get('precio')
        punto_minimo = patron.get('suelo1', {}).get('precio') or patron.get('cabeza', {}).get('precio')
        direccion = 'alcista'
        
    elif nombre_patron in ['triangulo_ascendente', 'bandera_alcista']:
        # Patrones de continuidad alcista
        punto_maximo = patron.get('resistencia') or patron.get('resistencia_dinamica')
        punto_minimo = min([m for m in df.tail(20)['low']])
        direccion = 'alcista'
        
    elif nombre_patron in ['triangulo_descendente', 'bandera_bajista']:
        # Patrones de continuidad bajista
        punto_maximo = max([m for m in df.tail(20)['high']])
        punto_minimo = patron.get('soporte') or patron.get('soporte_dinamico')
        direccion = 'bajista'
        
    else:
        return {'calculado': False, 'razon': f'Patrón {nombre_patron} no soportado para cálculo de objetivo'}
    
    if not punto_maximo or not punto_minimo:
        return {'calculado': False, 'razon': 'No se pudieron identificar puntos clave del patrón'}
    
    # Calcular altura del patrón
    altura_patron = abs(punto_maximo - punto_minimo)
    
    # Calcular nivel objetivo
    precio_actual = df.iloc[-1]['close']
    
    if direccion == 'alcista':
        # Proyectar hacia arriba
        punto_ruptura = punto_maximo
        nivel_objetivo = punto_ruptura + altura_patron
        distancia_objetivo = nivel_objetivo - precio_actual
        
    else:  # bajista
        # Proyectar hacia abajo
        punto_ruptura = punto_minimo
        nivel_objetivo = punto_ruptura - altura_patron
        distancia_objetivo = precio_actual - nivel_objetivo
    
    # Calcular porcentaje de movimiento esperado
    porcentaje_movimiento = (altura_patron / precio_actual) * 100
    
    # Determinar si el objetivo ya fue alcanzado
    if direccion == 'alcista':
        objetivo_alcanzado = precio_actual >= nivel_objetivo
    else:
        objetivo_alcanzado = precio_actual <= nivel_objetivo
    
    # Calcular zona de pullback (retroceso esperado)
    # Típicamente el pullback retrocede 38-61% del movimiento
    if direccion == 'alcista':
        zona_pullback_min = nivel_objetivo - (altura_patron * 0.38)
        zona_pullback_max = nivel_objetivo - (altura_patron * 0.61)
    else:
        zona_pullback_min = nivel_objetivo + (altura_patron * 0.38)
        zona_pullback_max = nivel_objetivo + (altura_patron * 0.61)
    
    return {
        'calculado': True,
        'patron': nombre_patron,
        'direccion': direccion,
        'punto_maximo': round(punto_maximo, 5),
        'punto_minimo': round(punto_minimo, 5),
        'altura_patron': round(altura_patron, 5),
        'punto_ruptura': round(punto_ruptura, 5),
        'nivel_objetivo': round(nivel_objetivo, 5),
        'distancia_objetivo': round(abs(distancia_objetivo), 5),
        'porcentaje_movimiento': round(porcentaje_movimiento, 2),
        'objetivo_alcanzado': objetivo_alcanzado,
        'zona_pullback': {
            'min': round(zona_pullback_min, 5),
            'max': round(zona_pullback_max, 5),
            'descripcion': 'Zona donde el precio podría retroceder tras alcanzar el objetivo'
        },
        'descripcion': f'Nivel Objetivo: {nivel_objetivo:.5f} ({porcentaje_movimiento:.1f}% de movimiento esperado)',
        'advertencia': '⚠️ Este nivel es una zona de PROBABILIDAD, no certeza. Usar como referencia.'
    }


def analizar_patrones_con_objetivos(df: pd.DataFrame, tendencia_actual: str = None) -> Dict:
    """
    Analiza patrones chartistas y calcula sus niveles objetivo
    
    Returns:
        dict: Patrones detectados con sus niveles objetivo
    """
    # Detectar patrones
    resultado_patrones = detectar_todos_patrones_chartistas(df, tendencia_actual)
    
    # Calcular objetivos para patrones válidos
    objetivos = []
    
    for patron in resultado_patrones.get('detalles_validos', []):
        objetivo = calcular_nivel_objetivo(patron, df)
        if objetivo.get('calculado', False):
            objetivos.append(objetivo)
    
    # Agregar información de objetivos al resultado
    resultado_patrones['niveles_objetivo'] = objetivos
    resultado_patrones['total_objetivos'] = len(objetivos)
    
    return resultado_patrones
