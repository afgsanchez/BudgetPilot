from __future__ import annotations
from pathlib import Path

APP_NAME = "BudgetPilot"

# Estados del flujo (puedes ajustar nombres luego)
STATUSES = [
    "SOLICITADO",
    "EN_ESPERA_RESPUESTA",
    "RECIBIDO",
    "APROBADO",
    "PEDIDO_REALIZADO",
    "ENTREGADO",
    "FACTURADO",
    "PAGADO",
    "CANCELADO",
    "RECHAZADO",
]

CLOSED_STATUSES = {"PAGADO", "CANCELADO", "RECHAZADO"}

def project_root() -> Path:
    """
    Devuelve la raíz del proyecto de forma portable.
    Asumimos estructura: <root>/src/budgetpilot/config.py
    """
    return Path(__file__).resolve().parents[2]

def data_dir() -> Path:
    return project_root() / "data"

def db_path() -> Path:
    return data_dir() / "budgetpilot.db"

def attachments_root() -> Path:
    return data_dir() / "attachments"

def exports_root() -> Path:
    return data_dir() / "exports"