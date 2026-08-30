# TaskLight — Build & Ship Guide

## Quick start: run from source

```bash
./setup_venv.sh          # creates venv/ and installs everything from requirements.txt
source venv/bin/activate
python3 main.py
```

`setup_venv.sh` builds the venv fresh using whatever `python3` is on your
`PATH`, so it's safe to run on any machine (Pop!_OS, Fedora, etc.) — a
committed/zipped `venv/` folder isn't, because compiled packages
(`evdev`, `Pillow`, `psutil`, `mss`) are built against one specific Python
version + architecture, and the venv's own scripts hardcode an absolute
path back to the interpreter that created them. Rebuilding locally with
this script avoids both problems.

---

## Option A: GitHub Actions (recommended — builds both Linux + Windows automatically)

1. Push your code to GitHub
2. Create a version tag to trigger a release build:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. GitHub Actions builds:
   - `TaskLight-x86_64.AppImage` (Linux, runs anywhere)
   - `TaskLight.exe` (Windows, standalone)
4. Both appear as downloadable files on the GitHub Releases page.

You can also trigger a build manually from the Actions tab → Build TaskLight → Run workflow.

---

## Option B: Build locally on Pop!_OS (Linux AppImage only)

```bash
# 1. set up (or reuse) the venv
./setup_venv.sh
source venv/bin/activate

# 2. build deps are already in requirements.txt (pyinstaller included)

# 3. download appimagetool (one time)
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

# 4. build
pyinstaller tasklight.spec --clean --noconfirm

# 5. make AppImage
mkdir -p AppDir/usr/bin AppDir/usr/share/applications
cp dist/tasklight AppDir/usr/bin/tasklight
# ... (see build_appimage.sh for full steps)
./appimagetool-x86_64.AppImage AppDir TaskLight-x86_64.AppImage

# 6. run
./TaskLight-x86_64.AppImage
```

---

## Option C: Windows .exe (run on a Windows machine)

```bat
pip install -r requirements.txt
pyinstaller tasklight_windows.spec --clean --noconfirm
```

Output: `dist\TaskLight.exe`

---

## File layout after build

```
tasklight/
  main.py              ← entry point
  config.py
  settings.py
  state.py
  recorder.py
  player.py
  humanizer.py
  duplicator.py
  fps.py
  network.py
  sysmon.py
  presets.py
  hotkeys.py
  tasklight.spec            ← Linux/Mac PyInstaller spec
  tasklight_windows.spec    ← Windows PyInstaller spec
  .github/workflows/build.yml  ← GitHub Actions CI/CD
  BUILD_README.md
  requirements.txt          ← pinned pip deps
  setup_venv.sh              ← run this first

After first run (next to the exe or AppImage):
  settings.json        ← all your settings, auto-saved
  presets/             ← saved macro recordings
```

## pip install (all deps)

Covered by `./setup_venv.sh` above — see "Quick start" at the top of this file.

---

## Linux permissions: hotkeys on Wayland (and injection generally)

TaskLight listens for global hotkeys and injects keyboard input at the
kernel level via `evdev`/`uinput` (see `hotkeys.py` / `injector.py`). This
is what makes hotkeys and playback work the same way under X11, under
Wayland (any compositor), and inside games — but it means your user needs
permission to read `/dev/input/event*` and write to `/dev/uinput`.

If hotkeys don't fire, or TaskLight's Keybinds section shows
"backend: pynput/X11" with an orange permission warning, add yourself to
the `input` group and log out/in (a reboot also works):

```bash
sudo usermod -aG input $USER
# Fedora/most distros also need a udev rule for /dev/uinput write access:
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-tasklight-uinput.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Then fully log out and back in (group membership only applies to new
login sessions). Without this, TaskLight automatically falls back to a
pynput/X11-based hotkey listener, which works fine on X11 but will miss
hotkeys pressed while a native Wayland window (not running under XWayland)
has focus — this is a Wayland/GNOME limitation, not a TaskLight bug; see
`GlobalListener` in `hotkeys.py` for details.
