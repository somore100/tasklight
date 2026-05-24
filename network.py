"""
network.py — Network control module
Linux:   tc netem (iproute2) via sudo/pkexec
Windows: clumsy.exe
"""
import os, sys, subprocess, threading, time, platform

PLATFORM = platform.system().lower()

class NetState:
    limiter_active  = False
    blocker_active  = False
    monitor_active  = False
    setup_done      = False
    interface       = ""
    ping_history    = []   # last 60 RTT ms values, None=timeout
    ping_current    = None
    ping_min        = None
    ping_avg        = None
    ping_max        = None

net_state = NetState()

# ── interface detection ───────────────────────────────────────────────────────

def detect_interfaces():
    """Returns [(name, is_default, ip), ...] sorted default-first."""
    ifaces  = []
    default = ""

    if PLATFORM == "linux":
        try:
            out = subprocess.check_output(
                ["ip","route","show","default"], stderr=subprocess.DEVNULL
            ).decode()
            for line in out.splitlines():
                parts = line.split()
                if "dev" in parts:
                    default = parts[parts.index("dev")+1]; break
        except: pass

        try:
            out = subprocess.check_output(
                ["ip","-o","-4","addr","show"], stderr=subprocess.DEVNULL
            ).decode()
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    name = parts[1]
                    ip   = parts[3].split("/")[0]
                    if name != "lo":
                        ifaces.append((name, name==default, ip))
        except: pass

        ifaces.sort(key=lambda x: (not x[1], x[0]))

    elif PLATFORM == "windows":
        try:
            out = subprocess.check_output(
                ["netsh","interface","show","interface"],
                stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            for line in out.splitlines()[3:]:
                parts = line.split()
                if len(parts) >= 4 and parts[1]=="Connected":
                    ifaces.append((" ".join(parts[3:]), False, ""))
        except: pass

    return ifaces or [("unknown", True, "")]

def get_default_interface():
    for name, is_def, ip in detect_interfaces():
        if is_def: return name
    return ""

# ── setup check ───────────────────────────────────────────────────────────────

def check_setup():
    info = {
        "os": PLATFORM,
        "tc_available":     False,
        "clumsy_available": False,
        "is_admin":         False,
        "interfaces":       detect_interfaces(),
        "default_iface":    get_default_interface(),
        "ready":            False,
        "missing":          [],
    }

    if PLATFORM == "linux":
        try:
            subprocess.check_output(["which","tc"], stderr=subprocess.DEVNULL)
            info["tc_available"] = True
        except: info["missing"].append("tc  (install: sudo apt install iproute2)")

        try:
            r = subprocess.run(["sudo","-n","tc","qdisc","show"],
                               capture_output=True, timeout=2)
            info["is_admin"] = (r.returncode == 0)
        except: pass

        if not info["is_admin"]:
            info["missing"].append("passwordless sudo for tc  (see instructions)")
        info["ready"] = info["tc_available"]

    elif PLATFORM == "windows":
        for p in ["clumsy.exe",
                  r"C:\clumsy\clumsy.exe",
                  r"C:\Program Files\clumsy\clumsy.exe"]:
            if os.path.exists(p):
                info["clumsy_available"] = True; break
        try:
            import ctypes
            info["is_admin"] = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except: pass
        if not info["clumsy_available"]:
            info["missing"].append("clumsy.exe  (see instructions)")
        if not info["is_admin"]:
            info["missing"].append("Administrator privileges")
        info["ready"] = info["clumsy_available"] and info["is_admin"]

    return info

def get_setup_instructions(info):
    if info["os"] == "linux":
        user = os.environ.get("USER","user")
        return [
            "Step 1 — install iproute2 (usually already present):",
            f"  sudo apt install iproute2",
            "",
            "Step 2 — allow tc without password prompt:",
            "  sudo visudo",
            f"  Add this line at the bottom:",
            f"  {user} ALL=(ALL) NOPASSWD: /sbin/tc",
            "",
            "  OR just run TaskLight with sudo:",
            "  sudo python3 main.py",
            "",
            "  OR click 'Run setup automatically' below",
            "  (will prompt for your password once via pkexec)",
        ]
    else:
        return [
            "Step 1 — download clumsy (free, open source):",
            "  https://jagt.github.io/clumsy/",
            "",
            "Step 2 — place clumsy.exe in one of:",
            r"  C:\clumsy\clumsy.exe",
            r"  C:\Program Files\clumsy\clumsy.exe",
            "  (or same folder as TaskLight.exe)",
            "",
            "Step 3 — run TaskLight as Administrator",
            "  Right-click TaskLight → Run as administrator",
        ]

# ── auto setup (Linux only) ───────────────────────────────────────────────────

def run_auto_setup_linux():
    """
    Attempts to add passwordless sudo for tc via pkexec.
    Returns (success, message).
    """
    user = os.environ.get("USER","user")
    sudoers_line = f"{user} ALL=(ALL) NOPASSWD: /sbin/tc\n"
    script = f"""#!/bin/bash
echo '{sudoers_line}' >> /etc/sudoers.d/tasklight-tc
chmod 440 /etc/sudoers.d/tasklight-tc
echo "done"
"""
    try:
        # write temp script
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh',
                                         delete=False) as f:
            f.write(script)
            tmp = f.name
        os.chmod(tmp, 0o755)
        result = subprocess.run(
            ["pkexec", "bash", tmp],
            capture_output=True, timeout=30
        )
        os.unlink(tmp)
        if result.returncode == 0:
            return True, "Setup complete — tc is now available without password"
        else:
            return False, result.stderr.decode(errors="ignore").strip() or "pkexec failed"
    except Exception as e:
        return False, str(e)

