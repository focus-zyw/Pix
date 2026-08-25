"""打包 Pix 为 Windows 单文件 exe。

用法:
  .\\.venv\\Scripts\\python build_pix.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    if ROOT.name.lower() != "pix":
        print("请把仓库目录改名为 pix 后再打包（内部按包名 pix 导入）。", file=sys.stderr)
        return 1

    pack_dir = ROOT / "pack"
    if str(pack_dir) not in sys.path:
        sys.path.insert(0, str(pack_dir))
    from make_pix_icon import write_pix_ico

    ico = write_pix_ico(pack_dir / "pix.ico")
    print(f"已生成图标: {ico}")

    spec = pack_dir / "pix.spec"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build" / "pix"),
        str(spec),
    ]
    print(" ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if completed.returncode != 0:
        return completed.returncode
    exe = ROOT / "dist" / "Pix.exe"
    print(f"打包完成: {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
