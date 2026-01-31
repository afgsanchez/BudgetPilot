from __future__ import annotations
import re

_invalid = re.compile(r'[<>:"/\\|?*\x00-\x1F]')  # inválidos en Windows
_whitespace = re.compile(r"\s+")

def safe_filename(name: str, max_len: int = 120) -> str:
    name = name.strip()
    name = _invalid.sub("_", name)
    name = _whitespace.sub(" ", name)
    name = name.rstrip(". ")
    if len(name) > max_len:
        base, dot, ext = name.rpartition(".")
        if dot:
            base = base[: max_len - (len(ext) + 1)]
            name = f"{base}.{ext}"
        else:
            name = name[:max_len]
    return name or "archivo"