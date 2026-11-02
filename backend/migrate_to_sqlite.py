"""Migration Script: Migrate products, packages, pallets, stillages, and trucks CSV datasets into SQLite.

Usage:
    cd backend
    python migrate_to_sqlite.py              # Migrates all datasets
    python migrate_to_sqlite.py --clean      # Drops/clears and recreates all tables

Optional arguments:
    --table <name>            Migrate a specific table (e.g. packages, products, base_pallets, metal_pallets, metal_stillages, trucks)
    --csv   <path_to_csv>     Override path to a specific input CSV
    --db    <path_to_db>      Path to SQLite DB (default: data/products.db)
    --clean                   Truncate and re-import records
"""

import argparse
import csv
import os
import sqlite3
import sys
from typing import Dict, Any, List, Optional

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from app.db import DEFAULT_DB_PATH, init_db, get_db_connection

DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# Mapping of table names to default CSV filenames
DATASET_MAP = {
    "products": os.path.join(DATA_DIR, "products_dataset.csv"),
    "packages": os.path.join(DATA_DIR, "packages.csv"),
    "base_pallets": os.path.join(DATA_DIR, "base_pallets.csv"),
    "metal_pallets": os.path.join(DATA_DIR, "metal_pallets.csv"),
    "metal_stillages": os.path.join(DATA_DIR, "metal_stillages.csv"),
    "trucks": os.path.join(DATA_DIR, "trucks.csv"),
}


def migrate_products(conn: sqlite3.Connection, csv_path: str, clean: bool = False) -> int:
    """Migrate products_dataset.csv into 'products' table."""
    if not os.path.exists(csv_path):
        print(f"[SKIP] Products CSV not found: {csv_path}")
        return 0

    if clean:
        conn.execute("DELETE FROM products")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='products'")

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sql = """
            INSERT INTO products (
                part_name, part_length, part_breadth, part_height, part_weight,
                part_type, standard_no_of_parts, domestic_or_international,
                per_day_requirement, minimum_order_quantity, line_feeding_method,
                model_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(part_name) DO UPDATE SET
                part_length = excluded.part_length,
                part_breadth = excluded.part_breadth,
                part_height = excluded.part_height,
                part_weight = excluded.part_weight,
                part_type = excluded.part_type,
                standard_no_of_parts = excluded.standard_no_of_parts,
                domestic_or_international = excluded.domestic_or_international,
                per_day_requirement = excluded.per_day_requirement,
                minimum_order_quantity = excluded.minimum_order_quantity,
                line_feeding_method = excluded.line_feeding_method,
                model_file = excluded.model_file
        """
        for row in reader:
            model_file = row.get("model_file", "").strip() or None
            conn.execute(sql, (
                row["part_name"].strip(),
                float(row["part_length"]),
                float(row["part_breadth"]),
                float(row["part_height"]),
                float(row.get("part_weight", 1.0)),
                row["part_type"].strip(),
                int(row["standard_no_of_parts"]),
                row["domestic_or_international"].strip(),
                int(row["per_day_requirement"]),
                int(row["minimum_order_quantity"]),
                row["line_feeding_method"].strip(),
                model_file,
            ))
            count += 1
    return count


def migrate_packages(conn: sqlite3.Connection, csv_path: str, clean: bool = False) -> int:
    """Migrate packages.csv into 'packages' table."""
    if not os.path.exists(csv_path):
        print(f"[SKIP] Packages CSV not found: {csv_path}")
        return 0

    if clean:
        conn.execute("DELETE FROM packages")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='packages'")

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sql = """
            INSERT INTO packages (
                package, outer_length_mm, outer_width_mm, outer_height_mm,
                inner_length_mm, inner_width_mm, inner_height_mm,
                empty_weight_kg, part_weight_kg, total_weight_kg,
                pallet_length_mm, pallet_width_mm, pallet_height_mm,
                bins_per_row, bins_per_column, layers_per_pallet,
                bins_per_pallet, stack_height_mm, pallet_load_weight_kg,
                inventory
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(package) DO UPDATE SET
                outer_length_mm = excluded.outer_length_mm,
                outer_width_mm = excluded.outer_width_mm,
                outer_height_mm = excluded.outer_height_mm,
                inner_length_mm = excluded.inner_length_mm,
                inner_width_mm = excluded.inner_width_mm,
                inner_height_mm = excluded.inner_height_mm,
                empty_weight_kg = excluded.empty_weight_kg,
                part_weight_kg = excluded.part_weight_kg,
                total_weight_kg = excluded.total_weight_kg,
                pallet_length_mm = excluded.pallet_length_mm,
                pallet_width_mm = excluded.pallet_width_mm,
                pallet_height_mm = excluded.pallet_height_mm,
                bins_per_row = excluded.bins_per_row,
                bins_per_column = excluded.bins_per_column,
                layers_per_pallet = excluded.layers_per_pallet,
                bins_per_pallet = excluded.bins_per_pallet,
                stack_height_mm = excluded.stack_height_mm,
                pallet_load_weight_kg = excluded.pallet_load_weight_kg,
                inventory = excluded.inventory
        """
        for row in reader:
            inner_l = float(row["inner_length_mm"])
            inner_w = float(row["inner_width_mm"])
            inner_h = float(row["inner_height_mm"])
            part_wt = float(row["part_weight_kg"])
            inventory = int(row["inventory"]) if row.get("inventory") else None

            conn.execute(sql, (
                row["package"].strip(),
                float(row["outer_length_mm"]),
                float(row["outer_width_mm"]),
                float(row["outer_height_mm"]),
                inner_l,
                inner_w,
                inner_h,
                float(row["empty_weight_kg"]),
                part_wt,
                float(row["total_weight_kg"]),
                float(row.get("pallet_length_mm", 1200.0)),
                float(row.get("pallet_width_mm", 1000.0)),
                float(row.get("pallet_height_mm", 150.0)),
                int(row.get("bins_per_row", 1)),
                int(row.get("bins_per_column", 1)),
                int(row.get("layers_per_pallet", 1)),
                int(row.get("bins_per_pallet", 1)),
                float(row.get("stack_height_mm", 1000.0)),
                float(row.get("pallet_load_weight_kg", 500.0)),
                inventory,
            ))
            count += 1
    return count


