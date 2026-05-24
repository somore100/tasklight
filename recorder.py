from pynput import mouse, keyboard
import time, state

def start_recording():
    state.events       = []
    state.is_recording = True

    def on_move(x, y):
        if state.is_recording:
            state.events.append(("move", x, y, time.time()))

    def on_click(x, y, button, pressed):
        if state.is_recording:
            state.events.append(("click", x, y, button.name, pressed, time.time()))

    def on_key(key):
        if state.is_recording:
            try:    state.events.append(("key", key.char, time.time()))
            except: state.events.append(("key", key.name, time.time()))

    ml = mouse.Listener(on_move=on_move, on_click=on_click)
    kl = keyboard.Listener(on_press=on_key)
    ml.start(); kl.start()
    return ml, kl

def stop_recording(ml, kl):
    state.is_recording = False
    ml.stop(); kl.stop()
