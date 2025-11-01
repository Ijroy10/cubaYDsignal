import json
import os
from datetime import datetime

# Ruta al archivo donde se guarda la clave pública del día
KEYS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'public_key.json')
KEYS_FILE = os.path.abspath(KEYS_FILE)

# ✅ Guarda la clave pública del día actual en el archivo JSON
def guardar_clave_publica_actual(clave: str):
    hoy = datetime.now().strftime("%Y-%m-%d")
    datos = {}

    # Si el archivo existe, intenta cargarlo
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, 'r') as archivo:
            try:
                datos = json.load(archivo)
            except json.JSONDecodeError:
                datos = {}

    # Asigna la clave al día de hoy
    datos[hoy] = clave

    # Guarda el archivo actualizado
    with open(KEYS_FILE, 'w') as archivo:
        json.dump(datos, archivo, indent=4)

# ✅ Carga la clave pública correspondiente al día actual
def cargar_clave_publica_actual():
    hoy = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(KEYS_FILE):
        return None

    with open(KEYS_FILE, 'r') as archivo:
        try:
            datos = json.load(archivo)
            return datos.get(hoy)
        except json.JSONDecodeError:
            return None
