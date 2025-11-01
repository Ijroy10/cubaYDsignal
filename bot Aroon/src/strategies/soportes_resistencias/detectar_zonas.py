import pandas as pd
from datetime import datetime, timedelta

def detectar_zonas_sr(df):
    """
    ESTRATEGIA 2: ANÁLISIS COMPLETO DE SOPORTES Y RESISTENCIAS
    
    METODOLOGÍA MEJORADA:
    - Soportes y resistencias son ZONAS, no líneas
    - Niveles débiles: 1 toque
    - Niveles normales: 2 toques
    - Niveles fuertes/Key Levels: 3+ toques o cambio de polaridad
    - Cambios de polaridad (FLIP): Resistencia → Soporte o viceversa
    - Niveles dinámicos (inclinados): Confirmados con 2+ testeos
    - Rompimientos falsos detectados
    
    Args:
        df: DataFrame con columnas ['time', 'open', 'high', 'low', 'close']
    
    Returns:
        dict: Resultado con efectividad y zonas detectadas
    """
    try:
        # Detectar puntos de soporte y resistencia
        soportes_raw, resistencias_raw = detectar_puntos_sr(df, ventana=3)
        
        # Agrupar y validar zonas según criterios
        zonas_soporte = validar_zonas_sr(soportes_raw, df, tipo='soporte')
        zonas_resistencia = validar_zonas_sr(resistencias_raw, df, tipo='resistencia')
        
        # NUEVO: Detectar cambios de polaridad (FLIP)
        flips = detectar_cambio_polaridad(zonas_soporte, zonas_resistencia, df)
        
        # NUEVO: Detectar niveles dinámicos (inclinados)
        niveles_dinamicos = detectar_niveles_dinamicos(df, ventana=20)
        
        # Calcular efectividad total (incluyendo flips)
        efectividad = calcular_efectividad_sr(zonas_soporte, zonas_resistencia, df, flips)
        
        # Determinar dirección predominante
        direccion = determinar_direccion_sr(zonas_soporte, zonas_resistencia, df)
        
        return {
            "efectividad": efectividad,
            "direccion": direccion,
            "detalles": {
                "zonas_soporte": zonas_soporte,
                "zonas_resistencia": zonas_resistencia,
                "cambios_polaridad": flips,
                "niveles_dinamicos": niveles_dinamicos,
                "soporte_mas_fuerte": get_zona_mas_fuerte(zonas_soporte),
                "resistencia_mas_fuerte": get_zona_mas_fuerte(zonas_resistencia),
                "total_key_levels": sum(1 for z in zonas_soporte + zonas_resistencia if z.get('es_key_level', False)),
                "total_flips": len(flips)
            }
        }
        
    except Exception as e:
        return {
            "efectividad": 0,
            "direccion": "indefinida",
            "error": str(e)
        }

def detectar_puntos_sr(df, ventana=3):
    """
    Detecta puntos potenciales de soporte y resistencia
    """
    soportes = []
    resistencias = []
    
    for i in range(ventana, len(df) - ventana):
        rango_ventana = df.iloc[i - ventana : i + ventana + 1]
        
        precio_max = df.iloc[i]['high']
        precio_min = df.iloc[i]['low']
        time_actual = df.iloc[i].get('time', i)
        
        # Resistencia = máximo local
        if precio_max == rango_ventana['high'].max():
            resistencias.append({
                'time': time_actual,
                'precio': precio_max,
                'indice': i
            })
        
        # Soporte = mínimo local
        if precio_min == rango_ventana['low'].min():
            soportes.append({
                'time': time_actual,
                'precio': precio_min,
                'indice': i
            })
    
    return soportes, resistencias

