import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
import os

USERS_FILE = os.path.join(os.path.dirname(__file__), '../data/registered_users.json')

async def ver_usuarios_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(USERS_FILE):
        await update.message.reply_text("📂 No se ha registrado ningún usuario hoy.")
        return

    with open(USERS_FILE, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            await update.message.reply_text("⚠️ Error al leer los usuarios registrados.")
            return

    if today not in data or not data[today]:
        await update.message.reply_text("👥 No hay usuarios registrados hoy.")
        return

    # Construir la lista de usuarios
    mensaje = f"📋 Usuarios registrados hoy ({today}):\n"
    for i, user in enumerate(data[today], 1):
        mensaje += f"{i}. {user['nombre']} (ID: {user['id']})\n"

    await update.message.reply_text(mensaje)
