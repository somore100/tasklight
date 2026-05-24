import time, random, threading
import pyautogui, state, settings

pyautogui.PAUSE = 0

def _fs(): return settings.get("failsafe")

def addon_jitter(x, y):
    px  = int(settings.get("jitter_px"))
    mx  = int(settings.get("jitter_max"))
    agg = float(settings.get("jitter_aggression"))
    scale = agg / 10.0
    lo = -int(px * scale); hi = int(px * scale)
    if lo == hi: lo, hi = -1, 1
    rx = max(-mx, min(mx, random.randint(lo, hi)))
    ry = max(-mx, min(mx, random.randint(lo, hi)))
    return x + rx, y + ry

def addon_delay():
    time.sleep(random.uniform(float(settings.get("delay_min")),
                              float(settings.get("delay_max"))))

def addon_smooth_move(tx, ty):
    steps = int(settings.get("smooth_steps"))
    if steps <= 1:
        pyautogui.FAILSAFE = _fs()
        pyautogui.moveTo(tx, ty, duration=0); return
    sx, sy = pyautogui.position()
    for i in range(1, steps + 1):
        if state.stop_flag: return
        t = i / steps
        pyautogui.FAILSAFE = _fs()
        try: pyautogui.moveTo(sx+(tx-sx)*t, sy+(ty-sy)*t, duration=0.01)
        except pyautogui.FailSafeException: return

def cps_interval():
    base = float(settings.get("clicker_cps_base"))
    loss = float(settings.get("clicker_cps_loss"))
    lo   = float(settings.get("clicker_cps_min"))
    hi   = float(settings.get("clicker_cps_max"))
    cps  = max(lo, min(hi, random.uniform(base-loss, base+loss)))
    return 1.0 / cps

def addon_click(x, y, button="left", use_jitter=True):
    if use_jitter: x, y = addon_jitter(x, y)
    if random.random() < float(settings.get("clicker_slip_chance")): return 0

    hold = random.uniform(float(settings.get("clicker_hold_min")),
                          float(settings.get("clicker_hold_max")))

    if random.random() < float(settings.get("clicker_burst_chance")):
        time.sleep(random.uniform(float(settings.get("clicker_burst_min")),
                                  float(settings.get("clicker_burst_max"))))
    pyautogui.FAILSAFE = _fs()
    try:
        btn = pyautogui.RIGHT if button == "right" else pyautogui.LEFT
        pyautogui.mouseDown(x=int(x), y=int(y), button=btn)
        time.sleep(hold)
        pyautogui.mouseUp(x=int(x), y=int(y), button=btn)
    except pyautogui.FailSafeException: pass
    return hold

# ── jitter solo ───────────────────────────────────────────────────────────────
_jitter_listener = None

def start_jitter_solo():
    global _jitter_listener
    from pynput import mouse as _m
    state.jitter_solo_active = True

    def on_click(x, y, button, pressed):
        if not state.jitter_solo_active: return False
        if pressed:
            jx, jy = addon_jitter(x, y)
            try:
                pyautogui.FAILSAFE = _fs()
                btn = pyautogui.RIGHT if button.name=="right" else pyautogui.LEFT
                pyautogui.mouseDown(x=int(jx), y=int(jy), button=btn)
                time.sleep(random.uniform(0.02, 0.06))
                pyautogui.mouseUp(x=int(jx), y=int(jy), button=btn)
            except: pass

    _jitter_listener = _m.Listener(on_click=on_click)
    _jitter_listener.daemon = True
    _jitter_listener.start()

def stop_jitter_solo():
    global _jitter_listener
    state.jitter_solo_active = False
    if _jitter_listener:
        try: _jitter_listener.stop()
        except: pass
        _jitter_listener = None

def toggle_jitter_solo():
    if state.jitter_solo_active: stop_jitter_solo()
    else: start_jitter_solo()

# ── clicker solo ──────────────────────────────────────────────────────────────
def start_clicker_solo():
    state.clicker_solo_active = True
    button = settings.get("clicker_button") or "left"

    def _loop():
        while state.clicker_solo_active and not state.quit_flag:
            target_interval = cps_interval()
            t_start = time.perf_counter()
            x, y = pyautogui.position()

            # handle "both" — alternate left/right
            if button == "both":
                btn = "left" if int(time.time()*1000) % 2 == 0 else "right"
            else:
                btn = button

            hold = addon_click(x, y, button=btn,
                               use_jitter=settings.get("jitter_addon")) or 0
            elapsed = time.perf_counter() - t_start
            remaining = target_interval - elapsed
            if remaining > 0: time.sleep(remaining)

    threading.Thread(target=_loop, daemon=True).start()

def stop_clicker_solo():
    state.clicker_solo_active = False

def toggle_clicker_solo():
    if state.clicker_solo_active: stop_clicker_solo()
    else: start_clicker_solo()
