import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def read_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def write_config(data):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def get_bot_token():
    return read_config().get('BOT_TOKEN')

def get_master_key():
    return read_config().get('MASTER_KEY')

def get_public_key():
    return read_config().get('PUBLIC_KEY')

def get_admin_id():
    return read_config().get('ADMIN_ID')

def set_public_key(new_key):
    data = read_config()
    data['PUBLIC_KEY'] = new_key
    write_config(data)