"""
Script para corregir todos los archivos de patrones que retornan Series/DataFrame
y convertirlos para que retornen listas de señales detectadas.
"""
import os
import re

def fix_pattern_file(filepath):
    """Corrige un archivo de patrón para que retorne lista en lugar de Series"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Si ya tiene la conversión, saltar
        if 'indices_detectados' in content or 'to_numpy()' in content:
            return False
        
        # Buscar el return statement
        if 'return ' in content and '&' in content:
            # Patrón típico: return cond1 & cond2 & ...
            # Agregar conversión a lista de índices
            
            # Encontrar la última línea de return
            lines = content.split('\n')
            new_lines = []
            modified = False
            
            for i, line in enumerate(lines):
                if line.strip().startswith('return ') and '&' in line:
                    # Esta es la línea de return con condiciones
                    indent = len(line) - len(line.lstrip())
                    indent_str = ' ' * indent
                    
                    # Extraer la expresión de return
                    return_expr = line.strip()[7:]  # Quitar 'return '
                    
                    # Reemplazar con código que convierte a lista
                    new_lines.append(f"{indent_str}# Detectar patrón")
                    new_lines.append(f"{indent_str}patron_detectado = {return_expr}")
                    new_lines.append(f"{indent_str}")
                    new_lines.append(f"{indent_str}# Convertir a lista de índices donde se detectó")
                    new_lines.append(f"{indent_str}if isinstance(patron_detectado, pd.Series):")
                    new_lines.append(f"{indent_str}    indices_detectados = patron_detectado[patron_detectado == True].index.tolist()")
                    new_lines.append(f"{indent_str}    if len(indices_detectados) > 0:")
                    new_lines.append(f"{indent_str}        # Retornar lista de señales")
                    new_lines.append(f"{indent_str}        return [{{'indice': idx, 'tipo': '{os.path.basename(filepath)[:-3]}', 'fuerza': 0.8}} for idx in indices_detectados]")
                    new_lines.append(f"{indent_str}return []")
                    modified = True
                else:
                    new_lines.append(line)
            
            if modified:
                new_content = '\n'.join(new_lines)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Corregido: {os.path.basename(filepath)}")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error en {filepath}: {e}")
        return False

def main():
    """Procesa todos los archivos de patrones"""
    base_path = r"c:\Users\tahiyana\Documents\Descargar Bot-CUBAYDSIGNAL (1)\src\strategies\calculo_velas_patrones\patrones_velas_perzonalizados"
    
    categorias = ['continuidad', 'indecision', 'rupturas', 'especiales', 'reversion']
    
    total_fixed = 0
    
    for categoria in categorias:
        cat_path = os.path.join(base_path, categoria)
        if not os.path.exists(cat_path):
            continue
        
        print(f"\n📁 Procesando categoría: {categoria}")
        
        for filename in os.listdir(cat_path):
            if filename.endswith('.py') and filename != '__init__.py':
                filepath = os.path.join(cat_path, filename)
                if fix_pattern_file(filepath):
                    total_fixed += 1
    
    print(f"\n✅ Total de archivos corregidos: {total_fixed}")

if __name__ == "__main__":
    main()
