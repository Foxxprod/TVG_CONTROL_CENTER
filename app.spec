# -*- mode: python ; coding: utf-8 -*-
#
# Specification PyInstaller (compilation en executable Windows) :
#
#     pyinstaller app.spec
#
# Resultat : dist\<APP_SLUG>\<APP_SLUG>.exe (mode "onedir", demarrage plus
# rapide qu'un "onefile" - garder tout le dossier ensemble). Le nom vient
# de project.APP_SLUG.
#
# icon.ico (vrai .ico, pas un .png renomme) sert deux fois : icone du .exe
# (icon=...) ET favicon embarque lu a l'execution (datas).
#
# console=True volontaire : les logs print() (play/take/stop...) restent
# visibles, et un print() sans console leverait une exception.

import sys

from PyInstaller.utils.hooks import collect_all

sys.path.insert(0, SPECPATH)
from project import APP_SLUG  # noqa: E402

datas = [
    ("assets", "assets"),
    ("templates.json", "."),
    ("icon.ico", "."),
]
binaries = []
hiddenimports = []

# NiceGUI embarque ses propres ressources statiques (JS/CSS/polices)
nicegui_datas, nicegui_binaries, nicegui_hiddenimports = collect_all("nicegui")
datas += nicegui_datas
binaries += nicegui_binaries
hiddenimports += nicegui_hiddenimports

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_SLUG,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_SLUG,
)
