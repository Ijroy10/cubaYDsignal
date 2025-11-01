"""
ESTRATEGIA DE TENDENCIA MULTI-TIMEFRAME MEJORADA
Analiza tendencias en 4 niveles temporales con ponderación inteligente
"""

import pandas as pd
import numpy as np
import warnings
import ta
from typing import Dict, Tuple, List, Optional

# Suprimir warnings de división por cero de la librería ta
warnings.filterwarnings('ignore', category=RuntimeWarning, module='ta.trend')

# Configuración de niveles de tendencia (SIN EMA 200)
NIVELES_TENDENCIA = {
    'secundaria': {'periodo': 50, 'peso': 0.50, 'nombre': 'Tendencia Secundaria'},
    'terciaria': {'periodo': 20, 'peso': 0.30, 'nombre': 'Tendencia Terciaria'},
    'inmediata': {'periodo': 9, 'peso': 0.20, 'nombre': 'Tendencia Inmediata'}
}

BONUS_ALINEACION = {
    3: 20,  # 3/3 tendencias alineadas
    2: 10,  # 2/3 tendencias alineadas
    1: -10, # Solo 1 tendencia alineada
    0: -15  # Ninguna alineación
}


def calcular_angulo_inclinacion(valores: pd.Series, periodos: int = 5) -> Tuple[float, str, str]:
    """
    Calcula el ángulo de inclinación de una tendencia en grados
    
    Clasificación según metodología:
    - Fuerte: 60° (pendiente pronunciada)
    - Saludable: 45° (pendiente ideal)
    - Débil: 30-15° (pendiente suave)
    - Consolidación: <15° (lateral)
    
    Returns:
        tuple: (angulo_grados, clasificacion_fuerza, tipo_tendencia)
    """
    if len(valores) < periodos:
        return 0.0, 'indefinida', 'indefinida'
    
    # Tomar últimos valores
    y = valores.tail(periodos).values
    x = np.arange(len(y))
    
    # Regresión lineal para obtener pendiente
    pendiente = np.polyfit(x, y, 1)[0]
    
    # Calcular ángulo en grados
    # arctan(pendiente) nos da el ángulo en radianes
    angulo_radianes = np.arctan(pendiente)
    angulo_grados = np.degrees(angulo_radianes)
    
    # Clasificar fuerza según ángulo
    angulo_abs = abs(angulo_grados)
    
    if angulo_abs >= 60:
        clasificacion = 'fuerte'
    elif angulo_abs >= 45:
        clasificacion = 'saludable'
    elif angulo_abs >= 15:
        clasificacion = 'debil'
    else:
        clasificacion = 'consolidacion'
    
    # Determinar tipo de tendencia
    if angulo_grados > 15:
        tipo = 'alcista'
    elif angulo_grados < -15:
        tipo = 'bajista'
    else:
        tipo = 'lateral'
    
    return angulo_grados, clasificacion, tipo


def calcular_pendiente(valores: pd.Series, periodos: int = 5) -> float:
    """
    Calcula la pendiente de una serie usando regresión lineal
    
    Returns:
        float: Pendiente normalizada (-1 a 1)
    """
    if len(valores) < periodos:
        return 0.0
    
    y = valores.tail(periodos).values
    x = np.arange(len(y))
    
    # Regresión lineal
    pendiente = np.polyfit(x, y, 1)[0]
    
    # Normalizar pendiente (aproximadamente entre -1 y 1)
    # Dividir por el valor medio para obtener porcentaje de cambio
    valor_medio = np.mean(y)
    if valor_medio != 0:
        pendiente_normalizada = (pendiente / valor_medio) * 100
        # Limitar entre -1 y 1
        return max(-1, min(1, pendiente_normalizada))
    
    return 0.0


def calcular_fuerza_por_angulo(angulo_grados: float, clasificacion: str) -> int:
    """
    Calcula puntos de fuerza basados en el ángulo de inclinación (0-40 puntos)
    
    Clasificación:
    - Fuerte (≥60°): 40 puntos
    - Saludable (≥45°): 35 puntos
    - Débil (30-15°): 20-25 puntos
    - Consolidación (<15°): 5-10 puntos
    """
    angulo_abs = abs(angulo_grados)
    
    if clasificacion == 'fuerte':  # ≥60°
        return 40
    elif clasificacion == 'saludable':  # ≥45°
        return 35
    elif clasificacion == 'debil':  # 30-15°
        # Graduar entre 20-25 según cercanía a 30°
        if angulo_abs >= 25:
            return 25
        elif angulo_abs >= 20:
            return 22
        else:
            return 20
    else:  # consolidacion (<15°)
        # Graduar entre 5-10 según cercanía a 15°
        if angulo_abs >= 10:
            return 10
        elif angulo_abs >= 5:
            return 7
        else:
            return 5


def calcular_fuerza_pendiente(pendiente: float) -> int:
    """
    Calcula puntos de fuerza basados en la pendiente (0-40 puntos)
    DEPRECATED: Usar calcular_fuerza_por_angulo() en su lugar
    """
    pendiente_abs = abs(pendiente)
    
    if pendiente_abs > 0.5:  # Pendiente pronunciada
        return 40
    elif pendiente_abs > 0.3:  # Pendiente moderada
        return 30
    elif pendiente_abs > 0.15:  # Pendiente suave
        return 20
    elif pendiente_abs > 0.05:  # Pendiente muy suave
        return 10
    else:  # Casi plano
        return 5


