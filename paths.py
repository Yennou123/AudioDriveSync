# paths.py
import os

APP_NAME = "AudioDriveSync"

def get_base_dir():
    return os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), APP_NAME)

def get_log_dir():
    path = os.path.join(get_base_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path

def get_config_file():
    base = get_base_dir()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "config.json")

def get_uploaded_db():
    base = get_base_dir()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "uploaded_files.json")

def get_token_file():
    base = get_base_dir()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "token.pickle")
