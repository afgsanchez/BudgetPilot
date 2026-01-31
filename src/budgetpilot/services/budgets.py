from __future__ import annotations
from typing import Optional, Sequence
from ..db import get_conn
from ..config import STATUSES
from datetime import datetime

def create_budget(title: str, vendor: str, amount_estimated: float | None = None, currency: str = "EUR") -> int:
    if not title.strip():
        raise ValueError("El título no puede estar vacío.")
    if not vendor.strip():
        raise ValueError("El proveedor no puede estar vacío.")
    status = "SOLICITADO"
    if status not in STATUSES:
        status = STATUSES[0]

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO budgets (title, vendor, amount_estimated, currency, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title.strip(), vendor.strip(), amount_estimated, currency, status),
        )
        budget_id = cur.lastrowid
        conn.execute(
            """
            INSERT INTO status_history (budget_id, from_status, to_status, note)
            VALUES (?, ?, ?, ?)
            """,
            (budget_id, None, status, "Creado"),
        )
        return int(budget_id)

def list_open_budgets(limit: int = 200) -> Sequence[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, vendor, title, status, amount_estimated, currency, updated_at
            FROM budgets
            WHERE status NOT IN ('PAGADO', 'CANCELADO', 'RECHAZADO')
            ORDER BY datetime(updated_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

def get_budget(budget_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM budgets
            WHERE id = ?
            """,
            (budget_id,),
        ).fetchone()
        return dict(row) if row else None

def list_status_history(budget_id: int) -> Sequence[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT from_status, to_status, changed_at, note
            FROM status_history
            WHERE budget_id = ?
            ORDER BY datetime(changed_at) DESC
            """,
            (budget_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    
def kpis() -> dict:
    with get_conn() as conn:
        open_count = conn.execute(
            "SELECT COUNT(*) AS c FROM budgets WHERE status NOT IN ('PAGADO','CANCELADO','RECHAZADO')"
        ).fetchone()["c"]
        approved_pending = conn.execute(
            "SELECT COUNT(*) AS c FROM budgets WHERE status = 'APROBADO'"
        ).fetchone()["c"]
        ordered_pending = conn.execute(
            "SELECT COUNT(*) AS c FROM budgets WHERE status = 'PEDIDO_REALIZADO'"
        ).fetchone()["c"]
        invoiced_pending = conn.execute(
            "SELECT COUNT(*) AS c FROM budgets WHERE status = 'FACTURADO'"
        ).fetchone()["c"]
        return {
            "abiertos": open_count,
            "aprobados": approved_pending,
            "pedidos": ordered_pending,
            "facturados": invoiced_pending,
        }

def stalled(days: int = 5, limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, vendor, title, status, updated_at,
                   CAST((julianday('now') - julianday(updated_at)) AS INTEGER) AS dias
            FROM budgets
            WHERE status NOT IN ('PAGADO', 'CANCELADO', 'RECHAZADO')
              AND (julianday('now') - julianday(updated_at)) >= ?
            ORDER BY dias DESC
            LIMIT ?
            """,
            (days, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    

def set_status(budget_id: int, new_status: str, note: str | None = None) -> None:
    """Cambia el estado del presupuesto y registra el cambio en status_history.
    Si el estado no cambia pero hay nota, registra igualmente la nota en el histórico.
    """
    if new_status not in STATUSES:
        raise ValueError(f"Estado inválido: {new_status}")

    with get_conn() as conn:
        row = conn.execute("SELECT status FROM budgets WHERE id = ?", (budget_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe el presupuesto {budget_id}")

        old_status = row["status"]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ✅ Si no cambia el estado, pero hay nota, la registramos igualmente
        if old_status == new_status:
            if note:  # solo si hay texto
                conn.execute(
                    """
                    INSERT INTO status_history (budget_id, from_status, to_status, changed_at, note)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (budget_id, old_status, new_status, now, note),
                )
                # Opcional: actualizar updated_at para reflejar que hubo actividad
                conn.execute(
                    """
                    UPDATE budgets
                    SET updated_at = ?
                    WHERE id = ?
                    """,
                    (now, budget_id),
                )
            return

        # Si hay cambio de estado normal, hacemos update + histórico
        conn.execute(
            """
            UPDATE budgets
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, now, budget_id),
        )

        conn.execute(
            """
            INSERT INTO status_history (budget_id, from_status, to_status, changed_at, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (budget_id, old_status, new_status, now, note),
        )

def list_closed_budgets(limit: int = 200):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, vendor, title, status, amount_estimated, currency, updated_at
            FROM budgets
            WHERE status IN ('PAGADO', 'CANCELADO', 'RECHAZADO')
            ORDER BY datetime(updated_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    