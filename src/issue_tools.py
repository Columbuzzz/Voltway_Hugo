# src/issue_tools.py
"""
Issue tracking tools for Hugo AI Agent.
Automatically creates issues for critical emails and tracks resolution.
"""

import sqlite3
import datetime
from langchain_core.tools import tool

DB_PATH = "voltway.db"


def get_db_connection():
    """Get a connection to the database."""
    return sqlite3.connect(DB_PATH)


def init_issues_table():
    """Initialize the issues table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id TEXT UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            intent TEXT,
            severity TEXT DEFAULT 'MEDIUM',
            status TEXT DEFAULT 'OPEN',
            part_id TEXT,
            order_id TEXT,
            source_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            resolution_notes TEXT,
            assigned_to TEXT DEFAULT 'HUGO'
        )
    """)
    
    conn.commit()
    conn.close()


def generate_issue_id():
    """Generate a unique issue ID like ISS-20251229-001."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.date.today().strftime("%Y%m%d")
    
    cursor.execute("""
        SELECT COUNT(*) FROM issues 
        WHERE issue_id LIKE ?
    """, (f"ISS-{today}-%",))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return f"ISS-{today}-{count + 1:03d}"


def create_issue_from_email(filename: str, intent: str, risk_score: int, 
                             part_id: str = None, order_id: str = None,
                             reasoning: str = None):
    """
    Automatically create an issue when a critical email (risk >= 4) is processed.
    Called from email processing workflow.
    Prevents duplicates by checking if similar issue already exists.
    """
    if risk_score < 4:
        return None  # Only create issues for high-risk emails
    
    init_issues_table()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # IMPROVED DEDUPLICATION: Check by part_id + intent + order_id combo
    # This catches duplicates even if they come from different sources
    cursor.execute("""
        SELECT issue_id FROM issues 
        WHERE status IN ('OPEN', 'IN_PROGRESS')
        AND intent = ?
        AND (part_id = ? OR (part_id IS NULL AND ? IS NULL))
        AND (order_id = ? OR (order_id IS NULL AND ? IS NULL))
    """, (intent, part_id, part_id, order_id, order_id))
    
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return existing[0]  # Return existing issue ID without creating duplicate
    
    issue_id = generate_issue_id()
    severity = "CRITICAL" if risk_score >= 5 else "HIGH"
    
    title = f"[{severity}] {intent}: {part_id or order_id or 'Supply Chain Alert'}"
    description = f"Auto-generated from email: {filename}\n\nReason: {reasoning or 'High-risk supplier communication detected.'}"
    
    try:
        cursor.execute("""
            INSERT INTO issues 
            (issue_id, title, description, intent, severity, status, part_id, order_id, source_email, created_at)
            VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)
        """, (
            issue_id,
            title,
            description,
            intent,
            severity,
            part_id,
            order_id,
            filename,
            datetime.datetime.now().isoformat()
        ))
        conn.commit()
        print(f"🚨 Issue Created: {issue_id} - {title}")
        return issue_id
    except Exception as e:
        print(f"Error creating issue: {e}")
        return None
    finally:
        conn.close()


@tool
def get_open_issues() -> str:
    """
    Get all open issues that need attention.
    Use this to see what critical problems are currently active.
    
    Returns:
        List of open issues with their details.
    """
    try:
        init_issues_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT issue_id, title, severity, status, part_id, order_id, created_at
            FROM issues
            WHERE status IN ('OPEN', 'IN_PROGRESS')
            ORDER BY 
                CASE severity 
                    WHEN 'CRITICAL' THEN 1 
                    WHEN 'HIGH' THEN 2 
                    WHEN 'MEDIUM' THEN 3 
                    ELSE 4 
                END,
                created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "✅ No open issues! All clear."
        
        report = [f"🚨 **OPEN ISSUES** ({len(rows)} active):\n"]
        
        for row in rows:
            sev_icon = "🔴" if row[2] == "CRITICAL" else ("🟠" if row[2] == "HIGH" else "🟡")
            created = row[6][:10] if row[6] else "Unknown"
            
            report.append(f"""
{sev_icon} **{row[0]}** [{row[2]}]
   {row[1]}
   Part: {row[4] or 'N/A'} | Order: {row[5] or 'N/A'}
   Status: {row[3]} | Created: {created}
