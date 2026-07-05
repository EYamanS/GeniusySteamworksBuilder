# PyInstaller spec for GENIUS Steamworks Builder
# Build with:  pyinstaller GENIUS.spec  (or run build_exe.bat)

from PyInstaller.utils.hooks import collect_all

datas = [("ui", "ui"), ("Icon.ico", ".")]
binaries = []
hiddenimports = [
    "keyring.backends.Windows",
    "clr",
]

for pkg in ("webview", "clr_loader", "pythonnet"):
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
    icon="Icon.ico",
)