def calcular_consistencia(ma_valores: pd.Series, periodos: int = 5) -> int:
    """
    Calcula consistencia de la tendencia (0-30 puntos)
    Verifica si la MA mantiene su dirección
    """
    if len(ma_valores) < periodos + 1:
        return 0
    
    ultimos_valores = ma_valores.tail(periodos + 1)
    cambios = ultimos_valores.diff().dropna()
    
    # Contar cuántos cambios van en la misma dirección
    if len(cambios) == 0:
        return 0
    
    # Determinar dirección predominante
    positivos = (cambios > 0).sum()
    negativos = (cambios < 0).sum()
    
    consistencia_ratio = max(positivos, negativos) / len(cambios)
    
    if consistencia_ratio >= 0.9:  # 90%+ consistente
        return 30
    elif consistencia_ratio >= 0.7:  # 70%+ consistente
        return 20
    elif consistencia_ratio >= 0.5:  # 50%+ consistente
        return 10
    else:
        return 0


def calcular_distancia_precio_ma(precio_actual: float, ma_valor: float) -> int:
    """
    Calcula puntos basados en distancia del precio a la MA (0-30 puntos)
    """
    if ma_valor == 0:
        return 0
    
    distancia_porcentaje = abs((precio_actual - ma_valor) / ma_valor) * 100
    
    if distancia_porcentaje < 0.1:  # Muy cerca (< 0.1%)
        return 30
    elif distancia_porcentaje < 0.3:  # Cerca (< 0.3%)
        return 25
    elif distancia_porcentaje < 0.5:  # Moderado (< 0.5%)
        return 20
    elif distancia_porcentaje < 1.0:  # Alejado (< 1%)
        return 10
    else:  # Muy alejado (posible reversión)
        return 5


def identificar_impulsos_retrocesos(df: pd.DataFrame, ventana: int = 10) -> Dict:
    """
    Identifica impulsos (a favor de tendencia) y retrocesos (contra tendencia)
    
    METODOLOGÍA:
    - Impulsos: Movimientos a favor de la tendencia general
    - Retrocesos: Movimientos contra la tendencia general (temporales)
    - Los fractales se repiten en diferentes escalas temporales
    - El precio rara vez se mueve de manera constante y lineal
    
    Returns:
        dict: {
            'tiene_impulsos': bool,
            'tiene_retrocesos': bool,
            'patron_fractal': str,
            'fuerza_impulso': str ('fuerte_acelerada'/'fuerte_lenta'/'debil'),
            'detalles': {...}
        }
    """
    try:
        if len(df) < ventana:
            return {
                'tiene_impulsos': False,
                'tiene_retrocesos': False,
                'patron_fractal': 'indefinido',
                'fuerza_impulso': 'indefinida',
                'detalles': {}
            }
        
        ultimas_velas = df.tail(ventana)
        
        # Analizar movimientos vela por vela
        impulsos_alcistas = 0
        impulsos_bajistas = 0
        retrocesos_alcistas = 0
        retrocesos_bajistas = 0
        
        # Determinar tendencia general (primeros vs últimos valores)
        precio_inicio = ultimas_velas['close'].iloc[0]
        precio_fin = ultimas_velas['close'].iloc[-1]
        tendencia_general = 'alcista' if precio_fin > precio_inicio else 'bajista'
        
        # Analizar cada vela
        velas_fuertes = 0  # Velas con cuerpo grande
        velas_debiles = 0  # Velas con cuerpo pequeño
        volumen_total = 0  # Suma de cuerpos
        
        for i in range(len(ultimas_velas)):
            vela = ultimas_velas.iloc[i]
            cuerpo = abs(vela['close'] - vela['open'])
            rango = vela['high'] - vela['low']
            
            # Clasificar vela por tamaño
            if rango > 0:
                ratio_cuerpo = cuerpo / rango
                if ratio_cuerpo > 0.6:
                    velas_fuertes += 1
                elif ratio_cuerpo < 0.3:
                    velas_debiles += 1
            
            volumen_total += cuerpo
            
            # Identificar impulsos y retrocesos
            es_alcista = vela['close'] > vela['open']
            es_bajista = vela['close'] < vela['open']
            
            if tendencia_general == 'alcista':
                if es_alcista:
                    impulsos_alcistas += 1
                elif es_bajista:
                    retrocesos_bajistas += 1
            else:  # tendencia_general == 'bajista'
                if es_bajista:
                    impulsos_bajistas += 1
                elif es_alcista:
                    retrocesos_alcistas += 1
        
        # Calcular volumen promedio
        volumen_promedio = volumen_total / len(ultimas_velas)
        
        # Determinar fuerza del impulso
        # Fuerte Acelerada: Ángulo pronunciado + velas fuertes
        # Fuerte Lenta: Avance constante + velas débiles (poco volumen)
        # Débil: Precio se contraresta a sí mismo
        
        if velas_fuertes >= ventana * 0.6:  # 60%+ velas fuertes
            fuerza_impulso = 'fuerte_acelerada'
            descripcion_fuerza = "Tendencia fuerte acelerada: precio recorre mucha distancia en poco tiempo"
        elif velas_debiles >= ventana * 0.5 and (impulsos_alcistas + impulsos_bajistas) >= ventana * 0.7:
            fuerza_impulso = 'fuerte_lenta'
            descripcion_fuerza = "Tendencia fuerte lenta: avance constante con poco volumen, muestra insistencia"
        else:
            fuerza_impulso = 'debil'
            descripcion_fuerza = "Tendencia débil: precio se contraresta, velas de poco avance"
        
        # Detectar patrón fractal (impulsos y retrocesos alternados)
        total_impulsos = impulsos_alcistas + impulsos_bajistas
        total_retrocesos = retrocesos_alcistas + retrocesos_bajistas
        
        tiene_impulsos = total_impulsos >= ventana * 0.5
        tiene_retrocesos = total_retrocesos >= ventana * 0.2  # Al menos 20% retrocesos
        
        if tiene_impulsos and tiene_retrocesos:
            patron_fractal = 'impulso_retroceso'
            descripcion_patron = "Patrón fractal detectado: impulsos a favor + retrocesos temporales"
        elif tiene_impulsos:
            patron_fractal = 'impulso_continuo'
            descripcion_patron = "Impulso continuo sin retrocesos significativos"
        else:
            patron_fractal = 'indefinido'
            descripcion_patron = "Sin patrón claro de impulsos/retrocesos"
        
        return {
            'tiene_impulsos': tiene_impulsos,
            'tiene_retrocesos': tiene_retrocesos,
            'patron_fractal': patron_fractal,
            'fuerza_impulso': fuerza_impulso,
            'detalles': {
                'tendencia_general': tendencia_general,
                'impulsos_alcistas': impulsos_alcistas,
                'impulsos_bajistas': impulsos_bajistas,
                'retrocesos_alcistas': retrocesos_alcistas,
                'retrocesos_bajistas': retrocesos_bajistas,
                'velas_fuertes': velas_fuertes,
                'velas_debiles': velas_debiles,
                'volumen_promedio': round(volumen_promedio, 6),
                'descripcion_fuerza': descripcion_fuerza,
                'descripcion_patron': descripcion_patron
            }
        }
        
    except Exception as e:
        return {
            'tiene_impulsos': False,
            'tiene_retrocesos': False,
            'patron_fractal': 'error',
            'fuerza_impulso': 'indefinida',
            'detalles': {'error': str(e)}
        }


