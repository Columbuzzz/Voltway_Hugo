# src/stock_tools.py
"""
Stock awareness tools for Hugo AI Agent.
Provides real-time visibility into inventory levels and alerts.
"""

from langchain_core.tools import tool
from src.tools import db


@tool
def get_stock_status(part_id: str = None) -> str:
    """
    Get current stock levels for a specific part or all parts.
    
    Args:
        part_id: Optional Part ID (e.g., 'P300'). If None, returns all stock levels.
    
    Returns:
        Detailed stock information including location and quantity.
    """
    try:
        if part_id:
            query = f"""
                SELECT part_id, part_name, location, quantity_available, status, quality_hold_reason
                FROM stock_levels
                WHERE part_id = '{part_id}'
            """
        else:
            query = """
                SELECT part_id, part_name, location, quantity_available, status
                FROM stock_levels
                ORDER BY quantity_available ASC
                LIMIT 20
            """
        
        result = db.run(query)
        data = eval(result) if result and result != "[]" else []
        
        if not data:
            return f"No stock data found{' for ' + part_id if part_id else ''}."
        
        if part_id:
            row = data[0]
            hold_reason = row[5] if len(row) > 5 and row[5] else "None"
            return f"""
📦 Stock Status for {row[0]}:
   Part Name: {row[1]}
   Location: {row[2]}
   Quantity Available: {row[3]}
   Status: {row[4]}
   Quality Hold Reason: {hold_reason}
"""
        else:
            report = ["📊 **Current Stock Levels** (sorted by quantity, lowest first):\n"]
            for row in data:
                report.append(f"  • {row[0]} | {row[1][:30]}... | Loc: {row[2]} | Qty: {row[3]} | {row[4]}")
            return "\n".join(report)
            
    except Exception as e:
        return f"Error fetching stock status: {e}"


@tool
def get_low_stock_alerts(threshold: int = 50) -> str:
    """
    Identify parts with stock below a specified threshold.
    Use this to proactively detect potential stockouts.
    
    Args:
        threshold: Minimum acceptable stock level (default: 50)
    
    Returns:
        List of parts that are below the threshold with recommendations.
    """
    try:
        query = f"""
            SELECT sl.part_id, sl.part_name, sl.quantity_available, sl.location, 
                   s.supplier_name, s.lead_time_days
            FROM stock_levels sl
            LEFT JOIN material_master mm ON sl.part_id = mm.part_id
            LEFT JOIN suppliers s ON mm.supplier_id = s.supplier_id
            WHERE sl.quantity_available < {threshold}
            ORDER BY sl.quantity_available ASC
        """
        
        result = db.run(query)
        data = eval(result) if result and result != "[]" else []
        
        if not data:
            return f"✅ All parts are above the threshold of {threshold} units. No alerts."
        
        report = [f"⚠️ **LOW STOCK ALERTS** (Below {threshold} units):\n"]
        for row in data:
            supplier = row[4] or "Unknown"
            lead_time = row[5] or "N/A"
            urgency = "🔴 CRITICAL" if row[2] < 25 else "🟡 WARNING"
            
            report.append(f"""
{urgency} {row[0]} - {row[1]}
   Current Stock: {row[2]} | Location: {row[3]}
   Supplier: {supplier} | Lead Time: {lead_time} days
""")
        
        report.append(f"\n📌 Total Parts at Risk: {len(data)}")
        return "\n".join(report)
        
    except Exception as e:
        return f"Error checking low stock: {e}"


@tool
def get_stock_summary() -> str:
    """
    Get an executive overview of stock levels by location and category.
    Useful for quick situational awareness.
    
    Returns:
        Summary statistics including totals by location and low stock counts.
    """
    try:
        # Stock by location
        loc_query = """
            SELECT location, COUNT(*) as part_count, SUM(quantity_available) as total_qty
            FROM stock_levels
            GROUP BY location
        """
        loc_result = db.run(loc_query)
        loc_data = eval(loc_result) if loc_result and loc_result != "[]" else []
        
        # Low stock count
        low_query = "SELECT COUNT(*) FROM stock_levels WHERE quantity_available < 50"
        low_result = db.run(low_query)
        low_count = eval(low_result)[0][0] if low_result else 0
        
        # Critical stock count
        critical_query = "SELECT COUNT(*) FROM stock_levels WHERE quantity_available < 25"
        critical_result = db.run(critical_query)
        critical_count = eval(critical_result)[0][0] if critical_result else 0
        
        # Quality holds
        hold_query = "SELECT COUNT(*) FROM stock_levels WHERE quality_hold_reason IS NOT NULL AND quality_hold_reason != ''"
        hold_result = db.run(hold_query)
        hold_count = eval(hold_result)[0][0] if hold_result else 0
        
        # Total parts
        total_query = "SELECT COUNT(*), SUM(quantity_available) FROM stock_levels"
        total_result = db.run(total_query)
        total_data = eval(total_result)[0] if total_result else (0, 0)
        
        report = ["""
📊 **STOCK SUMMARY DASHBOARD**
═══════════════════════════════════
"""]
        
        report.append(f"📦 Total SKUs: {total_data[0]}")
        report.append(f"📦 Total Units: {total_data[1]:,}")
        report.append(f"⚠️  Low Stock (<50): {low_count}")
        report.append(f"🔴 Critical (<25): {critical_count}")
        report.append(f"🚫 Quality Holds: {hold_count}")
        
        report.append("\n**Stock by Warehouse:**")
        for loc in loc_data:
            report.append(f"   {loc[0]}: {loc[1]} parts | {loc[2]:,} units")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"Error generating stock summary: {e}"


