# PyInstaller spec for GENIUS Steamworks Builder
# Windows:  pyinstaller GENIUS.spec  (or run build_exe.bat)  -> dist\GENIUS Steamworks Builder.exe
# macOS:    pyinstaller GENIUS.spec  (or run build_app.sh)   -> dist/GENIUS Steamworks Builder.app

import sys

from PyInstaller.utils.hooks import collect_all

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

datas = [("ui", "ui")]
binaries = []
hiddenimports = []

if IS_WIN:
    datas.append(("Icon.ico", "."))
    hiddenimports += ["keyring.backends.Windows", "clr"]
    collect_pkgs = ("webview", "clr_loader", "pythonnet")
else:
    hiddenimports += ["keyring.backends.macOS"]
    collect_pkgs = ("webview",)

for pkg in collect_pkgs:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ["genius_builder.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GENIUS Steamworks Builder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,          # no console window
    disable_windowed_traceback=False,
    icon="Icon.ico" if IS_WIN else "Icon.icns",
)

if IS_MAC:
    app = BUNDLE(
        exe,
        name="GENIUS Steamworks Builder.app",
        icon="Icon.icns",
        bundle_identifier="com.geniusy.steamworks-builder",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "LSApplicationCategoryType": "public.app-category.developer-tools",
            "NSHumanReadableCopyright": "MIT License",
        },
    )
