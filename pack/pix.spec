# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "data" / "stat_growth.json"), "pix/data"),
    (str(ROOT / "data" / "champion_aliases.json"), "pix/data"),
    (str(ROOT / "assets"), "pix/assets"),
    (str(ROOT / "pack" / "pix.ico"), "."),
]
datas += collect_data_files("certifi")

a = Analysis(
    [str(ROOT / "run_pix.py")],
    pathex=[str(ROOT.parent)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "certifi",
        "httpx",
        "httpcore",
        "h11",
        "anyio",
        "sniffio",
        "idna",
        "pix",
        "pix.app",
        "pix.calc",
        "pix.coach",
        "pix.input_win",
        "pix.live_client",
        "pix.overlay",
        "pix.paths",
        "pix.image_util",
        "pix.sprite",
        "pix.stg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "numpy",
        "webview",
        "rank_bm25",
        "bs4",
        "soupsieve",
        "pytest",
        "unittest",
        "tkinter",
        "tkinter.test",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Pix",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "pack" / "pix.ico"),
    version=str(ROOT / "pack" / "pix_version_info.txt"),
)
