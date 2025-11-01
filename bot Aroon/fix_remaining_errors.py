"""
Script para corregir los últimos errores en archivos de patrones
"""
import os

# Archivos con correcciones específicas
FIXES = {
    'soldados_cuervos.py': '''import pandas as pd

def detectar_soldados_cuervos(df: pd.DataFrame) -> list:
    """
    Detecta patrones de Tres Soldados Blancos (alcista) y Tres Cuervos Negros (bajista).
    """
    if len(df) < 3:
        return []
    
    o = df['open']
    c = df['close']
    h = df['high']
    l = df['low']
    
    # Tres Soldados Blancos (alcista)
    soldados = (
        (c.shift(2) > o.shift(2)) &
        (c.shift(1) > o.shift(1)) &
        (c > o) &
        (c.shift(1) > c.shift(2)) &
        (c > c.shift(1))
    )
    
    # Tres Cuervos Negros (bajista)
    cuervos = (
        (c.shift(2) < o.shift(2)) &
        (c.shift(1) < o.shift(1)) &
        (c < o) &
        (c.shift(1) < c.shift(2)) &
        (c < c.shift(1))
    )
    
    # Combinar ambos patrones
    patron_detectado = soldados | cuervos
    
    # Convertir a lista
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            resultados = []
            for idx in indices_detectados:
                if soldados.iloc[idx]:
                    resultados.append({'indice': idx, 'tipo': 'tres_soldados_blancos', 'accion': 'CALL', 'fuerza': 0.8})
                else:
                    resultados.append({'indice': idx, 'tipo': 'tres_cuervos_negros', 'accion': 'PUT', 'fuerza': 0.8})
            return resultados
    return []
''',
    'downside_gap_three_methods.py': '''import pandas as pd

def detectar_downside_gap_three_methods(df: pd.DataFrame) -> list:
    """
    Detecta el patrón Downside Gap Three Methods en velas japonesas.
    """
    if len(df) < 3:
        return []
    
    open_1 = df['open'].shift(2)
    close_1 = df['close'].shift(2)
    open_2 = df['open'].shift(1)
    close_2 = df['close'].shift(1)
    open_3 = df['open']
    close_3 = df['close']

    bajista_1 = close_1 < open_1
    bajista_2 = close_2 < open_2
    alcista_3 = close_3 > open_3

    gap_bajista = (open_2 < close_1) & (close_2 < close_1)
    tercera_dentro_del_segundo = (open_3 > close_2) & (close_3 < open_2)

    # Detectar patrón
    patron_detectado = bajista_1 & bajista_2 & alcista_3 & gap_bajista & tercera_dentro_del_segundo
    
    # Convertir a lista
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'downside_gap_three_methods', 'accion': 'PUT', 'fuerza': 0.75} for idx in indices_detectados]
    return []
''',
    'engaño_volumen.py': '''import pandas as pd

def detectar_engaño_volumen(df: pd.DataFrame) -> list:
    """
    Detecta engaños de volumen (requiere columna 'volume').
    Si no hay volumen, retorna lista vacía.
    """
    if len(df) < 2:
        return []
    
    # Verificar si existe columna de volumen
    if 'volume' not in df.columns:
        return []  # Sin volumen, no se puede detectar
    
    # Lógica de detección con volumen
    cuerpo = abs(df['close'] - df['open'])
    volumen_alto = df['volume'] > df['volume'].rolling(window=20).mean() * 1.5
    cuerpo_pequeño = cuerpo < cuerpo.rolling(window=20).mean() * 0.5
    
    # Patrón: volumen alto pero cuerpo pequeño (posible engaño)
    patron_detectado = volumen_alto & cuerpo_pequeño
    
    # Convertir a lista
    if isinstance(patron_detectado, pd.Series):
        indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
        if len(indices_detectados) > 0:
            return [{'indice': idx, 'tipo': 'engaño_volumen', 'accion': 'CALL', 'fuerza': 0.65} for idx in indices_detectados]
    return []
'''
}

# Archivos que necesitan import pandas
FILES_NEED_PD_IMPORT = [
    'marubozu.py',
    'railway_tracks.py',
    'patrones_3_velas.py',
    'opening_marubozu.py',
    'in_neck_pattern.py',
    'on_neck_pattern.py',
    'kicking_pattern.py'
]

def add_pd_import(filepath):
    """Agrega import pandas as pd al inicio del archivo si no existe"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'import pandas as pd' in content:
            return False
        
        # Agregar import al inicio
        new_content = 'import pandas as pd\n\n' + content
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Error en {filepath}: {e}")
        return False

def main():
    base_path = r"c:\Users\tahiyana\Documents\Descargar Bot-CUBAYDSIGNAL (1)\src\strategies\calculo_velas_patrones\patrones_velas_perzonalizados"
    
    # Aplicar correcciones específicas
    print("📝 Aplicando correcciones específicas...")
    for filename, content in FIXES.items():
        # Buscar el archivo en todas las categorías
        for categoria in ['continuidad', 'reversion', 'especiales']:
            filepath = os.path.join(base_path, categoria, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Corregido: {filename}")
                except Exception as e:
                    print(f"❌ Error en {filename}: {e}")
                break
    
    # Agregar imports faltantes
    print("\n📦 Agregando imports faltantes...")
    for filename in FILES_NEED_PD_IMPORT:
        filepath = os.path.join(base_path, 'especiales', filename)
        if os.path.exists(filepath):
            if add_pd_import(filepath):
                print(f"✅ Import agregado: {filename}")
    
    print("\n✅ Correcciones completadas")

if __name__ == "__main__":
    main()
