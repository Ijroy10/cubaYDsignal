import json
from data.config import CONFIG_PATH

def guardar_autorizado(user_id):
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    if user_id not in data:
        data.append(user_id)
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f)

def setup_logging():
    print("🟢 Logger iniciado.")