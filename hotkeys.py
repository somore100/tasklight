"""
hotkeys.py
──────────
Global hotkey / keybind-capture listener with two backends:

  evdev   – reads raw kernel input events directly from /dev/input/event*.
            Works identically under X11, Wayland (any compositor), or no
            display server at all. This is the listening counterpart to
            what injector.py already uses to *inject* key presses — same
            kernel-level approach, just reading instead of writing.
            Requires the running user to be able to read
            /dev/input/event* — usually membership in the "input" group
            (see BUILD_README.md).

  pynput  – X11 RECORD-extension based listener. Works fine on X11 and on
            Windows/macOS. On a native Wayland session it only sees keys
            pressed while an XWayland-backed window has focus, so hotkeys
            can silently stop firing whenever a native Wayland app is
            focused. Used as a fallback when evdev isn't available or we
            don't have permission to read input devices.

Both backends deliver already-normalized, lowercase string key names to
callbacks (e.g. "a", "1", "f6", "space", "ctrl", "shift", "alt", "super",
"num0".."num9", "numplus", "numminus", "numstar", "numslash", "numdot",
"numenter", "numlock"), so calling code never has to know — or care —
which backend is active.

Note: numpad digits are only distinguishable from the top-row digits on
the evdev backend, which has separate kernel key codes for them. The
pynput/X11 fallback generally cannot tell them apart (X11 usually
translates NumLock-on numpad digits to the same characters as the top
row), so under that fallback a numpad key may register as its top-row
equivalent — a pynput/X11 limitation, not something this module can fix.
"""
import platform, threading

PLATFORM = platform.system().lower()

_MODS = {"ctrl", "shift", "alt", "cmd", "super"}

# updated once a GlobalListener actually starts — read these for diagnostics/UI
BACKEND         = "pynput"
BACKEND_WARNING = ""


# ── name normalization ──────────────────────────────────────────────────────

def _evdev_code_map():
    """Build {evdev keycode -> normalized name}. Only call if evdev imports fine."""
    from evdev import ecodes as e
    m = {}
    for c in "abcdefghijklmnopqrstuvwxyz":
        code = getattr(e, f"KEY_{c.upper()}", None)
        if code is not None: m[code] = c
    for n in range(10):
        code = getattr(e, f"KEY_{n}", None)
        if code is not None: m[code] = str(n)
    for n in range(1, 13):
        code = getattr(e, f"KEY_F{n}", None)
        if code is not None: m[code] = f"f{n}"
    # numpad — distinct codes from evdev, so these are properly distinguishable
    # from the top-row digits (something the pynput/X11 fallback usually can't do)
    numpad = {
        "KEY_KP0": "num0", "KEY_KP1": "num1", "KEY_KP2": "num2",
        "KEY_KP3": "num3", "KEY_KP4": "num4", "KEY_KP5": "num5",
        "KEY_KP6": "num6", "KEY_KP7": "num7", "KEY_KP8": "num8",
        "KEY_KP9": "num9",
        "KEY_KPPLUS": "numplus", "KEY_KPMINUS": "numminus",
        "KEY_KPASTERISK": "numstar", "KEY_KPSLASH": "numslash",
        "KEY_KPDOT": "numdot", "KEY_KPENTER": "numenter",
        "KEY_NUMLOCK": "numlock",
    }
    for attr, name in numpad.items():
        code = getattr(e, attr, None)
        if code is not None: m[code] = name
    simple = {
        "KEY_SPACE": "space", "KEY_ENTER": "enter", "KEY_TAB": "tab",
        "KEY_ESC": "esc", "KEY_BACKSPACE": "backspace", "KEY_DELETE": "delete",
        "KEY_UP": "up", "KEY_DOWN": "down", "KEY_LEFT": "left", "KEY_RIGHT": "right",
        "KEY_HOME": "home", "KEY_END": "end",
        "KEY_PAGEUP": "pageup", "KEY_PAGEDOWN": "pagedown",
        "KEY_CAPSLOCK": "capslock",
    }
    for attr, name in simple.items():
        code = getattr(e, attr, None)
        if code is not None: m[code] = name
    # both sides of a modifier collapse to the same canonical name
    mods = {
        "KEY_LEFTCTRL": "ctrl",  "KEY_RIGHTCTRL": "ctrl",
        "KEY_LEFTSHIFT": "shift","KEY_RIGHTSHIFT": "shift",
        "KEY_LEFTALT": "alt",    "KEY_RIGHTALT": "alt",
        "KEY_LEFTMETA": "super", "KEY_RIGHTMETA": "super",
    }
    for attr, name in mods.items():
        code = getattr(e, attr, None)
        if code is not None: m[code] = name
    return m


