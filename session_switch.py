"""
session_switch.py — X11 / Wayland session switcher
────────────────────────────────────────────────────
Detects current session type and provides commands to switch.

Supports:
  - GDM  (Ubuntu, Pop!_OS, Fedora)
  - SDDM (KDE/Plasma)
  - LightDM
"""

import os, subprocess, platform

PLATFORM = platform.system().lower()


def detect_session():
    """Returns 'wayland' | 'x11' | 'unknown'"""
    xdg = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if xdg in ("wayland", "x11"): return xdg
    if os.environ.get("WAYLAND_DISPLAY"):  return "wayland"
    if os.environ.get("DISPLAY"):          return "x11"
    return "unknown"


def detect_display_manager():
    """Returns 'gdm' | 'sddm' | 'lightdm' | 'unknown'"""
    for dm in ("gdm", "gdm3", "sddm", "lightdm"):
        try:
            r = subprocess.run(["systemctl", "is-active", dm],
                               capture_output=True, timeout=2)
            if r.stdout.decode().strip() == "active":
                return dm.replace("gdm3", "gdm")
        except: pass
    # fallback — check running processes
    try:
        out = subprocess.check_output(["ps", "-e", "-o", "comm"],
                                       stderr=subprocess.DEVNULL).decode()
        for dm in ("gdm", "sddm", "lightdm"):
            if dm in out: return dm
    except: pass
    return "unknown"


def get_switch_info():
    """
    Returns dict with all info needed to show the switch UI.
    {
      session:        'wayland' | 'x11' | 'unknown'
      display_manager: 'gdm' | 'sddm' | 'lightdm' | 'unknown'
      can_switch:     bool
      to_x11_cmds:    [str, ...]   — commands to switch to X11
      to_wayland_cmds:[str, ...]   — commands to switch back to Wayland
      notes:          [str, ...]   — extra info for user
    }
    """
    session = detect_session()
    dm      = detect_display_manager()

    info = {
        "session":         session,
        "display_manager": dm,
        "can_switch":      PLATFORM == "linux",
        "to_x11_cmds":     [],
        "to_wayland_cmds": [],
        "notes":           [],
    }

    if PLATFORM != "linux":
        info["can_switch"] = False
        info["notes"].append("Session switching is Linux-only.")
        return info

    if dm == "gdm":
        info["to_x11_cmds"] = [
            "sudo sed -i 's/#WaylandEnable=false/WaylandEnable=false/' /etc/gdm3/custom.conf",
            "# Then log out and log back in",
        ]
        info["to_wayland_cmds"] = [
            "sudo sed -i 's/WaylandEnable=false/#WaylandEnable=false/' /etc/gdm3/custom.conf",
            "# Then log out and log back in",
        ]
        info["notes"].append("GDM detected — edits /etc/gdm3/custom.conf")
        info["notes"].append("You must log out and back in after switching.")

    elif dm == "sddm":
        info["to_x11_cmds"] = [
            "# At login screen: click the session icon → choose 'Plasma (X11)'",
            "# Or set default in /etc/sddm.conf:",
            "sudo bash -c 'echo -e \"[Autologin]\\nSession=plasma\" >> /etc/sddm.conf'",
        ]
        info["to_wayland_cmds"] = [
            "# At login screen: click the session icon → choose 'Plasma (Wayland)'",
        ]
        info["notes"].append("SDDM detected — easiest to switch at login screen.")

    elif dm == "lightdm":
        info["to_x11_cmds"] = [
            "# At login screen: click the settings gear → choose GNOME on Xorg",
        ]
        info["to_wayland_cmds"] = [
            "# At login screen: click the settings gear → choose GNOME",
        ]
        info["notes"].append("LightDM detected — switch at login screen via gear icon.")

    else:
        info["can_switch"] = False
        info["notes"].append("Display manager not detected.")
        info["notes"].append("Switch manually: log out → choose GNOME on Xorg at login screen.")

    return info


def run_switch_to_x11(dm):
    """
    Run the X11 switch commands automatically via pkexec.
    Returns (success, message).
    """
    if dm == "gdm":
        script = """#!/bin/bash
set -e
# Uncomment or add WaylandEnable=false in gdm3 config
if grep -q "^#WaylandEnable=false" /etc/gdm3/custom.conf; then
    sed -i 's/#WaylandEnable=false/WaylandEnable=false/' /etc/gdm3/custom.conf
elif ! grep -q "^WaylandEnable=false" /etc/gdm3/custom.conf; then
    echo "WaylandEnable=false" >> /etc/gdm3/custom.conf
fi
echo "done"
"""
    else:
        return False, f"Auto-switch not supported for {dm} — follow manual steps."

    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script); tmp = f.name
        os.chmod(tmp, 0o755)
        result = subprocess.run(["pkexec", "bash", tmp],
                                capture_output=True, timeout=30)
        os.unlink(tmp)
        if result.returncode == 0:
            return True, "Done — log out and back in to switch to X11."
        return False, result.stderr.decode(errors="ignore").strip() or "pkexec failed"
    except Exception as e:
        return False, str(e)


def run_switch_to_wayland(dm):
    """Re-enable Wayland. Returns (success, message)."""
    if dm == "gdm":
        script = """#!/bin/bash
set -e
if grep -q "^WaylandEnable=false" /etc/gdm3/custom.conf; then
    sed -i 's/^WaylandEnable=false/#WaylandEnable=false/' /etc/gdm3/custom.conf
fi
echo "done"
"""
    else:
        return False, f"Auto-switch not supported for {dm}."

    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script); tmp = f.name
        os.chmod(tmp, 0o755)
        result = subprocess.run(["pkexec", "bash", tmp],
                                capture_output=True, timeout=30)
        os.unlink(tmp)
        if result.returncode == 0:
            return True, "Done — log out and back in to switch to Wayland."
        return False, result.stderr.decode(errors="ignore").strip() or "pkexec failed"
    except Exception as e:
        return False, str(e)
