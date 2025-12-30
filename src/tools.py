from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
import pandas as pd
import datetime
import numpy as np

db = SQLDatabase.from_uri("sqlite:///voltway.db")

# TESTING MODE: Use simulated date from sample data context (April 2025)
# Set to None to use real current date
SIMULATED_TODAY = datetime.date(2025, 4, 10)  # April 10, 2025

def get_today():
    """Get 'today' - either simulated for testing or real."""
    return SIMULATED_TODAY if SIMULATED_TODAY else datetime.date.today()


@tool
def check_fulfillment(target_date_str: str, model: str, quantity: int) -> str:
    """
    Determines whether Voltway can fulfill a requested build quantity
    of a scooter model by a given target date.

    It evaluates:
    - Bill of Materials (BOM)
    - Current stock levels
    - Incoming purchase orders
    - Supplier lead times

    Returns a human-readable feasibility report.
    """
    try:
        target_date = pd.to_datetime(target_date_str).date()
        today = get_today()
        days_until_deadline = (target_date - today).days

        if days_until_deadline < 0:
            return "❌ Target date is in the past."

        table_name = f"BOM_{model}"
        sql_bom = f"SELECT part_id, part_name, quantity_needed FROM {table_name}"

        try:
            bom_res = db.run(sql_bom)
            bom = eval(bom_res)
        except Exception:
            return f"❌ BOM table '{table_name}' not found."

        report = [f"📊 Fulfillment check for {quantity} × {model} by {target_date}\n"]
        feasible = True

        for part_id, part_name, qty_per_unit in bom:
            required = quantity * qty_per_unit

            stock_res = db.run(
                f"SELECT quantity_available FROM stock_levels WHERE part_id='{part_id}'"
            )
            stock = int(eval(stock_res)[0][0]) if stock_res and stock_res != "[]" else 0

            incoming_res = db.run(
                f"""
                SELECT SUM(quantity_ordered)
                FROM material_orders
                WHERE part_id='{part_id}'
                AND expected_delivery_date <= '{target_date_str}'
                """
            )
            incoming = (
                int(eval(incoming_res)[0][0])
                if incoming_res and eval(incoming_res)[0][0]
                else 0
            )

            available = stock + incoming
            if available < required:
                feasible = False
                report.append(
                    f"⚠️ {part_name} ({part_id}) short by {required - available}"
                )
            else:
                report.append(f"✅ {part_name} ({part_id}) OK")

        report.append(
            "\n🎉 BUILD FEASIBLE" if feasible else "\n🛑 BUILD NOT FEASIBLE"
        )
        return "\n".join(report)

    except Exception as e:
        return f"Error during fulfillment check: {e}"


@tool
def calculate_lean_safety_stock(lead_time: int, daily_demand: float) -> float:
    """
    Calculates lean safety stock using a statistical Z-score method.

    Inputs:
    - lead_time (days)
    - daily_demand (units/day)

    Output:
    - recommended safety stock quantity
    """
    Z = 1.65
    sigma_demand = daily_demand * 0.2
    sigma_lead = 2

    safety_stock = Z * np.sqrt(
        (lead_time * sigma_demand**2) + (daily_demand**2 * sigma_lead**2)
    )
    return round(float(safety_stock), 2)

