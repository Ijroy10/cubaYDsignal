"""
ESTRATEGIA EMA 50/36 + AROON
Estrategia basada en cruces de EMAs, rebotes y confirmación con Aroon
"""
import pandas as pd
import numpy as np


def calcular_ema(df: pd.DataFrame, periodo: int) -> pd.Series:
    """Calcula la EMA (Exponential Moving Average)"""
    return df['close'].ewm(span=periodo, adjust=False).mean()


def calcular_aroon(df: pd.DataFrame, periodo: int = 14) -> tuple:
    """
    Calcula el indicador Aroon Up y Aroon Down
    Returns: (aroon_up, aroon_down)
    """
    aroon_up = []
    aroon_down = []
    
    for i in range(len(df)):
        if i < periodo - 1:
            aroon_up.append(np.nan)
            aroon_down.append(np.nan)
        else:
            ventana_high = df['high'].iloc[i - periodo + 1:i + 1]
            ventana_low = df['low'].iloc[i - periodo + 1:i + 1]
            
            # Posición del máximo más reciente
            pos_max = ventana_high.tolist().index(ventana_high.max())
            # Posición del mínimo más reciente
            pos_min = ventana_low.tolist().index(ventana_low.min())
            
            # Cálculo Aroon
            aroon_up_val = 100 * (periodo - (periodo - 1 - pos_max)) / periodo
            aroon_down_val = 100 * (periodo - (periodo - 1 - pos_min)) / periodo
            
            aroon_up.append(aroon_up_val)
            aroon_down.append(aroon_down_val)
    
    return pd.Series(aroon_up, index=df.index), pd.Series(aroon_down, index=df.index)


def calcular_atr(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    """Calcula el Average True Range (ATR)"""
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=periodo).mean()
    
    return atr


def detectar_vela_alcista(df: pd.DataFrame, idx: int) -> bool:
    """Detecta si una vela es alcista (cierre > apertura)"""
    return df['close'].iloc[idx] > df['open'].iloc[idx]


def detectar_vela_bajista(df: pd.DataFrame, idx: int) -> bool:
    """Detecta si una vela es bajista (cierre < apertura)"""
    return df['close'].iloc[idx] < df['open'].iloc[idx]


