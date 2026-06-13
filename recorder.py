from pynput import mouse, keyboard
import time, state, settings

def _is_hotkey(key_name):
    hks = [
        settings.get("hk_record"), settings.get("hk_play"),
        settings.get("hk_stop"),   settings.get("hk_quit"),
        settings.get("hk_jitter_solo"), settings.get("hk_clicker_solo"),
        settings.get("hk_net_blocker"), settings.get("hk_dup_solo"),
    ]
    return str(key_name).lower().strip() in [str(h).lower().strip() for h in hks if h]

def start_recording():
    state.events       = []
    state.is_recording = True

    def on_move(x, y):
        if state.is_recording:
            state.events.append(("move", x, y, time.time()))

    def on_click(x, y, button, pressed):
        if state.is_recording:
            state.events.append(("click", x, y, button.name, pressed, time.time()))

    def on_key_press(key):
        if state.is_recording:
            try:    name = key.char
            except: name = key.name
            if _is_hotkey(name): return
            state.events.append(("key_down", name, time.time()))

    def on_key_release(key):
        if state.is_recording:
            try:    name = key.char
            except: name = key.name
            if _is_hotkey(name): return
            state.events.append(("key_up", name, time.time()))

    ml = mouse.Listener(on_move=on_move, on_click=on_click)
    kl = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    ml.start(); kl.start()
    return ml, kl

def stop_recording(ml, kl):
    state.is_recording = False
    ml.stop(); kl.stop()
