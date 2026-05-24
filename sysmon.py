"""
sysmon.py — System performance monitor
Uses psutil (universal) + optional gputil/nvidia-smi for GPU.

Metrics: CPU, RAM, GPU, Disk, Temp, Network I/O
All optional — graceful fallback if unavailable.
"""
import threading, time, platform

PLATFORM = platform.system().lower()

try:
    import psutil
    PSUTIL = True
except ImportError:
    PSUTIL = False

# ── state ─────────────────────────────────────────────────────────────────────

class SysState:
    active       = False
    _thread      = None

    # CPU
    cpu_pct      = None   # total %
    cpu_per_core = []     # list of % per core
    cpu_temp     = None   # celsius or None

    # RAM
    ram_pct      = None
    ram_used_gb  = None
    ram_total_gb = None

    # GPU
    gpu_pct      = None
    gpu_vram_pct = None
    gpu_name     = ""
    gpu_temp     = None

    # Disk
    disk_pct     = None
    disk_read_mb = None   # MB/s
    disk_write_mb= None

    # Network I/O (MB/s)
    net_up_mb    = None
    net_down_mb  = None

    # histories (last 60 samples)
    cpu_hist     = []
    ram_hist     = []
    gpu_hist     = []
    disk_hist    = []

sys_state = SysState()

# ── GPU detection ─────────────────────────────────────────────────────────────

def _get_gpu():
    """Returns (pct, vram_pct, name, temp) or all None."""
    # try nvidia-smi
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=utilization.gpu,utilization.memory,name,temperature.gpu",
             "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip().split(",")
        if len(out) >= 4:
            return float(out[0]), float(out[1]), out[2].strip(), float(out[3])
    except: pass

    # try gputil
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            g = gpus[0]
            return g.load*100, g.memoryUtil*100, g.name, g.temperature
    except: pass

    # try AMD via radeontop (Linux)
    if PLATFORM == "linux":
        try:
            import subprocess
            out = subprocess.check_output(
                ["radeontop", "-d", "-", "-l", "1"],
                stderr=subprocess.DEVNULL, timeout=2
            ).decode()
            for line in out.splitlines():
                if "gpu" in line.lower():
                    import re
                    m = re.search(r"gpu\s+([\d.]+)%", line, re.I)
                    if m: return float(m.group(1)), None, "AMD GPU", None
        except: pass

    return None, None, "", None

# ── disk I/O ──────────────────────────────────────────────────────────────────

_prev_disk = None
_prev_net  = None
_prev_time = None

def _get_disk_io():
    global _prev_disk, _prev_time
    if not PSUTIL: return None, None
    try:
        now  = time.time()
        curr = psutil.disk_io_counters()
        if _prev_disk and _prev_time:
            dt = now - _prev_time
            if dt > 0:
                r = (curr.read_bytes  - _prev_disk.read_bytes)  / dt / 1024**2
                w = (curr.write_bytes - _prev_disk.write_bytes) / dt / 1024**2
                _prev_disk = curr; _prev_time = now
                return round(r, 2), round(w, 2)
        _prev_disk = curr; _prev_time = now
    except: pass
    return None, None

def _get_net_io():
    global _prev_net, _prev_time
    if not PSUTIL: return None, None
    try:
        now  = time.time()
        curr = psutil.net_io_counters()
        if _prev_net:
            dt = now - _prev_time if _prev_time else 1.0
            if dt > 0:
                up   = (curr.bytes_sent - _prev_net.bytes_sent)   / dt / 1024**2
                down = (curr.bytes_recv - _prev_net.bytes_recv)   / dt / 1024**2
                _prev_net  = curr
                return round(up, 2), round(down, 2)
        _prev_net = curr
    except: pass
    return None, None

# ── temperature ───────────────────────────────────────────────────────────────

def _get_cpu_temp():
    if not PSUTIL: return None
    try:
        temps = psutil.sensors_temperatures()
        for key in ("coretemp","k10temp","cpu_thermal","acpitz"):
            if key in temps and temps[key]:
                return temps[key][0].current
        # fallback: first available
        for entries in temps.values():
            if entries: return entries[0].current
    except: pass
    return None

# ── main sample loop ──────────────────────────────────────────────────────────

def _sample(interval):
    while sys_state.active:
        t0 = time.perf_counter()

        if PSUTIL:
            # CPU
            sys_state.cpu_pct      = psutil.cpu_percent(interval=None)
            sys_state.cpu_per_core = psutil.cpu_percent(percpu=True)
            sys_state.cpu_temp     = _get_cpu_temp()

            # RAM
            vm = psutil.virtual_memory()
            sys_state.ram_pct      = vm.percent
            sys_state.ram_used_gb  = round(vm.used  / 1024**3, 1)
            sys_state.ram_total_gb = round(vm.total / 1024**3, 1)

            # Disk
            sys_state.disk_pct     = psutil.disk_usage("/").percent
            sys_state.disk_read_mb, sys_state.disk_write_mb = _get_disk_io()

            # Network
            sys_state.net_up_mb, sys_state.net_down_mb = _get_net_io()

        # GPU
        gp, gv, gn, gt = _get_gpu()
        sys_state.gpu_pct   = gp
        sys_state.gpu_vram_pct = gv
        sys_state.gpu_name  = gn
        sys_state.gpu_temp  = gt

        # histories
        def _push(hist, val):
            hist.append(val)
            if len(hist) > 60: hist.pop(0)

        _push(sys_state.cpu_hist,  sys_state.cpu_pct)
        _push(sys_state.ram_hist,  sys_state.ram_pct)
        _push(sys_state.gpu_hist,  sys_state.gpu_pct)
        _push(sys_state.disk_hist, sys_state.disk_pct)

        elapsed = time.perf_counter() - t0
        rem = interval - elapsed
        if rem > 0: time.sleep(rem)

# ── public API ────────────────────────────────────────────────────────────────

def start(interval=1.0):
    if sys_state.active: return
    sys_state.active = True
    # prime psutil cpu_percent (first call always returns 0)
    if PSUTIL:
        try: psutil.cpu_percent(interval=None)
        except: pass
    sys_state._thread = threading.Thread(
        target=_sample, args=(interval,), daemon=True)
    sys_state._thread.start()

def stop():
    sys_state.active = False

def mini_str(show_cpu=True, show_ram=True, show_gpu=True,
             show_disk=False, show_net=False, show_temp=False):
    """Return compact string for mini mode display."""
    parts = []
    s = sys_state
    if show_cpu and s.cpu_pct is not None:
        t = f" {s.cpu_temp:.0f}°" if show_temp and s.cpu_temp else ""
        parts.append(f"CPU:{s.cpu_pct:.0f}%{t}")
    if show_ram and s.ram_pct is not None:
        parts.append(f"RAM:{s.ram_pct:.0f}%")
    if show_gpu and s.gpu_pct is not None:
        parts.append(f"GPU:{s.gpu_pct:.0f}%")
    if show_disk and s.disk_pct is not None:
        parts.append(f"DSK:{s.disk_pct:.0f}%")
    if show_net and s.net_up_mb is not None:
        parts.append(f"↑{s.net_up_mb:.1f}↓{s.net_down_mb:.1f}MB/s")
    return "  ".join(parts)

PSUTIL_AVAILABLE = PSUTIL
