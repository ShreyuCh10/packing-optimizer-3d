"""Migration Script: Migrate products_dataset.csv into SQLite database.

Usage:
    cd backend
    python migrate_to_sqlite.py

Optional arguments:
    --csv <path_to_csv>       Path to products CSV (default: data/products_dataset.csv)
    --db  <path_to_db>        Path to SQLite DB (default: data/products.db)
    --clean                   Drop and recreate table before migration
"""

import argparse
import csv
import os
import sqlite3
import sys

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from app.db import DEFAULT_DB_PATH, init_db, get_db_connection

DEFAULT_CSV_PATH = os.path.join(SCRIPT_DIR, "data", "products_dataset.csv")


def migrate_csv_to_sqlite(csv_path: str, db_path: str, clean: bool = False) -> int:
    """Migrate rows from CSV file into SQLite database table 'products'."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source CSV file not found at: {csv_path}")

    print(f"--> Source CSV: {os.path.abspath(csv_path)}")
    print(f"--> Target SQLite DB: {os.path.abspath(db_path)}")

    # Ensure database and table exist
    init_db(db_path)

    conn = get_db_connection(db_path)
    count = 0

    try:
        with conn:
            if clean:
                print("--> Clean flag enabled: Clearing existing 'products' records...")
                conn.execute("DELETE FROM products")
                conn.execute("DELETE FROM sqlite_sequence WHERE name='products'")

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                sql = """
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
                        line_feeding_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        line_feeding_method = excluded.line_feeding_method
                """

                for row in reader:
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
                    ))
                    count += 1

        print(f"[OK] Successfully migrated {count} products into table 'products'.")

        # Verification query on both 'products' and alias view 'prodcuts'
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            total_products = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM prodcuts")
            total_alias = cursor.fetchone()[0]

            cursor.execute("SELECT * FROM prodcuts LIMIT 1")
            sample = dict(cursor.fetchone())

        print(f"[OK] Verification Check: Table 'products' has {total_products} records.")
        print(f"[OK] Alias Check: View 'prodcuts' has {total_alias} records.")
        print(f"[OK] Sample Record: {sample['part_name']} ({sample['part_length']}x{sample['part_breadth']}x{sample['part_height']} mm, {sample['part_weight']} kg, {sample['part_type']})")
        print(f"[OK] Database ready at: {os.path.abspath(db_path)} ({os.path.getsize(db_path)} bytes)")

        return count
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate products CSV into SQLite database.")
    parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help="Path to input CSV file")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to output SQLite database")
    parser.add_argument("--clean", action="store_true", help="Truncate table before migrating")
    args = parser.parse_args()

    try:
        migrate_csv_to_sqlite(args.csv, args.db, clean=args.clean)
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

