import os
import sqlite3
from typing import List, Dict, Any, Optional

BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "data", "products.db")
DB_PATH = os.environ.get("SQLITE_DB_PATH", DEFAULT_DB_PATH)


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a SQLite database connection with row factory enabled."""
    target_path = db_path or DB_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and views."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            # Create primary 'products' table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_name TEXT NOT NULL UNIQUE,
                    part_length REAL NOT NULL,
                    part_breadth REAL NOT NULL,
                    part_height REAL NOT NULL,
                    part_weight REAL NOT NULL,
                    part_type TEXT NOT NULL,
                    standard_no_of_parts INTEGER NOT NULL,
                    domestic_or_international TEXT NOT NULL,
                    per_day_requirement INTEGER NOT NULL,
                    minimum_order_quantity INTEGER NOT NULL,
                    line_feeding_method TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create alias view 'prodcuts' to handle spelling variations
            conn.execute("""
                CREATE VIEW IF NOT EXISTS prodcuts AS SELECT * FROM products
            """)
    finally:
        conn.close()


def get_all_products(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query all products from SQLite database."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_product_by_name(part_name: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single product by part name."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE LOWER(part_name) = LOWER(?) LIMIT 1", (part_name.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

