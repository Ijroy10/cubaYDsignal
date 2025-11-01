import pandas as pd
import pandas_ta as ta
import importlib
import os
from typing import Dict, List, Any

def detectar_patrones(df, tendencia_info=None, zonas_sr=None):
    """
    ESTRATEGIA 3: ANÁLISIS COMPLETO DE PATRONES DE VELAS
    Detecta TODOS los patrones personalizados (33+ patrones) y los evalúa en contexto:
    - Patrones de continuidad, reversión, indecisión, especiales, rupturas
    - Evaluación contextual con tendencia y zonas S/R
    - Cálculo de efectividad por patrón y agregada
    
    Args:
        df: DataFrame con columnas ['open', 'high', 'low', 'close']
        tendencia_info: Información de tendencia (opcional)
        zonas_sr: Información de soportes/resistencias (opcional)
    
    Returns:
        dict: Resultado con efectividad total y patrones detectados
    """
    try:
        # Validar datos de entrada
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            raise ValueError("El DataFrame debe contener las columnas: 'open', 'high', 'low', 'close'")
        
        if len(df) < 10:
            return {"efectividad": 0, "direccion": "indefinida", "error": "Datos insuficientes"}
        
        # DETECTAR TODOS LOS PATRONES PERSONALIZADOS
        patrones_detectados = detectar_todos_los_patrones(df)
        
        # EVALUAR PATRONES EN CONTEXTO
        patrones_contextuales = evaluar_patrones_en_contexto(
            patrones_detectados, df, tendencia_info, zonas_sr
        )
        
        # CALCULAR EFECTIVIDAD AGREGADA
        efectividad_total = calcular_efectividad_patrones(patrones_contextuales)
        
        # DETERMINAR DIRECCIÓN PREDOMINANTE
        direccion = determinar_direccion_patrones(patrones_contextuales)
        
        return {
            "efectividad": efectividad_total,
            "direccion": direccion,
            "detalles": {
                "patrones_detectados": len(patrones_detectados),
                "patrones_validos": len([p for p in patrones_contextuales if p['efectividad'] > 60]),
                "mejor_patron": get_mejor_patron(patrones_contextuales),
                "patrones_alcistas": len([p for p in patrones_contextuales if p['direccion'] == 'alcista']),
                "patrones_bajistas": len([p for p in patrones_contextuales if p['direccion'] == 'bajista'])
            }
        }
        
    except Exception as e:
        return {
            "efectividad": 0,
            "direccion": "indefinida",
            "error": str(e)
        }

def detectar_todos_los_patrones(df):
    """
    Detecta todos los patrones personalizados disponibles
    """
    patrones_detectados = []
    
    # PATRONES BÁSICOS CON PANDAS-TA (para comparación)
    patrones_basicos = detectar_patrones_basicos(df)
    patrones_detectados.extend(patrones_basicos)
    
    # PATRONES PERSONALIZADOS POR CATEGORÍA
    categorias = ['continuidad', 'reversion', 'indecision', 'especiales', 'rupturas']
    
    for categoria in categorias:
        patrones_categoria = detectar_patrones_categoria(df, categoria)
        patrones_detectados.extend(patrones_categoria)
    
    return patrones_detectados

