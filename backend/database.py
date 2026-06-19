"""
database.py — SQLite connection helper for the FastAPI backend.
"""
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "trade_analytics.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with Row factory enabled."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Please run:  python etl/etl_pipeline.py"
        )
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