@tool
def get_stock_by_model(model: str) -> str:
    """
    Get stock levels for all parts related to a specific scooter model.
    
    Args:
        model: The scooter model (e.g., 'S1_V1', 'S2_V2', 'S3_V1')
    
    Returns:
        Stock levels for all BOM components of the specified model.
    """
    try:
        # Get BOM for the model
        bom_table = f"BOM_{model}"
        bom_query = f"SELECT part_id, part_name, quantity_needed FROM {bom_table}"
        
        try:
            bom_result = db.run(bom_query)
            bom_data = eval(bom_result) if bom_result and bom_result != "[]" else []
        except:
            return f"❌ BOM table '{bom_table}' not found. Check model name."
        
        if not bom_data:
            return f"No BOM data found for model {model}."
        
        report = [f"📋 **Stock Status for {model} Components:**\n"]
        total_issues = 0
        
        for part_id, part_name, qty_needed in bom_data:
            stock_query = f"SELECT quantity_available FROM stock_levels WHERE part_id = '{part_id}'"
            stock_result = db.run(stock_query)
            stock = int(eval(stock_result)[0][0]) if stock_result and stock_result != "[]" else 0
            
            # Calculate how many units we can build
            buildable = stock // qty_needed if qty_needed > 0 else 0
            status = "✅" if stock >= 50 else ("🟡" if stock >= 25 else "🔴")
            
            if stock < 50:
                total_issues += 1
            
            report.append(f"  {status} {part_id} - {part_name[:35]}")
            report.append(f"     Stock: {stock} | Per Unit: {qty_needed} | Can Build: {buildable}")
        
        report.append(f"\n📌 Components with Issues: {total_issues}/{len(bom_data)}")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"Error fetching model stock: {e}"


@tool
def check_part_usage(part_id: str) -> str:
    """
    Check which scooter models use a specific part and calculate demand.
    USE THIS TOOL BEFORE making claims about part demand or outbound requirements.
    
    Args:
        part_id: The part ID to check (e.g., 'P302')
    
    Returns:
        - Which BOMs contain this part
        - Quantity needed per unit
        - Estimated demand from open sales orders
        - Current stock vs demand comparison
    """
    try:
        # Check all BOM tables
        bom_models = ['S1_V1', 'S1_V2', 'S2_V1', 'S2_V2', 'S3_V1', 'S3_V2']
        found_in = []
        
        for model in bom_models:
            try:
                query = f"SELECT part_id, part_name, quantity_needed FROM BOM_{model} WHERE part_id = '{part_id}'"
                result = db.run(query)
                data = eval(result) if result and result != "[]" else []
                if data:
                    found_in.append({
                        'model': model,
                        'part_name': data[0][1],
                        'qty_per_unit': data[0][2]
                    })
            except:
                continue
        
        # Get current stock
        stock_query = f"SELECT quantity_available FROM stock_levels WHERE part_id = '{part_id}'"
        stock_result = db.run(stock_query)
        current_stock = int(eval(stock_result)[0][0]) if stock_result and stock_result != "[]" else 0
        
        # Get pending inbound orders
        inbound_query = f"""
            SELECT SUM(quantity_ordered) FROM material_orders 
            WHERE part_id = '{part_id}' AND status != 'delivered'
        """
        inbound_result = db.run(inbound_query)
        inbound = int(eval(inbound_result)[0][0] or 0) if inbound_result else 0
        
        # Build report
        report = [f"📋 **Part Usage Analysis for {part_id}**\n"]
        
        if not found_in:
            report.append(f"⚠️ Part {part_id} is NOT used in any current BOM.")
            report.append("   This may be a legacy part, spare part, or miscategorized item.")
            report.append(f"\n📦 Current Stock: {current_stock}")
            report.append(f"📥 Pending Inbound: {inbound}")
            report.append("\n💡 Recommendation: Verify if this part is still needed or should be phased out.")
            return "\n".join(report)
        
        report.append("**Used in BOM:**")
        total_demand = 0
        
        for item in found_in:
            # Calculate demand from sales orders for this model
            model_parts = item['model'].replace('_', "', '")  # S1_V1 -> S1', 'V1
            series, version = item['model'].split('_')
            
            demand_query = f"""
                SELECT SUM(quantity) FROM sales_orders 
                WHERE series = '{series}' AND variant = '{version}'
                AND status NOT IN ('delivered', 'cancelled')
            """
            try:
                demand_result = db.run(demand_query)
                model_demand = int(eval(demand_result)[0][0] or 0) if demand_result else 0
            except:
                model_demand = 0
            
            part_demand = model_demand * item['qty_per_unit']
            total_demand += part_demand
            
            report.append(f"   • {item['model']}: {item['qty_per_unit']} per unit")
            report.append(f"     Open orders: {model_demand} units → {part_demand} parts needed")
        
        report.append(f"\n📦 Current Stock: {current_stock}")
        report.append(f"📥 Pending Inbound: {inbound}")
        report.append(f"📤 Total Demand: {total_demand}")
        
        available = current_stock + inbound
        balance = available - total_demand
        
        if balance >= 0:
            report.append(f"\n✅ Status: SUFFICIENT (+{balance} units surplus)")
        else:
            report.append(f"\n🔴 Status: SHORTAGE ({abs(balance)} units deficit)")
            report.append("   ⚡ Recommend placing urgent order!")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"Error checking part usage: {e}"