def detectar_cambio_polaridad(zonas_soporte, zonas_resistencia, df):
    """
    Detecta cambios de polaridad (FLIP):
    - Resistencia rota que pasa a ser soporte
    - Soporte roto que pasa a ser resistencia
    
    Un FLIP es un nivel clave muy fuerte.
    """
    flips = []
    precio_actual = df.iloc[-1]['close']
    
    # Buscar resistencias rotas que ahora son soportes
    for resistencia in zonas_resistencia:
        precio_zona = resistencia['precio_medio']
        
        # Si el precio actual está por encima de la antigua resistencia
        if precio_actual > precio_zona:
            # Verificar si el precio ha vuelto a testear la zona desde arriba
            testeos_desde_arriba = 0
            for i in range(resistencia['indice_ultimo'] + 1, len(df)):
                if df.iloc[i]['low'] <= precio_zona * 1.005 and df.iloc[i]['low'] >= precio_zona * 0.995:
                    testeos_desde_arriba += 1
            
            if testeos_desde_arriba > 0:
                flips.append({
                    'precio': precio_zona,
                    'tipo_original': 'resistencia',
                    'tipo_actual': 'soporte',
                    'testeos_flip': testeos_desde_arriba,
                    'es_flip': True,
                    'fuerza_flip': 'muy_fuerte'  # Los flips son niveles clave
                })
    
    # Buscar soportes rotos que ahora son resistencias
    for soporte in zonas_soporte:
        precio_zona = soporte['precio_medio']
        
        # Si el precio actual está por debajo del antiguo soporte
        if precio_actual < precio_zona:
            # Verificar si el precio ha vuelto a testear la zona desde abajo
            testeos_desde_abajo = 0
            for i in range(soporte['indice_ultimo'] + 1, len(df)):
                if df.iloc[i]['high'] >= precio_zona * 0.995 and df.iloc[i]['high'] <= precio_zona * 1.005:
                    testeos_desde_abajo += 1
            
            if testeos_desde_abajo > 0:
                flips.append({
                    'precio': precio_zona,
                    'tipo_original': 'soporte',
                    'tipo_actual': 'resistencia',
                    'testeos_flip': testeos_desde_abajo,
                    'es_flip': True,
                    'fuerza_flip': 'muy_fuerte'
                })
    
    return flips


def detectar_niveles_dinamicos(df, ventana=20):
    """
    Detecta soportes y resistencias dinámicos (inclinados)
    
    IMPORTANTE:
    - Se identifican a partir del segundo testeo
    - Solo se pueden confiar UNA VEZ
    - Después de rotos, probabilidad de respeto es muy escasa
    """
    niveles_dinamicos = []
    
    if len(df) < ventana:
        return niveles_dinamicos
    
    # Buscar líneas de tendencia alcistas (soporte dinámico)
    minimos = []
    for i in range(1, len(df) - 1):
        if df.iloc[i]['low'] < df.iloc[i-1]['low'] and df.iloc[i]['low'] < df.iloc[i+1]['low']:
            minimos.append({'indice': i, 'precio': df.iloc[i]['low']})
    
    # Conectar mínimos para formar líneas de tendencia
    if len(minimos) >= 2:
        for i in range(len(minimos) - 1):
            p1 = minimos[i]
            p2 = minimos[i + 1]
            
            # Calcular pendiente
            pendiente = (p2['precio'] - p1['precio']) / (p2['indice'] - p1['indice'])
            
            # Solo líneas ascendentes (soporte dinámico)
            if pendiente > 0:
                # Contar testeos adicionales
                testeos = 2  # Los dos puntos iniciales
                for j in range(i + 2, len(minimos)):
                    p_test = minimos[j]
                    precio_esperado = p1['precio'] + pendiente * (p_test['indice'] - p1['indice'])
                    
                    # Si está cerca de la línea
                    if abs(p_test['precio'] - precio_esperado) / precio_esperado < 0.01:
                        testeos += 1
                
                if testeos >= 2:  # Confirmado con al menos 2 testeos
                    niveles_dinamicos.append({
                        'tipo': 'soporte_dinamico',
                        'punto_inicio': p1,
                        'punto_fin': p2,
                        'pendiente': pendiente,
                        'testeos': testeos,
                        'confirmado': testeos >= 2,
                        'confianza': 'una_vez',  # Solo confiar una vez
                        'advertencia': 'Después de roto, probabilidad de respeto muy escasa'
                    })
    
    # Buscar líneas de tendencia bajistas (resistencia dinámica)
    maximos = []
    for i in range(1, len(df) - 1):
        if df.iloc[i]['high'] > df.iloc[i-1]['high'] and df.iloc[i]['high'] > df.iloc[i+1]['high']:
            maximos.append({'indice': i, 'precio': df.iloc[i]['high']})
    
    if len(maximos) >= 2:
        for i in range(len(maximos) - 1):
            p1 = maximos[i]
            p2 = maximos[i + 1]
            
            pendiente = (p2['precio'] - p1['precio']) / (p2['indice'] - p1['indice'])
            
            # Solo líneas descendentes (resistencia dinámica)
            if pendiente < 0:
                testeos = 2
                for j in range(i + 2, len(maximos)):
                    p_test = maximos[j]
                    precio_esperado = p1['precio'] + pendiente * (p_test['indice'] - p1['indice'])
                    
                    if abs(p_test['precio'] - precio_esperado) / abs(precio_esperado) < 0.01:
                        testeos += 1
                
                if testeos >= 2:
                    niveles_dinamicos.append({
                        'tipo': 'resistencia_dinamica',
                        'punto_inicio': p1,
                        'punto_fin': p2,
                        'pendiente': pendiente,
                        'testeos': testeos,
                        'confirmado': testeos >= 2,
                        'confianza': 'una_vez',
                        'advertencia': 'Después de roto, probabilidad de respeto muy escasa'
                    })
    
    return niveles_dinamicos