def detectar_patrones_basicos(df):
    """
    Detecta patrones básicos usando análisis manual de velas
    pandas_ta no tiene módulo cdl - usamos lógica propia
    """
    patrones = []
    
    try:
        if len(df) < 2:
            return patrones
            
        # Obtener última vela
        ultima = df.iloc[-1]
        penultima = df.iloc[-2] if len(df) > 1 else None
        
        open_price = ultima['open']
        high = ultima['high']
        low = ultima['low']
        close = ultima['close']
        
        cuerpo = abs(close - open_price)
        rango_total = high - low
        sombra_superior = high - max(open_price, close)
        sombra_inferior = min(open_price, close) - low
        
        # Evitar división por cero
        if rango_total == 0:
            return patrones
        
        # DOJI: Cuerpo muy pequeño comparado con el rango total
        if cuerpo / rango_total < 0.1:
            patrones.append({
                'nombre': 'doji',
                'categoria': 'indecision',
                'direccion': 'neutral',
                'fuerza': 0.7,
                'posicion': len(df) - 1
            })
        
        # HAMMER: Sombra inferior larga, cuerpo pequeño en la parte superior
        if cuerpo > 0 and sombra_inferior > cuerpo * 2 and sombra_superior < cuerpo * 0.5:
            patrones.append({
                'nombre': 'hammer',
                'categoria': 'reversion',
                'direccion': 'alcista',
                'fuerza': min(sombra_inferior / cuerpo / 2, 1.0) if cuerpo > 0 else 0.5,
                'posicion': len(df) - 1
            })
        
        # SHOOTING STAR: Sombra superior larga, cuerpo pequeño en la parte inferior
        if cuerpo > 0 and sombra_superior > cuerpo * 2 and sombra_inferior < cuerpo * 0.5:
            patrones.append({
                'nombre': 'shooting_star',
                'categoria': 'reversion',
                'direccion': 'bajista',
                'fuerza': min(sombra_superior / cuerpo / 2, 1.0),
                'posicion': len(df) - 1
            })
        
        # ENGULFING: Vela actual envuelve completamente a la anterior
        if penultima is not None:
            prev_open = penultima['open']
            prev_close = penultima['close']
            prev_cuerpo = abs(prev_close - prev_open)
            
            # Engulfing alcista
            if close > open_price and prev_close < prev_open:
                if open_price < prev_close and close > prev_open:
                    patrones.append({
                        'nombre': 'engulfing_alcista',
                        'categoria': 'reversion',
                        'direccion': 'alcista',
                        'fuerza': min(cuerpo / prev_cuerpo, 1.0) if prev_cuerpo > 0 else 0.8,
                        'posicion': len(df) - 1
                    })
            
            # Engulfing bajista
            if close < open_price and prev_close > prev_open:
                if open_price > prev_close and close < prev_open:
                    patrones.append({
                        'nombre': 'engulfing_bajista',
                        'categoria': 'reversion',
                        'direccion': 'bajista',
                        'fuerza': min(cuerpo / prev_cuerpo, 1.0) if prev_cuerpo > 0 else 0.8,
                        'posicion': len(df) - 1
                    })
            
    except Exception as e:
        print(f"Error detectando patrones básicos: {e}")
    
    return patrones

def detectar_patrones_categoria(df, categoria):
    """
    Detecta patrones de una categoría específica usando los archivos personalizados
    """
    patrones = []
    
    # Mapeo COMPLETO de patrones por categoría (53 patrones personalizados reales)
    patrones_por_categoria = {
        'reversion': [
            # 21 patrones de reversión (archivos existentes)
            'envolventes', 'martillos', 'estrellas', 'harami', 'pinbar', 
            'tweezer', 'bebe_abandonado', 'combo_engulfing', 'doji_confirmacion',
            'fake_breakout', 'gap_escape', 'kicker', 'nube_piercing',
            'belt_hold', 'counterattack_lines', 'engaño_volumen', 'ioi_pattern',
            'meeting_lines', 'separating_line_reversal', 'three_inside_up_down',
            'thrusting_pattern'
        ],
        'continuidad': [
            # 11 patrones de continuidad (archivos existentes)
            'soldados_cuervos', 'rising_falling_three', 'three_line_strike',
            'advance_block', 'deliberation', 'separating_lines',
            'matt_hold', 'tasuki_gap', 'upside_gap_two_crows',
            'downside_gap_three_methods', 'stalled_pattern'
        ],
        'indecision': [
            # 6 patrones de indecisión (archivos existentes)
            'dojis', 'dragonfly_doji', 'gravestone_doji', 'spinning_top', 
            'high_wave_candle', 'long_legged_doji'
        ],
        'especiales': [
            # 10 patrones especiales (archivos existentes)
            'marubozu', 'heiken_ashi', 'railway_tracks', 'patrones_3_velas',
            'cocealing_baby_swallow', 'closing_marubozu', 'opening_marubozu',
            'in_neck_pattern', 'on_neck_pattern', 'kicking_pattern'
        ],
        'rupturas': [
            # 5 patrones de rupturas (archivos existentes)
            'breakout_bar', 'hikkake_pattern', 'inside_fake_breakout', 
            'trap_bar', 'outside_close'
        ]
    }
    
    # Detectar patrones específicos de la categoría
    for patron_nombre in patrones_por_categoria.get(categoria, []):
        patron_detectado = detectar_patron_especifico(df, patron_nombre, categoria)
        if patron_detectado:
            patrones.append(patron_detectado)
    
    return patrones

