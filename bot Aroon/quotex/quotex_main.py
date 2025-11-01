import datetime
from quotex.obtener_mercados_disponibles import obtener_mercados_disponibles
from strategy.tendencia.evaluar_estrategia_completa import evaluar_estrategia
from telegram_bot import enviar_senal_telegram

def esta_en_horario():
    ahora = datetime.datetime.now().time()
    return datetime.time(8, 0) <= ahora <= datetime.time(20, 0)

if __name__ == "__main__":
    if esta_en_horario():
        activos = obtener_mercados_disponibles(payout_minimo=80)
        if not activos:
            print("No hay activos disponibles con payout suficiente.")
        for activo in activos:
            resultado = evaluar_estrategia(activo)
            if resultado.get("efectividad", 0) >= 80:
                enviar_senal_telegram(resultado)
                print(f"Señal enviada para {activo}: {resultado}")
            else:
                print(f"Activo {activo} no cumple efectividad mínima.")
    else:
        print("⏱️ Fuera del horario permitido. El bot no analizará señales.")
