"""
Script para corregir archivos de patrones de indecisión que reciben una vela individual
"""
import os

# Plantilla para cada archivo
TEMPLATES = {
    'gravestone_doji': '''import pandas as pd

def detectar_gravestone_doji(df, tolerancia_cuerpo=0.1, min_mecha_ratio=2.0):
    """
    Detecta un patrón Gravestone Doji (Doji Lápida) en un DataFrame.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango = df['high'] - df['low']
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']

    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango.replace(0, 1)
    
    # Detectar patrón
    patron_detectado = (
        (rango > 0) &
        (cuerpo_ratio < tolerancia_cuerpo) &
        (mecha_superior > cuerpo * min_mecha_ratio) &
        (mecha_inferior < cuerpo * 0.5)
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'gravestone_doji', 'accion': 'PUT', 'fuerza': 0.7} for idx in indices_detectados]
    return []
''',
    'spinning_top': '''import pandas as pd

def detectar_spinning_top(df, max_cuerpo_ratio=0.4, min_mecha_ratio=0.3):
    """
    Detecta un patrón Spinning Top (Peonza) en un DataFrame.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango_total = df['high'] - df['low']

    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango_total.replace(0, 1)
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']

    mecha_superior_ratio = mecha_superior / rango_total.replace(0, 1)
    mecha_inferior_ratio = mecha_inferior / rango_total.replace(0, 1)

    # Detectar patrón
    patron_detectado = (
        (rango_total > 0) &
        (cuerpo_ratio <= max_cuerpo_ratio) &
        (mecha_superior_ratio >= min_mecha_ratio) &
        (mecha_inferior_ratio >= min_mecha_ratio)
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'spinning_top', 'accion': 'CALL', 'fuerza': 0.6} for idx in indices_detectados]
    return []
''',
    'high_wave_candle': '''import pandas as pd

def detectar_high_wave_candle(df, min_mecha_ratio=0.4, max_cuerpo_ratio=0.3):
    """
    Detecta el patrón High Wave Candle (Vela de Alta Onda) en un DataFrame.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango_total = df['high'] - df['low']

    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango_total.replace(0, 1)
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']

    mecha_superior_ratio = mecha_superior / rango_total.replace(0, 1)
    mecha_inferior_ratio = mecha_inferior / rango_total.replace(0, 1)

    # Detectar patrón
    patron_detectado = (
        (rango_total > 0) &
        (cuerpo_ratio <= max_cuerpo_ratio) &
        (mecha_superior_ratio >= min_mecha_ratio) &
        (mecha_inferior_ratio >= min_mecha_ratio) &
        ((mecha_superior_ratio + mecha_inferior_ratio) > 0.8)
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'high_wave_candle', 'accion': 'CALL', 'fuerza': 0.65} for idx in indices_detectados]
    return []
''',
    'long_legged_doji': '''import pandas as pd

def detectar_long_legged_doji(df, tolerancia_cuerpo=0.05, min_mecha_ratio=0.4):
    """
    Detecta el patrón Long-Legged Doji (Doji de piernas largas) en un DataFrame.
    """
    if len(df) < 1:
        return []
    
    cuerpo = abs(df['close'] - df['open'])
    rango_total = df['high'] - df['low']

    # Evitar división por cero
    cuerpo_ratio = cuerpo / rango_total.replace(0, 1)
    mecha_superior = df['high'] - df[['open', 'close']].max(axis=1)
    mecha_inferior = df[['open', 'close']].min(axis=1) - df['low']
    mechas_ratio_total = (mecha_superior + mecha_inferior) / rango_total.replace(0, 1)

    # Detectar patrón
    patron_detectado = (
        (rango_total > 0) &
        (cuerpo_ratio <= tolerancia_cuerpo) &
        (mecha_superior > 0) &
        (mecha_inferior > 0) &
        (mechas_ratio_total >= min_mecha_ratio)
    )
    
    # Convertir a lista de índices donde se detectó
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'long_legged_doji', 'accion': 'CALL', 'fuerza': 0.65} for idx in indices_detectados]
    return []
'''
}

def main():
    base_path = r"c:\Users\tahiyana\Documents\Descargar Bot-CUBAYDSIGNAL (1)\src\strategies\calculo_velas_patrones\patrones_velas_perzonalizados\indecision"
    
    for filename, template in TEMPLATES.items():
        filepath = os.path.join(base_path, f"{filename}.py")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(template)
            print(f"✅ Corregido: {filename}.py")
        except Exception as e:
            print(f"❌ Error en {filename}.py: {e}")
    
    print(f"\n✅ Total de archivos corregidos: {len(TEMPLATES)}")

if __name__ == "__main__":
    main()
