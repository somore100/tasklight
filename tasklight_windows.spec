# tasklight_windows.spec — PyInstaller spec (Windows)
# Run ON WINDOWS: pyinstaller tasklight_windows.spec --clean --noconfirm

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pyautogui', 'tkinter', 'tkinter.ttk',
        'tkinter.filedialog', 'tkinter.messagebox',
        'psutil', 'PIL', 'PIL.ImageGrab',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['Xlib', 'pynput._util.xorg'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='TaskLight',
    debug=False, strip=False, upx=True,
    console=False,
    # icon='icon.ico',
)
