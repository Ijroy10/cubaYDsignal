import requests

# Configura tu bot token y chat_id aquí
BOT_TOKEN = "AQUI_TU_BOT_TOKEN"
CHAT_ID = "AQUI_TU_CHAT_ID"

def enviar_senal_telegram(par, decision, efectividad):
    if not decision:
        return

    mensaje = f"📢 Señal: {decision.upper()} ({efectividad:.0f}% efectividad) en {par} – duración 5 minutos"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": mensaje
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"[Telegram] Error al enviar mensaje: {response.text}")
    except Exception as e:
        print(f"[Telegram] Excepción al enviar mensaje: {e}")

def send_telegram_message(mensaje, chat_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id if chat_id else CHAT_ID,
        "text": mensaje
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"[Telegram] Error al enviar mensaje: {response.text}")
    except Exception as e:
        print(f"[Telegram] Excepción al enviar mensaje: {e}")