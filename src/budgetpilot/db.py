from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import db_path, data_dir, attachments_root

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    vendor TEXT NOT NULL,
    amount_estimated REAL,
    currency TEXT DEFAULT 'EUR',
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    target_date TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_id INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    note TEXT,
    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_id INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    stored_rel_path TEXT NOT NULL,  -- ruta relativa dentro de /data
    mime TEXT,
    size_bytes INTEGER,
    sha256 TEXT,
    tags TEXT,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_budgets_status ON budgets(status);
CREATE INDEX IF NOT EXISTS idx_budgets_updated ON budgets(updated_at);
CREATE INDEX IF NOT EXISTS idx_attachments_budget ON attachments(budget_id);
"""

def init_storage() -> None:
    """Crea carpetas data/ y data/attachments/ si no existen."""
    data_dir().mkdir(parents=True, exist_ok=True)
    attachments_root().mkdir(parents=True, exist_ok=True)

def init_db() -> None:
    """Crea la DB y las tablas si no existen."""
    init_storage()
    path = db_path()
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA_SQL)

@contextmanager
def get_conn():
    """Context manager para conexión SQLite con Row factory."""
    init_db()
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()