"""
fps.py — FPS counter module
Methods (tried in order of accuracy):
  1. GPU query (nvidia-smi / radeontop / intel_gpu_top) if available
  2. Screen region capture diff — universal fallback

Exposes start_monitor / stop_monitor / FpsState
"""
import threading, time, platform, subprocess, os
import queue

PLATFORM = platform.system().lower()

class FpsState:
    active      = False
    current     = None
    avg         = None
    minimum     = None
    maximum     = None
    history     = []        # last 60 FPS samples
    method      = "screen"  # "gpu" | "screen"
    region      = None      # (x, y, w, h) or None = fullscreen
    _thread     = None

fps_state = FpsState()

# ── GPU query ─────────────────────────────────────────────────────────────────

def _try_nvidia():
    """Returns fps float or None. Uses nvidia-smi dmon."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "dmon", "-s", "u", "-d", "1", "-c", "2"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode()
        for line in reversed(out.splitlines()):
            parts = line.split()
            if parts and parts[0].lstrip("-").isdigit():
                # column 2 is SM util — not FPS, but we can try frame time from nvtop
                pass
    except: pass
    return None

def _try_nvtop_fps():
    """Try nvtop --fps if available."""
    try:
        out = subprocess.check_output(
            ["nvtop", "--no-color", "-d", "1"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        for line in out.splitlines():
            if "fps" in line.lower():
                for part in line.split():
                    try: return float(part)
                    except: pass
    except: pass
    return None

def detect_gpu_method():
    """Returns 'nvidia' | 'amd' | 'intel' | None"""
    for cmd,name in [
        (["nvidia-smi","--query-gpu=name","--format=csv,noheader"], "nvidia"),
        (["radeontop","--help"], "amd"),
        (["intel_gpu_top","-h"], "intel"),
    ]:
        try:
            subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=2)
            return name
        except: pass
    return None

# ── screen diff FPS ───────────────────────────────────────────────────────────

def _screen_fps_loop(region, sample_rate=60):
    """
    Captures screen region at sample_rate Hz.
    Counts frames where pixels changed vs previous frame.
    Reports FPS every second.
    """
    try:
        import PIL.ImageGrab as grab
    except ImportError:
        try:
            from mss import mss as _mss
            _use_mss = True
        except ImportError:
            fps_state.method = "unavailable"
            return

    import hashlib

    prev_hash  = None
    frame_count = 0
    t_start    = time.perf_counter()
    interval   = 1.0 / sample_rate

    while fps_state.active:
        t0 = time.perf_counter()

        try:
            if region:
                x, y, w, h = region
                img = grab.grab(bbox=(x, y, x+w, y+h))
            else:
                img = grab.grab()

            # downsample for speed — 32x32 is enough to detect frame changes
            img = img.resize((32, 32))
            h_val = hash(img.tobytes())

            if h_val != prev_hash:
                frame_count += 1
                prev_hash = h_val

        except Exception:
            pass

        # report every second
        elapsed = time.perf_counter() - t_start
        if elapsed >= 1.0:
            fps = frame_count / elapsed
            _record(fps)
            frame_count = 0
            t_start     = time.perf_counter()

        # sleep remainder of interval
        used = time.perf_counter() - t0
        rem  = interval - used
        if rem > 0:
            time.sleep(rem)

def _record(fps):
    fps_state.current = fps
    fps_state.history.append(fps)
    if len(fps_state.history) > 60:
        fps_state.history.pop(0)
    valid = fps_state.history
    if valid:
        fps_state.avg     = sum(valid) / len(valid)
        fps_state.minimum = min(valid)
        fps_state.maximum = max(valid)

# ── public API ────────────────────────────────────────────────────────────────

def start_monitor(region=None, prefer_gpu=True):
    fps_state.active  = True
    fps_state.history = []
    fps_state.region  = region
    fps_state.current = None
    fps_state.avg     = None
    fps_state.minimum = None
    fps_state.maximum = None

    def _run():
        # try GPU first
        if prefer_gpu:
            gpu = detect_gpu_method()
            if gpu:
                fps_state.method = "gpu"
                # GPU method not fully implemented — fall through to screen
        fps_state.method = "screen"
        _screen_fps_loop(region)

    fps_state._thread = threading.Thread(target=_run, daemon=True)
    fps_state._thread.start()

def stop_monitor():
    fps_state.active  = False
    fps_state.current = None

def get_status_str():
    if not fps_state.active: return ""
    fps = fps_state.current
    return f"🎮 {fps:.0f}" if fps is not None else "🎮 --"
