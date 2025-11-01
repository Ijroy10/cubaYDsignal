# Ejemplo de cómo leer variables del .env en cualquier archivo Python

import os
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
QUOTEX_EMAIL = os.getenv("QUOTEX_EMAIL")
QUOTEX_PASSWORD = os.getenv("QUOTEX_PASSWORD")

print("Bot token:", BOT_TOKEN)
print("Admin ID:", ADMIN_ID)
print("Quotex email:", QUOTEX_EMAIL)
print("Quotex password:", QUOTEX_PASSWORD)