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
                    model_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Ensure model_file column exists if table was created previously without it
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(products)")
            cols = [row["name"] for row in cursor.fetchall()]
            if "model_file" not in cols:
                conn.execute("ALTER TABLE products ADD COLUMN model_file TEXT")

            # Recreate alias view 'prodcuts' to keep columns and spelling variations in sync
            conn.execute("DROP VIEW IF EXISTS prodcuts")
            conn.execute("""
                CREATE VIEW prodcuts AS SELECT * FROM products
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


def get_product_by_id(product_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single product by ID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ? LIMIT 1", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
