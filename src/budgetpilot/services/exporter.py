from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ..config import data_dir, exports_root
from ..db import get_conn
from ..utils.paths import safe_filename

def _get_budget(budget_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
        return dict(row) if row else None

def _get_history(budget_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT from_status, to_status, changed_at, note
            FROM status_history
            WHERE budget_id = ?
            ORDER BY datetime(changed_at) ASC
            """,
            (budget_id,),
        ).fetchall()
        return [dict(r) for r in rows]

def _get_attachments(budget_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, original_name, stored_rel_path, mime, size_bytes, sha256, tags, added_at
            FROM attachments
            WHERE budget_id = ?
            ORDER BY datetime(added_at) ASC
            """,
            (budget_id,),
        ).fetchall()
        return [dict(r) for r in rows]

def export_budget(budget_id: int, destination_root: Path | None = None) -> Path:
    """
    Exporta un presupuesto a una carpeta:
      - resumen.txt (datos + histórico + lista de adjuntos)
      - attachments/ (copia física de adjuntos existentes)
    Devuelve la ruta a la carpeta exportada.
    """
    budget = _get_budget(budget_id)
    if not budget:
        raise ValueError(f"No existe el presupuesto {budget_id}")

    history = _get_history(budget_id)
    attachments = _get_attachments(budget_id)

    # Carpeta destino (por defecto data/exports)
    root = destination_root or exports_root()
    root.mkdir(parents=True, exist_ok=True)

    # Nombre de carpeta export (portable y legible)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    vendor = safe_filename(budget.get("vendor", "Proveedor"))
    title = safe_filename(budget.get("title", "SinTitulo"))
    folder_name = f"BP_{budget_id:06d}_{ts}_{vendor}_{title}"
    export_dir = root / folder_name
    export_dir.mkdir(parents=True, exist_ok=True)

    # Subcarpeta de adjuntos
    export_attachments_dir = export_dir / "attachments"
    export_attachments_dir.mkdir(parents=True, exist_ok=True)

    # Crear resumen.txt
    resumen_path = export_dir / "resumen.txt"

    amount = budget.get("amount_estimated")
    currency = budget.get("currency") or ""
    amount_str = f"{amount:.2f} {currency}".strip() if isinstance(amount, (int, float)) else "-"

    lines: list[str] = []
    lines.append(f"BudgetPilot - Export de presupuesto #{budget['id']}")
    lines.append("=" * 60)
    lines.append(f"Proveedor       : {budget.get('vendor', '')}")
    lines.append(f"Num. Presupuesto: {budget.get('title', '')}")
    lines.append(f"Estado          : {budget.get('status', '')}")
    lines.append(f"Importe         : {amount_str}")
    lines.append(f"Creado          : {budget.get('created_at', '')}")
    lines.append(f"Actualizado     : {budget.get('updated_at', '')}")
    if budget.get("target_date"):
        lines.append(f"Fecha objetivo : {budget.get('target_date')}")
    if budget.get("notes"):
        lines.append("")
        lines.append("Notas:")
        lines.append(budget.get("notes", ""))

    lines.append("")
    lines.append("Histórico de estados:")
    lines.append("-" * 60)
    if not history:
        lines.append("  (sin histórico)")
    else:
        for h in history:
            from_s = h.get("from_status") or "∅"
            to_s = h.get("to_status") or ""
            when = h.get("changed_at") or ""
            note = h.get("note") or ""
            lines.append(f"  - {when}: {from_s} -> {to_s} {('- ' + note) if note else ''}")

    lines.append("")
    lines.append("Adjuntos:")
    lines.append("-" * 60)
    if not attachments:
        lines.append("  (sin adjuntos)")
    else:
        for a in attachments:
            size = a.get("size_bytes") or 0
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.2f} MB"
            lines.append(
                f"  - ID {a['id']}: {a.get('original_name','')} | {a.get('added_at','')} | {size_str} | tags={a.get('tags') or ''}"
            )
            lines.append(f"    rel_path: {a.get('stored_rel_path','')}")
            if a.get("sha256"):
                lines.append(f"    sha256: {a.get('sha256')}")

    resumen_path.write_text("\n".join(lines), encoding="utf-8")

    # Copiar adjuntos físicos al export
    # stored_rel_path es relativo a data/
    for a in attachments:
        rel = a.get("stored_rel_path")
        if not rel:
            continue
        src = (data_dir() / rel).resolve()
        if src.exists() and src.is_file():
            # Conservamos el nombre real almacenado (timestamp + safe original)
            dest = export_attachments_dir / src.name
            try:
                shutil.copy2(src, dest)
            except Exception:
                # Si algún archivo no se puede copiar, seguimos (pero el resumen lo reflejará)
                pass

    return export_dir