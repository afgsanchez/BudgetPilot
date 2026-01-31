from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

def open_with_default_app(path: str | Path) -> None:
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(str(p))

    if sys.platform.startswith("win"):
        os.startfile(str(p))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(p)], check=False)
    else:
        subprocess.run(["xdg-open", str(p)], check=False)