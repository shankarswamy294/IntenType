#!/bin/bash
# IntenType installer — strips Gatekeeper quarantine and copies to /Applications.
# Users double-click this file; Terminal opens and asks for their password once.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_SRC="$SCRIPT_DIR/IntenType.app"
APP_DST="/Applications/IntenType.app"

echo ""
echo "  IntenType Installer"
echo "  ────────────────────────────────────"

# Verify the app bundle is present next to this script
if [ ! -d "$APP_SRC" ]; then
  echo "  ERROR: IntenType.app not found next to this installer."
  echo "  Make sure you opened the DMG and are running Install.command from inside it."
  exit 1
fi

# Remove existing install if present
if [ -d "$APP_DST" ]; then
  echo "  Removing previous installation..."
  rm -rf "$APP_DST"
fi

echo "  Copying IntenType to /Applications..."
cp -R "$APP_SRC" "$APP_DST"

echo "  Removing quarantine (requires your Mac password)..."
sudo xattr -cr "$APP_DST"

echo "  Launching IntenType..."
open "$APP_DST"

echo ""
echo "  Done! The IntenType waveform icon is now in your menubar."
echo "  You can close this window."
echo ""
