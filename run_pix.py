"""启动 Pix。仓库根目录须名为 pix，在其上级目录加入 sys.path。"""

from __future__ import annotations

import sys
from pathlib import Path

_pkg = Path(__file__).resolve().parent
_root = str(_pkg.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from pix.app import main

if __name__ == "__main__":
    main()
