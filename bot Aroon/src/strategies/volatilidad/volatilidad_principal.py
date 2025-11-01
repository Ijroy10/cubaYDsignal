import pandas as pd
import numpy as np
from .bollinger_bands import calcular_bollinger_bands
from .atr_analysis import calcular_atr

def evaluar_volatilidad(df, tendencia_info=None, zonas_sr=None):
    """
    ESTRATEGIA 4: ANÁLISIS COMPLETO DE ACCIÓN DEL PRECIO Y VOLATILIDAD
    Implementa:
    - Análisis de volatilidad (alta, baja, saludable)
    - Evaluación de la "salud" de las velas
    - Detección de pullback (con mechas, S/R, patrones)
    - Cálculo de efectividad
    
    Args:
        df: DataFrame con columnas ['open', 'high', 'low', 'close']
        tendencia_info: Información de tendencia (opcional)
        zonas_sr: Información de soportes/resistencias (opcional)
    
    Returns:
        dict: Resultado con efectividad total y análisis detallado
    """
    try:
        # PASO 1: ANÁLISIS DE VOLATILIDAD
        volatilidad_info = analizar_volatilidad_completa(df)
        
        # PASO 2: ANÁLISIS DE ACCIÓN DEL PRECIO
        accion_precio_info = analizar_accion_precio(df)
        
        # PASO 3: DETECCIÓN DE PULLBACK (mejorado con mechas, S/R, patrones)
        pullback_info = detectar_pullback(df, tendencia_info, zonas_sr)
        
        # PASO 4: CÁLCULO DE EFECTIVIDAD AGREGADA
        efectividad_total = calcular_efectividad_volatilidad(
            volatilidad_info, accion_precio_info, pullback_info
        )
        
        # PASO 5: DETERMINAR DIRECCIÓN
        direccion = determinar_direccion_volatilidad(
            volatilidad_info, accion_precio_info, pullback_info, tendencia_info
        )
        
        return {
            "efectividad": efectividad_total,
            "direccion": direccion,
            "detalles": {
                "volatilidad": volatilidad_info,
                "accion_precio": accion_precio_info,
                "pullback": pullback_info
            }
        }
        
    except Exception as e:
        return {
            "efectividad": 0,
            "direccion": "indefinida",
            "error": str(e)
        }

