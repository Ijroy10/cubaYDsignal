from telegram import Update
from telegram.ext import ContextTypes
from utils.keys import save_public_key
from data.config import get_admin_id  # ✅ Importamos el ID desde config.json

async def set_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = get_admin_id()  # ✅ Obtenemos el admin correctamente

    if update.effective_user.id != admin_id:
        await update.message.reply_text("🚫 No tienes permisos para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Usa el comando así:\n/setclave <clave>")
        return

    nueva_clave = " ".join(context.args)
    save_public_key(nueva_clave)

    await update.message.reply_text(f"✅ Clave pública del día actualizada:\n🔑 {nueva_clave}")