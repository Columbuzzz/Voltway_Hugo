import sqlite3
import pandas as pd
import os
import sys

# Import the new ingestion module
# Ensure python can find it
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ingest_specs import ingest_boms

# --- PATH CONFIGURATION ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(PROJECT_ROOT, "voltway.db")

def create_sql_db():
    print(f"⚙️ Building Database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Load CSVs (Standard Data)
    files = {
        "dispatch_parameters": "dispatch_parameters.csv",
        "material_master": "material_master.csv",
        "material_orders": "material_orders.csv",
        "sales_orders": "sales_orders.csv",
        "stock_levels": "stock_levels.csv",
        "stock_movements": "stock_movements.csv",
        "suppliers": "suppliers.csv"
    }

    for table_name, filename in files.items():
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                print(f"   ✅ Loaded {table_name}")
            except Exception as e:
                print(f"   ❌ Error loading {filename}: {e}")

    # 2. Fix Schema (Quality Columns)
    try:
        cursor.execute("ALTER TABLE stock_levels ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
        cursor.execute("ALTER TABLE stock_levels ADD COLUMN quality_hold_reason TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    # 3. CALL DYNAMIC BOM INGESTION (No more hardcoding)
    ingest_boms()

    print("\n🎉 Database generation complete.")

if __name__ == "__main__":
    create_sql_db()