def clasificar_volatilidad_por_velas(df, ventana=10):
    """
    Clasifica la volatilidad según el tamaño de los cuerpos de las velas y mechas
    
    METODOLOGÍA:
    - Volatilidad Débil: Cuerpos muy pequeños, muchas velas sin cuerpo (doji)
    - Volatilidad Saludable: Cuerpos de tamaño promedio, pocas mechas
    - Volatilidad Fuerte: Movimientos rápidos, cuerpos grandes, muchas mechas
    
    Returns:
        dict: {
            'tipo': 'debil'/'saludable'/'fuerte',
            'descripcion': str,
            'score': 0-100,
            'detalles': {...}
        }
    """
    if len(df) < ventana:
        return {
            'tipo': 'indefinida',
            'descripcion': 'Datos insuficientes',
            'score': 0,
            'detalles': {}
        }
    
    # Analizar últimas velas
    ultimas_velas = df.tail(ventana)
    
    # Métricas para clasificación
    cuerpos = []
    rangos = []
    mechas_superiores = []
    mechas_inferiores = []
    velas_sin_cuerpo = 0  # Doji o velas muy pequeñas
    
    for _, vela in ultimas_velas.iterrows():
        cuerpo = abs(vela['close'] - vela['open'])
        rango_total = vela['high'] - vela['low']
        mecha_superior = vela['high'] - max(vela['open'], vela['close'])
        mecha_inferior = min(vela['open'], vela['close']) - vela['low']
        
        cuerpos.append(cuerpo)
        rangos.append(rango_total)
        mechas_superiores.append(mecha_superior)
        mechas_inferiores.append(mecha_inferior)
        
        # Vela sin cuerpo: cuerpo < 10% del rango
        if rango_total > 0 and cuerpo / rango_total < 0.1:
            velas_sin_cuerpo += 1
    
    # Calcular promedios
    cuerpo_promedio = np.mean(cuerpos)
    rango_promedio = np.mean(rangos)
    mecha_promedio = np.mean(mechas_superiores + mechas_inferiores)
    
    # Calcular ratio cuerpo/rango (indica fuerza de movimiento)
    ratios_cuerpo = [c/r if r > 0 else 0 for c, r in zip(cuerpos, rangos)]
    ratio_promedio = np.mean(ratios_cuerpo)
    
    # Calcular variabilidad (indica si hay movimientos rápidos)
    variabilidad_rangos = np.std(rangos) / rango_promedio if rango_promedio > 0 else 0
    
    # CLASIFICACIÓN SEGÚN METODOLOGÍA
    
    # 1. VOLATILIDAD DÉBIL
    # - Cuerpos muy pequeños (ratio < 0.3)
    # - Muchas velas sin cuerpo (≥40%)
    # - Movimientos muy lentos
    if ratio_promedio < 0.3 or velas_sin_cuerpo >= ventana * 0.4:
        tipo = 'debil'
        descripcion = "Volatilidad DÉBIL: Precio se mueve muy poco, cuerpos pequeños, difícil ver reacciones"
        score = 35  # Evitar operar - engañoso
        recomendacion = "⚠️ Evitar operar - mercado sin movimiento claro"
        emoji = "💤"
    
    # 2. VOLATILIDAD FUERTE
    # - Movimientos rápidos e indecisos (variabilidad alta > 0.5)
    # - Muchas mechas (indica indecisión)
    # - Cuerpos grandes pero inconsistentes
    elif variabilidad_rangos > 0.5 or mecha_promedio > cuerpo_promedio * 1.5:
        tipo = 'fuerte'
        descripcion = "Volatilidad FUERTE: Movimientos rápidos e indecisos, mercado 'sucio' con ruido"
        score = 45  # Cuidado - requiere experiencia
        recomendacion = "⚠️ Mercado volátil - requiere paciencia y experiencia"
        emoji = "🔥"
    
    # 3. VOLATILIDAD SALUDABLE (IDEAL)
    # - Cuerpos de tamaño promedio (ratio 0.4-0.7)
    # - Pocas mechas (movimientos claros)
    # - Movimientos tranquilos y consistentes
    else:
        tipo = 'saludable'
        descripcion = "Volatilidad SALUDABLE: Movimientos claros y seguros, ideal para operar"
        score = 85  # Ideal para trading
        recomendacion = "✅ Condiciones ideales para operar"
        emoji = "✅"
    
    return {
        'tipo': tipo,
        'descripcion': descripcion,
        'score': score,
        'recomendacion': recomendacion,
        'emoji': emoji,
        'detalles': {
            'cuerpo_promedio': round(cuerpo_promedio, 6),
            'rango_promedio': round(rango_promedio, 6),
            'ratio_cuerpo_rango': round(ratio_promedio, 2),
            'velas_sin_cuerpo': velas_sin_cuerpo,
            'porcentaje_sin_cuerpo': round(velas_sin_cuerpo / ventana * 100, 1),
            'mecha_promedio': round(mecha_promedio, 6),
            'variabilidad': round(variabilidad_rangos, 2)
        }
    }