def migrate_base_pallets(conn: sqlite3.Connection, csv_path: str, clean: bool = False) -> int:
    """Migrate base_pallets.csv into 'base_pallets' table."""
    if not os.path.exists(csv_path):
        print(f"[SKIP] Base Pallets CSV not found: {csv_path}")
        return 0

    if clean:
        conn.execute("DELETE FROM base_pallets")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='base_pallets'")

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sql = """
            INSERT INTO base_pallets (
                base_pallet, outer_length_mm, outer_width_mm, outer_height_mm, empty_weight_kg
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(base_pallet) DO UPDATE SET
                outer_length_mm = excluded.outer_length_mm,
                outer_width_mm = excluded.outer_width_mm,
                outer_height_mm = excluded.outer_height_mm,
                empty_weight_kg = excluded.empty_weight_kg
        """
        for row in reader:
            conn.execute(sql, (
                row["base_pallet"].strip(),
                float(row["outer_length_mm"]),
                float(row["outer_width_mm"]),
                float(row["outer_height_mm"]),
                float(row["empty_weight_kg"]),
            ))
            count += 1
    return count


def migrate_metal_pallets(conn: sqlite3.Connection, csv_path: str, clean: bool = False) -> int:
    """Migrate metal_pallets.csv into 'metal_pallets' table."""
    if not os.path.exists(csv_path):
        print(f"[SKIP] Metal Pallets CSV not found: {csv_path}")
        return 0

    if clean:
        conn.execute("DELETE FROM metal_pallets")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='metal_pallets'")

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sql = """
            INSERT INTO metal_pallets (
                metal_pallet, outer_length_mm, outer_width_mm, outer_height_mm,
                inner_length_mm, inner_width_mm, inner_height_mm, empty_weight_kg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(metal_pallet) DO UPDATE SET
                outer_length_mm = excluded.outer_length_mm,
                outer_width_mm = excluded.outer_width_mm,
                outer_height_mm = excluded.outer_height_mm,
                inner_length_mm = excluded.inner_length_mm,
                inner_width_mm = excluded.inner_width_mm,
                inner_height_mm = excluded.inner_height_mm,
                empty_weight_kg = excluded.empty_weight_kg
        """
        for row in reader:
            conn.execute(sql, (
                row["metal_pallet"].strip(),
                float(row["outer_length_mm"]),
                float(row["outer_width_mm"]),
                float(row["outer_height_mm"]),
                float(row["inner_length_mm"]),
                float(row["inner_width_mm"]),
                float(row["inner_height_mm"]),
                float(row["empty_weight_kg"]),
            ))
            count += 1
    return count


