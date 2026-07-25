#!/bin/bash
set -e
echo "━━━ PyInstaller ━━━"
pyinstaller tasklight.spec --clean --noconfirm

echo "━━━ Building AppDir ━━━"
rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/share/applications \
         AppDir/usr/share/icons/hicolor/256x256/apps

cp dist/tasklight AppDir/usr/bin/tasklight

cat > AppDir/tasklight.desktop << 'DESKTOP'
[Desktop Entry]
Name=TaskLight
Comment=Macro recorder and system tools
Exec=tasklight
Icon=tasklight
Type=Application
Categories=Utility;
DESKTOP

cp AppDir/tasklight.desktop AppDir/usr/share/applications/

python3 -c "
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (256,256), (22,22,22,255))
    d = ImageDraw.Draw(img)
    d.ellipse([20,20,236,236], fill=(74,143,196,255))
    d.text((72,88), 'TL', fill='white')
    img.save('icon.png')
except: pass
" 2>/dev/null || true

[ -f icon.png ] && \
    cp icon.png AppDir/tasklight.png && \
    cp icon.png AppDir/usr/share/icons/hicolor/256x256/apps/tasklight.png

cat > AppDir/AppRun << 'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/tasklight" "$@"
APPRUN
chmod +x AppDir/AppRun

echo "━━━ Packing AppImage ━━━"
ARCH=x86_64 ./appimagetool-x86_64.AppImage AppDir TaskLight-x86_64.AppImage

echo "━━━ Done! ━━━"
echo "→ TaskLight-x86_64.AppImage"
