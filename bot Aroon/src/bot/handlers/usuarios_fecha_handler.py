from telegram import Update
from telegram.ext import ContextTypes
import json
import os

HISTORIAL_FILE = os.path.join(os.path.dirname(__file__), '../data/historial_usuarios.json')

async def usuarios_fecha_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❗ Usa el comando así: /usuariosfecha YYYY-MM-DD")
        return

    fecha = context.args[0]

    if not os.path.exists(HISTORIAL_FILE):
        await update.message.reply_text("📭 No hay historial disponible.")
        return

    with open(HISTORIAL_FILE, 'r') as f:
        try:
            historial = json.load(f)
        except json.JSONDecodeError:
            historial = {}

    if fecha not in historial:
        await update.message.reply_text(f"📭 No hay usuarios registrados el día {fecha}.")
        return

    usuarios = historial[fecha]
    texto = f"📅 Usuarios registrados el {fecha}:\n\n"
    for usuario in usuarios:
        texto += f"• {usuario['nombre']} (ID: {usuario['id']})\n"

    await update.message.reply_text(texto)



