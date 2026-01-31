from __future__ import annotations

import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import Sequence

from ..config import attachments_root, data_dir
from ..db import get_conn
from ..utils.hashing import sha256_file
from ..utils.paths import safe_filename

def _budget_folder(budget_id: int) -> Path:
    return attachments_root() / str(budget_id)

def add_attachment(budget_id: int, source_path: str, tags: str | None = None) -> int:
    src = Path(source_path).expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"No existe el archivo: {src}")

    dest_dir = _budget_folder(budget_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = safe_filename(src.name)
    dest_name = f"{ts}_{safe_name}"
    dest_abs = dest_dir / dest_name

    shutil.copy2(src, dest_abs)

    size_bytes = dest_abs.stat().st_size
    mime, _ = mimetypes.guess_type(dest_abs.name)
    file_hash = sha256_file(dest_abs)

    # Guardamos ruta RELATIVA a /data para máxima portabilidad
    rel = dest_abs.relative_to(data_dir()).as_posix()

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO attachments (budget_id, original_name, stored_rel_path, mime, size_bytes, sha256, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (budget_id, src.name, rel, mime, size_bytes, file_hash, tags),
        )
        return int(cur.lastrowid)

def list_attachments(budget_id: int) -> Sequence[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, original_name, stored_rel_path, mime, size_bytes, sha256, tags, added_at
            FROM attachments
            WHERE budget_id = ?
            ORDER BY datetime(added_at) DESC
            """,
            (budget_id,),
        ).fetchall()
        return [dict(r) for r in rows]

def resolve_attachment_path(stored_rel_path: str) -> Path:
    return (data_dir() / stored_rel_path).resolve()

def delete_attachment(attachment_id: int) -> None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT stored_rel_path FROM attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()
        if not row:
            return
        abs_path = resolve_attachment_path(row["stored_rel_path"])
        conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))

    # Borrado físico (best-effort)
    try:
        if abs_path.exists():
            abs_path.unlink()
    except Exception:
        pass