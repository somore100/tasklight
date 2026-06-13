import time, state, settings, humanizer, duplicator, injector
from duplicator import dup_state

def play(speed=1.0, loop=1):
    if not state.events: return
    events = list(state.events)
    if not events: return

    state.is_playing = True
    state.stop_flag  = False
    speed = max(float(speed), 0.01)
    infinite  = (loop == 0)
    run_count = 0

    human      = settings.get("human_enabled")
    do_jitter  = human and settings.get("jitter_addon")
    do_delay   = human and settings.get("delay_addon")
    do_clicker = human and settings.get("clicker_addon")
    do_smooth  = human and settings.get("smooth_addon")
    do_dup     = settings.get("dup_enabled") and settings.get("dup_addon")
    last_click_t = 0.0

    while True:
        if state.stop_flag or state.quit_flag: break
        if not infinite and run_count >= loop: break
        run_count += 1
        if not events: break
        base_time = events[0][-1]

        for i, event in enumerate(events):
            if state.stop_flag or state.quit_flag: break
            delay = (event[-1] - base_time) / speed
            base_time = event[-1]
            if delay > 0: time.sleep(delay)

            kind = event[0]
            try:
                if kind == "move":
                    _, x, y, _ = event
                    if do_jitter: x, y = humanizer.addon_jitter(x, y)
                    if do_smooth: injector.move_smooth(x, y, int(settings.get("smooth_steps") or 8))
                    else:         injector.move(x, y)
                    if do_delay:  humanizer.addon_delay()

                elif kind == "click":
                    _, x, y, button, pressed, _ = event
                    if pressed:
                        btn = button if isinstance(button, str) else "left"
                        if do_jitter: x, y = humanizer.addon_jitter(x, y)

                        if do_clicker:
                            now = time.time()
                            gap = humanizer.cps_interval()
                            elapsed = now - last_click_t
                            if elapsed < gap: time.sleep(gap - elapsed)
                            humanizer.addon_click(x, y, button=btn, use_jitter=False)
                            last_click_t = time.time()
                        else:
                            hold = 0.05
                            injector.mouse_down(x, y, btn)
                            time.sleep(hold)
                            injector.mouse_up(x, y, btn)

                        if do_dup:
                            gap_ms = 80
                            if i + 1 < len(events):
                                next_t = events[i+1][-1]
                                gap_ms = max(20, (next_t - event[-1]) * 1000 / speed * 0.8)
                            duplicator.addon_duplicate(x, y, button=btn, after_delay_ms=gap_ms)

                elif kind == "key":
                    # legacy format — single press, short hold
                    _, key, _ = event
                    injector.key_press(key, hold_s=0.05)

                elif kind == "key_down":
                    _, key, _ = event
                    injector.key_down(key)

                elif kind == "key_up":
                    _, key, _ = event
                    injector.key_up(key)

            except Exception:
                pass

    state.is_playing = False
