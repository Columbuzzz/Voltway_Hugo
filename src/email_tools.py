# src/email_tools.py
"""
Email awareness tools for Hugo AI Agent.
Provides visibility into processed emails and email history.
"""

import sqlite3
import datetime
from langchain_core.tools import tool

DB_PATH = "voltway.db"


def get_db_connection():
    """Get a connection to the database."""
    return sqlite3.connect(DB_PATH)


def store_email_metadata(filename: str, sender: str, subject: str, 
                         extraction: dict, summary = None):
    """
    Store processed email metadata in the database.
    Called after each email is processed by the workflow.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            sender TEXT,
            subject TEXT,
            intent TEXT,
            risk_score INTEGER,
            part_id TEXT,
            order_id TEXT,
            old_value TEXT,
            new_value TEXT,
            reasoning TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary TEXT
        )
    """)
    
    # Convert summary to string if it's a list or other type
    summary_str = None
    if summary is not None:
        if isinstance(summary, list):
            summary_str = "\n".join(str(item) for item in summary)
        elif isinstance(summary, dict):
            summary_str = str(summary)
        else:
            summary_str = str(summary)
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO processed_emails 
            (filename, sender, subject, intent, risk_score, part_id, order_id, 
             old_value, new_value, reasoning, processed_at, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            sender,
            subject,
            extraction.get("intent", "OTHER"),
            extraction.get("risk_score", 1),
            extraction.get("part_id"),
            extraction.get("order_id"),
            extraction.get("old_value"),
            extraction.get("new_value"),
            extraction.get("reasoning"),
            datetime.datetime.now().isoformat(),
            summary_str
        ))
        conn.commit()
    except Exception as e:
        print(f"Error storing email metadata: {e}")
    finally:
        conn.close()


@tool
def get_email_history(limit: int = 10) -> str:
    """
    Get recent processed emails with their intent, risk scores, and status.
    Use this to understand what supplier communications have been received.
    
    Args:
        limit: Maximum number of emails to return (default: 10)
    
    Returns:
        List of recent emails with key details.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filename, sender, subject, intent, risk_score, 
                   part_id, order_id, processed_at
            FROM processed_emails
            ORDER BY processed_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "📭 No processed emails found in the system."
        
        report = [f"📧 **Recent Processed Emails** (Last {len(rows)}):\n"]
        
        for row in rows:
            risk_icon = "🔴" if row[4] >= 4 else ("🟡" if row[4] >= 2 else "🟢")
            timestamp = row[7][:16] if row[7] else "Unknown"
            
            report.append(f"""
{risk_icon} **{row[3]}** (Risk: {row[4]}/5)
   File: {row[0]}
   From: {row[1] or 'Unknown'}
   Subject: {row[2] or 'N/A'}
   Part: {row[5] or 'N/A'} | Order: {row[6] or 'N/A'}
   Processed: {timestamp}
""")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"Error fetching email history: {e}"


@tool
def search_emails(keyword: str = None, intent: str = None, part_id: str = None) -> str:
    """
    Search processed emails by keyword, intent type, or part ID.
    
    Args:
        keyword: Optional keyword to search in subject and filename
        intent: Optional intent filter (DELAY, PRICE_CHANGE, QUALITY_ALERT, etc.)
        part_id: Optional part ID to filter by
    
    Returns:
        Matching emails with details.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT filename, sender, subject, intent, risk_score, 
                   part_id, order_id, reasoning, processed_at
            FROM processed_emails
            WHERE 1=1
        """
        params = []
        
        if keyword:
            query += " AND (subject LIKE ? OR filename LIKE ? OR reasoning LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        
        if intent:
            query += " AND intent = ?"
            params.append(intent.upper())
        
        if part_id:
            query += " AND part_id = ?"
            params.append(part_id.upper())
        
        query += " ORDER BY processed_at DESC LIMIT 20"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            filters = []
            if keyword: filters.append(f"keyword='{keyword}'")
            if intent: filters.append(f"intent='{intent}'")
            if part_id: filters.append(f"part='{part_id}'")
            return f"📭 No emails found matching: {', '.join(filters) or 'criteria'}"
        
        report = [f"🔍 **Search Results** ({len(rows)} emails found):\n"]
        
        for row in rows:
            risk_icon = "🔴" if row[4] >= 4 else ("🟡" if row[4] >= 2 else "🟢")
            
            report.append(f"""
{risk_icon} **{row[3]}** - {row[2] or row[0]}
   Risk: {row[4]}/5 | Part: {row[5] or 'N/A'} | Order: {row[6] or 'N/A'}
   Reason: {row[7][:100] if row[7] else 'N/A'}...
""")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"Error searching emails: {e}"


@tool
def get_email_summary(filename: str) -> str:
    """
    Get detailed information about a specific processed email.
    
    Args:
        filename: The email filename (e.g., 'email_001_Delay.eml')
    
    Returns:
        Complete details of the email including extraction results.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM processed_emails
            WHERE filename LIKE ?
        """, (f"%{filename}%",))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return f"❌ Email '{filename}' not found in processed emails."
        
        risk_level = {1: "Low", 2: "Moderate", 3: "Elevated", 4: "High", 5: "Critical"}
        
        return f"""
📧 **Email Details: {row[1]}**
═══════════════════════════════════

📤 **Sender:** {row[2] or 'Unknown'}
📋 **Subject:** {row[3] or 'N/A'}

**Classification:**
   • Intent: {row[4]}
   • Risk Score: {row[5]}/5 ({risk_level.get(row[5], 'Unknown')})

**Extracted Data:**
   • Part ID: {row[6] or 'N/A'}
   • Order ID: {row[7] or 'N/A'}
   • Old Value: {row[8] or 'N/A'}
   • New Value: {row[9] or 'N/A'}

**Analysis:**
{row[10] or 'No reasoning provided.'}

📅 **Processed At:** {row[11]}
"""
        
    except Exception as e:
        return f"Error fetching email details: {e}"


@tool
def get_emails_by_risk(min_risk: int = 3) -> str:
    """
    Get all emails with risk score at or above the specified level.
    Use this to identify high-priority supplier issues.
    
    Args:
        min_risk: Minimum risk score to filter by (1-5, default: 3)
    
    Returns:
        List of high-risk emails requiring attention.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filename, subject, intent, risk_score, part_id, order_id, reasoning
            FROM processed_emails
            WHERE risk_score >= ?
            ORDER BY risk_score DESC, processed_at DESC
        """, (min_risk,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return f"✅ No emails with risk score ≥ {min_risk} found."
        
        report = [f"🚨 **HIGH RISK EMAILS** (Risk ≥ {min_risk}):\n"]
        
        for row in rows:
            risk_icon = "🔴" if row[3] >= 4 else "🟡"
            
            report.append(f"""
{risk_icon} **Risk {row[3]}/5 - {row[2]}**
   {row[1] or row[0]}
   Part: {row[4] or 'N/A'} | Order: {row[5] or 'N/A'}
   Issue: {row[6][:80] if row[6] else 'N/A'}...
""")
        
        report.append(f"\n📌 Total High-Risk Items: {len(rows)}")
        return "\n".join(report)
        
    except Exception as e:
        return f"Error fetching high-risk emails: {e}"