def analizar_volatilidad_completa(df, periodo=20):
    """
    Análisis completo de volatilidad usando:
    1. Clasificación por velas (Débil/Saludable/Fuerte) - NUEVO
    2. Bollinger Bands
    3. ATR
    """
    df_copy = df.copy()
    
    # 1. CLASIFICACIÓN POR VELAS (METODOLOGÍA NUEVA)
    clasificacion_velas = clasificar_volatilidad_por_velas(df_copy, ventana=10)
    
    # 2. Calcular indicadores técnicos
    bollinger_df = calcular_bollinger_bands(df_copy, periodo)
    df_copy['media'] = bollinger_df['bollinger_mid']
    df_copy['banda_superior'] = bollinger_df['bollinger_upper']
    df_copy['banda_inferior'] = bollinger_df['bollinger_lower']
    df_copy['atr'] = calcular_atr(df_copy, periodo)
    
    # Datos actuales
    precio_actual = df_copy['close'].iloc[-1]
    banda_sup = df_copy['banda_superior'].iloc[-1]
    banda_inf = df_copy['banda_inferior'].iloc[-1]
    media = df_copy['media'].iloc[-1]
    atr_actual = df_copy['atr'].iloc[-1]
    atr_promedio = df_copy['atr'].tail(10).mean()
    
    # Calcular ancho de bandas (volatilidad)
    ancho_bandas = (banda_sup - banda_inf) / media
    ancho_promedio = df_copy.apply(lambda x: (x['banda_superior'] - x['banda_inferior']) / x['media'], axis=1).tail(20).mean()
    
    # USAR CLASIFICACIÓN POR VELAS COMO PRINCIPAL
    estado_volatilidad = clasificacion_velas['tipo']
    descripcion = clasificacion_velas['descripcion']
    score_volatilidad = clasificacion_velas['score']
    
    # ANÁLISIS ATR
    if atr_actual > atr_promedio * 1.5:
        atr_estado = "muy_alta"
        atr_descripcion = "ATR muy alto, movimiento fuerte en curso"
    elif atr_actual > atr_promedio * 1.2:
        atr_estado = "alta"
        atr_descripcion = "ATR alto, buena energía en el mercado"
    elif atr_actual < atr_promedio * 0.8:
        atr_estado = "baja"
        atr_descripcion = "ATR bajo, mercado consolidando"
    else:
        atr_estado = "normal"
        atr_descripcion = "ATR normal"
    
    # POSICIÓN EN BANDAS
    if precio_actual > banda_sup:
        posicion_bandas = "fuera_superior"
        banda_descripcion = "Precio fuera de banda superior"
    elif precio_actual < banda_inf:
        posicion_bandas = "fuera_inferior"
        banda_descripcion = "Precio fuera de banda inferior"
    elif precio_actual > media:
        posicion_bandas = "superior"
        banda_descripcion = "Precio en zona superior"
    else:
        posicion_bandas = "inferior"
        banda_descripcion = "Precio en zona inferior"
    
    return {
        "estado": estado_volatilidad,
        "descripcion": descripcion,
        "score": score_volatilidad,
        "clasificacion_velas": clasificacion_velas,  # NUEVO
        "atr_estado": atr_estado,
        "atr_descripcion": atr_descripcion,
        "posicion_bandas": posicion_bandas,
        "banda_descripcion": banda_descripcion,
        "ancho_bandas": ancho_bandas,
        "atr_actual": atr_actual,
        "atr_promedio": atr_promedio
    }

