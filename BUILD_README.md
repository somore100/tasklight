# TaskLight — Build & Ship Guide

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
# 1. activate your venv
source venv/bin/activate

# 2. install build deps
pip install pyinstaller psutil Pillow mss

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
pip install pyinstaller pynput pyautogui psutil Pillow
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
  tasklight.spec            ← Linux/Mac PyInstaller spec
  tasklight_windows.spec    ← Windows PyInstaller spec
  .github/workflows/build.yml  ← GitHub Actions CI/CD
  BUILD_README.md

After first run (next to the exe or AppImage):
  settings.json        ← all your settings, auto-saved
  presets/             ← saved macro recordings
```

## pip install (all deps)
```bash
pip install pynput pyautogui python-xlib psutil Pillow mss
```
