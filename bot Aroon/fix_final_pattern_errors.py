"""
Script para corregir los últimos archivos problemáticos de patrones
"""
import os

# Archivos que necesitan reescritura completa
REWRITE_FILES = {
    'martillos.py': '''import pandas as pd

def detectar_martillos(df: pd.DataFrame) -> list:
    """
    Detecta patrones Martillo (Hammer) y Hombre Colgado (Hanging Man).
    """
    if len(df) < 1:
        return []
    
    resultados = []
    for i in range(len(df)):
        try:
            cuerpo = abs(df.iloc[i]['close'] - df.iloc[i]['open'])
            mecha_superior = df.iloc[i]['high'] - max(df.iloc[i]['close'], df.iloc[i]['open'])
            mecha_inferior = min(df.iloc[i]['close'], df.iloc[i]['open']) - df.iloc[i]['low']

            # Condiciones del martillo/hombre colgado
            if cuerpo > 0 and mecha_inferior > 2 * cuerpo and mecha_superior < cuerpo * 0.3:
                if df.iloc[i]['close'] > df.iloc[i]['open']:
                    resultados.append({'indice': df.index[i], 'tipo': 'martillo', 'accion': 'CALL', 'fuerza': 0.75})
                else:
                    resultados.append({'indice': df.index[i], 'tipo': 'hombre_colgado', 'accion': 'PUT', 'fuerza': 0.75})
        except Exception:
            continue
    
    return resultados
''',
    'estrellas.py': '''import pandas as pd

def detectar_estrellas(df: pd.DataFrame) -> list:
    """
    Detecta patrones Estrella de la Mañana y Estrella de la Tarde.
    """
    if len(df) < 3:
        return []
    
    resultados = []
    for i in range(2, len(df)):
        try:
            # Velas
            v1_open, v1_close = df.iloc[i-2]['open'], df.iloc[i-2]['close']
            v2_open, v2_close = df.iloc[i-1]['open'], df.iloc[i-1]['close']
            v3_open, v3_close = df.iloc[i]['open'], df.iloc[i]['close']
            
            cuerpo1 = abs(v1_close - v1_open)
            cuerpo2 = abs(v2_close - v2_open)
            cuerpo3 = abs(v3_close - v3_open)
            
            # Estrella de la Mañana (alcista)
            if (v1_close < v1_open and  # Primera bajista
                cuerpo2 < cuerpo1 * 0.3 and  # Segunda pequeña
                v3_close > v3_open and  # Tercera alcista
                v3_close > (v1_open + v1_close) / 2):  # Cierra en mitad superior
                resultados.append({'indice': df.index[i], 'tipo': 'estrella_mañana', 'accion': 'CALL', 'fuerza': 0.8})
            
            # Estrella de la Tarde (bajista)
            elif (v1_close > v1_open and  # Primera alcista
                  cuerpo2 < cuerpo1 * 0.3 and  # Segunda pequeña
                  v3_close < v3_open and  # Tercera bajista
                  v3_close < (v1_open + v1_close) / 2):  # Cierra en mitad inferior
                resultados.append({'indice': df.index[i], 'tipo': 'estrella_tarde', 'accion': 'PUT', 'fuerza': 0.8})
        except Exception:
            continue
    
    return resultados
''',
    'tweezer.py': '''import pandas as pd

def detectar_tweezer(df: pd.DataFrame) -> list:
    """
    Detecta patrones Tweezer Top y Tweezer Bottom.
    """
    if len(df) < 2:
        return []
    
    resultados = []
    tolerancia = 0.001  # 0.1% de tolerancia
    
    for i in range(1, len(df)):
        try:
            high_prev = df.iloc[i-1]['high']
            high_curr = df.iloc[i]['high']
            low_prev = df.iloc[i-1]['low']
            low_curr = df.iloc[i]['low']
            
            # Tweezer Top (bajista) - máximos similares
            if abs(high_prev - high_curr) / high_prev < tolerancia:
                resultados.append({'indice': df.index[i], 'tipo': 'tweezer_top', 'accion': 'PUT', 'fuerza': 0.7})
            
            # Tweezer Bottom (alcista) - mínimos similares
            elif abs(low_prev - low_curr) / low_prev < tolerancia:
                resultados.append({'indice': df.index[i], 'tipo': 'tweezer_bottom', 'accion': 'CALL', 'fuerza': 0.7})
        except Exception:
            continue
    
    return resultados
''',
    'doji_confirmacion.py': '''import pandas as pd

def detectar_doji_confirmacion(df: pd.DataFrame) -> list:
    """
    Detecta Doji con confirmación (siguiente vela confirma dirección).
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            # Vela anterior (posible doji)
            prev_open = df.iloc[i-1]['open']
            prev_close = df.iloc[i-1]['close']
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            prev_cuerpo = abs(prev_close - prev_open)
            prev_rango = prev_high - prev_low
            
            # Vela actual (confirmación)
            curr_open = df.iloc[i]['open']
            curr_close = df.iloc[i]['close']
            curr_cuerpo = abs(curr_close - curr_open)
            
            # Es doji si cuerpo < 10% del rango
            if prev_rango > 0 and prev_cuerpo / prev_rango < 0.1:
                # Confirmación alcista
                if curr_close > curr_open and curr_cuerpo > prev_cuerpo * 2:
                    resultados.append({'indice': df.index[i], 'tipo': 'doji_confirmacion_alcista', 'accion': 'CALL', 'fuerza': 0.75})
                # Confirmación bajista
                elif curr_close < curr_open and curr_cuerpo > prev_cuerpo * 2:
                    resultados.append({'indice': df.index[i], 'tipo': 'doji_confirmacion_bajista', 'accion': 'PUT', 'fuerza': 0.75})
        except Exception:
            continue
    
    return resultados
''',
    'fake_breakout.py': '''import pandas as pd

def detectar_fake_breakout(df: pd.DataFrame) -> list:
    """
    Detecta rupturas falsas (precio rompe nivel pero vuelve).
    """
    if len(df) < 20:
        return []
    
    resultados = []
    
    for i in range(20, len(df)):
        try:
            # Calcular resistencia/soporte de últimas 20 velas
            ventana = df.iloc[i-20:i]
            resistencia = ventana['high'].max()
            soporte = ventana['low'].min()
            
            curr_high = df.iloc[i]['high']
            curr_low = df.iloc[i]['low']
            curr_close = df.iloc[i]['close']
            
            # Falsa ruptura alcista (rompe resistencia pero cierra abajo)
            if curr_high > resistencia and curr_close < resistencia:
                resultados.append({'indice': df.index[i], 'tipo': 'fake_breakout_bajista', 'accion': 'PUT', 'fuerza': 0.7})
            
            # Falsa ruptura bajista (rompe soporte pero cierra arriba)
            elif curr_low < soporte and curr_close > soporte:
                resultados.append({'indice': df.index[i], 'tipo': 'fake_breakout_alcista', 'accion': 'CALL', 'fuerza': 0.7})
        except Exception:
            continue
    
    return resultados
''',
    'gap_escape.py': '''import pandas as pd

def detectar_gap_escape(df: pd.DataFrame) -> list:
    """
    Detecta gaps (huecos) en el precio.
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            curr_high = df.iloc[i]['high']
            curr_low = df.iloc[i]['low']
            curr_close = df.iloc[i]['close']
            curr_open = df.iloc[i]['open']
            
            # Gap alcista (mínimo actual > máximo anterior)
            if curr_low > prev_high:
                resultados.append({'indice': df.index[i], 'tipo': 'gap_alcista', 'accion': 'CALL', 'fuerza': 0.75})
            
            # Gap bajista (máximo actual < mínimo anterior)
            elif curr_high < prev_low:
                resultados.append({'indice': df.index[i], 'tipo': 'gap_bajista', 'accion': 'PUT', 'fuerza': 0.75})
        except Exception:
            continue
    
    return resultados
''',
    'separating_line_reversal.py': '''import pandas as pd

def detectar_separating_line_reversal(df: pd.DataFrame) -> list:
    """
    Detecta patrón Separating Lines (líneas de separación).
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            prev_open = df.iloc[i-1]['open']
            prev_close = df.iloc[i-1]['close']
            curr_open = df.iloc[i]['open']
            curr_close = df.iloc[i]['close']
            
            # Alcista: vela bajista seguida de alcista con mismo open
            if (prev_close < prev_open and 
                curr_close > curr_open and 
                abs(curr_open - prev_open) / prev_open < 0.002):
                resultados.append({'indice': df.index[i], 'tipo': 'separating_line_alcista', 'accion': 'CALL', 'fuerza': 0.7})
            
            # Bajista: vela alcista seguida de bajista con mismo open
            elif (prev_close > prev_open and 
                  curr_close < curr_open and 
                  abs(curr_open - prev_open) / prev_open < 0.002):
                resultados.append({'indice': df.index[i], 'tipo': 'separating_line_bajista', 'accion': 'PUT', 'fuerza': 0.7})
        except Exception:
            continue
    
    return resultados
''',
    'thrusting_pattern.py': '''import pandas as pd

def detectar_thrusting_pattern(df: pd.DataFrame) -> list:
    """
    Detecta patrón Thrusting (empuje).
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            prev_open = df.iloc[i-1]['open']
            prev_close = df.iloc[i-1]['close']
            curr_open = df.iloc[i]['open']
            curr_close = df.iloc[i]['close']
            
            # Thrusting bajista
            if (prev_close < prev_open and  # Primera bajista
                curr_close > curr_open and  # Segunda alcista
                curr_open < prev_close and  # Abre abajo
                curr_close < (prev_open + prev_close) / 2):  # Cierra en mitad inferior
                resultados.append({'indice': df.index[i], 'tipo': 'thrusting_bajista', 'accion': 'PUT', 'fuerza': 0.65})
        except Exception:
            continue
    
    return resultados
''',
    'inside_fake_breakout.py': '''import pandas as pd

def detectar_inside_fake_breakout(df: pd.DataFrame) -> list:
    """
    Detecta inside bar con falsa ruptura.
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            curr_high = df.iloc[i]['high']
            curr_low = df.iloc[i]['low']
            curr_close = df.iloc[i]['close']
            
            # Inside bar (actual dentro de anterior)
            if curr_high < prev_high and curr_low > prev_low:
                resultados.append({'indice': df.index[i], 'tipo': 'inside_bar', 'accion': 'CALL', 'fuerza': 0.6})
        except Exception:
            continue
    
    return resultados
''',
    'trap_bar.py': '''import pandas as pd

def detectar_trap_bar(df: pd.DataFrame) -> list:
    """
    Detecta trap bars (velas trampa).
    """
    if len(df) < 3:
        return []
    
    resultados = []
    
    for i in range(2, len(df)):
        try:
            v1_high = df.iloc[i-2]['high']
            v2_high = df.iloc[i-1]['high']
            v3_close = df.iloc[i]['close']
            
            # Trap alcista (nuevo máximo pero cierra abajo)
            if v2_high > v1_high and v3_close < v1_high:
                resultados.append({'indice': df.index[i], 'tipo': 'trap_bajista', 'accion': 'PUT', 'fuerza': 0.7})
        except Exception:
            continue
    
    return resultados
''',
    'outside_close.py': '''import pandas as pd

def detectar_outside_close(df: pd.DataFrame) -> list:
    """
    Detecta outside bars (vela envolvente).
    """
    if len(df) < 2:
        return []
    
    resultados = []
    
    for i in range(1, len(df)):
        try:
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            curr_high = df.iloc[i]['high']
            curr_low = df.iloc[i]['low']
            curr_close = df.iloc[i]['close']
            curr_open = df.iloc[i]['open']
            
            # Outside bar alcista
            if curr_high > prev_high and curr_low < prev_low and curr_close > curr_open:
                resultados.append({'indice': df.index[i], 'tipo': 'outside_alcista', 'accion': 'CALL', 'fuerza': 0.75})
            
            # Outside bar bajista
            elif curr_high > prev_high and curr_low < prev_low and curr_close < curr_open:
                resultados.append({'indice': df.index[i], 'tipo': 'outside_bajista', 'accion': 'PUT', 'fuerza': 0.75})
        except Exception:
            continue
    
    return resultados
'''
}

def main():
    base_path = r"c:\Users\tahiyana\Documents\Descargar Bot-CUBAYDSIGNAL (1)\src\strategies\calculo_velas_patrones\patrones_velas_perzonalizados"
    
    print("🔧 Corrigiendo archivos problemáticos...")
    
    for filename, content in REWRITE_FILES.items():
        # Buscar en reversion y rupturas
        for categoria in ['reversion', 'rupturas']:
            filepath = os.path.join(base_path, categoria, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Corregido: {categoria}/{filename}")
                except Exception as e:
                    print(f"❌ Error en {filename}: {e}")
                break
    
    print("\n✅ Correcciones finales completadas")

if __name__ == "__main__":
    main()
