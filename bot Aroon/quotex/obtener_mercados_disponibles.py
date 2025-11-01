# obtener_mercados_disponibles.py
from quotex.conectar import conectar_quotex
import logging

def obtener_mercados_disponibles(payout_minimo=80):
    qx = conectar_quotex()
    if not qx:
        logging.error("No se pudo conectar a Quotex.")
        return []

    activos_disponibles = []
    qx.get_all_asset_payout()  # Cargar la lista de payouts

    for par, datos in qx.payouts.items():
        payout = datos.get("payout", 0)
        if payout >= payout_minimo and datos.get("is_open", False):
            activos_disponibles.append(par)

    qx.close()
    return activos_disponibles