def evaluar_estrategia_completa(df: pd.DataFrame, mercado: str = "EURUSD") -> dict:
    """
    ESTRATEGIA EMA 50/36 + AROON
    
    Señales de entrada:
    1. Cruce de EMAs con confirmación Aroon
    2. Rebote en EMAs en tendencia confirmada
    3. Dos velas consecutivas del mismo color en tendencia
    
    Args:
        df: DataFrame con columnas ['open', 'high', 'low', 'close']
        mercado: Nombre del mercado
    
    Returns:
        dict: Resultado con decisión y efectividad
    """
    try:
        # Validar datos mínimos
        if len(df) < 50:
            return {
                'mercado': mercado,
                'efectividad_total': 0,
                'decision': None,
                'error': 'Datos insuficientes (mínimo 50 velas)'
            }
        
        # ========== PARÁMETROS ==========
        ema_fast = 36
        ema_slow = 50
        aroon_period = 14
        aroon_threshold = 70
        
        # ========== CÁLCULO DE INDICADORES ==========
        print(f"[EMA-Aroon] Calculando indicadores para {mercado}...")
        
        ema36 = calcular_ema(df, ema_fast)
        ema50 = calcular_ema(df, ema_slow)
        aroon_up, aroon_down = calcular_aroon(df, aroon_period)
        atr = calcular_atr(df, 14)
        
        # Agregar indicadores al DataFrame
        df = df.copy()
        df['ema36'] = ema36
        df['ema50'] = ema50
        df['aroon_up'] = aroon_up
        df['aroon_down'] = aroon_down
        df['atr'] = atr
        
        # ========== ANÁLISIS DE ÚLTIMAS VELAS ==========
        # Necesitamos al menos 3 velas para análisis
        if len(df) < 3:
            return {
                'mercado': mercado,
                'efectividad_total': 0,
                'decision': None,
                'error': 'Datos insuficientes para análisis'
            }
        
        # Índices de las últimas velas
        idx_actual = -1
        idx_anterior = -2
        idx_anterior2 = -3
        
        # Valores actuales
        precio_actual = df['close'].iloc[idx_actual]
        ema36_actual = df['ema36'].iloc[idx_actual]
        ema50_actual = df['ema50'].iloc[idx_actual]
        aroon_up_actual = df['aroon_up'].iloc[idx_actual]
        aroon_down_actual = df['aroon_down'].iloc[idx_actual]
        atr_actual = df['atr'].iloc[idx_actual]
        
        # Valores anteriores
        ema36_anterior = df['ema36'].iloc[idx_anterior]
        ema50_anterior = df['ema50'].iloc[idx_anterior]
        aroon_up_anterior = df['aroon_up'].iloc[idx_anterior]
        aroon_down_anterior = df['aroon_down'].iloc[idx_anterior]
        
        # ========== DETECCIÓN DE TENDENCIA ==========
        uptrend = ema36_actual > ema50_actual
        downtrend = ema36_actual < ema50_actual
        
        # Cruce de EMAs
        ema_cross_up = ema36_anterior <= ema50_anterior and ema36_actual > ema50_actual
        ema_cross_down = ema36_anterior >= ema50_anterior and ema36_actual < ema50_actual
        
        # Confirmación Aroon
        aroon_bullish = aroon_up_actual > aroon_threshold and aroon_up_actual > aroon_down_actual
        aroon_bearish = aroon_down_actual > aroon_threshold and aroon_down_actual > aroon_up_actual
        aroon_bullish_anterior = aroon_up_anterior > aroon_threshold and aroon_up_anterior > aroon_down_anterior
        aroon_bearish_anterior = aroon_down_anterior > aroon_threshold and aroon_down_anterior > aroon_up_anterior
        
        # Detección de velas
        vela_alcista_actual = detectar_vela_alcista(df, idx_actual)
        vela_bajista_actual = detectar_vela_bajista(df, idx_actual)
        vela_alcista_anterior = detectar_vela_alcista(df, idx_anterior)
        vela_bajista_anterior = detectar_vela_bajista(df, idx_anterior)
        vela_alcista_anterior2 = detectar_vela_alcista(df, idx_anterior2)
        vela_bajista_anterior2 = detectar_vela_bajista(df, idx_anterior2)
        
        # ========== SEÑALES DE ENTRADA ==========
        
        # 1. ENTRADA POR CRUCE DE EMAs
        signal_cross_long = ema_cross_up and aroon_bullish_anterior and vela_alcista_anterior
        signal_cross_short = ema_cross_down and aroon_bearish_anterior and vela_bajista_anterior
        
        # 2. ENTRADA POR REBOTE EN EMAs
        touch_distance = atr_actual * 0.5 if not pd.isna(atr_actual) else precio_actual * 0.001
        
        low_anterior = df['low'].iloc[idx_anterior]
        high_anterior = df['high'].iloc[idx_anterior]
        
        touched_ema_up = (
            (low_anterior <= ema36_anterior + touch_distance or 
             low_anterior <= ema50_anterior + touch_distance) and
            uptrend
        )
        
        touched_ema_down = (
            (high_anterior >= ema36_anterior - touch_distance or 
             high_anterior >= ema50_anterior - touch_distance) and
            downtrend
        )
        
        signal_bounce_long = touched_ema_up and vela_alcista_anterior and aroon_bullish_anterior and uptrend
        signal_bounce_short = touched_ema_down and vela_bajista_anterior and aroon_bearish_anterior and downtrend
        
        # 3. ENTRADA POR 2 VELAS CONSECUTIVAS DEL MISMO COLOR
        two_bulls = vela_alcista_anterior2 and vela_alcista_anterior
        two_bears = vela_bajista_anterior2 and vela_bajista_anterior
        
        signal_consecutive_long = two_bulls and uptrend and aroon_bullish_anterior
        signal_consecutive_short = two_bears and downtrend and aroon_bearish_anterior
        
        # ========== SEÑALES FINALES ==========
        long_signal = signal_cross_long or signal_bounce_long or signal_consecutive_long
        short_signal = signal_cross_short or signal_bounce_short or signal_consecutive_short
        
        # ========== CÁLCULO DE EFECTIVIDAD ==========
        efectividad = 50  # Base
        
        # Bonus por tendencia clara
        if uptrend or downtrend:
            diferencia_emas = abs(ema36_actual - ema50_actual) / ema50_actual * 100
            efectividad += min(diferencia_emas * 10, 15)
        
        # Bonus por Aroon fuerte
        if aroon_bullish or aroon_bearish:
            diferencia_aroon = abs(aroon_up_actual - aroon_down_actual)
            efectividad += min(diferencia_aroon / 5, 15)
        
        # Bonus por señal de cruce
        if signal_cross_long or signal_cross_short:
            efectividad += 10
        
        # Bonus por rebote confirmado
        if signal_bounce_long or signal_bounce_short:
            efectividad += 8
        
        # Bonus por velas consecutivas
        if signal_consecutive_long or signal_consecutive_short:
            efectividad += 5
        
        # Limitar efectividad
        efectividad = min(efectividad, 100)
        
        # ========== DECISIÓN FINAL ==========
        decision = None
        
        # Requiere efectividad mínima del 75%
        if efectividad >= 75:
            if long_signal and not short_signal:
                decision = 'CALL'
            elif short_signal and not long_signal:
                decision = 'PUT'
        
        # ========== GENERAR DETALLES ==========
        tipo_senal = []
        if signal_cross_long or signal_cross_short:
            tipo_senal.append('Cruce de EMAs')
        if signal_bounce_long or signal_bounce_short:
            tipo_senal.append('Rebote en EMA')
        if signal_consecutive_long or signal_consecutive_short:
            tipo_senal.append('2 Velas Consecutivas')
        
        detalles = {
            'ema36': round(ema36_actual, 5),
            'ema50': round(ema50_actual, 5),
            'aroon_up': round(aroon_up_actual, 2),
            'aroon_down': round(aroon_down_actual, 2),
            'tendencia': 'ALCISTA' if uptrend else 'BAJISTA' if downtrend else 'LATERAL',
            'aroon_confirmado': aroon_bullish or aroon_bearish,
            'tipo_señal': tipo_senal,
            'precio_actual': round(precio_actual, 5)
        }
        
        # ========== RESUMEN ==========
        resumen = []
        if decision:
            resumen.append(f"🎯 SEÑAL {decision} CONFIRMADA")
            resumen.append(f"📊 Efectividad: {efectividad:.1f}%")
            resumen.append(f"📈 Tendencia: {detalles['tendencia']}")
            resumen.append(f"🔄 Aroon: UP={detalles['aroon_up']:.1f}% | DOWN={detalles['aroon_down']:.1f}%")
            if tipo_senal:
                resumen.append(f"✅ Tipo: {', '.join(tipo_senal)}")
        else:
            resumen.append(f"❌ Sin señal - Efectividad insuficiente ({efectividad:.1f}%)")
        
        print(f"[EMA-Aroon] Análisis completado: {decision or 'Sin señal'} ({efectividad:.1f}%)")
        
        return {
            'mercado': mercado,
            'efectividad_total': round(efectividad, 2),
            'decision': decision,
            'direccion': 'alcista' if decision == 'CALL' else 'bajista' if decision == 'PUT' else 'indefinida',
            'efectividad': round(efectividad, 2),
            'detalles': detalles,
            'resumen': resumen
        }
        
    except Exception as e:
        print(f"[EMA-Aroon] Error en evaluación: {e}")
        import traceback
        traceback.print_exc()
        return {
            'mercado': mercado,
            'efectividad_total': 0,
            'decision': None,
            'error': str(e)
        }
