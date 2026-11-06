import os
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "data", "products.db")
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
_configured_db_path = os.environ.get("SQLITE_DB_PATH")
if not _configured_db_path:
    DB_PATH = DEFAULT_DB_PATH
elif os.path.isabs(_configured_db_path):
    DB_PATH = _configured_db_path
else:
    normalized_db_path = os.path.normpath(_configured_db_path)
    path_root = PROJECT_ROOT if normalized_db_path.split(os.sep, 1)[0].lower() == os.path.basename(BACKEND_DIR).lower() else BACKEND_DIR
    DB_PATH = os.path.abspath(os.path.join(path_root, normalized_db_path))


def get_db_connection(db_path: Optional[str] = None, *, create: bool = False) -> sqlite3.Connection:
    """Create and return a SQLite database connection with row factory enabled."""
    target_path = os.path.abspath(db_path or DB_PATH)
    if not os.path.exists(target_path):
        if not create:
            raise FileNotFoundError(f"Configured SQLite database does not exist: {target_path}")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_database_status() -> Dict[str, Any]:
    """Inspect the configured database read-only so health checks never create an empty DB."""
    target_path = os.path.abspath(DB_PATH)
    if not os.path.isfile(target_path):
        return {"path": target_path, "exists": False, "required_tables": {"products": False, "packages": False}}
    uri = f"{Path(target_path).as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        required = {"products": "products" in tables, "packages": "packages" in tables}
        return {
            "path": target_path,
            "exists": True,
            "required_tables": required,
            "optional_packaging_tables": {
                name: name in tables for name in ("base_pallets", "metal_pallets", "metal_stillages")
            },
            "healthy": all(required.values()),
        }
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and views for products, packages, pallets, stillages, and trucks."""
    conn = get_db_connection(db_path, create=True)
    try:
        with conn:
            # 1. Primary 'products' table
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

            # 2. 'packages' table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package TEXT NOT NULL UNIQUE,
                    outer_length_mm REAL NOT NULL,
                    outer_width_mm REAL NOT NULL,
                    outer_height_mm REAL NOT NULL,
                    inner_length_mm REAL NOT NULL,
                    inner_width_mm REAL NOT NULL,
                    inner_height_mm REAL NOT NULL,
                    empty_weight_kg REAL NOT NULL,
                    part_weight_kg REAL NOT NULL,
                    total_weight_kg REAL NOT NULL,
                    pallet_length_mm REAL,
                    pallet_width_mm REAL,
                    pallet_height_mm REAL,
                    bins_per_row INTEGER,
                    bins_per_column INTEGER,
                    layers_per_pallet INTEGER,
                    bins_per_pallet INTEGER,
                    stack_height_mm REAL,
                    pallet_load_weight_kg REAL,
                    inventory INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. 'base_pallets' table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS base_pallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    base_pallet TEXT NOT NULL UNIQUE,
                    outer_length_mm REAL NOT NULL,
                    outer_width_mm REAL NOT NULL,
                    outer_height_mm REAL NOT NULL,
                    empty_weight_kg REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. 'metal_pallets' table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metal_pallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metal_pallet TEXT NOT NULL UNIQUE,
                    outer_length_mm REAL NOT NULL,
                    outer_width_mm REAL NOT NULL,
                    outer_height_mm REAL NOT NULL,
                    inner_length_mm REAL NOT NULL,
                    inner_width_mm REAL NOT NULL,
                    inner_height_mm REAL NOT NULL,
                    empty_weight_kg REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. 'metal_stillages' table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metal_stillages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metal_stillage TEXT NOT NULL UNIQUE,
                    outer_length_mm REAL NOT NULL,
                    outer_width_mm REAL NOT NULL,
                    outer_height_mm REAL NOT NULL,
                    inner_length_mm REAL NOT NULL,
                    inner_width_mm REAL NOT NULL,
                    inner_height_mm REAL NOT NULL,
                    empty_weight_kg REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. 'trucks' table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trucks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    truck TEXT NOT NULL UNIQUE,
                    inner_length_mm REAL NOT NULL,
                    inner_width_mm REAL NOT NULL,
                    inner_height_mm REAL NOT NULL,
                    capacity_kg REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. 'cart' table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cart (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    part_name TEXT NOT NULL UNIQUE,
                    part_type TEXT DEFAULT 'Standard',
                    part_length REAL NOT NULL,
                    part_breadth REAL NOT NULL,
                    part_height REAL NOT NULL,
                    part_weight REAL NOT NULL DEFAULT 0.0,
                    number_of_parts INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
                )
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


def insert_product(product_data: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Insert a single product into SQLite database.
    
    If part_name already exists, updates the product with new specifications.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            name = str(product_data.get("part_name") or product_data.get("name", "")).strip()
            if not name:
                raise ValueError("part_name is required")

            cursor.execute(
                """
                INSERT INTO products (
                    part_name,
                    part_length,
                    part_breadth,
                    part_height,
                    part_weight,
                    part_type,
                    standard_no_of_parts,
                    domestic_or_international,
                    per_day_requirement,
                    minimum_order_quantity,
                    line_feeding_method,
                    model_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(part_name) DO UPDATE SET
                    part_length=excluded.part_length,
                    part_breadth=excluded.part_breadth,
                    part_height=excluded.part_height,
                    part_weight=excluded.part_weight,
                    part_type=excluded.part_type,
                    standard_no_of_parts=excluded.standard_no_of_parts,
                    domestic_or_international=excluded.domestic_or_international,
                    per_day_requirement=excluded.per_day_requirement,
                    minimum_order_quantity=excluded.minimum_order_quantity,
                    line_feeding_method=excluded.line_feeding_method,
                    model_file=COALESCE(excluded.model_file, products.model_file)
                """,
                (
                    name,
                    float(product_data.get("part_length") or product_data.get("length", 100.0)),
                    float(product_data.get("part_breadth") or product_data.get("part_width") or product_data.get("width", 50.0)),
                    float(product_data.get("part_height") or product_data.get("height", 30.0)),
                    float(product_data.get("part_weight") or product_data.get("weight", 0.5)),
                    str(product_data.get("part_type") or product_data.get("material", "Standard")).strip(),
                    int(product_data.get("standard_no_of_parts") or product_data.get("snp", 1)),
                    str(product_data.get("domestic_or_international", "Domestic")).strip(),
                    int(product_data.get("per_day_requirement", 100)),
                    int(product_data.get("minimum_order_quantity") or product_data.get("moq", 1)),
                    str(product_data.get("line_feeding_method", "Two-Bin System")).strip(),
                    str(product_data.get("model_file") or "").strip() or None,
                ),
            )
            cursor.execute("SELECT * FROM products WHERE LOWER(part_name) = LOWER(?) LIMIT 1", (name,))
            row = cursor.fetchone()
            return dict(row) if row else {"part_name": name, **product_data}
    finally:
        conn.close()


def insert_products_batch(products_list: List[Dict[str, Any]], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Insert or update a batch of products in SQLite database.
    
    Returns total processed count, added count, and any row errors.
    """
    conn = get_db_connection(db_path)
    added_count = 0
    errors: List[str] = []

    try:
        with conn:
            cursor = conn.cursor()
            for idx, p in enumerate(products_list):
                try:
                    name = str(p.get("part_name") or p.get("name", "")).strip()
                    if not name:
                        errors.append(f"Row {idx + 1}: Missing part name")
                        continue

                    cursor.execute(
                        """
                        INSERT INTO products (
                            part_name,
                            part_length,
                            part_breadth,
                            part_height,
                            part_weight,
                            part_type,
                            standard_no_of_parts,
                            domestic_or_international,
                            per_day_requirement,
                            minimum_order_quantity,
                            line_feeding_method,
                            model_file
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(part_name) DO UPDATE SET
                            part_length=excluded.part_length,
                            part_breadth=excluded.part_breadth,
                            part_height=excluded.part_height,
                            part_weight=excluded.part_weight,
                            part_type=excluded.part_type,
                            standard_no_of_parts=excluded.standard_no_of_parts,
                            domestic_or_international=excluded.domestic_or_international,
                            per_day_requirement=excluded.per_day_requirement,
                            minimum_order_quantity=excluded.minimum_order_quantity,
                            line_feeding_method=excluded.line_feeding_method,
                            model_file=COALESCE(excluded.model_file, products.model_file)
                        """,
                        (
                            name,
                            float(p.get("part_length") or p.get("length", 100.0)),
                            float(p.get("part_breadth") or p.get("part_width") or p.get("width", 50.0)),
                            float(p.get("part_height") or p.get("height", 30.0)),
                            float(p.get("part_weight") or p.get("weight", 0.5)),
                            str(p.get("part_type") or p.get("material", "Standard")).strip(),
                            int(p.get("standard_no_of_parts") or p.get("snp", 1)),
                            str(p.get("domestic_or_international", "Domestic")).strip(),
                            int(p.get("per_day_requirement", 100)),
                            int(p.get("minimum_order_quantity") or p.get("moq", 1)),
                            str(p.get("line_feeding_method", "Two-Bin System")).strip(),
                            str(p.get("model_file") or "").strip() or None,
                        ),
                    )
                    added_count += 1
                except Exception as ex:
                    errors.append(f"Row {idx + 1} ('{p.get('part_name', 'Unknown')}'): {str(ex)}")

        return {
            "success": True,
            "added_count": added_count,
            "total_processed": len(products_list),
            "errors": errors,
        }
    finally:
        conn.close()


def get_all_packages(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query all packages from SQLite database."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM packages ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_base_pallets(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query all base pallets from SQLite database."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM base_pallets ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_metal_pallets(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query all metal pallets from SQLite database."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM metal_pallets ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_metal_stillages(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query all metal stillages from SQLite database."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM metal_stillages ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_trucks(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query all trucks from SQLite database."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trucks ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_unified_packaging(category: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query and return unified packaging units (excluding trucks).

    Supports filtering by category: 'carton', 'base_pallet', 'metal_pallet', 'metal_stillage', or None/'all'.
    """
    items: List[Dict[str, Any]] = []
    cat_lower = (category or "").lower().strip()

    # 1. Cartons (table: packages)
    if not cat_lower or cat_lower in ("all", "carton", "cartons", "box", "boxes"):
        cartons = get_all_packages(db_path)
        for c in cartons:
            item = dict(c)
            item["category"] = "carton"
            item["category_label"] = "Carton Box"
            item["inventory"] = None
            items.append(item)

    # 2. Base Pallets (table: base_pallets)
    if not cat_lower or cat_lower in ("all", "base_pallet", "base_pallets", "pallets"):
        pallets = get_all_base_pallets(db_path)
        for p in pallets:
            item = {
                "id": p.get("id"),
                "package": p.get("base_pallet"),
                "category": "base_pallet",
                "category_label": "Base Pallet",
                "outer_length_mm": p.get("outer_length_mm"),
                "outer_width_mm": p.get("outer_width_mm"),
                "outer_height_mm": p.get("outer_height_mm"),
                "inner_length_mm": None,
                "inner_width_mm": None,
                "inner_height_mm": None,
                "empty_weight_kg": p.get("empty_weight_kg"),
                "part_weight_kg": None,
                "total_weight_kg": p.get("empty_weight_kg"),
                "pallet_length_mm": p.get("outer_length_mm"),
                "pallet_width_mm": p.get("outer_width_mm"),
                "pallet_height_mm": p.get("outer_height_mm"),
                "bins_per_row": None,
                "bins_per_column": None,
                "layers_per_pallet": None,
                "bins_per_pallet": None,
                "stack_height_mm": p.get("outer_height_mm"),
                "pallet_load_weight_kg": None,
                "inventory": None,
                "created_at": p.get("created_at"),
            }
            items.append(item)

    # 3. Metal Pallets (table: metal_pallets)
    if not cat_lower or cat_lower in ("all", "metal_pallet", "metal_pallets"):
        mpallets = get_all_metal_pallets(db_path)
        for mp in mpallets:
            item = {
                "id": mp.get("id"),
                "package": mp.get("metal_pallet"),
                "category": "metal_pallet",
                "category_label": "Metal Pallet",
                "outer_length_mm": mp.get("outer_length_mm"),
                "outer_width_mm": mp.get("outer_width_mm"),
                "outer_height_mm": mp.get("outer_height_mm"),
                "inner_length_mm": mp.get("inner_length_mm"),
                "inner_width_mm": mp.get("inner_width_mm"),
                "inner_height_mm": mp.get("inner_height_mm"),
                "empty_weight_kg": mp.get("empty_weight_kg"),
                "part_weight_kg": None,
                "total_weight_kg": mp.get("empty_weight_kg"),
                "pallet_length_mm": mp.get("outer_length_mm"),
                "pallet_width_mm": mp.get("outer_width_mm"),
                "pallet_height_mm": mp.get("outer_height_mm"),
                "bins_per_row": None,
                "bins_per_column": None,
                "layers_per_pallet": None,
                "bins_per_pallet": None,
                "stack_height_mm": mp.get("outer_height_mm"),
                "pallet_load_weight_kg": None,
                "inventory": None,
                "created_at": mp.get("created_at"),
            }
            items.append(item)

    # 4. Metal Stillages (table: metal_stillages)
    if not cat_lower or cat_lower in ("all", "metal_stillage", "metal_stillages", "stillages"):
        stillages = get_all_metal_stillages(db_path)
        for st in stillages:
            item = {
                "id": st.get("id"),
                "package": st.get("metal_stillage"),
                "category": "metal_stillage",
                "category_label": "Metal Stillage",
                "outer_length_mm": st.get("outer_length_mm"),
                "outer_width_mm": st.get("outer_width_mm"),
                "outer_height_mm": st.get("outer_height_mm"),
                "inner_length_mm": st.get("inner_length_mm"),
                "inner_width_mm": st.get("inner_width_mm"),
                "inner_height_mm": st.get("inner_height_mm"),
                "empty_weight_kg": st.get("empty_weight_kg"),
                "part_weight_kg": None,
                "total_weight_kg": st.get("empty_weight_kg"),
                "pallet_length_mm": st.get("outer_length_mm"),
                "pallet_width_mm": st.get("outer_width_mm"),
                "pallet_height_mm": st.get("outer_height_mm"),
                "bins_per_row": None,
                "bins_per_column": None,
                "layers_per_pallet": None,
                "bins_per_pallet": None,
                "stack_height_mm": st.get("outer_height_mm"),
                "pallet_load_weight_kg": None,
                "inventory": None,
                "created_at": st.get("created_at"),
            }
            items.append(item)

    return items


def get_packaging_item_by_identifier(identifier: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single packaging item by ID or name across cartons, pallets, and stillages."""
    clean_id = str(identifier).strip()
    all_items = get_unified_packaging(category="all", db_path=db_path)

    # Check by exact name match first
    for item in all_items:
        if item.get("package", "").lower() == clean_id.lower():
            return item

    # Check by numeric ID match (cartons default if ambiguous)
    if clean_id.isdigit():
        target_id = int(clean_id)
        for item in all_items:
            if item.get("id") == target_id and item.get("category") == "carton":
                return item
        for item in all_items:
            if item.get("id") == target_id:
                return item

    # Check if prefixed like 'carton-1' or 'Package 1'
    for item in all_items:
        if f"{item.get('category')}-{item.get('id')}" == clean_id.lower():
            return item

    return None


# ==========================================
# Cart Database Operations
# ==========================================

def get_cart_items(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query all items currently in the cart with calculated volume and line weights."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.id,
                c.product_id,
                c.part_name,
                c.part_type,
                c.part_length,
                c.part_breadth,
                c.part_height,
                c.part_weight,
                c.number_of_parts,
                p.model_file,
                p.standard_no_of_parts AS product_snp,
                c.created_at,
                c.updated_at
            FROM cart c
            LEFT JOIN products p ON c.product_id = p.id OR LOWER(c.part_name) = LOWER(p.part_name)
            ORDER BY c.id ASC
        """)
        rows = cursor.fetchall()
        items = []
        for r in rows:
            d = dict(r)
            qty = int(d.get("number_of_parts") or 1)
            wt = float(d.get("part_weight") or 0.0)
            l = float(d.get("part_length") or 0.0)
            w = float(d.get("part_breadth") or 0.0)
            h = float(d.get("part_height") or 0.0)
            item_vol_cm3 = (l * w * h) / 1000.0
            item_vol_l = (l * w * h) / 1000000.0

            d["line_weight_kg"] = round(wt * qty, 3)
            d["unit_volume_liters"] = round(item_vol_l, 4)
            d["total_volume_liters"] = round(item_vol_l * qty, 4)
            items.append(d)
        return items
    finally:
        conn.close()


def get_cart_item_by_id(item_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single cart item by ID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cart WHERE id = ? LIMIT 1", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_or_update_cart_item(item_data: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Add a product to cart or update its number_of_parts if it already exists."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        product_id = item_data.get("product_id")
        part_name = item_data.get("part_name")

        # Auto-fill missing specs from products table if product_id or part_name is known
        product_info = None
        if product_id is not None:
            cursor.execute("SELECT * FROM products WHERE id = ? LIMIT 1", (product_id,))
            row = cursor.fetchone()
            if row:
                product_info = dict(row)
        if not product_info and part_name:
            cursor.execute("SELECT * FROM products WHERE LOWER(part_name) = LOWER(?) LIMIT 1", (part_name.strip(),))
            row = cursor.fetchone()
            if row:
                product_info = dict(row)

        if product_info:
            product_id = product_info["id"]
            part_name = product_info["part_name"]
            part_type = item_data.get("part_type") or product_info.get("part_type", "Standard")
            part_length = float(item_data.get("part_length") if item_data.get("part_length") is not None else product_info.get("part_length", 100.0))
            part_breadth = float(item_data.get("part_breadth") if item_data.get("part_breadth") is not None else product_info.get("part_breadth", 80.0))
            part_height = float(item_data.get("part_height") if item_data.get("part_height") is not None else product_info.get("part_height", 50.0))
            part_weight = float(item_data.get("part_weight") if item_data.get("part_weight") is not None else product_info.get("part_weight", 0.0))
        else:
            if not part_name or not str(part_name).strip():
                raise ValueError("part_name is required when product is not found in database")
            part_name = str(part_name).strip()
            part_type = str(item_data.get("part_type") or "Standard")
            part_length = float(item_data.get("part_length") or 100.0)
            part_breadth = float(item_data.get("part_breadth") or 80.0)
            part_height = float(item_data.get("part_height") or 50.0)
            part_weight = float(item_data.get("part_weight") or 0.0)

        requested_qty = max(1, int(item_data.get("number_of_parts") or 1))
        mode = item_data.get("mode", "increment")  # "increment" or "set"

        # Check if item exists in cart
        cursor.execute("SELECT id, number_of_parts FROM cart WHERE LOWER(part_name) = LOWER(?) LIMIT 1", (part_name,))
        existing = cursor.fetchone()

        if existing:
            item_id = existing["id"]
            new_qty = (existing["number_of_parts"] + requested_qty) if mode == "increment" else requested_qty
            cursor.execute("""
                UPDATE cart
                SET number_of_parts = ?,
                    product_id = COALESCE(?, product_id),
                    part_length = ?,
                    part_breadth = ?,
                    part_height = ?,
                    part_weight = ?,
                    part_type = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_qty, product_id, part_length, part_breadth, part_height, part_weight, part_type, item_id))
        else:
            cursor.execute("""
                INSERT INTO cart (
                    product_id, part_name, part_type, part_length, part_breadth,
                    part_height, part_weight, number_of_parts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (product_id, part_name, part_type, part_length, part_breadth, part_height, part_weight, requested_qty))
            item_id = cursor.lastrowid

        conn.commit()

        cursor.execute("SELECT * FROM cart WHERE id = ?", (item_id,))
        saved_row = dict(cursor.fetchone())
        return saved_row
    finally:
        conn.close()


def update_cart_item_quantity(item_id: int, number_of_parts: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Update the number of parts for an existing cart item. If number_of_parts <= 0, deletes it."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if number_of_parts <= 0:
            cursor.execute("DELETE FROM cart WHERE id = ?", (item_id,))
            conn.commit()
            return None

        cursor.execute("""
            UPDATE cart
            SET number_of_parts = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (int(number_of_parts), item_id))
        conn.commit()

        cursor.execute("SELECT * FROM cart WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_cart_item(item_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a single cart item by ID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def clear_cart(db_path: Optional[str] = None) -> int:
    """Empty the entire cart table and reset the sequence."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='cart'")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_sample_products(limit: int = 5, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve a sample of catalog products for user guidance."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, part_name, part_type, standard_no_of_parts FROM products ORDER BY id ASC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def match_product_from_text(
    text: str,
    product_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Find a product in the SQLite database based on ID or text keywords.
    Returns (best_match, top_candidates). If no valid database product matches, returns (None, []).
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()

        # 1. Check direct product_id
        if product_id is not None:
            cursor.execute("SELECT * FROM products WHERE id = ? LIMIT 1", (int(product_id),))
            r = cursor.fetchone()
            if r:
                prod = dict(r)
                return prod, [prod]

        clean_text = str(text or "").strip()
        if not clean_text:
            return None, []

        # 2. Check if text mentions 'product <number>' or 'product id <number>' or '#<number>'
        match_id = re.search(r"\b(?:product\s*(?:id)?|#)\s*[:#]?\s*(\d+)\b", clean_text, re.IGNORECASE)
        if match_id:
            pid = int(match_id.group(1))
            cursor.execute("SELECT * FROM products WHERE id = ? LIMIT 1", (pid,))
            r = cursor.fetchone()
            if r:
                prod = dict(r)
                return prod, [prod]

        # 3. Check exact name match (case-insensitive)
        cursor.execute("SELECT * FROM products WHERE LOWER(part_name) = LOWER(?) LIMIT 1", (clean_text,))
        r = cursor.fetchone()
        if r:
            prod = dict(r)
            return prod, [prod]

        # 4. Search all products with scoring
        cursor.execute("SELECT * FROM products ORDER BY id ASC")
        all_prods = [dict(row) for row in cursor.fetchall()]

        text_lower = clean_text.lower()
        stopwords = {
            "pack", "packaging", "package", "units", "unit", "pieces", "piece",
            "parts", "part", "items", "item", "boxes", "box", "for", "the", "a",
            "an", "i", "need", "want", "please", "confirm", "confirmed", "looking",
            "lookup", "find", "and", "with", "of", "in", "to", "can", "you", "measuring",
            "weighing", "weight", "dimensions", "size", "made"
        }
        tokens = [t for t in re.findall(r"[a-z0-9]+", text_lower) if t not in stopwords and not t.isdigit() and len(t) >= 2]

        scored_candidates = []
        for p in all_prods:
            pname = p["part_name"].lower()
            p_tokens = set(re.findall(r"[a-z0-9]+", pname))
            score = 0

            # Exact or close substring
            if pname in text_lower:
                score += 100
            elif any(part_segment in text_lower for part_segment in pname.split(" ") if len(part_segment) >= 4):
                score += 30

            # Token overlap
            overlap = sum(1 for t in tokens if t in p_tokens or any(t in pt for pt in p_tokens))
            score += overlap * 25

            # Material match
            ptype = (p.get("part_type") or "").lower()
            if ptype and ptype in text_lower:
                score += 10

            if score >= 30:
                scored_candidates.append((score, p))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        if scored_candidates:
            top_prods = [p for _, p in scored_candidates[:5]]
            return top_prods[0], top_prods

        return None, []
    finally:
        conn.close()