""")
        
        return "\n".join(report)
        
    except Exception as e:
        return f"Error fetching issues: {e}"


@tool
def get_issue_details(issue_id: str) -> str:
    """
    Get detailed information about a specific issue.
    
    Args:
        issue_id: The issue ID (e.g., 'ISS-20251229-001')
    
    Returns:
        Complete details of the issue.
    """
    try:
        init_issues_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM issues
            WHERE issue_id LIKE ?
        """, (f"%{issue_id}%",))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return f"❌ Issue '{issue_id}' not found."
        
        return f"""
📋 **Issue Details: {row[1]}**
═══════════════════════════════════════════

🔖 **Issue ID:** {row[1]}
📌 **Title:** {row[2]}

**Classification:**
   • Intent: {row[4]}
   • Severity: {row[5]}
   • Status: {row[6]}

**Affected:**
   • Part ID: {row[7] or 'N/A'}
   • Order ID: {row[8] or 'N/A'}
   • Source Email: {row[9] or 'N/A'}

**Description:**
{row[3] or 'No description provided.'}

**Timeline:**
   • Created: {row[10]}
   • Updated: {row[11]}
   • Resolved: {row[12] or 'Not yet resolved'}

**Resolution Notes:**
{row[13] or 'None yet.'}

**Assigned To:** {row[14]}
"""
        
    except Exception as e:
        return f"Error fetching issue details: {e}"


@tool
def resolve_issue(issue_id: str, resolution_notes: str) -> str:
    """
    Close an issue by marking it as resolved.
    Use this when a supply chain problem has been fixed.
    
    Args:
        issue_id: The issue ID to resolve
        resolution_notes: Description of how the issue was resolved
    
    Returns:
        Confirmation of issue resolution.
    """
    try:
        init_issues_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find the issue
        cursor.execute("SELECT issue_id, title FROM issues WHERE issue_id LIKE ?", (f"%{issue_id}%",))
        row = cursor.fetchone()
        
        if not row:
            return f"❌ Issue '{issue_id}' not found."
        
        # Update to resolved
        cursor.execute("""
            UPDATE issues
            SET status = 'RESOLVED',
                resolved_at = ?,
                updated_at = ?,
                resolution_notes = ?
            WHERE issue_id = ?
        """, (
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat(),
            resolution_notes,
            row[0]
        ))
        
        conn.commit()
        conn.close()
        
        return f"""
✅ **Issue Resolved Successfully**

🔖 Issue ID: {row[0]}
📌 Title: {row[1]}
📝 Resolution: {resolution_notes}
📅 Closed At: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
    except Exception as e:
        return f"Error resolving issue: {e}"


@tool
def create_issue(title: str, description: str, severity: str = "MEDIUM", 
                 part_id: str = None, order_id: str = None) -> str:
    """
    Manually create a new issue for tracking.
    
    Args:
        title: Brief title of the issue
        description: Detailed description of the problem
        severity: CRITICAL, HIGH, MEDIUM, or LOW
        part_id: Optional related part ID
        order_id: Optional related order ID
    
    Returns:
        Confirmation with the new issue ID.
    """
    try:
        init_issues_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        issue_id = generate_issue_id()
        severity = severity.upper() if severity else "MEDIUM"
        
        cursor.execute("""
            INSERT INTO issues 
            (issue_id, title, description, intent, severity, status, part_id, order_id, created_at)
            VALUES (?, ?, ?, 'MANUAL', ?, 'OPEN', ?, ?, ?)
        """, (
            issue_id,
            title,
            description,
            severity,
            part_id,
            order_id,
            datetime.datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        sev_icon = "🔴" if severity == "CRITICAL" else ("🟠" if severity == "HIGH" else "🟡")
        
        return f"""
{sev_icon} **New Issue Created**

🔖 Issue ID: {issue_id}
📌 Title: {title}
⚡ Severity: {severity}
📦 Part: {part_id or 'N/A'}
📋 Order: {order_id or 'N/A'}
"""
        
    except Exception as e:
        return f"Error creating issue: {e}"


@tool
def update_issue_status(issue_id: str, status: str) -> str:
    """
    Update the status of an issue.
    
    Args:
        issue_id: The issue ID to update
        status: New status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
    
    Returns:
        Confirmation of status update.
    """
    try:
        init_issues_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        valid_statuses = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']
        status = status.upper()
        
        if status not in valid_statuses:
            return f"❌ Invalid status. Use: {', '.join(valid_statuses)}"
        
        cursor.execute("SELECT issue_id, title FROM issues WHERE issue_id LIKE ?", (f"%{issue_id}%",))
        row = cursor.fetchone()
        
        if not row:
            return f"❌ Issue '{issue_id}' not found."
        
        cursor.execute("""
            UPDATE issues
            SET status = ?,
                updated_at = ?
            WHERE issue_id = ?
        """, (status, datetime.datetime.now().isoformat(), row[0]))
        
        conn.commit()
        conn.close()
        
        return f"✅ Issue {row[0]} status updated to: **{status}**"
        
    except Exception as e:
        return f"Error updating issue: {e}"


@tool 
def get_issue_summary() -> str:
    """
    Get a quick summary of all issues by status and severity.
    Use for a dashboard overview.
    
    Returns:
        Issue statistics and counts.
    """
    try:
        init_issues_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM issues 
            GROUP BY status
        """)
        status_counts = dict(cursor.fetchall())
        
        # Count by severity for open issues
        cursor.execute("""
            SELECT severity, COUNT(*) 
            FROM issues 
            WHERE status IN ('OPEN', 'IN_PROGRESS')
            GROUP BY severity
        """)
        severity_counts = dict(cursor.fetchall())
        
        conn.close()
        
        open_count = status_counts.get('OPEN', 0) + status_counts.get('IN_PROGRESS', 0)
        
        return f"""
📊 **ISSUE DASHBOARD**
═══════════════════════════════════════

**By Status:**
   • 🔓 Open: {status_counts.get('OPEN', 0)}
   • 🔄 In Progress: {status_counts.get('IN_PROGRESS', 0)}
   • ✅ Resolved: {status_counts.get('RESOLVED', 0)}
   • 📁 Closed: {status_counts.get('CLOSED', 0)}

**Open Issues by Severity:**
   • 🔴 Critical: {severity_counts.get('CRITICAL', 0)}
   • 🟠 High: {severity_counts.get('HIGH', 0)}
   • 🟡 Medium: {severity_counts.get('MEDIUM', 0)}
   • 🟢 Low: {severity_counts.get('LOW', 0)}

**Action Required:** {open_count} issue(s) need attention
"""
        
    except Exception as e:
        return f"Error getting issue summary: {e}"


