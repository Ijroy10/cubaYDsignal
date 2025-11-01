from messages.responses import acceso_correcto, acceso_rechazado, solicitar_clave_publica
from utils.logger import guardar_autorizado
import json
from data.config import CONFIG_PATH

async def handle_admin_auth(update, context):
    user_input = update.message.text
    if user_input == "Ijroy010702$Yorji050212":  # Clave maestra
        guardar_autorizado(update.effective_user.id)
        await update.message.reply_text("🔓 Acceso de administrador concedido.")
        return

async def handle_user_key(update, context):
    user_input = update.message.text
    if user_input == "CLAVE_PUBLICA_DEL_DIA":
        guardar_autorizado(update.effective_user.id)
        await update.message.reply_text(acceso_correcto)
    else:
        await update.message.reply_text(acceso_rechazado)