def detectar_patron_especifico(df, patron_nombre, categoria):
    """
    Detecta un patrón específico cargando dinámicamente los archivos .py personalizados
    """
    try:
        # Intentar cargar el módulo del patrón desde la carpeta correspondiente
        module_path = f"strategies.calculo_velas_patrones.patrones_velas_perzonalizados.{categoria}.{patron_nombre}"
        
        try:
            # Importar el módulo dinámicamente
            module = importlib.import_module(module_path)
            
            # Buscar la función de detección (formato: detectar_nombre_patron)
            function_name = f"detectar_{patron_nombre}"
            if hasattr(module, function_name):
                detect_func = getattr(module, function_name)
                
                # Ejecutar la función de detección
                señales = detect_func(df)
                
                # Si se detectó el patrón en la última vela, retornar info
                # Manejar diferentes tipos de retorno (list, DataFrame, Series, dict)
                if señales is not None:
                    # Convertir a lista si es necesario
                    if isinstance(señales, pd.DataFrame):
                        if not señales.empty and len(señales) > 0:
                            ultima_señal = señales.iloc[-1].to_dict()
                        else:
                            return None
                    elif isinstance(señales, pd.Series):
                        if not señales.empty:
                            ultima_señal = señales.to_dict()
                        else:
                            return None
                    elif isinstance(señales, list) and len(señales) > 0:
                        ultima_señal = señales[-1]
                    elif isinstance(señales, dict):
                        ultima_señal = señales
                    else:
                        return None
                    
                    # Convertir formato de señal a formato de patrón
                    return {
                        'nombre': ultima_señal.get('tipo', patron_nombre),
                        'categoria': categoria,
                        'direccion': 'alcista' if ultima_señal.get('accion') == 'CALL' else 'bajista',
                        'fuerza': ultima_señal.get('fuerza', 0.8),
                        'posicion': ultima_señal.get('indice', len(df) - 1)
                    }
        except (ImportError, AttributeError) as e:
            # Si no se puede cargar el módulo, usar fallback manual
            pass
        
        # Fallback: Lógica manual para patrones más importantes
        if patron_nombre == 'envolventes':
            return detectar_envolvente(df, categoria)
        elif patron_nombre == 'martillos':
            return detectar_martillo_avanzado(df, categoria)
        elif patron_nombre == 'dojis':
            return detectar_doji_avanzado(df, categoria)
        elif patron_nombre == 'pinbar':
            return detectar_pinbar(df, categoria)
        elif patron_nombre == 'marubozu':
            return detectar_marubozu(df, categoria)
        
    except Exception as e:
        print(f"Error detectando patrón {patron_nombre}: {e}")
    
    return None

def detectar_envolvente(df, categoria):
    """Detecta patrón envolvente avanzado"""
    if len(df) < 2:
        return None
    
    vela_anterior = df.iloc[-2]
    vela_actual = df.iloc[-1]
    
    # Envolvente alcista
    if (vela_anterior['close'] < vela_anterior['open'] and
        vela_actual['close'] > vela_actual['open'] and
        vela_actual['close'] > vela_anterior['open'] and
        vela_actual['open'] < vela_anterior['close']):
        
        return {
            'nombre': 'envolvente_alcista',
            'categoria': categoria,
            'direccion': 'alcista',
            'fuerza': 0.8,
            'posicion': len(df) - 1
        }
    
    # Envolvente bajista
    elif (vela_anterior['close'] > vela_anterior['open'] and
          vela_actual['close'] < vela_actual['open'] and
          vela_actual['open'] > vela_anterior['close'] and
          vela_actual['close'] < vela_anterior['open']):
        
        return {
            'nombre': 'envolvente_bajista',
            'categoria': categoria,
            'direccion': 'bajista',
            'fuerza': 0.8,
            'posicion': len(df) - 1
        }
    
    return None

