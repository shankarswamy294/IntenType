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

echo "==> Creating IntenType-${VERSION}.dmg"
DMG="dist/IntenType-${VERSION}.dmg"
TMP="dist/tmp_rw.dmg"
MOUNT="/Volumes/IntenType_Install"

rm -f "$TMP" "$DMG"

hdiutil create -size 400m -fs HFS+ -volname "IntenType" "$TMP" -ov -quiet
hdiutil attach "$TMP" -mountpoint "$MOUNT" -quiet

cp -R "$APP" "$MOUNT/"
ln -s /Applications "$MOUNT/Applications"

hdiutil detach "$MOUNT" -quiet
hdiutil convert "$TMP" -format UDZO -o "$DMG" -quiet
rm "$TMP"

echo "==> Done: $DMG ($(du -sh "$DMG" | cut -f1))"
