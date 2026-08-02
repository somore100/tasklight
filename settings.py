import json, os, sys
from config import DEFAULTS

def _app_dir():
    """
    Returns a WRITABLE directory for settings.json and presets/.

    Priority:
      1. AppImage: $APPIMAGE env var → directory next to the .AppImage file
      2. Frozen exe (Windows): next to the .exe
      3. Script: next to main.py
      4. Fallback: ~/.tasklight/
    """
    # AppImage sets $APPIMAGE to the actual .AppImage file path
    appimage_path = os.environ.get("APPIMAGE", "")
    if appimage_path and os.path.isfile(appimage_path):
        return os.path.dirname(os.path.abspath(appimage_path))

    if getattr(sys, "frozen", False):
        # PyInstaller .exe — sys.executable is the exe file
        candidate = os.path.dirname(sys.executable)
        # sanity check it's writable
        if os.access(candidate, os.W_OK):
            return candidate

    # Running as script
    candidate = os.path.dirname(os.path.abspath(__file__))
    if os.access(candidate, os.W_OK):
        return candidate

    # Last resort: ~/.tasklight/
    fallback = os.path.join(os.path.expanduser("~"), ".tasklight")
    os.makedirs(fallback, exist_ok=True)
    return fallback


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
