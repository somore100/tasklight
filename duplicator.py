"""
duplicator.py — Click Duplicator with left/right/both support
"""
import time, random, threading
import pyautogui, state, settings

pyautogui.PAUSE = 0

class DupState:
    solo_active = False
    _listener   = None

dup_state = DupState()

def _fire_extras(x, y, count, gap_ms, mode, use_jitter, button="left"):
    if count <= 0 or gap_ms <= 0: return
    gap_s = gap_ms / 1000.0

    if mode == "even":
        delays = [gap_s / (count+1) * (i+1) for i in range(count)]
    else:
        delays = sorted(random.uniform(0.01, gap_s*0.9) for _ in range(count))

    last = 0.0
    for d in delays:
        wait = d - last
        if wait > 0: time.sleep(wait)
        last = d

        cx, cy = x, y
        if use_jitter:
            try:
                import humanizer
                cx, cy = humanizer.addon_jitter(x, y)
            except: pass

        try:
            pyautogui.FAILSAFE = settings.get("failsafe")
            # handle "both" — alternate
            if button == "both":
                btn = pyautogui.LEFT if int(time.time()*1000) % 2 == 0 else pyautogui.RIGHT
            elif button == "right":
                btn = pyautogui.RIGHT
            else:
                btn = pyautogui.LEFT
            pyautogui.click(int(cx), int(cy), button=btn)
        except pyautogui.FailSafeException: pass
        except Exception: pass


def addon_duplicate(x, y, button="left", after_delay_ms=None):
    count  = int(settings.get("dup_count") or 1)
    gap_ms = float(after_delay_ms or settings.get("dup_gap_ms") or 80)
    mode   = settings.get("dup_mode") or "random"
    jitter = settings.get("dup_use_jitter") or False
    btn    = settings.get("dup_button") or "same"
    # "same" = match the original click button
    if btn == "same": btn = button

    threading.Thread(
        target=_fire_extras,
        args=(x, y, count, gap_ms, mode, jitter, btn),
        daemon=True
    ).start()


def start_solo():
    from pynput import mouse as _m
    dup_state.solo_active = True

    def on_click(x, y, button, pressed):
        if not dup_state.solo_active: return False
        if pressed:
            count  = int(settings.get("dup_count") or 1)
            gap_ms = float(settings.get("dup_gap_ms") or 80)
            mode   = settings.get("dup_mode") or "random"
            jitter = settings.get("dup_use_jitter") or False
            btn_setting = settings.get("dup_button") or "same"
            btn = button.name if btn_setting == "same" else btn_setting
            threading.Thread(
                target=_fire_extras,
                args=(x, y, count, gap_ms, mode, jitter, btn),
                daemon=True
            ).start()

    dup_state._listener = _m.Listener(on_click=on_click)
    dup_state._listener.daemon = True
    dup_state._listener.start()


def stop_solo():
    dup_state.solo_active = False
    if dup_state._listener:
        try: dup_state._listener.stop()
        except: pass
        dup_state._listener = None


def toggle_solo():
    if dup_state.solo_active: stop_solo()
    else: start_solo()
