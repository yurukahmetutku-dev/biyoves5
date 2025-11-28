# PyInstaller spec for building the BiyoVes Windows bundle with all required Qt6 assets.
from pathlib import Path

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ
from PyInstaller.utils.hooks import collect_all, collect_submodules
from PyInstaller.utils.hooks.qt import pyside6_library_info

block_cipher = None

qt_info = pyside6_library_info

datas = []
binaries = []
hiddenimports = []

# Explicitly collect the Qt modules the app uses so their dependent DLLs/plugins are copied.
qt_modules = ["QtCore", "QtGui", "QtWidgets"]
for module in qt_modules:
    module_hidden, module_bins, module_datas = qt_info.collect_module(f"PySide6.{module}")
    hiddenimports += module_hidden
    binaries += module_bins
    datas += module_datas

# Bundle core Qt plugin types (platform + image support + TLS).
plugin_types = [
    "platforms",
    "styles",
    "iconengines",
    "imageformats",
    "platformthemes",
    "networkinformation",
    "tls",
]
for plugin_type in plugin_types:
    binaries += qt_info.collect_plugins(plugin_type)

# Qt network helpers, QML files, and any extra binaries shipped with PySide6.
binaries += qt_info.collect_qtnetwork_files()
qml_bins, qml_datas = qt_info.collect_qtqml_files()
binaries += qml_bins
datas += qml_datas
binaries += qt_info.collect_extra_binaries()

# Collect everything shipped in the PySide6 and shiboken6 wheels to avoid missing DLLs.
pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all("PySide6")
shiboken_datas, shiboken_binaries, shiboken_hidden = collect_all("shiboken6")
datas += pyside6_datas + shiboken_datas
binaries += pyside6_binaries + shiboken_binaries
hiddenimports += pyside6_hidden + shiboken_hidden + collect_submodules("PySide6")

# Qt6 OpenGL helpers that are often required at runtime.
qt_bin_dir = Path(qt_info.location["BinariesPath"])
for lib in ("opengl32sw.dll", "libEGL.dll", "libGLESv2.dll", "d3dcompiler_47.dll"):
    lib_path = qt_bin_dir / lib
    if lib_path.exists():
        binaries.append((str(lib_path), "."))

# De-duplicate lists to prevent PyInstaller warnings.
def _dedupe(seq):
    seen = set()
    deduped = []
    for item in seq:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped

datas = _dedupe(datas)
binaries = _dedupe(binaries)
hiddenimports = sorted(set(hiddenimports))

a = Analysis(
    ["main.py"],
    pathex=[str(Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd())],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="BiyoVes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BiyoVes",
)
