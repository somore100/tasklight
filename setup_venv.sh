#!/usr/bin/env bash
# TaskLight — one-shot venv setup.
# Run this from the tasklight/ source folder:
#   ./setup_venv.sh
# Force a specific interpreter:
#   PYTHON=python3.11 ./setup_venv.sh
set -euo pipefail
cd "$(dirname "$0")"

MIN_MINOR=10   # don't accept anything older than 3.10

pick_python() {
    if [ -n "${PYTHON:-}" ]; then
        echo "$PYTHON"
        return
    fi
    # prefer the newest python3.X on PATH (3.13 down to 3.10), fall back to plain python3
    for v in 13 12 11 10; do
        if command -v "python3.$v" >/dev/null 2>&1; then
            echo "python3.$v"
            return
        fi
    done
    echo "python3"
}

PY="$(pick_python)"

if ! command -v "$PY" >/dev/null 2>&1; then
    echo "error: $PY not found. Install a recent Python 3 first, e.g.:" >&2
    echo "  Fedora:      sudo dnf install python3.12" >&2
    echo "  Pop!_OS/Debian: sudo apt install python3.12 python3.12-venv" >&2
    exit 1
fi

PY_MINOR="$("$PY" -c 'import sys; print(sys.version_info[1])')"
echo "Using $($PY --version) at $(command -v "$PY")"

if [ "$PY_MINOR" -lt "$MIN_MINOR" ]; then
    echo
    echo "warning: $PY is Python 3.$PY_MINOR, which is older than the 3.$MIN_MINOR+"
    echo "this project targets. This still may work, but if you have a newer"
    echo "interpreter installed under a different name, re-run with e.g.:"
    echo "  PYTHON=python3.12 ./setup_venv.sh"
    echo
fi

if [ -d venv ]; then
    VENV_MINOR="$(./venv/bin/python3 -c 'import sys; print(sys.version_info[1])' 2>/dev/null || echo '?')"
    if [ "$VENV_MINOR" != "$PY_MINOR" ]; then
        echo "venv/ exists but was built with a different Python (3.$VENV_MINOR vs 3.$PY_MINOR here)."
        echo "Rebuilding it with $PY..."
        rm -rf venv
        "$PY" -m venv venv
    else
        echo "venv/ already exists and matches $PY — reusing it."
    fi
else
    "$PY" -m venv venv
fi

./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt

echo
echo "Done. Activate with:"
echo "  source venv/bin/activate"
echo
echo "Then run TaskLight from source with:"
echo "  python3 main.py"
echo
echo "If hotkeys don't fire on Linux, you likely also need /dev/input read"
echo "access — see the 'Linux permissions' section in BUILD_README.md."