def validar_zonas_sr(puntos, df, tipo='soporte', delta=0.005):
    """
    Valida zonas según los criterios:
    - Mínimo 2-3 toques
    - Recencia de toques
    - Fuerza de zona (3+ toques = key level)
    - Cambios de polaridad (FLIP)
    - Zonas (no líneas)
    """
    if not puntos:
        return []
    
    zonas = []
    precio_actual = df.iloc[-1]['close']
    tiempo_actual = df.iloc[-1].get('time', len(df)-1)
    
    # Agrupar puntos cercanos
    for punto in puntos:
        zona_encontrada = False
        
        for zona in zonas:
            if abs(zona['precio_medio'] - punto['precio']) <= delta:
                zona['toques'] += 1
                zona['puntos'].append(punto)
                
                # Actualizar precio medio
                zona['precio_medio'] = sum(p['precio'] for p in zona['puntos']) / len(zona['puntos'])
                
                # Actualizar tiempo más reciente
                if punto['time'] > zona['ultimo_toque']:
                    zona['ultimo_toque'] = punto['time']
                    zona['indice_ultimo'] = punto['indice']
                
                zona_encontrada = True
                break
        
        if not zona_encontrada:
            zonas.append({
                'precio_medio': punto['precio'],
                'toques': 1,
                'puntos': [punto],
                'ultimo_toque': punto['time'],
                'indice_ultimo': punto['indice'],
                'tipo': tipo
            })
    
    # VALIDAR SEGÚN CRITERIOS DEL USUARIO
    zonas_validas = []
    for zona in zonas:
        # Criterio 1: Mínimo 2-3 toques
        if zona['toques'] < 2:
            continue
        
        # Criterio 2: Calcular recencia (más reciente = mejor)
        velas_desde_ultimo = len(df) - 1 - zona['indice_ultimo']
        recencia_score = max(0, 100 - (velas_desde_ultimo * 2))  # Penalizar por antigüedad
        
        # Criterio 3: Identificar niveles según fuerza
        # - Débil: 1 toque (no válido)
        # - Normal: 2 toques
        # - Fuerte/Key Level: 3+ toques o cambio de polaridad
        if zona['toques'] == 1:
            fuerza_nivel = 'debil'
            es_key_level = False
        elif zona['toques'] == 2:
            fuerza_nivel = 'normal'
            es_key_level = False
        else:  # 3+ toques
            fuerza_nivel = 'fuerte'
            es_key_level = True
        
        # Criterio 4: Proximidad al precio actual
        distancia_precio = abs(zona['precio_medio'] - precio_actual) / precio_actual
        proximidad_score = max(0, 100 - (distancia_precio * 1000))  # Penalizar por distancia
        
        # Calcular efectividad de la zona
        efectividad_zona = calcular_efectividad_zona(
            zona['toques'], recencia_score, proximidad_score, es_key_level
        )
        
        zona.update({
            'recencia_score': recencia_score,
            'proximidad_score': proximidad_score,
            'es_key_level': es_key_level,
            'fuerza_nivel': fuerza_nivel,
            'efectividad': efectividad_zona,
            'velas_desde_ultimo': velas_desde_ultimo,
            'es_zona': True,  # S/R son zonas, no líneas
            'rango_zona': zona['precio_medio'] * delta  # Ancho de la zona
        })
        
        zonas_validas.append(zona)
    
    # Ordenar por efectividad (mejores primero)
    zonas_validas.sort(key=lambda x: x['efectividad'], reverse=True)
    
    return zonas_validas

