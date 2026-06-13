"""
injector.py — Input injection backend
──────────────────────────────────────
Tries backends in order of game compatibility:

  1. evdev/uinput  — kernel-level, works with raw input games (Minecraft, Roblox)
  2. pyautogui     — X11/XTest fallback, works for most desktop apps

One-time setup on Linux (run once, then reboot/relogin):
  sudo usermod -a -G input $USER
  sudo chmod 660 /dev/uinput
  echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-uinput.rules
  sudo udevadm control --reload-rules
  # then log out and back in
"""

import time, platform

PLATFORM = platform.system().lower()
BACKEND  = "pyautogui"

_uinput_mouse    = None
_uinput_keyboard = None
_abs_x_max       = 1920
_abs_y_max       = 1080


# ── setup ─────────────────────────────────────────────────────────────────────

def setup():
    """Detect best backend. Call once at startup."""
    global BACKEND, _uinput_mouse, _uinput_keyboard, _abs_x_max, _abs_y_max

    if PLATFORM != "linux":
        BACKEND = "pyautogui"
        return

    try:
        import evdev
        from evdev import UInput, AbsInfo, ecodes as e
        import subprocess, re

        # detect screen size
        try:
            out = subprocess.check_output(["xrandr"], stderr=subprocess.DEVNULL).decode()
            m = re.search(r"current (\d+) x (\d+)", out)
            if m:
                _abs_x_max = int(m.group(1))
                _abs_y_max = int(m.group(2))
        except: pass

        mouse_cap = {
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL],
            e.EV_ABS: [
                (e.ABS_X, AbsInfo(0, 0, _abs_x_max, 0, 0, 0)),
                (e.ABS_Y, AbsInfo(0, 0, _abs_y_max, 0, 0, 0)),
            ],
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
        }
        _uinput_mouse = UInput(mouse_cap, name="tasklight-mouse", version=0x3)

        key_cap = {e.EV_KEY: list(range(1, 256))}
        _uinput_keyboard = UInput(key_cap, name="tasklight-keyboard", version=0x3)

        BACKEND = "evdev"

    except Exception as ex:
        BACKEND = "pyautogui"


def get_backend():
    return BACKEND


# ── key name → evdev code ─────────────────────────────────────────────────────

_KEY_MAP = {
    **{c: f"KEY_{c.upper()}" for c in "abcdefghijklmnopqrstuvwxyz"},
    **{str(n): f"KEY_{n}" for n in range(10)},
    "space": "KEY_SPACE", " ": "KEY_SPACE",
    "enter": "KEY_ENTER", "return": "KEY_ENTER",
    "shift": "KEY_LEFTSHIFT", "lshift": "KEY_LEFTSHIFT",
    "rshift": "KEY_RIGHTSHIFT",
    "ctrl": "KEY_LEFTCTRL", "lctrl": "KEY_LEFTCTRL",
    "rctrl": "KEY_RIGHTCTRL",
    "alt": "KEY_LEFTALT", "lalt": "KEY_LEFTALT", "ralt": "KEY_RIGHTALT",
    "tab": "KEY_TAB", "escape": "KEY_ESC", "esc": "KEY_ESC",
    "backspace": "KEY_BACKSPACE", "delete": "KEY_DELETE",
    "up": "KEY_UP", "down": "KEY_DOWN",
    "left": "KEY_LEFT", "right": "KEY_RIGHT",
    "home": "KEY_HOME", "end": "KEY_END",
    "pageup": "KEY_PAGEUP", "pagedown": "KEY_PAGEDOWN",
    **{f"f{n}": f"KEY_F{n}" for n in range(1, 13)},
    "capslock": "KEY_CAPSLOCK",
    "key.f1":"KEY_F1","key.f2":"KEY_F2","key.f3":"KEY_F3","key.f4":"KEY_F4",
    "key.f5":"KEY_F5","key.f6":"KEY_F6","key.f7":"KEY_F7","key.f8":"KEY_F8",
    "key.f9":"KEY_F9","key.f10":"KEY_F10","key.f11":"KEY_F11","key.f12":"KEY_F12",
    "key.space":"KEY_SPACE","key.enter":"KEY_ENTER","key.tab":"KEY_TAB",
    "key.shift":"KEY_LEFTSHIFT","key.ctrl":"KEY_LEFTCTRL","key.alt":"KEY_LEFTALT",
    "key.esc":"KEY_ESC","key.backspace":"KEY_BACKSPACE","key.delete":"KEY_DELETE",
    "key.up":"KEY_UP","key.down":"KEY_DOWN","key.left":"KEY_LEFT","key.right":"KEY_RIGHT",
    "key.caps_lock":"KEY_CAPSLOCK",
}

