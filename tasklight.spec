# tasklight.spec — PyInstaller spec (Linux / Mac)
# Usage: pyinstaller tasklight.spec --clean --noconfirm

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pynput.keyboard._xorg',
        'pynput.mouse._xorg',
        'pynput._util.xorg',
        'pynput._util.xorg_keysyms',
        'Xlib', 'Xlib.display', 'Xlib.protocol',
        'Xlib.ext', 'Xlib.keysymdef',
        'pyautogui', 'tkinter', 'tkinter.ttk',
        'tkinter.filedialog', 'tkinter.messagebox',
        'psutil', 'PIL', 'PIL.ImageGrab',
        'mss',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='tasklight',
    debug=False, strip=False, upx=True,
    console=False,
    runtime_tmpdir=None,
)
