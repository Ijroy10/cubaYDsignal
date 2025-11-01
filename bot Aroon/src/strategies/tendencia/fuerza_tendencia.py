import pandas as pd
import warnings
import ta  # librería de technical analysis
from .detectar_divergencias import detectar_divergencias, detectar_agotamiento_tendencia

# Suprimir warnings de división por cero de la librería ta
warnings.filterwarnings('ignore', category=RuntimeWarning, module='ta.trend')

def calcular_fuerza_tendencia(df, periodo_adx=14, periodo_macd_fast=12, periodo_macd_slow=26, periodo_macd_signal=9):
    """
    Calcula la fuerza de la tendencia usando ADX y MACD.

    Parámetros:
    - df: DataFrame con columnas ['high', 'low', 'close']
    - periodo_adx: período para ADX
    - periodo_macd_fast, slow, signal: periodos para MACD

    Retorna un diccionario con:
    - 'adx': valor actual del ADX
    - 'tendencia_fuerte': True si ADX > 25
    - 'macd_cruce': 'alcista', 'bajista' o 'neutral'
    - 'divergencia': True si hay divergencia
    - 'agotamiento': True si hay agotamiento de tendencia
    """
    
    try:
        # Verificar datos suficientes
        if len(df) < max(periodo_adx, periodo_macd_slow) + 10:
            return {
                'adx': 0,
                'tendencia_fuerte': False,
                'macd_cruce': 'neutral',
                'divergencia': False,
                'agotamiento': False,
                'error': 'Datos insuficientes'
            }

        # Calcular ADX con manejo de errores
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            adx = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=periodo_adx)
            adx_series = adx.adx()
            
            # Verificar si hay valores válidos
            if adx_series.isna().all():
                adx_valor = 0
            else:
                adx_valor = adx_series.iloc[-1]
                # Si es NaN, usar el último valor válido
                if pd.isna(adx_valor):
                    adx_valor = adx_series.dropna().iloc[-1] if not adx_series.dropna().empty else 0

        # Calcular MACD con manejo de errores
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            macd = ta.trend.MACD(close=df['close'], window_slow=periodo_macd_slow, window_fast=periodo_macd_fast, window_sign=periodo_macd_signal)
            macd_hist = macd.macd_diff()
            macd_series = macd.macd()
            macd_signal_series = macd.macd_signal()
            
            # Obtener valores con manejo de NaN
            macd_valor = macd_series.iloc[-1] if not pd.isna(macd_series.iloc[-1]) else 0
            macd_signal_val = macd_signal_series.iloc[-1] if not pd.isna(macd_signal_series.iloc[-1]) else 0
            macd_hist_val = macd_hist.iloc[-1] if not pd.isna(macd_hist.iloc[-1]) else 0

        # Determinar cruce MACD
        macd_cruce = 'neutral'
        if macd_valor > macd_signal_val and macd_hist_val > 0:
            macd_cruce = 'alcista'
        elif macd_valor < macd_signal_val and macd_hist_val < 0:
            macd_cruce = 'bajista'

        fuerza = adx_valor > 25

        # DETECTAR DIVERGENCIAS
        try:
            divergencias = detectar_divergencias(df)
        except:
            divergencias = False
        
        # DETECTAR AGOTAMIENTO DE TENDENCIA
        try:
            agotamiento = detectar_agotamiento_tendencia(df)
        except:
            agotamiento = False

        return {
            'adx': float(adx_valor) if not pd.isna(adx_valor) else 0,
            'tendencia_fuerte': bool(fuerza),
            'macd_cruce': macd_cruce,
            'divergencia': divergencias,
            'agotamiento': agotamiento
        }
        
    except Exception as e:
        # En caso de error, devolver valores seguros
        return {
            'adx': 0,
            'tendencia_fuerte': False,
            'macd_cruce': 'neutral',
            'divergencia': False,
            'agotamiento': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Ejemplo básico
    data = {
        'high': [103, 104, 105, 106, 107, 109, 110, 111, 112, 113],
        'low':  [99, 101, 102, 101, 103, 105, 104, 106, 107, 108],
        'close':[102, 103, 103, 105, 106, 108, 109, 110, 111, 112]
    }
    df = pd.DataFrame(data)

    resultado = calcular_fuerza_tendencia(df)
    print(resultado)