def calcular_efectividad_zona(toques, recencia, proximidad, es_key_level):
    """
    Calcula la efectividad de una zona individual
    """
    # Peso base por número de toques
    base_score = min(toques * 20, 60)  # Máximo 60 por toques
    
    # Bonus por key level (3+ toques)
    key_level_bonus = 20 if es_key_level else 0
    
    # Factores de recencia y proximidad
    recencia_factor = recencia * 0.15  # Máximo 15 puntos
    proximidad_factor = proximidad * 0.25  # Máximo 25 puntos
    
    efectividad = base_score + key_level_bonus + recencia_factor + proximidad_factor
    
    return min(efectividad, 100)

def calcular_efectividad_sr(zonas_soporte, zonas_resistencia, df, flips=[]):
    """
    Calcula la efectividad total de la estrategia de S/R
    Incluye bonus por cambios de polaridad (FLIP)
    """
    if not zonas_soporte and not zonas_resistencia and not flips:
        return 0
    
    # Obtener las mejores zonas
    mejor_soporte = zonas_soporte[0] if zonas_soporte else None
    mejor_resistencia = zonas_resistencia[0] if zonas_resistencia else None
    
    efectividad_total = 0
    
    # Evaluar soporte más fuerte
    if mejor_soporte:
        efectividad_total += mejor_soporte['efectividad'] * 0.4
    
    # Evaluar resistencia más fuerte
    if mejor_resistencia:
        efectividad_total += mejor_resistencia['efectividad'] * 0.4
    
    # Bonus por tener ambos tipos de zonas
    if mejor_soporte and mejor_resistencia:
        efectividad_total += 10
    
    # NUEVO: Bonus por cambios de polaridad (FLIP)
    # Los FLIPs son niveles clave muy fuertes
    if flips:
        bonus_flip = min(len(flips) * 15, 30)  # Máximo 30 puntos
        efectividad_total += bonus_flip
    
    return min(efectividad_total, 100)

def determinar_direccion_sr(zonas_soporte, zonas_resistencia, df):
    """
    Determina dirección basada en proximidad a zonas S/R
    """
    precio_actual = df.iloc[-1]['close']
    
    mejor_soporte = zonas_soporte[0] if zonas_soporte else None
    mejor_resistencia = zonas_resistencia[0] if zonas_resistencia else None
    
    if not mejor_soporte and not mejor_resistencia:
        return 'indefinida'
    
    # Calcular distancias
    dist_soporte = float('inf')
    dist_resistencia = float('inf')
    
    if mejor_soporte:
        dist_soporte = abs(precio_actual - mejor_soporte['precio_medio'])
    
    if mejor_resistencia:
        dist_resistencia = abs(precio_actual - mejor_resistencia['precio_medio'])
    
    # Dirección basada en zona más cercana y fuerte
    if dist_soporte < dist_resistencia:
        return 'alcista' if mejor_soporte['efectividad'] > 70 else 'indefinida'
    else:
        return 'bajista' if mejor_resistencia['efectividad'] > 70 else 'indefinida'

def get_zona_mas_fuerte(zonas):
    """
    Obtiene la zona más fuerte de una lista
    """
    if not zonas:
        return None
    
    return {
        'precio': zonas[0]['precio_medio'],
        'toques': zonas[0]['toques'],
        'efectividad': zonas[0]['efectividad'],
        'es_key_level': zonas[0]['es_key_level'],
        'velas_desde_ultimo': zonas[0]['velas_desde_ultimo']
    }