def analizar_accion_precio(df):
    """
    Análisis de la acción del precio: evalúa la "salud" de las velas
    """
    if len(df) < 5:
        return {"estado": "datos_insuficientes", "score": 0}
    
    # Analizar las últimas 5 velas
    ultimas_velas = df.tail(5)
    
    velas_info = []
    for i, (idx, vela) in enumerate(ultimas_velas.iterrows()):
        cuerpo = abs(vela['close'] - vela['open'])
        rango_total = vela['high'] - vela['low']
        
        if rango_total == 0:
            continue
            
        # Calcular volatilidad de la vela (rango)
        volatilidad_vela = rango_total
        
        # Clasificar vela por tamaño
        if rango_total > df['high'].tail(20).subtract(df['low'].tail(20)).mean() * 1.5:
            tamano = "grande"  # Vela fuerte
            fuerza = 3
        elif rango_total < df['high'].tail(20).subtract(df['low'].tail(20)).mean() * 0.5:
            tamano = "pequeña"  # Vela débil
            fuerza = 1
        else:
            tamano = "normal"
            fuerza = 2
        
        # Dirección de la vela
        direccion = "alcista" if vela['close'] > vela['open'] else "bajista"
        
        velas_info.append({
            "posicion": i,
            "tamano": tamano,
            "fuerza": fuerza,
            "direccion": direccion,
            "volatilidad": volatilidad_vela,
            "cuerpo_ratio": cuerpo / rango_total if rango_total > 0 else 0
        })
    
    # EVALUAR SALUD GENERAL
    if not velas_info:
        return {"estado": "error", "score": 0}
    
    fuerza_promedio = sum(v['fuerza'] for v in velas_info) / len(velas_info)
    velas_fuertes = len([v for v in velas_info if v['fuerza'] >= 2])
    velas_debiles = len([v for v in velas_info if v['fuerza'] == 1])
    
    # CLASIFICAR SALUD DEL MERCADO
    if fuerza_promedio >= 2.5 and velas_fuertes >= 3:
        estado_salud = "muy_saludable"
        descripcion = "Mercado con energía, velas fuertes"
        score_salud = 90
    elif fuerza_promedio >= 2.0 and velas_fuertes >= 2:
        estado_salud = "saludable"
        descripcion = "Mercado con buena energía"
        score_salud = 75
    elif velas_debiles >= 3:
        estado_salud = "debil"
        descripcion = "Mercado sin energía, evitar operar"
        score_salud = 30
    else:
        estado_salud = "normal"
        descripcion = "Mercado en estado normal"
        score_salud = 60
    
    return {
        "estado": estado_salud,
        "descripcion": descripcion,
        "score": score_salud,
        "fuerza_promedio": fuerza_promedio,
        "velas_fuertes": velas_fuertes,
        "velas_debiles": velas_debiles,
        "velas_info": velas_info
    }

