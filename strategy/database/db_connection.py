import sqlite3
from pathlib import Path


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Database directory
DATABASE_DIR = PROJECT_ROOT / "database"

# SQLite database file
DATABASE_PATH = DATABASE_DIR / "crypto_research.db"


def get_connection():
    """
    Create and return a SQLite database connection.
    """

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    # Enable foreign key constraints
    connection.execute("PRAGMA foreign_keys = ON")

    return connection

