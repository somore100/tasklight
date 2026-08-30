"""
injector.py
───────────
Mouse:    pyautogui only (evdev mouse creates a visible second cursor on X11)
Keyboard: evdev/uinput if available (game raw input), pyautogui fallback

This gives us:
  - No double cursor
  - Keyboard works in games (evdev kernel-level)
  - Mouse moves/clicks work everywhere (pyautogui X11)
"""
import time, platform
import pyautogui

PLATFORM   = platform.system().lower()
KB_BACKEND = "pyautogui"   # "evdev" | "pyautogui"

_uinput_keyboard = None

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0


def setup():
    global KB_BACKEND, _uinput_keyboard

    if PLATFORM != "linux":
        KB_BACKEND = "pyautogui"
        return

    try:
        import evdev
        from evdev import UInput, ecodes as e

        key_cap = {e.EV_KEY: list(range(1, 256))}
        _uinput_keyboard = UInput(key_cap, name="tasklight-keyboard", version=0x3)
        KB_BACKEND = "evdev"

    except Exception:
        KB_BACKEND = "pyautogui"


def get_backend():
    return f"mouse=pyautogui kb={KB_BACKEND}"


# ── key mapping ───────────────────────────────────────────────────────────────

_KEY_MAP = {
    **{c: f"KEY_{c.upper()}" for c in "abcdefghijklmnopqrstuvwxyz"},
    **{str(n): f"KEY_{n}" for n in range(10)},
    "space":      "KEY_SPACE",    " ":           "KEY_SPACE",
    "enter":      "KEY_ENTER",    "return":      "KEY_ENTER",
    "shift":      "KEY_LEFTSHIFT","lshift":      "KEY_LEFTSHIFT",
    "rshift":     "KEY_RIGHTSHIFT",
    "ctrl":       "KEY_LEFTCTRL", "lctrl":       "KEY_LEFTCTRL",
    "rctrl":      "KEY_RIGHTCTRL",
    "alt":        "KEY_LEFTALT",  "lalt":        "KEY_LEFTALT",
    "ralt":       "KEY_RIGHTALT",
    "tab":        "KEY_TAB",      "escape":      "KEY_ESC",
    "esc":        "KEY_ESC",      "backspace":   "KEY_BACKSPACE",
    "delete":     "KEY_DELETE",   "up":          "KEY_UP",
    "down":       "KEY_DOWN",     "left":        "KEY_LEFT",
    "right":      "KEY_RIGHT",    "home":        "KEY_HOME",
    "end":        "KEY_END",      "pageup":      "KEY_PAGEUP",
    "pagedown":   "KEY_PAGEDOWN", "capslock":    "KEY_CAPSLOCK",
    **{f"f{n}": f"KEY_F{n}" for n in range(1, 13)},
    # numpad
    **{f"num{n}": f"KEY_KP{n}" for n in range(10)},
    "numplus":  "KEY_KPPLUS",   "numminus": "KEY_KPMINUS",
    "numstar":  "KEY_KPASTERISK","numslash": "KEY_KPSLASH",
    "numdot":   "KEY_KPDOT",    "numenter": "KEY_KPENTER",
    "numlock":  "KEY_NUMLOCK",
    "key.space":    "KEY_SPACE",   "key.enter":   "KEY_ENTER",
    "key.tab":      "KEY_TAB",     "key.shift":   "KEY_LEFTSHIFT",
    "key.ctrl":     "KEY_LEFTCTRL","key.alt":     "KEY_LEFTALT",
    "key.esc":      "KEY_ESC",     "key.backspace":"KEY_BACKSPACE",
    "key.delete":   "KEY_DELETE",  "key.up":      "KEY_UP",
    "key.down":     "KEY_DOWN",    "key.left":    "KEY_LEFT",
    "key.right":    "KEY_RIGHT",   "key.caps_lock":"KEY_CAPSLOCK",
    **{f"key.f{n}": f"KEY_F{n}" for n in range(1, 13)},
}

def _ekc(name):
    try:
        from evdev import ecodes as e
        name   = str(name).lower().strip()
        mapped = _KEY_MAP.get(name, f"KEY_{name.upper()}")
        return getattr(e, mapped, None)
    except: return None


# ── mouse — pyautogui only ────────────────────────────────────────────────────

def move(x, y):
    try: pyautogui.moveTo(int(x), int(y), duration=0)
    except: pass

def move_smooth(tx, ty, steps=8):
    try:
        sx, sy = pyautogui.position()
    except:
        sx, sy = tx, ty
    for i in range(1, steps + 1):
        t = i / steps
        move(int(sx + (tx-sx)*t), int(sy + (ty-sy)*t))
        time.sleep(0.008)

def mouse_down(x, y, button="left"):
    move(x, y)
    time.sleep(0.008)
    btn = pyautogui.RIGHT if button == "right" else pyautogui.LEFT
    try: pyautogui.mouseDown(x=int(x), y=int(y), button=btn)
    except: pass

def mouse_up(x, y, button="left"):
    btn = pyautogui.RIGHT if button == "right" else pyautogui.LEFT
    try: pyautogui.mouseUp(x=int(x), y=int(y), button=btn)
    except: pass

def click(x, y, button="left", hold_s=0.05):
    mouse_down(x, y, button)
    if hold_s > 0: time.sleep(hold_s)
    mouse_up(x, y, button)


# ── keyboard ──────────────────────────────────────────────────────────────────

def key_down(name):
    if KB_BACKEND == "evdev" and _uinput_keyboard:
        try:
            from evdev import ecodes as e
            code = _ekc(name)
            if code is not None:
                _uinput_keyboard.write(e.EV_KEY, code, 1)
                _uinput_keyboard.syn()
                return
        except: pass
    try: pyautogui.keyDown(str(name))
    except: pass

def key_up(name):
    if KB_BACKEND == "evdev" and _uinput_keyboard:
        try:
            from evdev import ecodes as e
            code = _ekc(name)
            if code is not None:
                _uinput_keyboard.write(e.EV_KEY, code, 0)
                _uinput_keyboard.syn()
                return
        except: pass
    try: pyautogui.keyUp(str(name))
    except: pass

def key_press(name, hold_s=0.05):
    key_down(name)
    if hold_s > 0: time.sleep(hold_s)
    key_up(name)


# ── release all held keys ─────────────────────────────────────────────────────

def release_all():
    """Release everything — called on stop."""
    if KB_BACKEND == "evdev" and _uinput_keyboard:
        try:
            from evdev import ecodes as e
            for code in range(1, 256):
                try: _uinput_keyboard.write(e.EV_KEY, code, 0)
                except: pass
            _uinput_keyboard.syn()
        except: pass
    # also release common pyautogui keys just in case
    for k in ["shift","ctrl","alt","w","a","s","d","space","lshift","rshift"]:
        try: pyautogui.keyUp(k)
        except: pass
    # release mouse buttons
    for btn in [pyautogui.LEFT, pyautogui.RIGHT]:
        try: pyautogui.mouseUp(button=btn)
        except: pass


def close():
    release_all()
    global _uinput_keyboard
    if _uinput_keyboard:
        try: _uinput_keyboard.close()
        except: pass
        _uinput_keyboard = None

def reset():
    """Release all inputs. Don't recreate devices — avoids double cursor."""
    release_all()
