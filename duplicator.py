"""
duplicator.py — Click Duplicator
Fires N extra clicks within the gap after a real click.
Fixed: guard against overlapping threads at high counts.
"""
import time, random, threading
import pyautogui, state, settings

pyautogui.PAUSE = 0

class DupState:
    solo_active  = False
    _listener    = None
    _firing      = False   # guard: only one fire thread at a time

dup_state = DupState()

def _fire_extras(x, y, count, gap_ms, mode, use_jitter, button="left"):
    if dup_state._firing: return   # already firing, skip this one
    dup_state._firing = True
    try:
        if count <= 0 or gap_ms <= 0: return
        count  = min(count, 4)      # hard cap at 4
        gap_s  = gap_ms / 1000.0

        if mode == "even":
            delays = [gap_s / (count+1) * (i+1) for i in range(count)]
        else:
            delays = sorted(random.uniform(0.01, gap_s * 0.85) for _ in range(count))

        last = 0.0
        for d in delays:
            if state.stop_flag or state.quit_flag: break
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
                import injector
                if button == "both":
                    btn = "left" if int(time.time()*1000) % 2 == 0 else "right"
                else:
                    btn = button
                injector.mouse_down(int(cx), int(cy), btn)
                time.sleep(random.uniform(0.02, 0.06))
                injector.mouse_up(int(cx), int(cy), btn)
            except Exception: pass
    finally:
        dup_state._firing = False


def addon_duplicate(x, y, button="left", after_delay_ms=None):
    if dup_state._firing: return   # don't stack
    count  = int(settings.get("dup_count") or 1)
    gap_ms = float(after_delay_ms or settings.get("dup_gap_ms") or 80)
    mode   = settings.get("dup_mode") or "random"
    jitter = settings.get("dup_use_jitter") or False
    btn    = settings.get("dup_button") or "same"
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
        if pressed and not dup_state._firing:
            count  = int(settings.get("dup_count") or 1)
            gap_ms = float(settings.get("dup_gap_ms") or 80)
            mode   = settings.get("dup_mode") or "random"
            jitter = settings.get("dup_use_jitter") or False
            btn_s  = settings.get("dup_button") or "same"
            btn    = button.name if btn_s == "same" else btn_s
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
