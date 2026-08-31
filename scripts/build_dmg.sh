#!/usr/bin/env bash
# Build IntenType.app via py2app then package as IntenType.dmg
set -euo pipefail

VERSION="${APP_VERSION:-0.1.0}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Building IntenType $VERSION"

# Clean previous build
rm -rf build dist

# Build .app
python setup.py py2app 2>&1

APP="dist/IntenType.app"
if [ ! -d "$APP" ]; then
  echo "ERROR: $APP not found after py2app build"
  exit 1
fi

echo "==> Creating IntenType.dmg"
DMG="dist/IntenType-${VERSION}.dmg"

# Create a temporary writable image
TMP_DMG="dist/tmp_rw.dmg"
hdiutil create -size 300m -fs HFS+ -volname "IntenType" "$TMP_DMG" -ov -quiet

# Mount it
MOUNT="$(hdiutil attach "$TMP_DMG" -quiet -mountpoint /Volumes/IntenType_build && echo /Volumes/IntenType_build)"
MOUNT="/Volumes/IntenType_build"
hdiutil attach "$TMP_DMG" -mountpoint "$MOUNT" -quiet

# Copy app + Applications symlink
cp -R "$APP" "$MOUNT/"
ln -s /Applications "$MOUNT/Applications"

# Unmount and convert to compressed read-only
hdiutil detach "$MOUNT" -quiet
hdiutil convert "$TMP_DMG" -format UDZO -o "$DMG" -quiet
rm "$TMP_DMG"

echo "==> Done: $DMG"