def detectar_martillo_avanzado(df, categoria):
    """Detecta patrón martillo avanzado"""
    if len(df) < 1:
        return None
    
    vela = df.iloc[-1]
    cuerpo = abs(vela['close'] - vela['open'])
    sombra_inferior = min(vela['close'], vela['open']) - vela['low']
    sombra_superior = vela['high'] - max(vela['close'], vela['open'])
    rango_total = vela['high'] - vela['low']
    
    if rango_total == 0:
        return None
    
    # Martillo: cuerpo pequeño, sombra inferior larga
    if (cuerpo / rango_total <= 0.3 and
        sombra_inferior >= 2 * cuerpo and
        sombra_superior <= cuerpo):
        
        return {
            'nombre': 'martillo',
            'categoria': categoria,
            'direccion': 'alcista',
            'fuerza': min(sombra_inferior / cuerpo / 2, 1.0) if cuerpo > 0 else 0.5,
            'posicion': len(df) - 1
        }
    
    return None

def detectar_doji_avanzado(df, categoria):
    """Detecta patrón doji avanzado"""
    if len(df) < 1:
        return None
    
    vela = df.iloc[-1]
    cuerpo = abs(vela['close'] - vela['open'])
    rango_total = vela['high'] - vela['low']
    
    if rango_total == 0:
        return None
    
    # Doji: cuerpo muy pequeño
    if cuerpo / rango_total <= 0.1:
        return {
            'nombre': 'doji',
            'categoria': categoria,
            'direccion': 'neutral',
            'fuerza': 1.0 - (cuerpo / rango_total),
            'posicion': len(df) - 1
        }
    
    return None

def detectar_pinbar(df, categoria):
    """Detecta patrón pin bar"""
    if len(df) < 1:
        return None
    
    vela = df.iloc[-1]
    cuerpo = abs(vela['close'] - vela['open'])
    sombra_inferior = min(vela['close'], vela['open']) - vela['low']
    sombra_superior = vela['high'] - max(vela['close'], vela['open'])
    
    # Pin bar alcista: mecha inferior larga
    if sombra_inferior >= 2 * cuerpo and sombra_superior <= cuerpo:
        return {
            'nombre': 'pinbar_alcista',
            'categoria': categoria,
            'direccion': 'alcista',
            'fuerza': min(sombra_inferior / cuerpo / 2, 1.0) if cuerpo > 0 else 0.5,
            'posicion': len(df) - 1
        }
    
    # Pin bar bajista: mecha superior larga
    elif sombra_superior >= 2 * cuerpo and sombra_inferior <= cuerpo:
        return {
            'nombre': 'pinbar_bajista',
            'categoria': categoria,
            'direccion': 'bajista',
            'fuerza': min(sombra_superior / cuerpo / 2, 1.0) if cuerpo > 0 else 0.5,
            'posicion': len(df) - 1
        }
    
    return None

def detectar_marubozu(df, categoria):
    """Detecta patrón marubozu"""
    if len(df) < 1:
        return None
    
    vela = df.iloc[-1]
    cuerpo = abs(vela['close'] - vela['open'])
    sombra_inferior = min(vela['close'], vela['open']) - vela['low']
    sombra_superior = vela['high'] - max(vela['close'], vela['open'])
    
    # Marubozu: sin mechas o mechas muy pequeñas
    if sombra_inferior <= cuerpo * 0.1 and sombra_superior <= cuerpo * 0.1:
        direccion = 'alcista' if vela['close'] > vela['open'] else 'bajista'
        return {
            'nombre': 'marubozu',
            'categoria': categoria,
            'direccion': direccion,
            'fuerza': 0.9,
            'posicion': len(df) - 1
        }
    
    return None

