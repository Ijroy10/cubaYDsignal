"""
Script comprehensivo para corregir TODOS los archivos de patrones
"""
import os
import re

def fix_pattern_comprehensive(filepath):
    """Corrige cualquier archivo de patrón para que retorne lista"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Si ya tiene la conversión, saltar
        if 'indices_detectados' in content:
            return False
        
        filename = os.path.basename(filepath)[:-3]  # Sin .py
        
        # Buscar la función detectar_
        func_match = re.search(r'def (detectar_\w+)\(df[^)]*\)', content)
        if not func_match:
            return False
        
        func_name = func_match.group(1)
        
        # Buscar el último return
        lines = content.split('\n')
        return_line_idx = None
        return_indent = 0
        
        for i in range(len(lines) - 1, -1, -1):
            if 'return ' in lines[i] and not lines[i].strip().startswith('#'):
                return_line_idx = i
                return_indent = len(lines[i]) - len(lines[i].lstrip())
                break
        
        if return_line_idx is None:
            return False
        
        # Extraer la expresión de return (puede ser multilínea)
        return_expr_lines = []
        i = return_line_idx
        
        # Si el return está en una línea
        if lines[i].strip().endswith(')') or '&' not in lines[i]:
            return_expr = lines[i].strip()[7:]  # Quitar 'return '
            return_expr_lines = [return_expr]
        else:
            # Return multilínea
            while i < len(lines):
                line = lines[i].strip()
                if i == return_line_idx:
                    return_expr_lines.append(line[7:])  # Quitar 'return '
                else:
                    return_expr_lines.append(line)
                
                if line.endswith(')') and line.count('(') <= line.count(')'):
                    break
                i += 1
        
        return_expr = '\n        '.join(return_expr_lines)
        
        # Determinar la acción basada en el nombre del patrón
        accion = 'CALL'  # Por defecto
        if any(word in filename.lower() for word in ['bajista', 'bear', 'down', 'sell', 'put', 'falling', 'shooting', 'gravestone']):
            accion = 'PUT'
        
        # Crear el nuevo código
        indent_str = ' ' * return_indent
        new_code = f"""{indent_str}# Detectar patrón
{indent_str}patron_detectado = {return_expr}
{indent_str}
{indent_str}# Convertir a lista de índices donde se detectó
{indent_str}if isinstance(patron_detectado, pd.Series):
{indent_str}    indices_detectados = patron_detectado[patron_detectado == True].index.tolist()
{indent_str}    if len(indices_detectados) > 0:
{indent_str}        return [{{'indice': idx, 'tipo': '{filename}', 'accion': '{accion}', 'fuerza': 0.75}} for idx in indices_detectados]
{indent_str}return []"""
        
        # Reemplazar el return original
        end_idx = i + 1
        new_lines = lines[:return_line_idx] + [new_code] + lines[end_idx:]
        
        new_content = '\n'.join(new_lines)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Corregido: {filename}.py")
        return True
        
    except Exception as e:
        print(f"❌ Error en {os.path.basename(filepath)}: {e}")
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
                if fix_pattern_comprehensive(filepath):
                    total_fixed += 1
    
    print(f"\n✅ Total de archivos corregidos: {total_fixed}")

if __name__ == "__main__":
    main()
