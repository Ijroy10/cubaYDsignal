from telegram import Update
from telegram.ext import ContextTypes
from data.config import set_public_key, get_admin_id
from utils.keys import guardar_clave_publica_actual  # 👈 Importar función correcta

from data.usuarios_clave import (
    obtener_usuarios_hoy,
    eliminar_usuario_de_hoy,
    bloquear_usuario,
    desbloquear_usuario
)

# ✅ Establecer la clave pública
async def set_public_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != get_admin_id():
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Debes proporcionar una clave.\nEjemplo: /setclave 123456")
        return

    clave = context.args[0]

    set_public_key(clave)                  # Guarda en config.json
    guardar_clave_publica_actual(clave)   # Guarda en public_key.json

    await update.message.reply_text(f"✅ Clave pública del día establecida: {clave}")


# ✅ Obtener usuarios que han usado la clave hoy
async def obtener_usuarios_hoy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != get_admin_id():
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    usuarios = obtener_usuarios_hoy()
    if not usuarios:
        await update.message.reply_text("📭 Hoy aún nadie ha usado la clave.")
        return

    mensaje = f"👥 Usuarios que usaron la clave hoy: {len(usuarios)}\n\n"
    for usuario in usuarios:
        mensaje += f"• {usuario['nombre']} (ID: {usuario['id']})\n"

    await update.message.reply_text(mensaje)

# ✅ Eliminar un usuario del acceso de hoy
async def eliminar_usuario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != get_admin_id():
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Debes escribir el ID del usuario o su nombre exacto.\nEjemplo:\n/eliminar_usuario 123456789")
        return

    identificador = context.args[0]
    eliminado, nombre = eliminar_usuario_de_hoy(identificador)

    if eliminado:
        await update.message.reply_text(f"✅ Usuario eliminado: {nombre} (ID: {identificador})")
    else:
        await update.message.reply_text("❌ Usuario no encontrado en la lista de hoy.")

# ✅ Bloquear usuario
async def bloquear_usuario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != get_admin_id():
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Usa el comando así:\n/bloquear <user_id>")
        return

    user_id = context.args[0]
    bloquear_usuario(user_id)
    await update.message.reply_text(f"🚫 Usuario {user_id} ha sido bloqueado para hoy.")

# ✅ Desbloquear usuario
async def desbloquear_usuario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != get_admin_id():
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Usa el comando así:\n/desbloquear <user_id>")
        return

    user_id = context.args[0]
    desbloqueado = desbloquear_usuario(user_id)

    if desbloqueado:
        await update.message.reply_text(f"✅ Usuario {user_id} ha sido desbloqueado para hoy.")

        try:
            # Intentar notificar al usuario desbloqueado
            await context.bot.send_message(
                chat_id=int(user_id),
                text="✅ Has sido desbloqueado y ahora puedes volver a ingresar la clave pública."
            )
        except Exception as e:
            await update.message.reply_text("⚠️ Usuario desbloqueado, pero no se pudo enviar el mensaje (quizás bloqueó el bot o nunca lo inició).")
    else:
        await update.message.reply_text("❌ Ese usuario no estaba bloqueado o ya fue desbloqueado.")
