from setuptools import setup
import os

APP = ["daemon/main.py"]
DIST_DIR = os.path.join("dashboard", "dist")
DATA_FILES = [("dist", [os.path.join(DIST_DIR, f) for f in os.listdir(DIST_DIR)])]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "LSUIElement": True,
        "CFBundleName": "IntenType",
        "CFBundleDisplayName": "IntenType",
        "CFBundleIdentifier": "com.intentype.app",
        "NSMicrophoneUsageDescription": "Required to record audio for voice typing.",
        "NSAccessibilityUsageDescription": "Required to read cursor focus and inject text.",
    },
    "packages": [
        "fastapi", "uvicorn", "starlette", "pydantic",
        "sounddevice", "numpy", "faster_whisper",
        "openai", "httpx", "anyio",
        "objc", "Cocoa", "Quartz", "AppKit", "CoreFoundation",
    ],
    "includes": ["daemon"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