def detectar_pullback(df, tendencia_info=None, zonas_sr=None):
    """
    Detecta si el mercado está haciendo pullback (retroceso temporal)
    
    Pullback = Retroceso temporal del precio dentro de una tendencia:
    - Tendencia alcista: precio sube → retrocede (baja) → sigue subiendo
    - Tendencia bajista: precio baja → retrocede (sube) → sigue bajando
    
    Detecta:
    1. Tendencia clara
    2. Retroceso temporal
    3. Confirmación de finalización (vela de rechazo, mechas, S/R, patrón)
    4. Diferencia pullback de reversión
    """
    if len(df) < 10 or not tendencia_info:
        return {"detectado": False, "score": 0}
    
    # PASO 1: VERIFICAR TENDENCIA CLARA
    tendencia_principal = tendencia_info.get('direccion', 'indefinida')
    efectividad_tendencia = tendencia_info.get('efectividad', 0)
    
    if tendencia_principal == 'indefinida' or efectividad_tendencia < 60:
        return {"detectado": False, "score": 0, "motivo": "Sin tendencia clara"}
    
    # PASO 2: ANALIZAR RETROCESO
    precio_actual = df.iloc[-1]['close']
    precio_hace_5 = df.iloc[-6]['close'] if len(df) >= 6 else df.iloc[0]['close']
    precio_hace_10 = df.iloc[-11]['close'] if len(df) >= 11 else df.iloc[0]['close']
    
    # Calcular movimientos
    movimiento_total = (precio_actual - precio_hace_10) / precio_hace_10  # Tendencia general
    movimiento_reciente = (precio_actual - precio_hace_5) / precio_hace_5  # Retroceso reciente
    
    pullback_detectado = False
    tipo_pullback = None
    fuerza_pullback = 0
    descripcion = ""
    
    # DETECTAR PULLBACK EN TENDENCIA ALCISTA
    if tendencia_principal == 'alcista':
        # Pullback: precio sube (tendencia) pero retrocede (baja) temporalmente
        if movimiento_total > 0.01 and movimiento_reciente < -0.003:  # Retroceso mínimo 0.3%
            pullback_detectado = True
            tipo_pullback = "pullback_alcista"
            fuerza_pullback = abs(movimiento_reciente) * 100
            descripcion = "Pullback en tendencia alcista: precio retrocedió, esperando continuación"
    
    # DETECTAR PULLBACK EN TENDENCIA BAJISTA
    elif tendencia_principal == 'bajista':
        # Pullback: precio baja (tendencia) pero retrocede (sube) temporalmente
        if movimiento_total < -0.01 and movimiento_reciente > 0.003:  # Retroceso mínimo 0.3%
            pullback_detectado = True
            tipo_pullback = "pullback_bajista"
            fuerza_pullback = abs(movimiento_reciente) * 100
            descripcion = "Pullback en tendencia bajista: precio retrocedió, esperando continuación"
    
    if not pullback_detectado:
        return {"detectado": False, "score": 0}
    
    # PASO 3: BUSCAR CONFIRMACIÓN DE FINALIZACIÓN
    confirmaciones = []
    score_confirmacion = 0
    
    ultima_vela = df.iloc[-1]
    penultima_vela = df.iloc[-2] if len(df) >= 2 else ultima_vela
    
    # 3.1 VELA DE RECHAZO (confirmación más importante)
    vela_rechazo = detectar_vela_rechazo(ultima_vela, tipo_pullback)
    if vela_rechazo:
        confirmaciones.append("vela_rechazo")
        score_confirmacion += 30
    
    # 3.2 MECHAS (indican rechazo del precio)
    mecha_rechazo = detectar_mecha_rechazo(ultima_vela, penultima_vela, tipo_pullback)
    if mecha_rechazo:
        confirmaciones.append("mecha_rechazo")
        score_confirmacion += 25
    
    # 3.3 ZONA S/R (pullback cerca de soporte/resistencia)
    if zonas_sr:
        zona_sr_confirmacion = verificar_pullback_en_zona_sr(df, zonas_sr, tipo_pullback)
        if zona_sr_confirmacion:
            confirmaciones.append("zona_sr")
            score_confirmacion += 20
    
    # 3.4 PATRÓN DE VELA (martillo, pinbar, etc.)
    patron_confirmacion = detectar_patron_pullback(ultima_vela, penultima_vela, tipo_pullback)
    if patron_confirmacion:
        confirmaciones.append(f"patron_{patron_confirmacion}")
        score_confirmacion += 15
    
    # 3.5 VELA A FAVOR DE TENDENCIA
    vela_continuacion = False
    if tipo_pullback == "pullback_alcista":
        # Vela alcista fuerte después del retroceso
        if (ultima_vela['close'] > ultima_vela['open'] and 
            ultima_vela['close'] > penultima_vela['close']):
            vela_continuacion = True
            confirmaciones.append("vela_alcista")
            score_confirmacion += 10
    elif tipo_pullback == "pullback_bajista":
        # Vela bajista fuerte después del retroceso
        if (ultima_vela['close'] < ultima_vela['open'] and 
            ultima_vela['close'] < penultima_vela['close']):
            vela_continuacion = True
            confirmaciones.append("vela_bajista")
            score_confirmacion += 10
    
    # PASO 4: DIFERENCIAR PULLBACK DE REVERSIÓN
    es_posible_reversion = detectar_posible_reversion(df, tendencia_info, movimiento_reciente)
    if es_posible_reversion:
        score_confirmacion -= 30  # Penalización si parece reversión
        confirmaciones.append("⚠️_posible_reversion")
    
    # CALCULAR SCORE FINAL
    score_base = 40
    score_pullback = score_base + score_confirmacion
    score_pullback += min(fuerza_pullback * 5, 10)  # Bonus por fuerza del retroceso
    
    # Requiere al menos 2 confirmaciones para score alto
    confirmaciones_validas = [c for c in confirmaciones if not c.startswith("⚠️")]
    if len(confirmaciones_validas) < 2:
        score_pullback = min(score_pullback, 60)  # Limitar score si pocas confirmaciones
    
    return {
        "detectado": True,
        "tipo": tipo_pullback,
        "fuerza": fuerza_pullback,
        "score": max(0, min(score_pullback, 100)),
        "descripcion": descripcion,
        "confirmaciones": confirmaciones,
        "num_confirmaciones": len(confirmaciones_validas),
        "es_posible_reversion": es_posible_reversion
    }

