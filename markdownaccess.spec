# -*- mode: python ; coding: utf-8 -*-
"""Recette PyInstaller (mode onedir) pour MarkdownAccess.

Build :  uv run pyinstaller markdownaccess.spec
Sortie : dist/MarkdownAccess/  (dossier packageable par Inno Setup)

onedir (et non onefile) : Inno empaquette le dossier ; la mise à jour remplace
les fichiers en place. Les pièges d'embarquement sont ceux documentés dans
CLAUDE.md (locales, accessible_output2, mdit_py_plugins, WebView2).
"""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []

# locales compilées (.mo) — sinon l'anglais disparaît dans l'exe.
if os.path.isdir("locales"):
    datas.append(("locales", "locales"))

# DLL de accessible_output2 (nvdaControllerClient*.dll) : ce sont des *données*
# non vues par l'analyse statique.
datas += collect_data_files("accessible_output2")

# WebView2Loader.dll (aperçu F6, backend Edge) : fournie par wxPython, non
# détectée automatiquement → on la place à la racine du build.
try:
    import wx as _wx
    _wxdir = os.path.dirname(_wx.__file__)
    for _root, _dirs, _files in os.walk(_wxdir):
        if "WebView2Loader.dll" in _files:
            datas.append((os.path.join(_root, "WebView2Loader.dll"), "."))
            break
except Exception:
    pass

# Sous-modules chargés dynamiquement par l'aperçu (footnotes/tasklists) + backend
# JAWS de accessible_output2 qui passe par COM (pywin32).
hiddenimports = collect_submodules("mdit_py_plugins") + [
    "win32com",
    "win32com.client",
    "pythoncom",
    "pywintypes",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
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
    [],
    exclude_binaries=True,
    name="MarkdownAccess",
    debug=False,
    strip=False,
    upx=False,
    console=False,          # équivalent --windowed (pas de console)
    icon=None,              # TODO: icône .ico quand disponible
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MarkdownAccess",
)
