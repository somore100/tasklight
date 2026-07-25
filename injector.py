"""
injector.py — Input injection backend
──────────────────────────────────────
Backend priority:
  1. evdev/uinput REL — works in games using raw input (Minecraft, Roblox)
  2. pyautogui/X11   — fallback for desktop apps

Key insight: games use RAW INPUT which reads REL_X/REL_Y delta events,
not ABS_X/ABS_Y absolute coordinates. We track last position and send
the delta so games see natural relative movement.

One-time Linux setup:
  sudo usermod -a -G input $USER
  sudo chmod 660 /dev/uinput
  echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-uinput.rules
  sudo udevadm control --reload-rules
  # log out and back in
"""

import time, platform

PLATFORM = platform.system().lower()
BACKEND  = "pyautogui"

_uinput_mouse    = None
_uinput_keyboard = None
_last_x          = 0
_last_y          = 0


def setup():
    global BACKEND, _uinput_mouse, _uinput_keyboard, _last_x, _last_y

    if PLATFORM != "linux":
        BACKEND = "pyautogui"
        return

    try:
        import evdev
        from evdev import UInput, ecodes as e

        # REL-only mouse — exactly what games expect from raw input
        mouse_cap = {
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL],
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
        }
        _uinput_mouse = UInput(mouse_cap, name="tasklight-mouse", version=0x3)

        key_cap = {e.EV_KEY: list(range(1, 256))}
        _uinput_keyboard = UInput(key_cap, name="tasklight-keyboard", version=0x3)

        # seed position
        try:
            import pyautogui
            _last_x, _last_y = pyautogui.position()
        except:
            _last_x, _last_y = 960, 540

        BACKEND = "evdev"

    except Exception:
        BACKEND = "pyautogui"


def get_backend():
    return BACKEND


# ── key name → evdev keycode ──────────────────────────────────────────────────

_KEY_MAP = {
    **{c: f"KEY_{c.upper()}" for c in "abcdefghijklmnopqrstuvwxyz"},
    **{str(n): f"KEY_{n}" for n in range(10)},
    "space":     "KEY_SPACE",   " ":         "KEY_SPACE",
    "enter":     "KEY_ENTER",   "return":    "KEY_ENTER",
    "shift":     "KEY_LEFTSHIFT","lshift":   "KEY_LEFTSHIFT",
    "rshift":    "KEY_RIGHTSHIFT",
    "ctrl":      "KEY_LEFTCTRL","lctrl":    "KEY_LEFTCTRL",
    "rctrl":     "KEY_RIGHTCTRL",
    "alt":       "KEY_LEFTALT", "lalt":     "KEY_LEFTALT",
    "ralt":      "KEY_RIGHTALT",
    "tab":       "KEY_TAB",     "escape":   "KEY_ESC",
    "esc":       "KEY_ESC",     "backspace":"KEY_BACKSPACE",
    "delete":    "KEY_DELETE",  "up":       "KEY_UP",
    "down":      "KEY_DOWN",    "left":     "KEY_LEFT",
    "right":     "KEY_RIGHT",   "home":     "KEY_HOME",
    "end":       "KEY_END",     "pageup":   "KEY_PAGEUP",
    "pagedown":  "KEY_PAGEDOWN","capslock": "KEY_CAPSLOCK",
    **{f"f{n}": f"KEY_F{n}" for n in range(1, 13)},
    # pynput name format
    "key.space":     "KEY_SPACE",   "key.enter":  "KEY_ENTER",
    "key.tab":       "KEY_TAB",     "key.shift":  "KEY_LEFTSHIFT",
    "key.ctrl":      "KEY_LEFTCTRL","key.alt":    "KEY_LEFTALT",
    "key.esc":       "KEY_ESC",     "key.backspace":"KEY_BACKSPACE",
    "key.delete":    "KEY_DELETE",  "key.up":     "KEY_UP",
    "key.down":      "KEY_DOWN",    "key.left":   "KEY_LEFT",
    "key.right":     "KEY_RIGHT",   "key.caps_lock":"KEY_CAPSLOCK",
    **{f"key.f{n}": f"KEY_F{n}" for n in range(1, 13)},
}

def _ekc(name):
    try:
        from evdev import ecodes as e
        name   = str(name).lower().strip()
        mapped = _KEY_MAP.get(name, f"KEY_{name.upper()}")
        return getattr(e, mapped, None)
    except: return None


# ── mouse ─────────────────────────────────────────────────────────────────────

def move(x, y):
    """Move to absolute position — sends REL delta so games register it."""
    global _last_x, _last_y
    dx = int(x) - _last_x
    dy = int(y) - _last_y

    if BACKEND == "evdev" and _uinput_mouse:
        try:
            from evdev import ecodes as e
            if dx != 0: _uinput_mouse.write(e.EV_REL, e.REL_X, dx)
            if dy != 0: _uinput_mouse.write(e.EV_REL, e.REL_Y, dy)
            if dx != 0 or dy != 0: _uinput_mouse.syn()
            _last_x, _last_y = int(x), int(y)
            return
        except: pass

    import pyautogui
    try:
        pyautogui.moveTo(int(x), int(y), duration=0)
        _last_x, _last_y = int(x), int(y)
    except: pass


def move_smooth(tx, ty, steps=8):
    """Smooth interpolated move — each step sends a REL delta."""
    sx, sy = _last_x, _last_y
    for i in range(1, steps + 1):
        t  = i / steps
        nx = int(sx + (tx - sx) * t)
        ny = int(sy + (ty - sy) * t)
        move(nx, ny)
        time.sleep(0.008)


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