def evaluar_patrones_en_contexto(patrones, df, tendencia_info, zonas_sr):
    """
    Evalúa cada patrón en el contexto de tendencia y zonas S/R
    """
    patrones_contextuales = []
    
    for patron in patrones:
        efectividad_contextual = calcular_efectividad_contextual(
            patron, df, tendencia_info, zonas_sr
        )
        
        patron_contextual = patron.copy()
        patron_contextual['efectividad'] = efectividad_contextual
        patrones_contextuales.append(patron_contextual)
    
    return patrones_contextuales

def calcular_efectividad_contextual(patron, df, tendencia_info, zonas_sr):
    """
    Calcula efectividad del patrón considerando contexto
    """
    efectividad_base = patron['fuerza'] * 60  # Base 60%
    
    # Bonus por alineación con tendencia
    if tendencia_info and tendencia_info.get('direccion'):
        if patron['direccion'] == tendencia_info['direccion']:
            efectividad_base += 20
        elif patron['direccion'] != 'neutral' and patron['direccion'] != tendencia_info['direccion']:
            efectividad_base -= 10
    
    # Bonus por proximidad a zonas S/R
    if zonas_sr:
        precio_actual = df.iloc[-1]['close']
        cerca_de_zona = False
        
        # Verificar soportes
        for soporte in zonas_sr.get('detalles', {}).get('zonas_soporte', []):
            if abs(precio_actual - soporte['precio_medio']) / precio_actual <= 0.005:
                cerca_de_zona = True
                if soporte.get('es_key_level', False):
                    efectividad_base += 15
                else:
                    efectividad_base += 10
                break
        
        # Verificar resistencias
        if not cerca_de_zona:
            for resistencia in zonas_sr.get('detalles', {}).get('zonas_resistencia', []):
                if abs(precio_actual - resistencia['precio_medio']) / precio_actual <= 0.005:
                    if resistencia.get('es_key_level', False):
                        efectividad_base += 15
                    else:
                        efectividad_base += 10
                    break
    
    return min(efectividad_base, 100)

def calcular_efectividad_patrones(patrones_contextuales):
    """
    Calcula efectividad agregada de todos los patrones
    """
    if not patrones_contextuales:
        return 0
    
    # Obtener los mejores patrones
    patrones_validos = [p for p in patrones_contextuales if p['efectividad'] > 50]
    
    if not patrones_validos:
        return 0
    
    # Promedio ponderado por fuerza
    efectividad_total = sum(p['efectividad'] * p['fuerza'] for p in patrones_validos)
    peso_total = sum(p['fuerza'] for p in patrones_validos)
    
    if peso_total == 0:
        return 0
    
    return min(efectividad_total / peso_total, 100)

def determinar_direccion_patrones(patrones_contextuales):
    """
    Determina dirección predominante basada en patrones válidos
    """
    patrones_validos = [p for p in patrones_contextuales if p['efectividad'] > 60]
    
    if not patrones_validos:
        return 'indefinida'
    
    votos_alcista = sum(p['fuerza'] for p in patrones_validos if p['direccion'] == 'alcista')
    votos_bajista = sum(p['fuerza'] for p in patrones_validos if p['direccion'] == 'bajista')
    
    if votos_alcista > votos_bajista * 1.2:  # Requiere ventaja clara
        return 'alcista'
    elif votos_bajista > votos_alcista * 1.2:
        return 'bajista'
    else:
        return 'indefinida'

def get_mejor_patron(patrones_contextuales):
    """
    Obtiene el patrón con mayor efectividad
    """
    if not patrones_contextuales:
        return None
    
    mejor = max(patrones_contextuales, key=lambda x: x['efectividad'])
    return {
        'nombre': mejor['nombre'],
        'categoria': mejor['categoria'],
        'direccion': mejor['direccion'],
        'efectividad': mejor['efectividad']
    }