def detectar_vela_rechazo(vela, tipo_pullback):
    """
    Detecta vela de rechazo: vela que rechaza el retroceso y vuelve a la tendencia
    """
    cuerpo = abs(vela['close'] - vela['open'])
    rango_total = vela['high'] - vela['low']
    
    if rango_total == 0:
        return False
    
    if tipo_pullback == "pullback_alcista":
        # Vela alcista con cuerpo fuerte (>50% del rango)
        if vela['close'] > vela['open'] and cuerpo / rango_total > 0.5:
            return True
    
    elif tipo_pullback == "pullback_bajista":
        # Vela bajista con cuerpo fuerte (>50% del rango)
        if vela['close'] < vela['open'] and cuerpo / rango_total > 0.5:
            return True
    
    return False

def detectar_mecha_rechazo(vela, vela_anterior, tipo_pullback):
    """
    Detecta mechas que indican rechazo del precio
    Las mechas muestran que el precio intentó ir en una dirección pero fue rechazado
    """
    cuerpo = abs(vela['close'] - vela['open'])
    rango_total = vela['high'] - vela['low']
    sombra_superior = vela['high'] - max(vela['open'], vela['close'])
    sombra_inferior = min(vela['open'], vela['close']) - vela['low']
    
    if rango_total == 0 or cuerpo == 0:
        return False
    
    if tipo_pullback == "pullback_alcista":
        # Mecha inferior larga indica rechazo de precios bajos (quiere subir)
        if sombra_inferior > cuerpo * 1.5 and sombra_inferior > sombra_superior:
            return True
    
    elif tipo_pullback == "pullback_bajista":
        # Mecha superior larga indica rechazo de precios altos (quiere bajar)
        if sombra_superior > cuerpo * 1.5 and sombra_superior > sombra_inferior:
            return True
    
    return False

def verificar_pullback_en_zona_sr(df, zonas_sr, tipo_pullback):
    """
    Verifica si el pullback está ocurriendo cerca de una zona S/R
    Esto aumenta la probabilidad de que sea un pullback válido
    """
    precio_actual = df.iloc[-1]['close']
    tolerancia = 0.005  # 0.5%
    
    if tipo_pullback == "pullback_alcista":
        # Buscar soporte cercano (precio debería rebotar en soporte)
        zonas_soporte = zonas_sr.get('detalles', {}).get('zonas_soporte', [])
        for soporte in zonas_soporte:
            precio_soporte = soporte.get('precio_medio', 0)
            if abs(precio_actual - precio_soporte) / precio_actual <= tolerancia:
                return True
    
    elif tipo_pullback == "pullback_bajista":
        # Buscar resistencia cercana (precio debería rebotar en resistencia)
        zonas_resistencia = zonas_sr.get('detalles', {}).get('zonas_resistencia', [])
        for resistencia in zonas_resistencia:
            precio_resistencia = resistencia.get('precio_medio', 0)
            if abs(precio_actual - precio_resistencia) / precio_actual <= tolerancia:
                return True
    
    return False

