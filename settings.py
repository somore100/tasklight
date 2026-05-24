import json, os, sys
from config import DEFAULTS

def _app_dir():
    """
    Returns the directory where settings.json and presets/ should live.
    - When frozen (PyInstaller exe/AppImage): next to the executable
    - When running as script: next to main.py
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller sets sys.executable to the exe path
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

_PATH = os.path.join(_app_dir(), "settings.json")
_data = {}

def load():
    global _data
    _data = dict(DEFAULTS)
    if os.path.exists(_PATH):
        try:
            with open(_PATH) as f:
                _data.update(json.load(f))
        except Exception:
            pass

def save():
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, "w") as f:
            json.dump(_data, f, indent=2)
    except Exception:
        pass

def get(key):
    return _data.get(key, DEFAULTS.get(key))

def set(key, value):
    _data[key] = value
    save()

def get_preset_folder():
    folder = get("preset_folder")
    if not folder:
        folder = os.path.join(_app_dir(), "presets")
    os.makedirs(folder, exist_ok=True)
    return folder