# ── tc helpers (Linux) ────────────────────────────────────────────────────────

# Session-cached sudo password — user authenticates once per session
_sudo_password = None

def set_sudo_password(pw):
    global _sudo_password
    _sudo_password = pw

def clear_sudo_password():
    global _sudo_password
    _sudo_password = None

def _tc(args, iface=""):
    """
    Run tc with authentication priority:
    1. Passwordless sudo (sudoers rule set up) — instant, no prompt
    2. Cached session password via sudo -S — user typed once this session
    3. pkexec — graphical polkit dialog
    """
    global _sudo_password

    # 1. try passwordless sudo
    try:
        r = subprocess.run(["sudo","-n","tc"]+args, capture_output=True, timeout=5)
        if r.returncode == 0:
            return True, ""
    except Exception:
        pass

    # 2. try cached password
    if _sudo_password:
        try:
            pw_input = (_sudo_password + "\n").encode()
            r = subprocess.run(["sudo","-S","tc"]+args,
                               input=pw_input,
                               capture_output=True, timeout=5)
            if r.returncode == 0:
                return True, ""
            else:
                # wrong password — clear cache
                _sudo_password = None
        except Exception:
            pass

    # 3. pkexec graphical dialog
    try:
        r = subprocess.run(["pkexec","tc"]+args, capture_output=True, timeout=30)
        return r.returncode == 0, r.stderr.decode(errors="ignore").strip()
    except Exception as e:
        return False, str(e)

def _clear(iface):
    try:
        # try passwordless first
        r = subprocess.run(["sudo","-n","tc","qdisc","del","dev",iface,"root"],
                           capture_output=True, timeout=3)
        if r.returncode != 0:
            subprocess.run(["pkexec","tc","qdisc","del","dev",iface,"root"],
                           capture_output=True, timeout=10)
    except Exception:
        pass

def _linux_limiter(iface, delay_ms, loss_ms, pkt_loss):
    _clear(iface)
    args = ["qdisc","add","dev",iface,"root","netem",
            "delay",f"{delay_ms}ms",f"{loss_ms}ms","distribution","normal"]
    if pkt_loss > 0:
        args += ["loss",f"{pkt_loss}%"]
    return _tc(args)

def _linux_blocker(iface):
    _clear(iface)
    return _tc(["qdisc","add","dev",iface,"root","netem","loss","100%"])

# ── clumsy helpers (Windows) ──────────────────────────────────────────────────

_clumsy_proc = None

def _find_clumsy():
    for p in ["clumsy.exe",
              r"C:\clumsy\clumsy.exe",
              r"C:\Program Files\clumsy\clumsy.exe"]:
        if os.path.exists(p): return p
    return None

