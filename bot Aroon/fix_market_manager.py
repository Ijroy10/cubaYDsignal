#!/usr/bin/env python3
"""
Script para eliminar código duplicado en market_manager.py
"""

# Leer el archivo
with open('src/core/market_manager.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"📄 Total de líneas originales: {len(lines)}")

# Eliminar líneas 847-1227 (índices 846-1226 en Python)
# Estas líneas contienen código duplicado/basura
lineas_limpias = lines[:846] + lines[1226:]

print(f"✂️ Eliminando líneas 847-1227 (código duplicado)")
print(f"✅ Total de líneas después de limpieza: {len(lineas_limpias)}")

# Crear backup
import shutil
shutil.copy('src/core/market_manager.py', 'src/core/market_manager.py.backup')
print(f"💾 Backup creado: market_manager.py.backup")

# Escribir archivo limpio
with open('src/core/market_manager.py', 'w', encoding='utf-8') as f:
    f.writelines(lineas_limpias)

print(f"✅ Archivo limpiado exitosamente")
print(f"📊 Líneas eliminadas: {len(lines) - len(lineas_limpias)}")
