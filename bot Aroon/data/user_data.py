import json
from datetime import datetime
import os

USERS_FILE = os.path.join(os.path.dirname(__file__), 'registered_users.json')

def registrar_usuario(user_id, nombre):
    today = datetime.now().strftime("%Y-%m-%d")

    # Si no existe el archivo, se crea
    if not os.path.exists(USERS_FILE):
        data = {}
    else:
        with open(USERS_FILE, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}

    if today not in data:
        data[today] = []

    # Verificar si ya está registrado hoy
    if any(user["id"] == user_id for user in data[today]):
        return  # Ya está registrado, no hacer nada

    # Registrar nuevo usuario
    data[today].append({
        "id": user_id,
        "nombre": nombre
    })

    with open(USERS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def usuario_ya_registrado(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(USERS_FILE):
        return False

    with open(USERS_FILE, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return False

    if today not in data:
        return False

    return any(u["id"] == user_id for u in data[today])



# Limpiar ususarios antiguos y guardarlos en historial 
def limpiar_registro_viejo():
    today = datetime.now().strftime("%Y-%m-%d")
    HISTORIAL_FILE = os.path.join(os.path.dirname(__file__), 'historial_usuarios.json')

    if not os.path.exists(USERS_FILE):
        return

    with open(USERS_FILE, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    # Solo dejar los usuarios de hoy en el archivo principal
    data_hoy = {today: data.get(today, [])}

    # Guardar los días anteriores en el historial
    data_historial = {fecha: usuarios for fecha, usuarios in data.items() if fecha != today}

    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, 'r') as f:
            try:
                historial_existente = json.load(f)
            except json.JSONDecodeError:
                historial_existente = {}
    else:
        historial_existente = {}

    historial_existente.update(data_historial)

    with open(HISTORIAL_FILE, 'w') as f:
        json.dump(historial_existente, f, indent=4)

    with open(USERS_FILE, 'w') as f:
        json.dump(data_hoy, f, indent=4)


#Obtener usuarios por fecha 
def obtener_usuarios_por_fecha(fecha: str):
    usuarios = []

    # Buscar en el archivo actual
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            try:
                data = json.load(f)
                if fecha in data:
                    usuarios.extend(data[fecha])
            except json.JSONDecodeError:
                pass

    # Buscar también en el historial
    HISTORIAL_FILE = os.path.join(os.path.dirname(__file__), 'historial_usuarios.json')
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, 'r') as f:
            try:
                historial = json.load(f)
                if fecha in historial:
                    usuarios.extend(historial[fecha])
            except json.JSONDecodeError:
                pass

    return usuarios