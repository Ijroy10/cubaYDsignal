from telegram import Update
from telegram.ext import ContextTypes
from utils.keys import get_today_public_key
from data.usuarios_clave import registrar_usuario, esta_bloqueado_hoy


clave_actual = get_today_public_key()

async def verificar_clave_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    user_text = update.message.text.strip()
    clave_actual = get_today_public_key()

    if user_text == clave_actual:
        if esta_bloqueado_hoy(user_id):
            await update.message.reply_text("🚫 Has sido bloqueado del acceso a la clave de hoy.")
            return

        registrado = registrar_usuario(user_id, user_name)
        if registrado:
            await update.message.reply_text("✅ ¡Clave correcta! Ahora tienes acceso a las señales del día.")
        else:
            await update.message.reply_text("⚠️ Ya estabas registrado para hoy.")
    else:
        await update.message.reply_text(
            "🚫 Clave incorrecta detectada.\n"
            "La frase ingresada no coincide con la clave activa del día.\n\n"
            "🔑 Contacta a tu líder para obtener la clave correcta.\n"
            "🚀 *CubaYDsignal – Donde la disciplina vence a la suerte!*"
        )