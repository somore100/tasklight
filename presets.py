"""
presets.py — save/load recorded events in three formats:
  - in-app   : stored inside settings.json under "presets" key
  - .json     : plain JSON file, human-readable
  - .tljson.gz: gzip-compressed JSON, compact power-user format
"""

import json, gzip, os, sys
import settings, state

# ── serialisation ─────────────────────────────────────────────────────────────

def _events_to_list(events):
    """Convert tuples to lists for JSON serialisation."""
    return [list(e) for e in events]

def _list_to_events(lst):
    """Restore: booleans come back as bool from JSON — fix pressed field."""
    out = []
    for e in lst:
        if e[0] == "click":
            # ensure pressed is bool
            e[4] = bool(e[4])
        out.append(tuple(e))
    return out

def _size_str(data_bytes):
    kb = len(data_bytes) / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb/1024:.2f} MB"

def _warn_threshold(data_bytes):
    """Return warning string if size is large, else empty string."""
    kb = len(data_bytes) / 1024
    if kb > 500:
        return f"⚠ {_size_str(data_bytes)} — consider saving as .tljson.gz or JSON file"
    if kb > 200:
        return f"ℹ {_size_str(data_bytes)} — getting large, file format recommended"
    return f"Size: {_size_str(data_bytes)}"

# ── IN-APP ────────────────────────────────────────────────────────────────────

def save_inapp(name, events):
    presets = dict(settings.get("presets") or {})
    presets[name] = _events_to_list(events)
    settings.set("presets", presets)
    raw = json.dumps(presets).encode()
    return _warn_threshold(raw)

def load_inapp(name):
    presets = settings.get("presets") or {}
    if name not in presets:
        raise KeyError(f"Preset '{name}' not found")
    return _list_to_events(presets[name])

def delete_inapp(name):
    presets = dict(settings.get("presets") or {})
    presets.pop(name, None)
    settings.set("presets", presets)

def list_inapp():
    return sorted((settings.get("presets") or {}).keys())

# ── JSON FILE ─────────────────────────────────────────────────────────────────

def save_json(name, events, folder=None):
    if folder is None:
        folder = settings.get_preset_folder()
    path = os.path.join(folder, f"{name}.json")
    data = {"name": name, "events": _events_to_list(events)}
    raw  = json.dumps(data, indent=2).encode()
    with open(path, "wb") as f:
        f.write(raw)
    return path, _size_str(raw)

def load_json(path):
    with open(path) as f:
        data = json.load(f)
    return _list_to_events(data["events"])

# ── COMPRESSED .tljson.gz ─────────────────────────────────────────────────────

def save_gz(name, events, folder=None):
    if folder is None:
        folder = settings.get_preset_folder()
    path = os.path.join(folder, f"{name}.tljson.gz")
    data = {"name": name, "events": _events_to_list(events)}
    raw  = json.dumps(data).encode()
    with gzip.open(path, "wb") as f:
        f.write(raw)
    ratio = len(raw) / max(os.path.getsize(path), 1)
    return path, _size_str(raw), f"{ratio:.1f}x"

def load_gz(path):
    with gzip.open(path, "rb") as f:
        data = json.loads(f.read().decode())
    return _list_to_events(data["events"])

# ── AUTO-DETECT LOAD ──────────────────────────────────────────────────────────

def load_file(path):
    """Load any supported file format by extension."""
    if path.endswith(".tljson.gz"):
        return load_gz(path)
    elif path.endswith(".json"):
        return load_json(path)
    raise ValueError(f"Unknown format: {path}")

# ── LIST FILES IN FOLDER ──────────────────────────────────────────────────────

def list_files(folder=None):
    """Return list of (name, path, size_str) for all presets in folder."""
    if folder is None:
        folder = settings.get_preset_folder()
    if not os.path.exists(folder):
        return []
    out = []
    for fn in sorted(os.listdir(folder)):
        if fn.endswith(".json") or fn.endswith(".tljson.gz"):
            path = os.path.join(folder, fn)
            size = os.path.getsize(path)
            name = fn.replace(".tljson.gz","").replace(".json","")
            fmt  = "gz" if fn.endswith(".gz") else "json"
            out.append((name, path, _size_str(size), fmt))
    return out
