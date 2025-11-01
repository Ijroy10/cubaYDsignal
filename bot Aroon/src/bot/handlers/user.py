from telegram import Update
from telegram.ext import ContextTypes
from utils.keys import cargar_clave_publica_actual
from data.user_data import registrar_usuario, usuario_ya_registrado
from send_telegram import send_telegram_message

# Reemplaza esto por tu chat ID de Telegram (como admin)
ADMIN_CHAT_ID = 5806367733  # Ejemplo: 123456789


async def verificar_clave_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    user_id = update.effective_user.id

    # Cargar la clave correcta del día actual
    clave_correcta = cargar_clave_publica_actual()

    if not clave_correcta:
        await update.message.reply_text(
            "⚠️ No hay una clave pública activa para hoy.\n"
            "Contacta con el administrador para que la configure."
        )
        return

    if texto == clave_correcta:
        if usuario_ya_registrado(user_id):
            await update.message.reply_text("✅ Ya estás registrado para hoy.\n¡Prepárate para las señales!")
        else:
            registrar_usuario(user_id, update.effective_user.full_name)
            await update.message.reply_text("🔓 Acceso concedido.\n¡Bienvenido a CubaYDsignal!")
        # Notificar al admin cada vez que un usuario use la clave correctamente
        usuario = update.effective_user
        mensaje = (
            f"🔔 El usuario @{usuario.username or usuario.id} "
            f"({usuario.full_name}) usó la clave del día correctamente."
        )
        send_telegram_message(mensaje, chat_id=ADMIN_CHAT_ID)
    else:
        await update.message.reply_text(
            "🚫 Clave incorrecta detectada.\n"
            "La frase ingresada no coincide con la clave activa del día.\n"
            "‼️ Tu acceso a las señales ha sido pausado temporalmente.\n\n"
            "🔑 Ponte en contacto con tu líder o administrador para recuperar el acceso.\n"
            "🚀 CubaYDsignal – ¡Donde la disciplina vence a la suerte!"
        )