def identificar_maximos_minimos(df: pd.DataFrame, ventana: int = 5) -> Dict:
    """
    Identifica máximos y mínimos para determinar tipo de tendencia:
    - Alcista: máximos y mínimos más altos
    - Bajista: máximos y mínimos más bajos
    - Lateral: máximos y mínimos al mismo nivel
    
    Returns:
        dict: {'tipo': 'alcista'/'bajista'/'lateral', 'confirmacion': bool}
    """
    try:
        if len(df) < ventana * 2:
            return {'tipo': 'indefinida', 'confirmacion': False}
        
        # Dividir en dos mitades para comparar
        mitad = len(df) // 2
        primera_mitad = df.iloc[:mitad]
        segunda_mitad = df.iloc[mitad:]
        
        # Máximos y mínimos de cada mitad
        max_1 = primera_mitad['high'].max()
        min_1 = primera_mitad['low'].min()
        max_2 = segunda_mitad['high'].max()
        min_2 = segunda_mitad['low'].min()
        
        # Calcular diferencias porcentuales
        if max_1 > 0 and min_1 > 0:
            diff_max = (max_2 - max_1) / max_1
            diff_min = (min_2 - min_1) / min_1
            
            # Umbral: 0.1% de cambio
            umbral = 0.001
            
            # Tendencia alcista: máximos y mínimos más altos
            if diff_max > umbral and diff_min > umbral:
                return {'tipo': 'alcista', 'confirmacion': True}
            
            # Tendencia bajista: máximos y mínimos más bajos
            elif diff_max < -umbral and diff_min < -umbral:
                return {'tipo': 'bajista', 'confirmacion': True}
            
            # Lateral: máximos y mínimos al mismo nivel
            elif abs(diff_max) < umbral and abs(diff_min) < umbral:
                return {'tipo': 'lateral', 'confirmacion': True}
            
            # Mixto (no claro)
            else:
                return {'tipo': 'indefinida', 'confirmacion': False}
        
        return {'tipo': 'indefinida', 'confirmacion': False}
        
    except Exception as e:
        return {'tipo': 'indefinida', 'confirmacion': False}


