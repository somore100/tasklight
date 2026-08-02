# tasklight_macos.spec — PyInstaller spec for macOS
# Run on macOS: pyinstaller tasklight_macos.spec --clean --noconfirm

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('logo.png', '.')],
    hiddenimports=[
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
        'pyautogui',
        'tkinter', 'tkinter.ttk',
        'tkinter.filedialog', 'tkinter.messagebox',
        'psutil', 'PIL', 'PIL.ImageGrab',
        'mss', 'session_switch',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['Xlib', 'pynput._util.xorg', 'evdev'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='TaskLight',
    debug=False, strip=False, upx=True, console=False,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True,
    name='TaskLight',
)

app = BUNDLE(
    coll,
    name='TaskLight.app',
    icon='logo.png',
    bundle_identifier='com.tasklight.app',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleName': 'TaskLight',
        'NSHighResolutionCapable': True,
        'LSUIElement': False,
    },
)