def migrate_metal_stillages(conn: sqlite3.Connection, csv_path: str, clean: bool = False) -> int:
    """Migrate metal_stillages.csv into 'metal_stillages' table."""
    if not os.path.exists(csv_path):
        print(f"[SKIP] Metal Stillages CSV not found: {csv_path}")
        return 0

    if clean:
        conn.execute("DELETE FROM metal_stillages")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='metal_stillages'")

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sql = """
            INSERT INTO metal_stillages (
                metal_stillage, outer_length_mm, outer_width_mm, outer_height_mm,
                inner_length_mm, inner_width_mm, inner_height_mm, empty_weight_kg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(metal_stillage) DO UPDATE SET
                outer_length_mm = excluded.outer_length_mm,
                outer_width_mm = excluded.outer_width_mm,
                outer_height_mm = excluded.outer_height_mm,
                inner_length_mm = excluded.inner_length_mm,
                inner_width_mm = excluded.inner_width_mm,
                inner_height_mm = excluded.inner_height_mm,
                empty_weight_kg = excluded.empty_weight_kg
        """
        for row in reader:
            conn.execute(sql, (
                row["metal_stillage"].strip(),
                float(row["outer_length_mm"]),
                float(row["outer_width_mm"]),
                float(row["outer_height_mm"]),
                float(row["inner_length_mm"]),
                float(row["inner_width_mm"]),
                float(row["inner_height_mm"]),
                float(row["empty_weight_kg"]),
            ))
            count += 1
    return count


def migrate_trucks(conn: sqlite3.Connection, csv_path: str, clean: bool = False) -> int:
    """Migrate trucks.csv into 'trucks' table."""
    if not os.path.exists(csv_path):
        print(f"[SKIP] Trucks CSV not found: {csv_path}")
        return 0

    if clean:
        conn.execute("DELETE FROM trucks")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='trucks'")

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sql = """
            INSERT INTO trucks (
                truck, inner_length_mm, inner_width_mm, inner_height_mm, capacity_kg
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(truck) DO UPDATE SET
                inner_length_mm = excluded.inner_length_mm,
                inner_width_mm = excluded.inner_width_mm,
                inner_height_mm = excluded.inner_height_mm,
                capacity_kg = excluded.capacity_kg
        """
        for row in reader:
            conn.execute(sql, (
                row["truck"].strip(),
                float(row["inner_length_mm"]),
                float(row["inner_width_mm"]),
                float(row["inner_height_mm"]),
                float(row["capacity_kg"]),
            ))
            count += 1
    return count


MIGRATION_DISPATCH = {
    "products": migrate_products,
    "packages": migrate_packages,
    "base_pallets": migrate_base_pallets,
    "metal_pallets": migrate_metal_pallets,
    "metal_stillages": migrate_metal_stillages,
    "trucks": migrate_trucks,
}


def migrate_all_datasets(db_path: str, clean: bool = False, specific_table: Optional[str] = None, csv_override: Optional[str] = None):
    """Migrate all datasets into SQLite database."""
    print(f"--> Target SQLite DB: {os.path.abspath(db_path)}")
    init_db(db_path)

    conn = get_db_connection(db_path)
    results = {}

    try:
        with conn:
            tables_to_migrate = [specific_table] if specific_table else list(DATASET_MAP.keys())

            for table_name in tables_to_migrate:
                if table_name not in MIGRATION_DISPATCH:
                    print(f"[WARN] Unknown table '{table_name}'. Skipping.")
                    continue

                csv_file = csv_override if (specific_table and csv_override) else DATASET_MAP.get(table_name)
                print(f"--> Migrating table '{table_name}' from: {csv_file}")
                handler = MIGRATION_DISPATCH[table_name]
                count = handler(conn, csv_file, clean=clean)
                results[table_name] = count
                print(f"    [OK] Table '{table_name}': {count} rows imported.")

        # Verification summaries
        print("\n================ DATABASE VERIFICATION ================")
        with conn:
            cursor = conn.cursor()
            for table_name in results.keys():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                total = cursor.fetchone()[0]
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                first_row = cursor.fetchone()
                sample_desc = ""
                if first_row:
                    row_d = dict(first_row)
                    key_col = next((k for k in ["package", "part_name", "base_pallet", "metal_pallet", "metal_stillage", "truck"] if k in row_d), "id")
                    sample_desc = f" (Sample: {row_d.get(key_col)})"
                print(f"  * Table '{table_name}': {total} rows verified{sample_desc}")

            # Check view
            cursor.execute("SELECT COUNT(*) FROM prodcuts")
            alias_count = cursor.fetchone()[0]
            print(f"  * View 'prodcuts': {alias_count} rows verified")

        print(f"--> Database ready at: {os.path.abspath(db_path)} ({os.path.getsize(db_path)} bytes)")
        return results

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate products and packages datasets into SQLite database.")
    parser.add_argument("--table", default=None, help="Migrate a specific table (products, packages, base_pallets, metal_pallets, metal_stillages, trucks)")
    parser.add_argument("--csv", default=None, help="Override path to a specific input CSV")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to output SQLite database")
    parser.add_argument("--clean", action="store_true", help="Drop and recreate records before migration")
    args = parser.parse_args()

    try:
        migrate_all_datasets(db_path=args.db, clean=args.clean, specific_table=args.table, csv_override=args.csv)
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