def _win_stop():
    global _clumsy_proc
    if _clumsy_proc:
        try: _clumsy_proc.terminate()
        except: pass
        _clumsy_proc = None

def _win_limiter(delay_ms, pkt_loss):
    global _clumsy_proc
    c = _find_clumsy()
    if not c: return False, "clumsy.exe not found"
    _win_stop()
    args = [c,"--filter","outbound","--lag","on","--lag-time",str(delay_ms),"--lag-chance","100"]
    if pkt_loss > 0:
        args += ["--drop","on","--drop-chance",str(int(pkt_loss))]
    try:
        _clumsy_proc = subprocess.Popen(args)
        return True, ""
    except Exception as e:
        return False, str(e)

def _win_blocker():
    global _clumsy_proc
    c = _find_clumsy()
    if not c: return False, "clumsy.exe not found"
    _win_stop()
    try:
        _clumsy_proc = subprocess.Popen(
            [c,"--filter","outbound","--drop","on","--drop-chance","100"])
        return True, ""
    except Exception as e:
        return False, str(e)

# ── public API ────────────────────────────────────────────────────────────────

def apply_limiter(iface, delay_ms, loss_ms, pkt_loss):
    net_state.limiter_active = True
    if PLATFORM == "linux":
        return _linux_limiter(iface, delay_ms, loss_ms, pkt_loss)
    return _win_limiter(delay_ms, pkt_loss)

def stop_limiter(iface):
    net_state.limiter_active = False
    if PLATFORM == "linux" and iface:
        threading.Thread(target=_clear, args=(iface,), daemon=True).start()
    else: _win_stop()

def apply_blocker(iface):
    net_state.blocker_active = True
    if PLATFORM == "linux": return _linux_blocker(iface)
    return _win_blocker()

def stop_blocker(iface):
    net_state.blocker_active = False
    if PLATFORM == "linux" and iface:
        threading.Thread(target=_clear, args=(iface,), daemon=True).start()
    else: _win_stop()

def toggle_blocker(iface):
    if net_state.blocker_active: stop_blocker(iface)
    else: apply_blocker(iface)


def stop_all(iface=""):
    iface = iface or net_state.interface
    # only run cleanup if something was actually activated
    if not net_state.limiter_active and not net_state.blocker_active:
        net_state.limiter_active = False
        net_state.blocker_active = False
        return
    net_state.limiter_active = False
    net_state.blocker_active = False
    if PLATFORM == "linux" and iface:
        threading.Thread(target=_clear, args=(iface,), daemon=True).start()
    elif PLATFORM == "windows":
        _win_stop()

# ── ping monitor ──────────────────────────────────────────────────────────────

def _ping_once(host):
    try:
        if PLATFORM == "windows":
            out = subprocess.check_output(
                ["ping","-n","1","-w","1000",host],
                stderr=subprocess.DEVNULL, timeout=3
            ).decode(errors="ignore")
        else:
            out = subprocess.check_output(
                ["ping","-c","1","-W","1",host],
                stderr=subprocess.DEVNULL, timeout=3
            ).decode()
        for line in out.splitlines():
            if "time=" in line.lower():
                for part in line.split():
                    if "time=" in part.lower():
                        val = part.split("=")[-1].replace("ms","").strip("<")
                        try: return float(val)
                        except: pass
    except: pass
    return None

def start_monitor(host="8.8.8.8", interval=1.0):
    net_state.monitor_active = True
    net_state.ping_history   = []

    def _loop():
        while net_state.monitor_active:
            rtt = _ping_once(host)
            net_state.ping_current = rtt
            net_state.ping_history.append(rtt)
            if len(net_state.ping_history) > 60:
                net_state.ping_history.pop(0)
            valid = [x for x in net_state.ping_history if x is not None]
            if valid:
                net_state.ping_min = min(valid)
                net_state.ping_max = max(valid)
                net_state.ping_avg = sum(valid)/len(valid)
            else:
                net_state.ping_min = None
                net_state.ping_avg = None
                net_state.ping_max = None
            time.sleep(interval)

    threading.Thread(target=_loop, daemon=True).start()

def stop_monitor():
    net_state.monitor_active = False