def _ekc(name):
    """Convert key name to evdev keycode."""
    try:
        from evdev import ecodes as e
        name = str(name).lower().strip()
        mapped = _KEY_MAP.get(name, f"KEY_{name.upper()}")
        return getattr(e, mapped, None)
    except: return None


# ── mouse ─────────────────────────────────────────────────────────────────────

def move(x, y):
    if BACKEND == "evdev" and _uinput_mouse:
        try:
            from evdev import ecodes as e
            _uinput_mouse.write(e.EV_ABS, e.ABS_X, int(x))
            _uinput_mouse.write(e.EV_ABS, e.ABS_Y, int(y))
            _uinput_mouse.syn(); return
        except: pass
    import pyautogui
    try: pyautogui.moveTo(int(x), int(y), duration=0)
    except: pass


def move_smooth(tx, ty, steps=8):
    import pyautogui
    sx, sy = pyautogui.position()
    for i in range(1, steps + 1):
        t = i / steps
        nx = int(sx + (tx - sx) * t)
        ny = int(sy + (ty - sy) * t)
        move(nx, ny)
        time.sleep(0.01)


def mouse_down(x, y, button="left"):
    move(x, y)
    time.sleep(0.005)
    if BACKEND == "evdev" and _uinput_mouse:
        try:
            from evdev import ecodes as e
            btn = e.BTN_RIGHT if button == "right" else e.BTN_LEFT
            _uinput_mouse.write(e.EV_KEY, btn, 1)
            _uinput_mouse.syn(); return
        except: pass
    import pyautogui
    btn = pyautogui.RIGHT if button == "right" else pyautogui.LEFT
    try: pyautogui.mouseDown(x=int(x), y=int(y), button=btn)
    except: pass


def mouse_up(x, y, button="left"):
    if BACKEND == "evdev" and _uinput_mouse:
        try:
            from evdev import ecodes as e
            btn = e.BTN_RIGHT if button == "right" else e.BTN_LEFT
            _uinput_mouse.write(e.EV_KEY, btn, 0)
            _uinput_mouse.syn(); return
        except: pass
    import pyautogui
    btn = pyautogui.RIGHT if button == "right" else pyautogui.LEFT
    try: pyautogui.mouseUp(x=int(x), y=int(y), button=btn)
    except: pass


def click(x, y, button="left", hold_s=0.05):
    mouse_down(x, y, button)
    if hold_s > 0: time.sleep(hold_s)
    mouse_up(x, y, button)


# ── keyboard ──────────────────────────────────────────────────────────────────

def key_down(name):
    if BACKEND == "evdev" and _uinput_keyboard:
        try:
            from evdev import ecodes as e
            code = _ekc(name)
            if code is not None:
                _uinput_keyboard.write(e.EV_KEY, code, 1)
                _uinput_keyboard.syn(); return
        except: pass
    import pyautogui
    try: pyautogui.keyDown(str(name))
    except: pass


def key_up(name):
    if BACKEND == "evdev" and _uinput_keyboard:
        try:
            from evdev import ecodes as e
            code = _ekc(name)
            if code is not None:
                _uinput_keyboard.write(e.EV_KEY, code, 0)
                _uinput_keyboard.syn(); return
        except: pass
    import pyautogui
    try: pyautogui.keyUp(str(name))
    except: pass


def key_press(name, hold_s=0.05):
    key_down(name)
    if hold_s > 0: time.sleep(hold_s)
    key_up(name)


# ── cleanup ───────────────────────────────────────────────────────────────────

def close():
    for dev in [_uinput_mouse, _uinput_keyboard]:
        if dev:
            try: dev.close()
            except: pass