@tool
def merge_duplicate_issues() -> str:
    """
    Find and merge duplicate issues.
    Keeps the oldest issue and marks newer duplicates as CLOSED.
    Duplicates are identified by same: intent + part_id + order_id.
    
    Returns:
        Summary of merged duplicates.
    """
    try:
        init_issues_table()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find duplicate groups (same intent + part_id + order_id)
        cursor.execute("""
            SELECT intent, part_id, order_id, GROUP_CONCAT(issue_id), COUNT(*) as cnt
            FROM issues
            WHERE status IN ('OPEN', 'IN_PROGRESS')
            GROUP BY intent, COALESCE(part_id, ''), COALESCE(order_id, '')
            HAVING cnt > 1
        """)
        
        duplicates = cursor.fetchall()
        
        if not duplicates:
            conn.close()
            return "✅ No duplicate issues found!"
        
        merged_count = 0
        report = ["🔄 **Merging Duplicate Issues:**\n"]
        
        for intent, part_id, order_id, issue_ids_str, count in duplicates:
            issue_ids = issue_ids_str.split(',')
            
            # Keep the first (oldest) issue, close the rest
            keep_id = issue_ids[0]
            close_ids = issue_ids[1:]
            
            for close_id in close_ids:
                cursor.execute("""
                    UPDATE issues
                    SET status = 'CLOSED',
                        resolution_notes = ?,
                        resolved_at = ?
                    WHERE issue_id = ?
                """, (
                    f"Duplicate - merged with {keep_id}",
                    datetime.datetime.now().isoformat(),
                    close_id
                ))
                merged_count += 1
            
            report.append(f"• **{intent}** ({part_id or 'N/A'}/{order_id or 'N/A'}): Kept {keep_id}, closed {len(close_ids)} duplicates")
        
        conn.commit()
        conn.close()
        
        report.append(f"\n📌 **Total merged:** {merged_count} duplicate issues closed")
        return "\n".join(report)
        
    except Exception as e:
        return f"Error merging duplicates: {e}"


def cleanup_all_duplicates():
    """
    Standalone function to clean up all duplicate issues.
    Can be run directly: python -c "from src.issue_tools import cleanup_all_duplicates; cleanup_all_duplicates()"
    """
    print("🔄 Scanning for duplicate issues...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    init_issues_table()
    
    # Find all open issues grouped by intent + part_id + order_id
    cursor.execute("""
        SELECT issue_id, intent, part_id, order_id, created_at
        FROM issues
        WHERE status IN ('OPEN', 'IN_PROGRESS')
        ORDER BY created_at ASC
    """)
    
    issues = cursor.fetchall()
    
    # Group by key
    groups = {}
    for issue_id, intent, part_id, order_id, created_at in issues:
        key = (intent, part_id or '', order_id or '')
        if key not in groups:
            groups[key] = []
        groups[key].append(issue_id)
    
    # Close duplicates (keep first)
    closed_count = 0
    for key, issue_ids in groups.items():
        if len(issue_ids) > 1:
            keep_id = issue_ids[0]
            for close_id in issue_ids[1:]:
                cursor.execute("""
                    UPDATE issues
                    SET status = 'CLOSED',
                        resolution_notes = ?,
                        resolved_at = ?
                    WHERE issue_id = ?
                """, (
                    f"Duplicate - merged with {keep_id}",
                    datetime.datetime.now().isoformat(),
                    close_id
                ))
                print(f"  ❌ Closed {close_id} (duplicate of {keep_id})")
                closed_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Cleanup complete! Closed {closed_count} duplicate issues.")
    return closed_count


if __name__ == "__main__":
    cleanup_all_duplicates()

