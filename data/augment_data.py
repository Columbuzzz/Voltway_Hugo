import pandas as pd
import os

# Define file paths (assuming current directory)
files = [
    "material_master.csv", "material_orders.csv", "sales_orders.csv", 
    "stock_levels.csv", "suppliers.csv"
]

# Load DataFrames
dfs = {f: pd.read_csv(f) for f in files if os.path.exists(f)}

print("🔧 Augmenting Data to match Email Test Cases...")

# --- 1. UPDATE MATERIAL MASTER (Fix Part Names & Add Missing Parts) ---
# Emails reference specific parts (P302 as Battery, P301 as Controller) which might differ from original data.
mm = dfs["material_master.csv"]
parts_to_update = [
    {"part_id": "P300", "part_name": "S1 V1 500W Brushless Motor", "used_in_models": "S1_V1"},
    {"part_id": "P301", "part_name": "Analog Controller ZX", "used_in_models": "S1_V1"}, # Aligns with Email 006
    {"part_id": "P302", "part_name": "Li-Po 48V 12Ah Battery Pack", "used_in_models": "S1_V2"}, # Aligns with Email 002
    {"part_id": "P303", "part_name": "Carbon Fiber Frame", "used_in_models": "S1_V2"}, # Aligns with Email 004
    {"part_id": "P309", "part_name": "S2 V1 Li-Ion 36V 10Ah Battery Pack", "used_in_models": "S2_V1"}, # Aligns with Email 010
    {"part_id": "P312", "part_name": "LCD Dashboard Display", "used_in_models": "S1_V1"},
    {"part_id": "P313", "part_name": "Mechanical Disc Brake", "used_in_models": "S1_V1"},
    {"part_id": "P323", "part_name": "S3 V2 Carbon Fiber Frame", "used_in_models": "S3_V2"},
    {"part_id": "P330", "part_name": "12-inch Alloy Wheel", "used_in_models": "S1_V2"},
]

for p in parts_to_update:
    # Update existing or append new
    mask = mm['part_id'] == p['part_id']
    if mask.any():
        for k, v in p.items():
            mm.loc[mask, k] = v
    else:
        new_row = {col: None for col in mm.columns}
        new_row.update(p)
        new_row['part_type'] = 'assembly' # Default
        mm = pd.concat([mm, pd.DataFrame([new_row])], ignore_index=True)

dfs["material_master.csv"] = mm

# --- 2. ADD MISSING ORDERS (For Delays, Cancels, Partials) ---
mo = dfs["material_orders.csv"]
new_orders = [
    # Email 001: Delay (O5007)
    {"order_id": "O5007", "part_id": "P300", "quantity_ordered": 50, "order_date": "2025-01-15", "expected_delivery_date": "2025-03-20", "supplier_id": "SupA", "status": "ordered"},
    # Email 004: Cancellation (O5021)
    {"order_id": "O5021", "part_id": "P303", "quantity_ordered": 100, "order_date": "2025-02-01", "expected_delivery_date": "2025-04-20", "supplier_id": "SupC", "status": "ordered"},
    # Email 007: Partial Shipment (O5045)
    {"order_id": "O5045", "part_id": "P313", "quantity_ordered": 100, "order_date": "2025-02-15", "expected_delivery_date": "2025-04-15", "supplier_id": "SupB", "status": "ordered"},
    # Email 008: Early Partial (O5075)
    {"order_id": "O5075", "part_id": "P330", "quantity_ordered": 60, "order_date": "2025-02-20", "expected_delivery_date": "2025-04-22", "supplier_id": "SupC", "status": "ordered"},
    # Email 009: Quality Alert Batch (O5023)
    {"order_id": "O5023", "part_id": "P323", "quantity_ordered": 200, "order_date": "2025-01-10", "expected_delivery_date": "2025-04-10", "supplier_id": "SupA", "status": "delivered", "actual_delivered_at": "2025-04-10"},
]

# Append new orders (avoiding duplicates)
existing_ids = set(mo['order_id'])
orders_to_add = [o for o in new_orders if o['order_id'] not in existing_ids]
if orders_to_add:
    mo = pd.concat([mo, pd.DataFrame(orders_to_add)], ignore_index=True)
dfs["material_orders.csv"] = mo

# --- 3. ADD FRAMEWORK CONTRACT (For Email 003) ---
so = dfs["sales_orders.csv"]
if "FC-S60034" not in so['sales_order_id'].values:
    new_sale = {
        "sales_order_id": "FC-S60034", "model": "S2", "version": "V2", "quantity": 200, 
        "order_type": "fleet_framework", "requested_date": "2025-05-01", 
        "created_at": "2025-01-01", "accepted_request_date": "2025-01-02"
    }
    so = pd.concat([so, pd.DataFrame([new_sale])], ignore_index=True)
dfs["sales_orders.csv"] = so

# --- 4. FIX STOCK LEVELS (Add Missing Columns for Quality Alerts) ---
sl = dfs["stock_levels.csv"]
if "status" not in sl.columns:
    sl["status"] = "Active" # Default status
if "quality_hold_reason" not in sl.columns:
    sl["quality_hold_reason"] = None

# Ensure we have stock entries for new parts
parts_in_stock = sl['part_id'].unique()
for p in parts_to_update:
    if p['part_id'] not in parts_in_stock:
        new_stock = {
            "part_id": p['part_id'], "part_name": p['part_name'], "location": "WH1", 
            "quantity_available": 50, "status": "Active", "quality_hold_reason": None
        }
        sl = pd.concat([sl, pd.DataFrame([new_stock])], ignore_index=True)
dfs["stock_levels.csv"] = sl

# --- 5. UPDATE SUPPLIERS (For Price Checks) ---
su = dfs["suppliers.csv"]
price_updates = [
    # Email 002: SupB, P302, old price $78.50
    {"supplier_id": "SupB", "part_id": "P302", "price_per_unit": 78.50, "lead_time_days": 15, "min_order_qty": 50, "reliability_rating": 0.95},
    # Email 010: SupA, P309, price $65.00
    {"supplier_id": "SupA", "part_id": "P309", "price_per_unit": 65.00, "lead_time_days": 10, "min_order_qty": 50, "reliability_rating": 0.92},
]
for pu in price_updates:
    mask = (su['supplier_id'] == pu['supplier_id']) & (su['part_id'] == pu['part_id'])
    if mask.any():
        for k, v in pu.items():
            su.loc[mask, k] = v
    else:
        su = pd.concat([su, pd.DataFrame([pu])], ignore_index=True)
dfs["suppliers.csv"] = su

# --- SAVE ALL FILES ---
for name, df in dfs.items():
    df.to_csv(name, index=False)
    print(f"✅ Updated {name}")

print("\n🚀 Data Augmentation Complete! Please Re-run 'create_sql_db()' or 'main.py'.")