import os
from setuptools import setup

APP = ["daemon/main.py"]

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icon.icns" if os.path.exists("assets/icon.icns") else None,
    "plist": {
        "LSUIElement": True,
        "CFBundleName": "IntenType",
        "CFBundleDisplayName": "IntenType",
        "CFBundleIdentifier": "com.intentype.app",
        "CFBundleVersion": os.environ.get("APP_VERSION", "0.1.0"),
        "CFBundleShortVersionString": os.environ.get("APP_VERSION", "0.1.0"),
        "NSMicrophoneUsageDescription": "IntenType records audio while you hold the Right Option key.",
        "NSAccessibilityUsageDescription": "IntenType reads the focused element to skip password fields.",
        "NSInputMonitoringUsageDescription": "IntenType listens for the Right Option key to start recording.",
        "NSHumanReadableCopyright": "© 2025 IntenType",
    },
    "packages": [
        "daemon",
        "numpy", "sounddevice",
        "faster_whisper", "tokenizers", "ctranslate2",
        "openai", "httpx", "anyio",
        "objc", "AppKit", "Foundation", "Quartz",
        "CoreFoundation", "ApplicationServices",
    ],
    "strip": False,
    # Native dylibs (e.g. libportaudio) can't load from inside a zip
    "compressed": False,
    "resources": [
        "assets/menubar.png",
        "assets/menubar_rec_0.png",
        "assets/menubar_rec_1.png",
        "assets/menubar_rec_2.png",
        "assets/menubar_rec_3.png",
    ],
}

setup(
    name="IntenType",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