def detectar_patron_pullback(vela, vela_anterior, tipo_pullback):
    """
    Detecta patrones de velas comunes en pullbacks
    """
    cuerpo = abs(vela['close'] - vela['open'])
    rango_total = vela['high'] - vela['low']
    sombra_inferior = min(vela['open'], vela['close']) - vela['low']
    sombra_superior = vela['high'] - max(vela['open'], vela['close'])
    
    if rango_total == 0:
        return None
    
    if tipo_pullback == "pullback_alcista":
        # Martillo: cuerpo pequeño arriba, mecha larga abajo
        if (cuerpo / rango_total <= 0.3 and 
            sombra_inferior >= 2 * cuerpo and 
            sombra_superior <= cuerpo):
            return "martillo"
        
        # Pinbar alcista
        if sombra_inferior > cuerpo * 2:
            return "pinbar_alcista"
    
    elif tipo_pullback == "pullback_bajista":
        # Estrella fugaz: cuerpo pequeño abajo, mecha larga arriba
        if (cuerpo / rango_total <= 0.3 and 
            sombra_superior >= 2 * cuerpo and 
            sombra_inferior <= cuerpo):
            return "estrella_fugaz"
        
        # Pinbar bajista
        if sombra_superior > cuerpo * 2:
            return "pinbar_bajista"
    
    return None

def detectar_posible_reversion(df, tendencia_info, movimiento_reciente):
    """
    Detecta si el 'pullback' podría ser en realidad una reversión de tendencia
    
    Diferencias:
    - Pullback: retroceso pequeño (< 2%), luego continúa
    - Reversión: retroceso grande (> 3%), cambia dirección
    """
    # Si el retroceso es muy grande, podría ser reversión
    if abs(movimiento_reciente) > 0.03:  # > 3%
        return True
    
    # Si la tendencia está perdiendo fuerza
    efectividad_tendencia = tendencia_info.get('efectividad', 0)
    if efectividad_tendencia < 65:
        return True
    
    # Analizar últimas 3 velas: si todas van contra la tendencia, posible reversión
    ultimas_3 = df.tail(3)
    tendencia_principal = tendencia_info.get('direccion')
    
    velas_contra_tendencia = 0
    for _, vela in ultimas_3.iterrows():
        if tendencia_principal == 'alcista' and vela['close'] < vela['open']:
            velas_contra_tendencia += 1
        elif tendencia_principal == 'bajista' and vela['close'] > vela['open']:
            velas_contra_tendencia += 1
    
    if velas_contra_tendencia >= 3:  # Todas las velas contra tendencia
        return True
    
    return False

def calcular_efectividad_volatilidad(volatilidad_info, accion_precio_info, pullback_info):
    """
    Calcula efectividad agregada de la estrategia de volatilidad
    """
    # Pesos para cada componente
    peso_volatilidad = 0.4
    peso_accion_precio = 0.4
    peso_pullback = 0.2
    
    efectividad_total = (
        volatilidad_info['score'] * peso_volatilidad +
        accion_precio_info['score'] * peso_accion_precio +
        pullback_info['score'] * peso_pullback
    )
    
    return min(efectividad_total, 100)

def determinar_direccion_volatilidad(volatilidad_info, accion_precio_info, pullback_info, tendencia_info):
    """
    Determina dirección basada en análisis de volatilidad y pullback
    """
    # Si hay pullback confirmado, seguir la tendencia principal
    if pullback_info['detectado'] and pullback_info.get('confirmacion', False):
        if pullback_info['tipo'] == 'pullback_alcista':
            return 'alcista'
        elif pullback_info['tipo'] == 'pullback_bajista':
            return 'bajista'
    
    # Si no hay pullback, evaluar basado en volatilidad y acción del precio
    if (volatilidad_info['estado'] == 'saludable' and 
        accion_precio_info['estado'] in ['saludable', 'muy_saludable']):
        
        # Usar tendencia principal si está disponible
        if tendencia_info and tendencia_info.get('direccion') in ['alcista', 'bajista']:
            return tendencia_info['direccion']
    
    return 'indefinida'

# Mantener función original para compatibilidad
def analizar_volatilidad(df, periodo=20):
    """Función original mantenida para compatibilidad"""
    result = evaluar_volatilidad(df)
    return {
        'bollinger': result['detalles']['volatilidad']['posicion_bandas'],
        'atr': result['detalles']['volatilidad']['atr_estado']
    }