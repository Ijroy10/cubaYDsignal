"""
ANÁLISIS DE VELAS JAPONESAS
============================

Este módulo implementa el análisis detallado de velas japonesas (candlesticks),
incluyendo la clasificación de velas individuales según su estructura y contexto.

COMPONENTES DE UNA VELA:
1. Apertura (Open)
2. Máximo (High)
3. Mínimo (Low)
4. Cierre (Close)

PARTES DE UNA VELA:
- Cuerpo: Distancia entre apertura y cierre
- Mecha Superior: Distancia entre máximo y el mayor de (apertura, cierre)
- Mecha Inferior: Distancia entre el menor de (apertura, cierre) y mínimo

TIPOS DE VELAS:
- Alcista (Verde): Cierre > Apertura (demanda/fuerza compradora)
- Bajista (Roja): Cierre < Apertura (oferta/fuerza vendedora)
- Neutral (Doji): Cierre ≈ Apertura (indecisión/equilibrio)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


# ============================================================================
# ANÁLISIS BÁSICO DE VELAS
# ============================================================================

def analizar_vela(vela: pd.Series) -> Dict:
    """
    Analiza una vela japonesa individual y extrae toda su información
    
    Args:
        vela: Serie con ['open', 'high', 'low', 'close']
    
    Returns:
        dict: Información completa de la vela
    """
    open_price = vela['open']
    high = vela['high']
    low = vela['low']
    close = vela['close']
    
    # Calcular componentes
    cuerpo = abs(close - open_price)
    rango_total = high - low
    
    # Determinar tipo de vela
    if close > open_price:
        tipo = 'alcista'
        color = 'verde'
        mecha_superior = high - close
        mecha_inferior = open_price - low
    elif close < open_price:
        tipo = 'bajista'
        color = 'roja'
        mecha_superior = high - open_price
        mecha_inferior = close - low
    else:
        tipo = 'neutral'
        color = 'gris'
        mecha_superior = high - open_price
        mecha_inferior = open_price - low
    
    # Calcular proporciones (evitar división por cero)
    if rango_total > 0:
        porcentaje_cuerpo = (cuerpo / rango_total) * 100
        porcentaje_mecha_superior = (mecha_superior / rango_total) * 100
        porcentaje_mecha_inferior = (mecha_inferior / rango_total) * 100
    else:
        porcentaje_cuerpo = 0
        porcentaje_mecha_superior = 0
        porcentaje_mecha_inferior = 0
    
    return {
        'apertura': round(open_price, 5),
        'maximo': round(high, 5),
        'minimo': round(low, 5),
        'cierre': round(close, 5),
        'cuerpo': round(cuerpo, 5),
        'mecha_superior': round(mecha_superior, 5),
        'mecha_inferior': round(mecha_inferior, 5),
        'rango_total': round(rango_total, 5),
        'tipo': tipo,
        'color': color,
        'porcentaje_cuerpo': round(porcentaje_cuerpo, 1),
        'porcentaje_mecha_superior': round(porcentaje_mecha_superior, 1),
        'porcentaje_mecha_inferior': round(porcentaje_mecha_inferior, 1),
        'es_alcista': tipo == 'alcista',
        'es_bajista': tipo == 'bajista',
        'es_doji': tipo == 'neutral'
    }


def clasificar_vela_por_estructura(info_vela: Dict) -> Dict:
    """
    Clasifica una vela según su estructura (cuerpo y mechas)
    
    CLASIFICACIONES:
    
    ALCISTAS (Fuerza Compradora):
    - Marubozu Alcista: Cuerpo grande (>80%), sin mechas
    - Martillo: Cuerpo pequeño arriba, mecha inferior larga (>2x cuerpo)
    - Martillo Invertido: Cuerpo pequeño abajo, mecha superior larga
    
    BAJISTAS (Fuerza Vendedora):
    - Marubozu Bajista: Cuerpo grande (>80%), sin mechas
    - Estrella Fugaz: Cuerpo pequeño abajo, mecha superior larga
    - Hombre Colgado: Cuerpo pequeño arriba, mecha inferior larga
    
    NEUTRALES (Indecisión):
    - Doji: Sin cuerpo o muy pequeño (<5%)
    - Peonza: Cuerpo pequeño (5-30%), mechas largas
    - Vela Equilibrada: Proporciones similares
    
    Args:
        info_vela: Diccionario con información de la vela
    
    Returns:
        dict: Clasificación de la vela
    """
    tipo = info_vela['tipo']
    porc_cuerpo = info_vela['porcentaje_cuerpo']
    porc_mecha_sup = info_vela['porcentaje_mecha_superior']
    porc_mecha_inf = info_vela['porcentaje_mecha_inferior']
    cuerpo = info_vela['cuerpo']
    mecha_sup = info_vela['mecha_superior']
    mecha_inf = info_vela['mecha_inferior']
    
    clasificacion = {
        'patron': 'vela_normal',
        'fuerza': 'neutral',
        'descripcion': 'Vela sin patrón específico',
        'presion': 'equilibrada'
    }
    
    # ===== PATRONES ALCISTAS =====
    
    if tipo == 'alcista':
        # Marubozu Alcista
        if porc_cuerpo > 80 and porc_mecha_sup < 5 and porc_mecha_inf < 5:
            clasificacion = {
                'patron': 'marubozu_alcista',
                'fuerza': 'muy_fuerte',
                'descripcion': 'Marubozu Alcista: Fuerte presión compradora, sin rechazo',
                'presion': 'compradora_extrema'
            }
        
        # Martillo (Hammer)
        elif porc_cuerpo < 30 and mecha_inf > (cuerpo * 2) and mecha_sup < cuerpo:
            clasificacion = {
                'patron': 'martillo',
                'fuerza': 'fuerte',
                'descripcion': 'Martillo: Rechazo de precios bajos, compradores toman control',
                'presion': 'compradora_fuerte'
            }
        
        # Martillo Invertido
        elif porc_cuerpo < 30 and mecha_sup > (cuerpo * 2) and mecha_inf < cuerpo:
            clasificacion = {
                'patron': 'martillo_invertido',
                'fuerza': 'moderada',
                'descripcion': 'Martillo Invertido: Intento de subida, posible reversión alcista',
                'presion': 'compradora_moderada'
            }
        
        # Vela Alcista Fuerte
        elif porc_cuerpo > 60:
            clasificacion = {
                'patron': 'vela_alcista_fuerte',
                'fuerza': 'fuerte',
                'descripcion': 'Vela Alcista Fuerte: Clara presión compradora',
                'presion': 'compradora_fuerte'
            }
        
        # Vela Alcista Normal
        else:
            clasificacion = {
                'patron': 'vela_alcista',
                'fuerza': 'moderada',
                'descripcion': 'Vela Alcista: Presión compradora moderada',
                'presion': 'compradora_moderada'
            }
    
    # ===== PATRONES BAJISTAS =====
    
    elif tipo == 'bajista':
        # Marubozu Bajista
        if porc_cuerpo > 80 and porc_mecha_sup < 5 and porc_mecha_inf < 5:
            clasificacion = {
                'patron': 'marubozu_bajista',
                'fuerza': 'muy_fuerte',
                'descripcion': 'Marubozu Bajista: Fuerte presión vendedora, sin rechazo',
                'presion': 'vendedora_extrema'
            }
        
        # Estrella Fugaz (Shooting Star)
        elif porc_cuerpo < 30 and mecha_sup > (cuerpo * 2) and mecha_inf < cuerpo:
            clasificacion = {
                'patron': 'estrella_fugaz',
                'fuerza': 'fuerte',
                'descripcion': 'Estrella Fugaz: Rechazo de precios altos, vendedores toman control',
                'presion': 'vendedora_fuerte'
            }
        
        # Hombre Colgado (Hanging Man)
        elif porc_cuerpo < 30 and mecha_inf > (cuerpo * 2) and mecha_sup < cuerpo:
            clasificacion = {
                'patron': 'hombre_colgado',
                'fuerza': 'moderada',
                'descripcion': 'Hombre Colgado: Presión vendedora, posible reversión bajista',
                'presion': 'vendedora_moderada'
            }
        
        # Vela Bajista Fuerte
        elif porc_cuerpo > 60:
            clasificacion = {
                'patron': 'vela_bajista_fuerte',
                'fuerza': 'fuerte',
                'descripcion': 'Vela Bajista Fuerte: Clara presión vendedora',
                'presion': 'vendedora_fuerte'
            }
        
        # Vela Bajista Normal
        else:
            clasificacion = {
                'patron': 'vela_bajista',
                'fuerza': 'moderada',
                'descripcion': 'Vela Bajista: Presión vendedora moderada',
                'presion': 'vendedora_moderada'
            }
    
    # ===== PATRONES NEUTRALES (INDECISIÓN) =====
    
    else:  # tipo == 'neutral'
        # Doji
        if porc_cuerpo < 5:
            clasificacion = {
                'patron': 'doji',
                'fuerza': 'neutral',
                'descripcion': 'Doji: Indecisión total, equilibrio entre compradores y vendedores',
                'presion': 'equilibrada'
            }
        
        # Peonza (Spinning Top)
        elif porc_cuerpo < 30 and (mecha_sup > cuerpo or mecha_inf > cuerpo):
            clasificacion = {
                'patron': 'peonza',
                'fuerza': 'neutral',
                'descripcion': 'Peonza: Indecisión, lucha entre compradores y vendedores',
                'presion': 'equilibrada'
            }
        
        # Vela Equilibrada
        else:
            clasificacion = {
                'patron': 'vela_equilibrada',
                'fuerza': 'neutral',
                'descripcion': 'Vela Equilibrada: Sin dirección clara',
                'presion': 'equilibrada'
            }
    
    return clasificacion


def analizar_vela_completa(vela: pd.Series) -> Dict:
    """
    Análisis completo de una vela japonesa
    
    Args:
        vela: Serie con ['open', 'high', 'low', 'close']
    
    Returns:
        dict: Análisis completo de la vela
    """
    # Análisis básico
    info_basica = analizar_vela(vela)
    
    # Clasificación por estructura
    clasificacion = clasificar_vela_por_estructura(info_basica)
    
    # Combinar resultados
    return {
        **info_basica,
        **clasificacion
    }


# ============================================================================
# ANÁLISIS DE SECUENCIAS DE VELAS
# ============================================================================

def analizar_ultimas_velas(df: pd.DataFrame, n_velas: int = 3) -> Dict:
    """
    Analiza las últimas N velas del DataFrame
    
    Args:
        df: DataFrame con OHLC
        n_velas: Número de velas a analizar
    
    Returns:
        dict: Análisis de las últimas velas
    """
    if len(df) < n_velas:
        n_velas = len(df)
    
    ultimas_velas = df.tail(n_velas)
    analisis_velas = []
    
    for idx, vela in ultimas_velas.iterrows():
        analisis = analizar_vela_completa(vela)
        analisis['indice'] = idx
        analisis_velas.append(analisis)
    
    # Estadísticas generales
    velas_alcistas = sum(1 for v in analisis_velas if v['es_alcista'])
    velas_bajistas = sum(1 for v in analisis_velas if v['es_bajista'])
    velas_doji = sum(1 for v in analisis_velas if v['es_doji'])
    
    # Determinar presión predominante
    if velas_alcistas > velas_bajistas:
        presion_predominante = 'compradora'
        fuerza_presion = (velas_alcistas / n_velas) * 100
    elif velas_bajistas > velas_alcistas:
        presion_predominante = 'vendedora'
        fuerza_presion = (velas_bajistas / n_velas) * 100
    else:
        presion_predominante = 'equilibrada'
        fuerza_presion = 50
    
    return {
        'velas_analizadas': n_velas,
        'velas': analisis_velas,
        'estadisticas': {
            'velas_alcistas': velas_alcistas,
            'velas_bajistas': velas_bajistas,
            'velas_doji': velas_doji,
            'presion_predominante': presion_predominante,
            'fuerza_presion': round(fuerza_presion, 1)
        },
        'ultima_vela': analisis_velas[-1] if analisis_velas else None
    }


def detectar_presion_compradores_vendedores(df: pd.DataFrame, ventana: int = 10) -> Dict:
    """
    Detecta la presión de compradores vs vendedores analizando las mechas
    
    CONCEPTO:
    - Mechas largas superiores: Rechazo de precios altos (presión vendedora)
    - Mechas largas inferiores: Rechazo de precios bajos (presión compradora)
    - Cuerpos grandes: Dominio claro de una dirección
    
    Args:
        df: DataFrame con OHLC
        ventana: Número de velas a analizar
    
    Returns:
        dict: Análisis de presión
    """
    if len(df) < ventana:
        ventana = len(df)
    
    ultimas_velas = df.tail(ventana)
    
    presion_compradora = 0
    presion_vendedora = 0
    
    for _, vela in ultimas_velas.iterrows():
        info = analizar_vela(vela)
        
        # Presión compradora
        if info['es_alcista']:
            presion_compradora += info['porcentaje_cuerpo']
        
        # Mechas inferiores largas = rechazo de precios bajos = compradores
        if info['porcentaje_mecha_inferior'] > 30:
            presion_compradora += info['porcentaje_mecha_inferior'] * 0.5
        
        # Presión vendedora
        if info['es_bajista']:
            presion_vendedora += info['porcentaje_cuerpo']
        
        # Mechas superiores largas = rechazo de precios altos = vendedores
        if info['porcentaje_mecha_superior'] > 30:
            presion_vendedora += info['porcentaje_mecha_superior'] * 0.5
    
    # Normalizar
    total_presion = presion_compradora + presion_vendedora
    
    if total_presion > 0:
        porc_compradora = (presion_compradora / total_presion) * 100
        porc_vendedora = (presion_vendedora / total_presion) * 100
    else:
        porc_compradora = 50
        porc_vendedora = 50
    
    # Determinar dominio
    if porc_compradora > 60:
        dominio = 'compradores'
        fuerza_dominio = 'fuerte'
    elif porc_compradora > 55:
        dominio = 'compradores'
        fuerza_dominio = 'moderado'
    elif porc_vendedora > 60:
        dominio = 'vendedores'
        fuerza_dominio = 'fuerte'
    elif porc_vendedora > 55:
        dominio = 'vendedores'
        fuerza_dominio = 'moderado'
    else:
        dominio = 'equilibrado'
        fuerza_dominio = 'neutral'
    
    return {
        'presion_compradora': round(porc_compradora, 1),
        'presion_vendedora': round(porc_vendedora, 1),
        'dominio': dominio,
        'fuerza_dominio': fuerza_dominio,
        'descripcion': f'{dominio.capitalize()} con fuerza {fuerza_dominio}',
        'velas_analizadas': ventana
    }


# ============================================================================
# ANÁLISIS CONTEXTUAL DE VELAS
# ============================================================================

def analizar_vela_en_contexto(df: pd.DataFrame, tendencia: str = None, zona_sr: str = None) -> Dict:
    """
    Analiza la última vela en contexto de tendencia y zonas S/R
    
    CONTEXTO:
    - En tendencia alcista: Velas alcistas = continuación, Velas bajistas = retroceso
    - En tendencia bajista: Velas bajistas = continuación, Velas alcistas = retroceso
    - En zona de soporte: Velas alcistas = rebote, Velas bajistas = ruptura
    - En zona de resistencia: Velas bajistas = rechazo, Velas alcistas = ruptura
    
    Args:
        df: DataFrame con OHLC
        tendencia: 'alcista', 'bajista' o None
        zona_sr: 'soporte', 'resistencia' o None
    
    Returns:
        dict: Análisis contextual de la vela
    """
    if len(df) < 1:
        return {'error': 'No hay datos suficientes'}
    
    # Analizar última vela
    ultima_vela = df.iloc[-1]
    analisis = analizar_vela_completa(ultima_vela)
    
    # Interpretación según contexto
    interpretacion = []
    señal = 'neutral'
    efectividad = 50
    
    # Contexto de TENDENCIA
    if tendencia:
        if tendencia == 'alcista':
            if analisis['es_alcista']:
                interpretacion.append('✅ Vela alcista en tendencia alcista = CONTINUACIÓN')
                señal = 'alcista'
                efectividad += 15
            elif analisis['es_bajista']:
                interpretacion.append('⚠️ Vela bajista en tendencia alcista = RETROCESO temporal')
                señal = 'retroceso'
                efectividad -= 10
            else:
                interpretacion.append('⚪ Doji en tendencia alcista = INDECISIÓN')
                señal = 'indecision'
        
        elif tendencia == 'bajista':
            if analisis['es_bajista']:
                interpretacion.append('✅ Vela bajista en tendencia bajista = CONTINUACIÓN')
                señal = 'bajista'
                efectividad += 15
            elif analisis['es_alcista']:
                interpretacion.append('⚠️ Vela alcista en tendencia bajista = RETROCESO temporal')
                señal = 'retroceso'
                efectividad -= 10
            else:
                interpretacion.append('⚪ Doji en tendencia bajista = INDECISIÓN')
                señal = 'indecision'
    
    # Contexto de ZONA S/R
    if zona_sr:
        if zona_sr == 'soporte':
            if analisis['es_alcista'] and analisis['mecha_inferior'] > analisis['cuerpo']:
                interpretacion.append('✅ Vela alcista con mecha inferior en soporte = REBOTE')
                señal = 'rebote_alcista'
                efectividad += 20
            elif analisis['es_bajista']:
                interpretacion.append('⚠️ Vela bajista en soporte = Posible RUPTURA')
                señal = 'ruptura_bajista'
                efectividad += 10
        
        elif zona_sr == 'resistencia':
            if analisis['es_bajista'] and analisis['mecha_superior'] > analisis['cuerpo']:
                interpretacion.append('✅ Vela bajista con mecha superior en resistencia = RECHAZO')
                señal = 'rechazo_bajista'
                efectividad += 20
            elif analisis['es_alcista']:
                interpretacion.append('⚠️ Vela alcista en resistencia = Posible RUPTURA')
                señal = 'ruptura_alcista'
                efectividad += 10
    
    # Análisis de FUERZA de la vela
    if analisis['patron'] in ['marubozu_alcista', 'marubozu_bajista']:
        interpretacion.append(f'💪 {analisis["patron"].replace("_", " ").title()}: Fuerza EXTREMA')
        efectividad += 10
    elif analisis['patron'] in ['martillo', 'estrella_fugaz']:
        interpretacion.append(f'⚡ {analisis["patron"].replace("_", " ").title()}: Patrón de REVERSIÓN')
        efectividad += 15
    
    return {
        'analisis_vela': analisis,
        'contexto': {
            'tendencia': tendencia,
            'zona_sr': zona_sr
        },
        'interpretacion': interpretacion,
        'señal': señal,
        'efectividad': min(efectividad, 100),
        'descripcion': ' | '.join(interpretacion) if interpretacion else 'Sin interpretación contextual'
    }


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def generar_resumen_velas(df: pd.DataFrame, n_velas: int = 5) -> str:
    """
    Genera un resumen textual del análisis de velas
    
    Args:
        df: DataFrame con OHLC
        n_velas: Número de velas a resumir
    
    Returns:
        str: Resumen textual
    """
    analisis = analizar_ultimas_velas(df, n_velas)
    presion = detectar_presion_compradores_vendedores(df, n_velas)
    
    resumen = []
    resumen.append(f"\n{'='*60}")
    resumen.append(f"ANÁLISIS DE VELAS JAPONESAS ({n_velas} últimas velas)")
    resumen.append(f"{'='*60}\n")
    
    # Estadísticas generales
    stats = analisis['estadisticas']
    resumen.append(f"📊 ESTADÍSTICAS:")
    resumen.append(f"   • Velas Alcistas: {stats['velas_alcistas']} 🟢")
    resumen.append(f"   • Velas Bajistas: {stats['velas_bajistas']} 🔴")
    resumen.append(f"   • Velas Doji: {stats['velas_doji']} ⚪")
    resumen.append(f"   • Presión Predominante: {stats['presion_predominante'].upper()} ({stats['fuerza_presion']:.1f}%)\n")
    
    # Presión de compradores vs vendedores
    resumen.append(f"⚖️ PRESIÓN DE MERCADO:")
    resumen.append(f"   • Compradores: {presion['presion_compradora']:.1f}%")
    resumen.append(f"   • Vendedores: {presion['presion_vendedora']:.1f}%")
    resumen.append(f"   • Dominio: {presion['descripcion']}\n")
    
    # Última vela
    ultima = analisis['ultima_vela']
    if ultima:
        resumen.append(f"🕯️ ÚLTIMA VELA:")
        resumen.append(f"   • Tipo: {ultima['tipo'].upper()} ({ultima['color']})")
        resumen.append(f"   • Patrón: {ultima['patron'].replace('_', ' ').title()}")
        resumen.append(f"   • Fuerza: {ultima['fuerza'].upper()}")
        resumen.append(f"   • Presión: {ultima['presion'].replace('_', ' ').title()}")
        resumen.append(f"   • Descripción: {ultima['descripcion']}\n")
        
        resumen.append(f"📏 COMPONENTES:")
        resumen.append(f"   • Cuerpo: {ultima['porcentaje_cuerpo']:.1f}% del rango")
        resumen.append(f"   • Mecha Superior: {ultima['porcentaje_mecha_superior']:.1f}%")
        resumen.append(f"   • Mecha Inferior: {ultima['porcentaje_mecha_inferior']:.1f}%")
    
    resumen.append(f"\n{'='*60}\n")
    
    return '\n'.join(resumen)


# ============================================================================
# DETECCIÓN DE PATRONES AVANZADOS (INTEGRACIÓN CON PATRONES EXISTENTES)
# ============================================================================

def detectar_todos_patrones_velas(df: pd.DataFrame) -> Dict:
    """
    Detecta TODOS los patrones de velas disponibles en el sistema
    
    Integra:
    - Patrones básicos (individuales)
    - Patrones de reversión (21 patrones)
    - Patrones de continuidad (11 patrones)
    - Patrones de indecisión (6 patrones)
    - Patrones especiales (10 patrones)
    - Patrones de rupturas (5 patrones)
    
    Total: 53+ patrones de velas
    
    Args:
        df: DataFrame con OHLC
    
    Returns:
        dict: Todos los patrones detectados organizados por categoría
    """
    import importlib
    
    patrones_detectados = {
        'reversion': [],
        'continuidad': [],
        'indecision': [],
        'especiales': [],
        'rupturas': [],
        'basicos': []
    }
    
    # 1. PATRONES BÁSICOS (del análisis individual)
    if len(df) >= 1:
        ultima_vela = df.iloc[-1]
        analisis_basico = analizar_vela_completa(ultima_vela)
        
        if analisis_basico['patron'] != 'vela_normal':
            patrones_detectados['basicos'].append({
                'nombre': analisis_basico['patron'],
                'tipo': analisis_basico['tipo'],
                'fuerza': analisis_basico['fuerza'],
                'descripcion': analisis_basico['descripcion'],
                'efectividad': 60 if analisis_basico['fuerza'] == 'fuerte' else 50
            })
    
    # 2. PATRONES DE REVERSIÓN (21 patrones)
    patrones_reversion = [
        'envolventes', 'martillos', 'estrellas', 'harami', 'pinbar',
        'tweezer', 'bebe_abandonado', 'combo_engulfing', 'doji_confirmacion',
        'fake_breakout', 'gap_escape', 'kicker', 'nube_piercing',
        'belt_hold', 'counterattack_lines', 'engaño_volumen', 'ioi_pattern',
        'meeting_lines', 'separating_line_reversal', 'three_inside_up_down',
        'thrusting_pattern'
    ]
    
    for patron in patrones_reversion:
        resultado = _detectar_patron_categoria(df, patron, 'reversion')
        if resultado:
            patrones_detectados['reversion'].append(resultado)
    
    # 3. PATRONES DE CONTINUIDAD (11 patrones)
    patrones_continuidad = [
        'soldados_cuervos', 'rising_falling_three', 'three_line_strike',
        'advance_block', 'deliberation', 'separating_lines',
        'matt_hold', 'tasuki_gap', 'upside_gap_two_crows',
        'downside_gap_three_methods', 'stalled_pattern'
    ]
    
    for patron in patrones_continuidad:
        resultado = _detectar_patron_categoria(df, patron, 'continuidad')
        if resultado:
            patrones_detectados['continuidad'].append(resultado)
    
    # 4. PATRONES DE INDECISIÓN (6 patrones)
    patrones_indecision = [
        'dojis', 'dragonfly_doji', 'gravestone_doji', 'spinning_top',
        'high_wave_candle', 'long_legged_doji'
    ]
    
    for patron in patrones_indecision:
        resultado = _detectar_patron_categoria(df, patron, 'indecision')
        if resultado:
            patrones_detectados['indecision'].append(resultado)
    
    # 5. PATRONES ESPECIALES (10 patrones)
    patrones_especiales = [
        'marubozu', 'heiken_ashi', 'railway_tracks', 'patrones_3_velas',
        'cocealing_baby_swallow', 'closing_marubozu', 'opening_marubozu',
        'in_neck_pattern', 'on_neck_pattern', 'kicking_pattern'
    ]
    
    for patron in patrones_especiales:
        resultado = _detectar_patron_categoria(df, patron, 'especiales')
        if resultado:
            patrones_detectados['especiales'].append(resultado)
    
    # 6. PATRONES DE RUPTURAS (5 patrones)
    patrones_rupturas = [
        'breakout_bar', 'hikkake_pattern', 'inside_fake_breakout',
        'trap_bar', 'outside_close'
    ]
    
    for patron in patrones_rupturas:
        resultado = _detectar_patron_categoria(df, patron, 'rupturas')
        if resultado:
            patrones_detectados['rupturas'].append(resultado)
    
    # Calcular estadísticas
    total_patrones = sum(len(v) for v in patrones_detectados.values())
    patrones_alcistas = sum(
        1 for categoria in patrones_detectados.values()
        for patron in categoria
        if patron.get('direccion') == 'alcista'
    )
    patrones_bajistas = sum(
        1 for categoria in patrones_detectados.values()
        for patron in categoria
        if patron.get('direccion') == 'bajista'
    )
    
    return {
        'patrones': patrones_detectados,
        'estadisticas': {
            'total_patrones': total_patrones,
            'patrones_alcistas': patrones_alcistas,
            'patrones_bajistas': patrones_bajistas,
            'por_categoria': {
                'reversion': len(patrones_detectados['reversion']),
                'continuidad': len(patrones_detectados['continuidad']),
                'indecision': len(patrones_detectados['indecision']),
                'especiales': len(patrones_detectados['especiales']),
                'rupturas': len(patrones_detectados['rupturas']),
                'basicos': len(patrones_detectados['basicos'])
            }
        }
    }


def _detectar_patron_categoria(df: pd.DataFrame, patron_nombre: str, categoria: str) -> Dict:
    """
    Detecta un patrón específico de una categoría
    
    Args:
        df: DataFrame con OHLC
        patron_nombre: Nombre del patrón
        categoria: Categoría del patrón
    
    Returns:
        dict: Información del patrón detectado o None
    """
    try:
        # Intentar cargar el módulo del patrón
        module_path = f"src.strategies.calculo_velas_patrones.patrones_velas_perzonalizados.{categoria}.{patron_nombre}"
        
        try:
            module = importlib.import_module(module_path)
            
            # Buscar la función de detección
            function_name = f"detectar_{patron_nombre}"
            if hasattr(module, function_name):
                detect_func = getattr(module, function_name)
                
                # Ejecutar la función
                resultado = detect_func(df)
                
                if resultado is not None:
                    # Procesar resultado según tipo
                    if isinstance(resultado, pd.DataFrame) and not resultado.empty:
                        ultima_señal = resultado.iloc[-1]
                        return {
                            'nombre': patron_nombre,
                            'categoria': categoria,
                            'direccion': 'alcista' if ultima_señal.get('accion') == 'CALL' else 'bajista',
                            'fuerza': ultima_señal.get('fuerza', 0.7),
                            'efectividad': int(ultima_señal.get('fuerza', 0.7) * 100),
                            'descripcion': f'{patron_nombre.replace("_", " ").title()} detectado'
                        }
                    elif isinstance(resultado, dict):
                        return {
                            'nombre': patron_nombre,
                            'categoria': categoria,
                            'direccion': resultado.get('direccion', 'neutral'),
                            'fuerza': resultado.get('fuerza', 0.7),
                            'efectividad': resultado.get('efectividad', 70),
                            'descripcion': resultado.get('descripcion', f'{patron_nombre.replace("_", " ").title()} detectado')
                        }
        except (ImportError, AttributeError):
            pass
        
        # Fallback: Patrones más comunes implementados manualmente
        return _detectar_patron_fallback(df, patron_nombre, categoria)
        
    except Exception as e:
        return None


def _detectar_patron_fallback(df: pd.DataFrame, patron_nombre: str, categoria: str) -> Dict:
    """
    Implementación fallback para patrones comunes
    """
    if len(df) < 2:
        return None
    
    ultima = df.iloc[-1]
    penultima = df.iloc[-2] if len(df) > 1 else None
    
    # ENVOLVENTE (Engulfing)
    if patron_nombre == 'envolventes' and penultima is not None:
        # Envolvente alcista
        if (ultima['close'] > ultima['open'] and 
            penultima['close'] < penultima['open'] and
            ultima['open'] < penultima['close'] and
            ultima['close'] > penultima['open']):
            return {
                'nombre': 'envolvente_alcista',
                'categoria': 'reversion',
                'direccion': 'alcista',
                'fuerza': 0.85,
                'efectividad': 85,
                'descripcion': 'Envolvente Alcista: Fuerte reversión alcista'
            }
        # Envolvente bajista
        elif (ultima['close'] < ultima['open'] and 
              penultima['close'] > penultima['open'] and
              ultima['open'] > penultima['close'] and
              ultima['close'] < penultima['open']):
            return {
                'nombre': 'envolvente_bajista',
                'categoria': 'reversion',
                'direccion': 'bajista',
                'fuerza': 0.85,
                'efectividad': 85,
                'descripcion': 'Envolvente Bajista: Fuerte reversión bajista'
            }
    
    # MARTILLO (Hammer)
    elif patron_nombre == 'martillos':
        cuerpo = abs(ultima['close'] - ultima['open'])
        mecha_inferior = min(ultima['open'], ultima['close']) - ultima['low']
        mecha_superior = ultima['high'] - max(ultima['open'], ultima['close'])
        
        if cuerpo > 0 and mecha_inferior > (cuerpo * 2) and mecha_superior < cuerpo:
            return {
                'nombre': 'martillo',
                'categoria': 'reversion',
                'direccion': 'alcista',
                'fuerza': 0.80,
                'efectividad': 80,
                'descripcion': 'Martillo: Rechazo de precios bajos, reversión alcista'
            }
    
    # ESTRELLA FUGAZ (Shooting Star)
    elif patron_nombre == 'estrellas':
        cuerpo = abs(ultima['close'] - ultima['open'])
        mecha_inferior = min(ultima['open'], ultima['close']) - ultima['low']
        mecha_superior = ultima['high'] - max(ultima['open'], ultima['close'])
        
        if cuerpo > 0 and mecha_superior > (cuerpo * 2) and mecha_inferior < cuerpo:
            return {
                'nombre': 'estrella_fugaz',
                'categoria': 'reversion',
                'direccion': 'bajista',
                'fuerza': 0.80,
                'efectividad': 80,
                'descripcion': 'Estrella Fugaz: Rechazo de precios altos, reversión bajista'
            }
    
    # DOJI
    elif patron_nombre == 'dojis':
        cuerpo = abs(ultima['close'] - ultima['open'])
        rango = ultima['high'] - ultima['low']
        
        if rango > 0 and (cuerpo / rango) < 0.1:
            return {
                'nombre': 'doji',
                'categoria': 'indecision',
                'direccion': 'neutral',
                'fuerza': 0.70,
                'efectividad': 70,
                'descripcion': 'Doji: Indecisión del mercado'
            }
    
    # MARUBOZU
    elif patron_nombre == 'marubozu':
        cuerpo = abs(ultima['close'] - ultima['open'])
        rango = ultima['high'] - ultima['low']
        
        if rango > 0 and (cuerpo / rango) > 0.90:
            if ultima['close'] > ultima['open']:
                return {
                    'nombre': 'marubozu_alcista',
                    'categoria': 'especiales',
                    'direccion': 'alcista',
                    'fuerza': 0.90,
                    'efectividad': 90,
                    'descripcion': 'Marubozu Alcista: Fuerza compradora extrema'
                }
            else:
                return {
                    'nombre': 'marubozu_bajista',
                    'categoria': 'especiales',
                    'direccion': 'bajista',
                    'fuerza': 0.90,
                    'efectividad': 90,
                    'descripcion': 'Marubozu Bajista: Fuerza vendedora extrema'
                }
    
    return None


def generar_reporte_patrones(df: pd.DataFrame) -> str:
    """
    Genera un reporte completo de todos los patrones detectados
    
    Args:
        df: DataFrame con OHLC
    
    Returns:
        str: Reporte textual completo
    """
    resultado = detectar_todos_patrones_velas(df)
    
    reporte = []
    reporte.append(f"\n{'='*70}")
    reporte.append(f"REPORTE COMPLETO DE PATRONES DE VELAS JAPONESAS")
    reporte.append(f"{'='*70}\n")
    
    # Estadísticas generales
    stats = resultado['estadisticas']
    reporte.append(f"📊 ESTADÍSTICAS GENERALES:")
    reporte.append(f"   • Total de Patrones Detectados: {stats['total_patrones']}")
    reporte.append(f"   • Patrones Alcistas: {stats['patrones_alcistas']} 🟢")
    reporte.append(f"   • Patrones Bajistas: {stats['patrones_bajistas']} 🔴\n")
    
    # Patrones por categoría
    reporte.append(f"📋 PATRONES POR CATEGORÍA:")
    for categoria, cantidad in stats['por_categoria'].items():
        if cantidad > 0:
            emoji = {
                'reversion': '🔄',
                'continuidad': '➡️',
                'indecision': '⚪',
                'especiales': '⭐',
                'rupturas': '💥',
                'basicos': '🕯️'
            }.get(categoria, '•')
            reporte.append(f"   {emoji} {categoria.title()}: {cantidad} patrones")
    reporte.append("")
    
    # Detalles de patrones detectados
    patrones = resultado['patrones']
    
    for categoria, lista_patrones in patrones.items():
        if lista_patrones:
            reporte.append(f"\n{'─'*70}")
            reporte.append(f"{categoria.upper()} ({len(lista_patrones)} patrones):")
            reporte.append(f"{'─'*70}")
            
            for patron in lista_patrones:
                direccion_emoji = '🟢' if patron['direccion'] == 'alcista' else '🔴' if patron['direccion'] == 'bajista' else '⚪'
                reporte.append(f"\n{direccion_emoji} {patron['nombre'].replace('_', ' ').title()}")
                reporte.append(f"   • Dirección: {patron['direccion'].upper()}")
                reporte.append(f"   • Efectividad: {patron.get('efectividad', 70)}%")
                reporte.append(f"   • Descripción: {patron['descripcion']}")
    
    reporte.append(f"\n{'='*70}\n")
    
    return '\n'.join(reporte)