def _pynput_key_name(key):
    """Normalize a pynput Key/KeyCode into the same scheme evdev produces."""
    try:
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        name = key.name.lower()
    except Exception:
        return ""
    for m in _MODS:
        if m in name:
            return m
    return name


# ── evdev backend ────────────────────────────────────────────────────────────

class _EvdevListener:
    def __init__(self, on_press=None, on_release=None):
        self._on_press  = on_press
        self._on_release = on_release
        self._devices   = []
        self._running   = False

    def _open_devices(self):
        import evdev
        from evdev import ecodes as e
        opened = []
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities().get(e.EV_KEY, [])
                # heuristic: only keep devices that look like real keyboards
                if e.KEY_A in caps and e.KEY_ENTER in caps:
                    opened.append(dev)
                else:
                    dev.close()
            except Exception:
                continue
        return opened

    def start(self):
        code_map = _evdev_code_map()
        self._devices = self._open_devices()
        if not self._devices:
            raise RuntimeError("no readable keyboard input devices")
        self._running = True
        for dev in self._devices:
            threading.Thread(target=self._read_loop, args=(dev, code_map),
                              daemon=True).start()

    def _read_loop(self, dev, code_map):
        from evdev import ecodes as e
        try:
            for event in dev.read_loop():
                if not self._running: break
                if event.type != e.EV_KEY: continue
                if event.value == 2: continue  # ignore autorepeat
                name = code_map.get(event.code)
                if not name: continue
                if event.value == 1 and self._on_press:
                    self._on_press(name)
                elif event.value == 0 and self._on_release:
                    self._on_release(name)
        except Exception:
            pass  # device unplugged / closed — just let the thread end

    def stop(self):
        self._running = False
        for dev in self._devices:
            try: dev.close()
            except Exception: pass
        self._devices = []


# ── pynput fallback backend ─────────────────────────────────────────────────

class _PynputListener:
    def __init__(self, on_press=None, on_release=None):
        self._on_press  = on_press
        self._on_release = on_release
        self._listener  = None

    def start(self):
        from pynput import keyboard as kb
        def _press(key):
            if self._on_press: self._on_press(_pynput_key_name(key))
        def _release(key):
            if self._on_release: self._on_release(_pynput_key_name(key))
        self._listener = kb.Listener(on_press=_press, on_release=_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            try: self._listener.stop()
            except Exception: pass
            self._listener = None


# ── backend probing / selection ─────────────────────────────────────────────

def _evdev_probe():
    """Returns 'ok' if we can read at least one keyboard device, else a
    short reason string. Only meaningful on Linux."""
    if PLATFORM != "linux":
        return "not-linux"
    try:
        tmp = _EvdevListener()
        devs = tmp._open_devices()
        for d in devs:
            try: d.close()
            except Exception: pass
        return "ok" if devs else "no-permission"
    except Exception:
        return "unavailable"


class GlobalListener:
    """Drop-in global key listener. Delivers normalized lowercase string key
    names to on_press/on_release callbacks. Uses evdev on Linux when the
    keyboard device(s) are readable, otherwise falls back to pynput."""

    def __init__(self, on_press=None, on_release=None):
        self._on_press  = on_press
        self._on_release = on_release
        self._impl = None

    def start(self):
        global BACKEND, BACKEND_WARNING
        probe = _evdev_probe()
        if probe == "ok":
            try:
                impl = _EvdevListener(self._on_press, self._on_release)
                impl.start()
                self._impl = impl
                BACKEND, BACKEND_WARNING = "evdev", ""
                return
            except Exception:
                self._impl = None  # fall through to pynput below

        if PLATFORM == "linux" and probe in ("no-permission", "unavailable"):
            BACKEND_WARNING = (
                "Can't read /dev/input/event* — hotkeys are using the X11 "
                "fallback and won't fire while a native Wayland app is "
                "focused. Add your user to the 'input' group and log out/in "
                "to fix this (see BUILD_README.md)."
            )

        impl = _PynputListener(self._on_press, self._on_release)
        impl.start()
        self._impl = impl
        BACKEND = "pynput"

    def stop(self):
        if self._impl:
            self._impl.stop()
            self._impl = None
