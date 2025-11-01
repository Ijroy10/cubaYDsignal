import os
from quotexapi.ws_connect import Quotex
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("QUOTEX_EMAIL", "TU_CORREO")
PASSWORD = os.getenv("QUOTEX_PASSWORD", "TU_CONTRASEÑA")

def conectar_quotex():
    qx = Quotex(EMAIL, PASSWORD)
    if qx.connect():
        print("[Quotex] Conexión exitosa.")
        return qx
    else:
        print("[Quotex] Error al conectar.")
        return None