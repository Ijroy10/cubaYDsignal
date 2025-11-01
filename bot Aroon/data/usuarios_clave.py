import json
import os
from datetime import datetime, timedelta

RUTA_REGISTRO = os.path.join(os.path.dirname(__file__), 'registro_usuarios.json')

def obtener_fecha_actual():
    return (datetime.utcnow() - timedelta(hours=4)).strftime('%Y-%m-%d')  # Hora Cuba

def leer_registro():
    if not os.path.exists(RUTA_REGISTRO):
        return {}
    with open(RUTA_REGISTRO, 'r') as f:
        return json.load(f)

def escribir_registro(data):
    with open(RUTA_REGISTRO, 'w') as f:
        json.dump(data, f, indent=4)

def registrar_usuario(user_id, nombre):
    hoy = obtener_fecha_actual()
    datos = leer_registro()

    # No registrar si está bloqueado
    if hoy in datos and str(user_id) in datos.get(f"{hoy}_bloqueados", []):
        return False

    if hoy not in datos:
        datos[hoy] = {}

    if str(user_id) not in datos[hoy]:
        datos[hoy][str(user_id)] = nombre
        escribir_registro(datos)
        return True  # Registrado correctamente

    return True  # Ya estaba registrado

def obtener_usuarios_hoy():
    hoy = obtener_fecha_actual()
    datos = leer_registro()
    return datos.get(hoy, {})

def eliminar_usuario_de_hoy(identificador):
    hoy = obtener_fecha_actual()
    datos = leer_registro()

    if hoy not in datos:
        return False, None

    usuarios_hoy = datos[hoy]
    for user_id, nombre in list(usuarios_hoy.items()):
        if str(user_id) == identificador or nombre.lower() == identificador.lower():
            del datos[hoy][user_id]

            # Añadir a lista de bloqueados
            clave_bloqueados = f"{hoy}_bloqueados"
            if clave_bloqueados not in datos:
                datos[clave_bloqueados] = []
            datos[clave_bloqueados].append(str(user_id))

            escribir_registro(datos)
            return True, nombre

    return False, None

def esta_bloqueado(user_id):
    hoy = obtener_fecha_actual()
    datos = leer_registro()
    bloqueados = datos.get(f"{hoy}_bloqueados", [])
    return str(user_id) in bloqueados

def bloquear_usuario(user_id):
    hoy = obtener_fecha_actual()
    datos = leer_registro()
    clave_bloqueados = f"{hoy}_bloqueados"

    if clave_bloqueados not in datos:
        datos[clave_bloqueados] = []

    if str(user_id) not in datos[clave_bloqueados]:
        datos[clave_bloqueados].append(str(user_id))
        escribir_registro(datos)

def desbloquear_usuario(user_id):
    hoy = obtener_fecha_actual()
    datos = leer_registro()
    clave_bloqueados = f"{hoy}_bloqueados"

    if clave_bloqueados in datos and str(user_id) in datos[clave_bloqueados]:
        datos[clave_bloqueados].remove(str(user_id))
        escribir_registro(datos)
        return True

    return False
