from __future__ import annotations

import os
import sys
from pathlib import Path

PREFS_NAME = "prefs.json"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def package_root() -> Path:
    """pix 包所在目录（含 app.py、data/ 等）。"""
    return Path(__file__).resolve().parent


def pix_dir() -> Path:
    return package_root()


def project_root() -> Path:
    """开发时含 run_pix.py 的上层目录；打包后为 exe 所在目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    pkg = package_root()
    parent = pkg.parent
    if (parent / "run_pix.py").is_file():
        return parent
    return pkg


def _search_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            roots.append(resolved)

    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            add(Path(meipass) / "pix")
        add(Path(sys.executable).resolve().parent)
    else:
        add(package_root())
        add(project_root())

    return roots


def resolve_pix_file(category: str, name: str) -> Path | None:
    """在包目录与上层目录中查找 <category>/<name>。"""
    rels = (Path(category) / name, Path("pix") / category / name)
    for root in _search_roots():
        for rel in rels:
            path = root / rel
            if path.is_file():
                return path
    return None


def resolve_stat_growth_path() -> Path | None:
    found = resolve_pix_file("data", "stat_growth.json")
    if found:
        return found
    for root in _search_roots():
        alt = root / "data" / "lol_wiki" / "stat_growth.json"
        if alt.is_file():
            return alt
    return None


def data_dir() -> Path:
    found = resolve_stat_growth_path()
    if found:
        return found.parent
    return package_root() / "data"


def assets_dir() -> Path:
    for name in ("pix.png", "ready.png", "windup.png", "recovery.png"):
        found = resolve_pix_file("assets", name)
        if found:
            return found.parent
    for root in _search_roots():
        for rel in (Path("assets"), Path("pix") / "assets"):
            candidate = root / rel
            if candidate.is_dir():
                return candidate
    return package_root() / "assets"


def prefs_path() -> Path:
    if is_frozen():
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Pix"
        base.mkdir(parents=True, exist_ok=True)
        return base / PREFS_NAME
    return data_dir() / PREFS_NAME