def calcular_tendencia_nivel(df: pd.DataFrame, periodo: int, nombre: str) -> Dict:
    """
    Analiza la tendencia para un nivel específico (una MA)
    
    METODOLOGÍA MEJORADA:
    1. Identifica máximos y mínimos (alcista/bajista/lateral)
    2. Calcula ángulo de inclinación en grados (60°, 45°, 30-15°, <15°)
    3. Clasifica fuerza según ángulo (fuerte/saludable/débil/consolidación)
    
    Returns:
        dict: {
            'direccion': 'alcista'/'bajista'/'lateral',
            'fuerza': 0-100,
            'detalles': {...}
        }
    """
    try:
        print(f"[Tendencia] calcular_tendencia_nivel - periodo: {periodo}, nombre: {nombre}, len(df): {len(df)}")
        
        if len(df) < periodo:
            print(f"[Tendencia] ⚠️ Datos insuficientes - len(df)={len(df)} < periodo={periodo}")
            return {
                'direccion': 'indefinida',
                'fuerza': 0,
                'detalles': {
                    'error': 'Datos insuficientes',
                    'periodo': periodo,
                    'nombre': nombre,
                    'pendiente': 0.0,
                    'angulo_grados': 0.0,
                    'ma_actual': 0.0,
                    'precio_actual': 0.0
                }
            }
        
        # Calcular MA
        ma = df['close'].rolling(window=periodo).mean()
        
        if ma.isna().all():
            print(f"[Tendencia] ⚠️ MA no calculable - todos los valores son NaN")
            return {
                'direccion': 'indefinida',
                'fuerza': 0,
                'detalles': {
                    'error': 'MA no calculable',
                    'periodo': periodo,
                    'nombre': nombre,
                    'pendiente': 0.0,
                    'angulo_grados': 0.0,
                    'ma_actual': 0.0,
                    'precio_actual': 0.0
                }
            }
        
        # 1. NUEVO: Calcular ángulo de inclinación en grados
        angulo_grados, clasificacion_fuerza, tipo_angulo = calcular_angulo_inclinacion(
            ma, periodos=min(10, len(ma) // 2)
        )
        puntos_angulo = calcular_fuerza_por_angulo(angulo_grados, clasificacion_fuerza)
        
        # Calcular pendiente real (sin normalizar excesivamente)
        pendiente_real = calcular_pendiente(ma, periodos=min(10, len(ma) // 2))
        
        # 2. NUEVO: Identificar máximos y mínimos
        analisis_maxmin = identificar_maximos_minimos(df, ventana=5)
        tipo_maxmin = analisis_maxmin['tipo']
        confirmacion_maxmin = analisis_maxmin['confirmacion']
        
        # 3. NUEVO: Identificar impulsos y retrocesos (fractales)
        analisis_impulsos = identificar_impulsos_retrocesos(df, ventana=10)
        patron_fractal = analisis_impulsos['patron_fractal']
        fuerza_impulso = analisis_impulsos['fuerza_impulso']
        
        # 4. Calcular consistencia
        puntos_consistencia = calcular_consistencia(ma, periodos=min(5, len(ma) // 4))
        
        # 5. Calcular distancia precio-MA
        precio_actual = df['close'].iloc[-1]
        ma_actual = ma.iloc[-1]
        puntos_distancia = calcular_distancia_precio_ma(precio_actual, ma_actual)
        
        # Calcular fuerza total (0-100)
        fuerza_total = puntos_angulo + puntos_consistencia + puntos_distancia
        
        # BONUS 1: Si máximos/mínimos confirman la dirección del ángulo
        bonus_confirmacion = 0
        if confirmacion_maxmin and tipo_maxmin == tipo_angulo:
            bonus_confirmacion = 10
            fuerza_total += bonus_confirmacion
        
        # BONUS 2: Si hay patrón fractal (impulsos + retrocesos)
        bonus_fractal = 0
        if patron_fractal == 'impulso_retroceso':
            bonus_fractal = 5  # Patrón saludable
            fuerza_total += bonus_fractal
        
        # BONUS 3: Ajuste por fuerza del impulso
        bonus_impulso = 0
        if fuerza_impulso == 'fuerte_acelerada':
            bonus_impulso = 10  # Tendencia muy fuerte
            fuerza_total += bonus_impulso
        elif fuerza_impulso == 'fuerte_lenta':
            bonus_impulso = 7  # Tendencia fuerte pero lenta
            fuerza_total += bonus_impulso
        elif fuerza_impulso == 'debil':
            bonus_impulso = -5  # Penalización por tendencia débil
            fuerza_total += bonus_impulso
        
        # Limitar fuerza entre 0-100
        fuerza_total = min(100, max(0, fuerza_total))
        
        # Determinar dirección final (priorizar ángulo, confirmar con máx/mín)
        if tipo_angulo == 'lateral' or clasificacion_fuerza == 'consolidacion':
            direccion = 'lateral'
        elif confirmacion_maxmin and tipo_maxmin != 'indefinida':
            # Si hay confirmación de máx/mín, usar esa dirección
            direccion = tipo_maxmin
        else:
            # Sino, usar dirección del ángulo
            direccion = tipo_angulo
        
        return {
            'direccion': direccion,
            'fuerza': fuerza_total,
            'detalles': {
                'periodo': periodo,
                'nombre': nombre,
                'pendiente': round(pendiente_real, 5),
                'angulo_grados': round(angulo_grados, 2),
                'clasificacion_fuerza': clasificacion_fuerza,
                'tipo_maximos_minimos': tipo_maxmin,
                'confirmacion_maxmin': confirmacion_maxmin,
                'patron_fractal': patron_fractal,
                'fuerza_impulso': fuerza_impulso,
                'analisis_impulsos': analisis_impulsos['detalles'],
                'puntos_angulo': puntos_angulo,
                'puntos_consistencia': puntos_consistencia,
                'puntos_distancia': puntos_distancia,
                'bonus_confirmacion': bonus_confirmacion,
                'bonus_fractal': bonus_fractal,
                'bonus_impulso': bonus_impulso,
                'ma_actual': round(ma_actual, 5),
                'precio_actual': round(precio_actual, 5)
            }
        }
        
    except Exception as e:
        return {
            'direccion': 'indefinida',
            'fuerza': 0,
            'detalles': {'error': str(e)}
        }


def analizar_alineacion(tendencias: Dict) -> Tuple[int, str]:
    """
    Analiza la alineación entre las diferentes tendencias
    
    Returns:
        tuple: (bonus_puntos, direccion_predominante)
    """
    direcciones = [t['direccion'] for t in tendencias.values() if t['direccion'] != 'indefinida']
    
    if not direcciones:
        return 0, 'indefinida'
    
    # Contar votos por dirección
    votos_alcista = direcciones.count('alcista')
    votos_bajista = direcciones.count('bajista')
    votos_lateral = direcciones.count('lateral')
    
    total_tendencias = len(direcciones)
    
    # Determinar dirección predominante
    if votos_alcista > votos_bajista and votos_alcista > votos_lateral:
        direccion_predominante = 'alcista'
        tendencias_alineadas = votos_alcista
    elif votos_bajista > votos_alcista and votos_bajista > votos_lateral:
        direccion_predominante = 'bajista'
        tendencias_alineadas = votos_bajista
    elif votos_lateral > votos_alcista and votos_lateral > votos_bajista:
        direccion_predominante = 'lateral'
        tendencias_alineadas = votos_lateral
    else:
        direccion_predominante = 'indefinida'
        tendencias_alineadas = 0
    
    # Calcular bonus según alineación
    bonus = BONUS_ALINEACION.get(tendencias_alineadas, 0)
    
    return bonus, direccion_predominante


def calcular_efectividad_ponderada(tendencias: Dict) -> float:
    """
    Calcula efectividad ponderada de todas las tendencias
    """
    efectividad_total = 0
    
    for nivel, config in NIVELES_TENDENCIA.items():
        if nivel in tendencias:
            fuerza = tendencias[nivel]['fuerza']
            peso = config['peso']
            efectividad_total += fuerza * peso
    
    return efectividad_total


def validar_entrada_pullback(
    df: pd.DataFrame,
    tendencias: Dict,
    direccion: str,
    zonas_sr: Dict = None
) -> Tuple[bool, str, Dict]:
    """
    Valida que la entrada cumpla con reglas estrictas de pullback:
    1. Tendencia primaria clara y alineada
    2. Retroceso hacia EMA50 o zona S/R
    3. Vela de confirmación en dirección de tendencia
    4. RSI saliendo de zona extrema (confirmación)
    5. ADX > 20 (tendencia con fuerza)
    
    Args:
        df: DataFrame con datos OHLC
        tendencias: Diccionario con análisis de tendencias
        direccion: Dirección esperada ('alcista' o 'bajista')
        zonas_sr: Zonas de soporte/resistencia (opcional)
    
    Returns:
        tuple: (es_valida, motivo, detalles)
    """
    try:
        detalles = {}
        
        # 1. VERIFICAR TENDENCIA PRIMARIA
        if 'primaria' not in tendencias:
            return False, "No hay análisis de tendencia primaria", {}
        
        tendencia_primaria = tendencias['primaria']['direccion']
        if tendencia_primaria != direccion:
            return False, f"Tendencia primaria {tendencia_primaria} no coincide con señal {direccion}", {}
        
        detalles['tendencia_primaria'] = tendencia_primaria
        
        # 2. VERIFICAR RETROCESO HACIA EMA50
        if len(df) < 50:
            return False, "Datos insuficientes para calcular EMA50", {}
        
        precio_actual = df['close'].iloc[-1]
        ma_50 = df['close'].rolling(50).mean().iloc[-1]
        distancia_ema = abs(precio_actual - ma_50) / ma_50
        
        detalles['precio_actual'] = round(precio_actual, 5)
        detalles['ema50'] = round(ma_50, 5)
        detalles['distancia_ema_pct'] = round(distancia_ema * 100, 2)
        
        # Para opciones binarias: debe estar MUY cerca de la EMA (máximo 0.3% de distancia)
        if distancia_ema > 0.003:
            return False, f"Precio muy alejado de EMA50 ({distancia_ema*100:.2f}% - no hay pullback)", detalles
        
        # 3. VERIFICAR VELA DE CONFIRMACIÓN
        if len(df) < 2:
            return False, "Datos insuficientes para analizar vela", detalles
        
        vela_actual = df.iloc[-1]
        vela_anterior = df.iloc[-2]
        
        es_vela_alcista = vela_actual['close'] > vela_actual['open']
        es_vela_bajista = vela_actual['close'] < vela_actual['open']
        
        # Calcular fuerza de la vela (tamaño del cuerpo vs rango total)
        cuerpo = abs(vela_actual['close'] - vela_actual['open'])
        rango_total = vela_actual['high'] - vela_actual['low']
        
        if rango_total > 0:
            fuerza_vela = cuerpo / rango_total
        else:
            fuerza_vela = 0
        
        detalles['fuerza_vela'] = round(fuerza_vela, 2)
        
        # Para opciones binarias: vela debe ser MUY fuerte (>50% del rango)
        if fuerza_vela < 0.5:
            return False, f"Vela sin fuerza suficiente ({fuerza_vela*100:.0f}% del rango - mínimo 50%)", detalles
        
        # Verificar dirección de la vela
        if direccion == 'alcista' and not es_vela_alcista:
            return False, "Falta vela de confirmación alcista (vela actual es bajista)", detalles
        elif direccion == 'bajista' and not es_vela_bajista:
            return False, "Falta vela de confirmación bajista (vela actual es alcista)", detalles
        
        detalles['vela_confirmacion'] = 'alcista' if es_vela_alcista else 'bajista'
        
        # 4. VERIFICAR RSI (debe estar saliendo de zona extrema)
        try:
            rsi_indicator = ta.momentum.RSIIndicator(df['close'], window=14)
            rsi = rsi_indicator.rsi().iloc[-1]
            rsi_anterior = rsi_indicator.rsi().iloc[-2] if len(df) > 2 else rsi
            
            detalles['rsi'] = round(rsi, 2)
            detalles['rsi_anterior'] = round(rsi_anterior, 2)
            
            # Para opciones binarias: RSI debe estar en zona IDEAL
            if direccion == 'alcista':
                # RSI debe estar entre 40-55 (saliendo de zona baja pero no sobrecomprado)
                if rsi > 55:
                    return False, f"RSI muy alto ({rsi:.1f}) - riesgo de reversión", detalles
                if rsi < 35:
                    return False, f"RSI muy bajo ({rsi:.1f}) - puede seguir cayendo", detalles
                # Bonus: RSI subiendo desde zona de sobreventa
                if rsi < 45 and rsi > rsi_anterior:
                    detalles['rsi_bonus'] = "Saliendo de sobreventa (zona ideal)"
            
            # Para señal bajista: RSI debe estar en zona IDEAL
            elif direccion == 'bajista':
                # RSI debe estar entre 45-60 (saliendo de zona alta pero no sobrevendido)
                if rsi < 45:
                    return False, f"RSI muy bajo ({rsi:.1f}) - riesgo de reversión", detalles
                if rsi > 65:
                    return False, f"RSI muy alto ({rsi:.1f}) - puede seguir subiendo", detalles
                # Bonus: RSI bajando desde zona de sobrecompra
                if rsi > 55 and rsi < rsi_anterior:
                    detalles['rsi_bonus'] = "Saliendo de sobrecompra (zona ideal)"
        
        except Exception as e:
            return False, f"Error calculando RSI: {e}", detalles
        
        # 5. VERIFICAR ADX (fuerza de tendencia)
        try:
            adx_indicator = ta.trend.ADXIndicator(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=14
            )
            adx = adx_indicator.adx().iloc[-1]
            
            detalles['adx'] = round(adx, 2)
            
            # Para opciones binarias: ADX debe ser >25 (tendencia clara y fuerte)
            if adx < 25:
                return False, f"ADX muy bajo ({adx:.1f}) - tendencia insuficiente para binarias", detalles
            
            # Bonus por ADX muy fuerte
            if adx > 35:
                detalles['adx_bonus'] = "Tendencia muy fuerte (ideal para binarias)"
        
        except Exception as e:
            return False, f"Error calculando ADX: {e}", detalles
        
        # 6. VERIFICAR PROXIMIDAD A ZONA S/R (si está disponible)
        if zonas_sr and isinstance(zonas_sr, dict):
            detalles_sr = zonas_sr.get('detalles', {})
            
            if direccion == 'alcista':
                soporte = detalles_sr.get('soporte_mas_fuerte', {})
                if soporte and 'nivel' in soporte:
                    nivel_sr = soporte['nivel']
                    distancia_sr = abs(precio_actual - nivel_sr) / precio_actual
                    detalles['distancia_soporte'] = round(distancia_sr * 100, 2)
                    
                    if distancia_sr < 0.003:  # Menos del 0.3%
                        detalles['sr_bonus'] = "Rebote en soporte clave"
            
            elif direccion == 'bajista':
                resistencia = detalles_sr.get('resistencia_mas_fuerte', {})
                if resistencia and 'nivel' in resistencia:
                    nivel_sr = resistencia['nivel']
                    distancia_sr = abs(precio_actual - nivel_sr) / precio_actual
                    detalles['distancia_resistencia'] = round(distancia_sr * 100, 2)
                    
                    if distancia_sr < 0.003:  # Menos del 0.3%
                        detalles['sr_bonus'] = "Rechazo en resistencia clave"
        
        # TODAS LAS VALIDACIONES PASARON
        motivo = f"✅ Pullback válido: Precio retrocedió a EMA50, vela {direccion} confirmada, RSI {rsi:.1f}, ADX {adx:.1f}"
        return True, motivo, detalles
        
    except Exception as e:
        return False, f"Error en validación: {str(e)}", {}


def verificar_mercado_lateral(tendencias: Dict, df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Verifica si el mercado está lateral (VETO ABSOLUTO para señales)
    
    Criterios:
    - Todas las MAs con pendiente plana (< 0.05)
    - ADX < 20
    - Precio oscilando en rango estrecho
    
    Returns:
        tuple: (es_lateral, motivo)
    """
    try:
        # 1. Verificar pendientes de todas las tendencias
        pendientes_planas = 0
        total_tendencias = 0
        
        for nivel, tendencia in tendencias.items():
            if tendencia.get('direccion') == 'lateral':
                pendientes_planas += 1
            total_tendencias += 1
        
        # Si 3 o más tendencias son laterales
        if pendientes_planas >= 3:
            return True, f"Mercado lateral: {pendientes_planas}/{total_tendencias} tendencias planas"
        
        # 2. Verificar ADX
        if len(df) >= 14:
            try:
                adx_indicator = ta.trend.ADXIndicator(
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    window=14
                )
                adx = adx_indicator.adx().iloc[-1]
                
                if adx < 20:
                    return True, f"ADX muy bajo ({adx:.1f}) - sin tendencia clara"
            except:
                pass
        
        # 3. Verificar rango de precio (últimas 20 velas)
        if len(df) >= 20:
            ultimas_20 = df.tail(20)
            precio_max = ultimas_20['high'].max()
            precio_min = ultimas_20['low'].min()
            precio_medio = ultimas_20['close'].mean()
            
            if precio_medio > 0:
                rango_pct = (precio_max - precio_min) / precio_medio
                
                # Si el rango es menor al 0.2%, está muy lateral (ajustado para Forex)
                if rango_pct < 0.002:
                    return True, f"Rango muy estrecho ({rango_pct*100:.2f}%) - mercado lateral"
        
        return False, "Mercado con tendencia válida"
        
    except Exception as e:
        # En caso de error, no vetamos (asumimos que no es lateral)
        return False, f"No se pudo verificar (error: {e})"


def integrar_con_estrategias(
    efectividad_tendencia: float,
    direccion_tendencia: str,
    tendencias: Dict,
    otras_estrategias: Dict = None
) -> float:
    """
    Ajusta efectividad de tendencia según otras estrategias
    
    Args:
        efectividad_tendencia: Efectividad calculada de tendencia
        direccion_tendencia: Dirección predominante
        tendencias: Diccionario con todas las tendencias
        otras_estrategias: Dict con resultados de otras estrategias
    
    Returns:
        float: Efectividad ajustada
    """
    if not otras_estrategias:
        return efectividad_tendencia
    
    ajuste = 0
    
    # Obtener dirección de otras estrategias
    direcciones_otras = []
    efectividades_otras = []
    
    for estrategia, resultado in otras_estrategias.items():
        if isinstance(resultado, dict):
            dir_est = resultado.get('direccion')
            efec_est = resultado.get('efectividad', 0)
            
            if dir_est and efec_est > 60:  # Solo considerar estrategias con efectividad > 60%
                direcciones_otras.append(dir_est)
                efectividades_otras.append(efec_est)
    
    if not direcciones_otras:
        return efectividad_tendencia
    
    # Calcular efectividad promedio de otras estrategias
    efectividad_promedio_otras = sum(efectividades_otras) / len(efectividades_otras)
    
    # Contar cuántas estrategias coinciden con tendencia
    coincidencias = sum(1 for d in direcciones_otras if d == direccion_tendencia)
    total_estrategias = len(direcciones_otras)
    
    # Ajustar según alineación
    if coincidencias == total_estrategias and efectividad_promedio_otras > 70:
        # Todas las estrategias alineadas con tendencia
        ajuste = +15
    elif coincidencias >= total_estrategias * 0.7:
        # Mayoría alineada
        ajuste = +10
    elif coincidencias < total_estrategias * 0.3:
        # Mayoría contradice
        ajuste = -20
    
    # Bonus adicional si tendencia primaria está alineada
    if 'primaria' in tendencias:
        if tendencias['primaria']['direccion'] == direccion_tendencia:
            ajuste += 5
    
    return min(100, max(0, efectividad_tendencia + ajuste))


def analizar_tendencia_multitimeframe(
    df: pd.DataFrame,
    otras_estrategias: Dict = None,
    validar_pullback: bool = True
) -> Dict:
    """
    FUNCIÓN PRINCIPAL: Analiza tendencias en múltiples timeframes
    
    Args:
        df: DataFrame con columnas ['open', 'high', 'low', 'close']
        otras_estrategias: Resultados de otras estrategias para integración
    
    Returns:
        dict: {
            'efectividad': 0-100,
            'direccion': 'alcista'/'bajista'/'lateral'/'indefinida',
            'detalles': {...}
        }
    """
    try:
        # Analizar cada nivel de tendencia
        tendencias = {}
        
        for nivel, config in NIVELES_TENDENCIA.items():
            tendencias[nivel] = calcular_tendencia_nivel(
                df,
                periodo=config['periodo'],
                nombre=config['nombre']
            )
        
        # Calcular efectividad ponderada
        efectividad_base = calcular_efectividad_ponderada(tendencias)
        
        # Analizar alineación
        bonus_alineacion, direccion_predominante = analizar_alineacion(tendencias)
        
        # Aplicar bonus/penalización por alineación
        efectividad_con_alineacion = efectividad_base + bonus_alineacion
        
        # FILTRO 1: VETO POR MERCADO LATERAL
        es_lateral, motivo_lateral = verificar_mercado_lateral(tendencias, df)
        if es_lateral:
            return {
                'efectividad': 0,
                'direccion': 'lateral',
                'veto': True,
                'motivo_veto': motivo_lateral,
                'detalles': {
                    'tendencias': tendencias,
                    'efectividad_base': round(efectividad_base, 2),
                    'bonus_alineacion': bonus_alineacion,
                    'resumen': [f"❌ VETO: {motivo_lateral}"]
                }
            }
        
        # Integrar con otras estrategias si están disponibles
        efectividad_final = integrar_con_estrategias(
            efectividad_con_alineacion,
            direccion_predominante,
            tendencias,
            otras_estrategias
        )
        
        # FILTRO 2: VALIDACIÓN DE PULLBACK (si está habilitada)
        validacion_pullback = {'valida': False, 'motivo': 'Efectividad base insuficiente para validar pullback', 'detalles': {}}
        
        if validar_pullback and efectividad_final >= 70:
            # Extraer zonas S/R de otras estrategias
            zonas_sr = None
            if otras_estrategias and 'soportes_resistencias' in otras_estrategias:
                zonas_sr = otras_estrategias['soportes_resistencias']
            
            es_valida, motivo, detalles_pullback = validar_entrada_pullback(
                df, tendencias, direccion_predominante, zonas_sr
            )
            
            validacion_pullback = {
                'valida': es_valida,
                'motivo': motivo,
                'detalles': detalles_pullback
            }
            
            # Si no pasa la validación de pullback, reducir efectividad drásticamente
            if not es_valida:
                efectividad_final = min(efectividad_final * 0.6, 70)  # Máximo 70%
            else:
                # Bonus por pullback perfecto
                efectividad_final = min(efectividad_final + 10, 100)
        
        # Limitar entre 0 y 100
        efectividad_final = max(0, min(100, efectividad_final))
        
        # Generar resumen
        resumen = generar_resumen_tendencias(tendencias, direccion_predominante, efectividad_final, validacion_pullback)
        
        return {
            'efectividad': round(efectividad_final, 2),
            'direccion': direccion_predominante,
            'validacion_pullback': validacion_pullback,
            'detalles': {
                'tendencias': tendencias,
                'efectividad_base': round(efectividad_base, 2),
                'bonus_alineacion': bonus_alineacion,
                'efectividad_con_alineacion': round(efectividad_con_alineacion, 2),
                'resumen': resumen
            }
        }
        
    except Exception as e:
        return {
            'efectividad': 0,
            'direccion': 'indefinida',
            'error': str(e)
        }


def generar_resumen_tendencias(tendencias: Dict, direccion: str, efectividad: float, validacion_pullback: Dict = None) -> List[str]:
    """
    Genera un resumen legible del análisis de tendencias
    Incluye: ángulos, impulsos/retrocesos, fractales
    """
    resumen = []
    
    # Resumen por nivel con ángulos e impulsos
    for nivel, config in NIVELES_TENDENCIA.items():
        if nivel in tendencias:
            t = tendencias[nivel]
            nombre = config['nombre']
            dir_t = t['direccion']
            fuerza = t['fuerza']
            
            # Obtener detalles de ángulo
            detalles = t.get('detalles', {})
            angulo = detalles.get('angulo_grados', 0)
            clasificacion = detalles.get('clasificacion_fuerza', 'indefinida')
            patron_fractal = detalles.get('patron_fractal', 'indefinido')
            fuerza_impulso = detalles.get('fuerza_impulso', 'indefinida')
            
            emoji = "📈" if dir_t == 'alcista' else "📉" if dir_t == 'bajista' else "➡️"
            
            # Emoji de fuerza según clasificación
            if clasificacion == 'fuerte':
                emoji_fuerza = "🔥"  # Fuerte (≥60°)
            elif clasificacion == 'saludable':
                emoji_fuerza = "✅"  # Saludable (≥45°)
            elif clasificacion == 'debil':
                emoji_fuerza = "⚠️"  # Débil (30-15°)
            else:
                emoji_fuerza = "💤"  # Consolidación (<15°)
            
            # Emoji de impulso
            if fuerza_impulso == 'fuerte_acelerada':
                emoji_impulso = "⚡"  # Acelerada
            elif fuerza_impulso == 'fuerte_lenta':
                emoji_impulso = "🐢"  # Lenta pero constante
            elif fuerza_impulso == 'debil':
                emoji_impulso = "⚠️"  # Débil
            else:
                emoji_impulso = ""
            
            # Línea principal
            linea = f"{emoji} {nombre}: {dir_t.upper()} {emoji_fuerza} (Ángulo: {angulo:.1f}°, Fuerza: {fuerza}/100)"
            
            # Agregar info de impulsos si está disponible
            if fuerza_impulso != 'indefinida':
                linea += f" {emoji_impulso}"
            
            resumen.append(linea)
            
            # Agregar detalles de patrón fractal si es relevante
            if patron_fractal == 'impulso_retroceso':
                resumen.append(f"   🔄 Patrón fractal: Impulsos + Retrocesos (saludable)")
            elif patron_fractal == 'impulso_continuo':
                resumen.append(f"   ➡️ Impulso continuo sin retrocesos")
    
    # Resumen de alineación
    direcciones = [t['direccion'] for t in tendencias.values()]
    alineadas = sum(1 for d in direcciones if d == direccion)
    
    if alineadas >= 3:
        resumen.append(f"✅ Alta alineación: {alineadas}/4 tendencias {direccion}")
    elif alineadas >= 2:
        resumen.append(f"⚠️ Alineación moderada: {alineadas}/4 tendencias {direccion}")
    else:
        resumen.append(f"❌ Baja alineación: tendencias contradictorias")
    
    # Resumen de validación de pullback
    if validacion_pullback:
        if validacion_pullback.get('valida'):
            detalles = validacion_pullback.get('detalles', {})
            rsi = detalles.get('rsi', 0)
            adx = detalles.get('adx', 0)
            resumen.append(f"🔄 Pullback confirmado: RSI {rsi:.1f}, ADX {adx:.1f}")
            
            # Bonus adicionales
            if 'rsi_bonus' in detalles:
                resumen.append(f"   ⭐ {detalles['rsi_bonus']}")
            if 'adx_bonus' in detalles:
                resumen.append(f"   ⭐ {detalles['adx_bonus']}")
            if 'sr_bonus' in detalles:
                resumen.append(f"   ⭐ {detalles['sr_bonus']}")
        else:
            motivo = validacion_pullback.get('motivo', 'No validado')
            resumen.append(f"⚠️ Sin pullback válido: {motivo}")
    
    # Resumen final
    if efectividad >= 80:
        resumen.append(f"🎯 TENDENCIA FUERTE: {direccion.upper()} ({efectividad:.1f}%)")
    elif efectividad >= 60:
        resumen.append(f"✅ Tendencia válida: {direccion} ({efectividad:.1f}%)")
    else:
        resumen.append(f"⚠️ Tendencia débil o indefinida ({efectividad:.1f}%)")
    
    return resumen


# Función de compatibilidad con código antiguo
def analizar_tendencia_completa(df: pd.DataFrame) -> Dict:
    """
    Función de compatibilidad con el código antiguo
    Redirige a la nueva implementación multi-timeframe
    """
    return analizar_tendencia_multitimeframe(df)


if __name__ == "__main__":
    # Test con datos de ejemplo
    data = {
        'time': range(250),
        'open': [100 + i * 0.1 + np.random.randn() * 0.5 for i in range(250)],
        'high': [101 + i * 0.1 + np.random.randn() * 0.5 for i in range(250)],
        'low': [99 + i * 0.1 + np.random.randn() * 0.5 for i in range(250)],
        'close': [100 + i * 0.1 + np.random.randn() * 0.5 for i in range(250)]
    }
    
    df = pd.DataFrame(data)
    
    print("=" * 60)
    print("TEST: ANÁLISIS DE TENDENCIA MULTI-TIMEFRAME")
    print("=" * 60)
    
    resultado = analizar_tendencia_multitimeframe(df)
    
    print(f"\n📊 RESULTADO FINAL:")
    print(f"Efectividad: {resultado['efectividad']}%")
    print(f"Dirección: {resultado['direccion']}")
    
    print(f"\n📋 RESUMEN:")
    for linea in resultado['detalles']['resumen']:
        print(f"  {linea}")
    
    print(f"\n🔍 DETALLES POR NIVEL:")
    for nivel, tendencia in resultado['detalles']['tendencias'].items():
        print(f"\n  {nivel.upper()}:")
        print(f"    Dirección: {tendencia['direccion']}")
        print(f"    Fuerza: {tendencia['fuerza']}/100")
        if 'detalles' in tendencia:
            det = tendencia['detalles']
            print(f"    Pendiente: {det.get('pendiente', 'N/A')}")
            print(f"    Periodo MA: {det.get('periodo', 'N/A')}")
