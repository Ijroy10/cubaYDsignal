#!/usr/bin/env python3
"""Script para limpiar signal_scheduler.py eliminando código duplicado"""

import os

# Ruta del archivo
archivo = r"c:\Users\tahiyana\Documents\Descargar Bot-CUBAYDSIGNAL (1)\src\core\signal_scheduler.py"

print(f"Limpiando archivo: {archivo}")

# Leer todas las líneas
with open(archivo, 'r', encoding='utf-8') as f:
    lineas = f.readlines()

print(f"Total de líneas originales: {len(lineas)}")

# Encontrar la primera ocurrencia de "if __name__"
primera_ocurrencia = None
for i, linea in enumerate(lineas):
    if linea.strip().startswith('if __name__ == "__main__":'):
        primera_ocurrencia = i
        print(f"Primera ocurrencia de 'if __name__' en línea: {i + 1}")
        break

if primera_ocurrencia is None:
    print("❌ No se encontró 'if __name__'")
    exit(1)

# Encontrar el final del primer bloque (línea con asyncio.run)
fin_primer_bloque = None
for i in range(primera_ocurrencia, min(primera_ocurrencia + 10, len(lineas))):
    if 'asyncio.run(ejecutar_bot_completo())' in lineas[i]:
        fin_primer_bloque = i
        print(f"Fin del primer bloque en línea: {i + 1}")
        break

if fin_primer_bloque is None:
    print("❌ No se encontró el fin del bloque")
    exit(1)

# Mantener solo hasta el fin del primer bloque + línea en blanco
lineas_limpias = lineas[:fin_primer_bloque + 1]

# Agregar línea en blanco al final si no existe
if lineas_limpias[-1].strip() != '':
    lineas_limpias.append('\n')

print(f"Total de líneas después de limpiar: {len(lineas_limpias)}")

# Crear backup
backup = archivo + '.backup'
with open(backup, 'w', encoding='utf-8') as f:
    f.writelines(lineas)
print(f"✅ Backup creado: {backup}")

# Escribir archivo limpio
with open(archivo, 'w', encoding='utf-8') as f:
    f.writelines(lineas_limpias)

print(f"✅ Archivo limpiado exitosamente")
print(f"   Líneas eliminadas: {len(lineas) - len(lineas_limpias)}")
print(f"   Líneas finales: {len(lineas_limpias)}")
