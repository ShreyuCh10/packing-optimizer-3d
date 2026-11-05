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
    """Initialize database tables and views for products, packages, pallets, stillages, and trucks."""
    conn = get_db_connection(db_path)
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
