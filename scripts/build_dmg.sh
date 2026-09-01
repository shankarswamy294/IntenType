#!/usr/bin/env bash
# Build IntenType.app via py2app then package as IntenType.dmg
set -euo pipefail

VERSION="${APP_VERSION:-0.1.0}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Building IntenType $VERSION"
rm -rf build dist

PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" setup.py py2app 2>&1

APP="dist/IntenType.app"
[ -d "$APP" ] || { echo "ERROR: $APP not found"; exit 1; }

# py2app zips _sounddevice_data which contains libportaudio.dylib.
# Native dylibs can't dlopen from inside a zip — extract to the real lib dir.
echo "==> Extracting _sounddevice_data from python314.zip (libportaudio can't load from zip)"
"$PYTHON" -c "
import zipfile, os, shutil, tempfile

zip_path = 'dist/IntenType.app/Contents/Resources/lib/python314.zip'
out_dir  = 'dist/IntenType.app/Contents/Resources/lib/python3.14'

# Extract to real directory
with zipfile.ZipFile(zip_path) as z:
    names = [n for n in z.namelist() if n.startswith('_sounddevice_data/')]
    for name in names:
        z.extract(name, out_dir)
    print(f'  extracted {len(names)} entries -> {out_dir}')

# Rewrite zip without the _sounddevice_data entries so Python uses the directory
tmp = zip_path + '.tmp'
with zipfile.ZipFile(zip_path) as src, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as dst:
    for item in src.infolist():
        if not item.filename.startswith('_sounddevice_data/'):
            dst.writestr(item, src.read(item.filename))
os.replace(tmp, zip_path)
print('  removed _sounddevice_data from zip')
"

echo "==> Signing app bundle (ad-hoc)"
# Replace liblzma with a clean Homebrew copy before signing
LZMA_SRC="$(brew --prefix xz)/lib/liblzma.5.dylib"
LZMA_DST="$APP/Contents/Frameworks/liblzma.5.dylib"
[ -f "$LZMA_SRC" ] && cp "$LZMA_SRC" "$LZMA_DST"
# Sign all dylibs and .so files first (leaf nodes)
find "$APP" -type f \( -name "*.dylib" -o -name "*.so" \) | while read f; do
  codesign --sign - --force --timestamp=none "$f" 2>/dev/null; true
done
# Sign the full bundle
codesign --sign - --force --deep --timestamp=none "$APP" 2>&1 || true
xattr -cr "$APP"

echo "==> Creating IntenType-${VERSION}.dmg"
DMG="dist/IntenType-${VERSION}.dmg"
TMP="dist/tmp_rw.dmg"
MOUNT="/Volumes/IntenType_Install"

rm -f "$TMP" "$DMG"

hdiutil create -size 400m -fs HFS+ -volname "IntenType" "$TMP" -ov -quiet
hdiutil attach "$TMP" -mountpoint "$MOUNT" -quiet

cp -R "$APP" "$MOUNT/"
ln -s /Applications "$MOUNT/Applications"

# Bundle the installer script so users can bypass Gatekeeper without Terminal
cp scripts/Install.command "$MOUNT/Install.command"
chmod +x "$MOUNT/Install.command"
# Strip quarantine from the installer script itself
xattr -d com.apple.quarantine "$MOUNT/Install.command" 2>/dev/null || true

hdiutil detach "$MOUNT" -quiet
hdiutil convert "$TMP" -format UDZO -o "$DMG" -quiet
rm "$TMP"

echo "==> Done: $DMG ($(du -sh "$DMG" | cut -f1))"
