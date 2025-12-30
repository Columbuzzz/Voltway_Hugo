# streamlit_app.py
"""
Hugo AI Dashboard - Streamlit Web Application
Real-time monitoring dashboard for Voltway's procurement AI agent.

Run with: streamlit run streamlit_app.py

Features:
- 🎫 Issue Tracking Panel
- 📧 Email Feed
- 📦 Stock Alerts
- 💬 Chat with Hugo
- 📊 Analytics
- 🔄 Background Email Watcher (auto-starts)
"""

import os
import sys
import threading
import time
from pathlib import Path
from email import policy
import email as email_lib

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
EMAIL_DIR = PROJECT_ROOT / "data" / "emails"

# Suppress warnings
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Database path
DB_PATH = PROJECT_ROOT / "voltway.db"

def get_processed_emails_from_db():
    """Get list of already processed email filenames from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM processed_emails")
        result = {row[0] for row in cursor.fetchall()}
        conn.close()
        return result
    except:
        return set()

# Track processed emails - PERSIST across restarts by loading from DB
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = get_processed_emails_from_db()
if 'watcher_started' not in st.session_state:
    st.session_state.watcher_started = False
if 'new_email_count' not in st.session_state:
    st.session_state.new_email_count = 0


def process_single_email(filename):
    """Process a single email file through Hugo's AI analysis."""
    try:
        from src.email_tools import store_email_metadata
        from src.issue_tools import create_issue_from_email
        
        # Direct LLM call (avoids circular imports)
        import json as json_module
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        filepath = EMAIL_DIR / filename
        with open(filepath, "rb") as f:
            msg = email_lib.message_from_binary_file(f, policy=policy.default)
        
        # Extract content
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            body = msg.get_content() if hasattr(msg, 'get_content') else str(msg.get_payload())
        
        sender = msg["From"] or ""
        subject = msg["Subject"] or ""
        content = f"From: {sender}\nSubject: {subject}\n\n{body}"
        
        # Load credentials and call LLM directly
        import os as os_module
        creds_path = str(PROJECT_ROOT / "google_credentials.json")
        os_module.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        with open(creds_path) as f:
            project_id = json_module.load(f)["project_id"]
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            project=project_id,
            temperature=0
        )
        
        # Simple classification prompt with importance guidelines
        prompt = """Analyze this supplier email and extract:
- intent: One of [DELAY, QUALITY_ALERT, DISCONTINUATION, PRICE_CHANGE, SHIPMENT_UPDATE, CONTRACT_CHANGE, PROPOSAL, OTHER]
- risk_score: 1-5 based on IMPORTANCE (5 is critical)
- part_id: If mentioned (e.g., P300)
- order_id: If mentioned (e.g., O5007)
- reasoning: Brief explanation

IMPORTANCE GUIDELINES for risk_score:
  5 - CRITICAL: QUALITY_ALERT (defects, recalls, safety), DISCONTINUATION (part end-of-life)
  4 - HIGH: DELAY (shipment delays), CANCELLATION (order cancelled)
  3 - MEDIUM: PARTIAL_SHIPMENT, CONTRACT_CHANGE, SHIPMENT_UPDATE
  2 - LOW: PRICE_CHANGE (cost adjustments)
  1 - INFO: PROPOSAL, general inquiries, discounts

Return JSON only: {"intent": "...", "risk_score": N, "part_id": "...", "order_id": "...", "reasoning": "..."}"""
        
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=content[:1500])
        ])
        
        # Parse response
        try:
            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            extraction_dict = json_module.loads(text)
        except:
            extraction_dict = {"intent": "OTHER", "risk_score": 1, "part_id": None, "order_id": None, "reasoning": "Parse error"}
        
        # Store metadata
        store_email_metadata(
            filename=filename,
            sender=sender,
            subject=subject,
            extraction=extraction_dict,
            summary=f"Intent: {extraction_dict.get('intent', 'N/A')}, Risk: {extraction_dict.get('risk_score', 1)}"
        )
        
        # Create issue if critical
        risk_score = extraction_dict.get("risk_score", 1)
        if risk_score >= 4:
            create_issue_from_email(
                filename=filename,
                intent=extraction_dict.get("intent", "OTHER"),
                risk_score=risk_score,
                part_id=extraction_dict.get("part_id"),
                order_id=extraction_dict.get("order_id"),
                reasoning=extraction_dict.get("reasoning")
            )
        
        st.session_state.new_email_count += 1
        return True
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return False


def scan_and_process_emails():
    """Scan email directory and process new emails."""
    if not EMAIL_DIR.exists():
        return 0
    
    new_count = 0
    for f in os.listdir(EMAIL_DIR):
        if f.endswith(".eml") and f not in st.session_state.processed_files:
            if process_single_email(f):
                st.session_state.processed_files.add(f)
                new_count += 1
    return new_count


# Page config - MUST be first Streamlit command
st.set_page_config(
    page_title="Hugo AI - Voltway Procurement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Track current page in session
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Dashboard"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 0;
    }
    .sub-header {
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: black;
    }
    .critical-issue {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
        color: #333;
    }
    .high-issue {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
        color: #333;
    }
    .medium-issue {
        background-color: #fffde7;
        border-left: 4px solid #ffeb3b;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
        color: #333;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# ============== DATABASE HELPERS ==============

@st.cache_resource
def get_db_connection():
    """Get database connection."""
    return sqlite3.connect('voltway.db', check_same_thread=False)


def query_df(query, params=()):
    """Execute query and return DataFrame."""
    conn = sqlite3.connect('voltway.db')
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def execute_query(query, params=()):
    """Execute a write query."""
    conn = sqlite3.connect('voltway.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


# ============== DATA FETCHING ==============

def get_open_issues():
    """Get all open issues."""
    return query_df("""
        SELECT issue_id, title, severity, status, part_id, order_id, 
               source_email, created_at
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


def get_recent_emails(limit=10):
    """Get recent processed emails."""
    return query_df("""
        SELECT filename, sender, subject, intent, risk_score, 
               part_id, order_id, processed_at
        FROM processed_emails
        ORDER BY processed_at DESC
        LIMIT ?
    """, (limit,))


def get_low_stock(threshold=50):
    """Get low stock alerts."""
    return query_df("""
        SELECT part_id, part_name, quantity_available, location, status
        FROM stock_levels
        WHERE quantity_available < ?
        ORDER BY quantity_available ASC
    """, (threshold,))


def get_stock_summary():
    """Get stock statistics."""
    return query_df("""
        SELECT 
            COUNT(*) as total_parts,
            SUM(quantity_available) as total_units,
            SUM(CASE WHEN quantity_available < 50 THEN 1 ELSE 0 END) as low_stock,
            SUM(CASE WHEN quantity_available < 25 THEN 1 ELSE 0 END) as critical_stock
        FROM stock_levels
    """)


def get_issue_counts():
    """Get issue counts by status."""
    return query_df("""
        SELECT status, COUNT(*) as count
        FROM issues
        GROUP BY status
    """)


# ============== CHAT FUNCTION ==============

def chat_with_hugo(message, conversation_history=None):
    """Send message to Hugo and get response with conversation history."""
    try:
        from src.agents import chat_with_hugo as hugo_chat
        return hugo_chat(message, conversation_history)
    except Exception as e:
        return f"Error: {str(e)}"


# ============== SIDEBAR ==============

with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/robot-2.png", width=80)
    st.markdown("## 🤖 Hugo AI")
    st.markdown("*Voltway Procurement Assistant*")
    
    st.markdown("---")
    
    # Navigation - use session state for programmatic navigation
    pages = ["🏠 Dashboard", "🎫 Issues", "📧 Emails", "📦 Stock", "💬 Chat"]
    
    # Get index from session state if navigating programmatically
    default_index = 0
    if "current_page" in st.session_state and st.session_state.current_page in pages:
        default_index = pages.index(st.session_state.current_page)
    
    page = st.radio(
        "Navigate",
        pages,
        index=default_index,
        label_visibility="collapsed"
    )
    
    # Store current page
    st.session_state.current_page = page

# Auto-refresh ONLY when NOT on Chat page (UI refresh only - no heavy processing)
if page != "💬 Chat":
    try:
        from streamlit_autorefresh import st_autorefresh
        # Refresh every 10 seconds (10000 milliseconds) - ONLY refreshes UI
        count = st_autorefresh(interval=10000, limit=None, key="email_watcher")
        # NOTE: Email processing removed from auto-refresh to prevent freezing
        # Emails are now only processed on first load or manual trigger
    except ImportError:
        pass

# Continue with sidebar
with st.sidebar:
    
    st.markdown("---")
    
    # Quick Stats
    st.markdown("### Quick Stats")
    
    try:
        issues_df = get_open_issues()
        st.metric("Open Issues", len(issues_df))
        
        critical = len(issues_df[issues_df['severity'] == 'CRITICAL']) if not issues_df.empty else 0
        st.metric("Critical", critical, delta=None if critical == 0 else f"{critical} urgent!")
        
        stock_df = get_low_stock()
        st.metric("Low Stock Items", len(stock_df))
    except:
        st.info("Database initializing...")
    
    st.markdown("---")
    st.markdown("*Last updated:*")
    st.markdown(f"*{datetime.now().strftime('%H:%M:%S')}*")
    
    if st.button("🔄 Refresh Data"):
        st.rerun()
    
    # Email Processing
    st.markdown("---")
    st.markdown("### 📧 Email Monitor")
    
    email_count = len([f for f in os.listdir(EMAIL_DIR) if f.endswith('.eml')]) if EMAIL_DIR.exists() else 0
    # Always get fresh count from database
    processed_count = len(get_processed_emails_from_db())
    st.session_state.processed_files = get_processed_emails_from_db()  # Sync session state
    pending = email_count - processed_count
    
    st.markdown(f"📥 **Total:** {email_count}")
    st.markdown(f"✅ **Processed:** {processed_count}")
    if pending > 0:
        st.markdown(f"⏳ **Pending:** {pending}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Process", help="Process new emails", disabled=(pending == 0)):
            with st.spinner("Processing..."):
                try:
                    new_count = scan_and_process_emails()
                    if new_count > 0:
                        st.success(f"✅ {new_count} email(s)!")
                    else:
                        st.info("No new emails")
                except Exception as e:
                    st.error(f"Error: {str(e)[:50]}")
            st.rerun()
    
    with col2:
        if st.button("🔄 Reprocess All", help="Clear and reprocess all emails"):
            execute_query("DELETE FROM processed_emails")
            execute_query("DELETE FROM issues")
            st.session_state.processed_files = set()
            st.success("✅ Reset! Click Process again.")
            st.rerun()
    
    st.markdown("*UI auto-refreshes every 10s*")
    
    # Testing Tools
    st.markdown("---")
    st.markdown("### 🧪 Testing Tools")
    
    if st.button("🗑️ Clear All Emails", help="Delete all processed email records"):
        execute_query("DELETE FROM processed_emails")
        st.session_state.processed_files = set()
        st.success("✅ Cleared all email records!")
        st.rerun()
    
    if st.button("🗑️ Clear All Issues", help="Delete all issues"):
        execute_query("DELETE FROM issues")
        st.success("✅ Cleared all issues!")
        st.rerun()
    
    # Gmail Integration
    st.markdown("---")
    st.markdown("### 📬 Gmail Integration")
    
    gmail_status = "🔴 Not connected"
    if 'gmail_connected' in st.session_state and st.session_state.gmail_connected:
        gmail_status = "🟢 Connected"
    st.markdown(f"Status: {gmail_status}")
    
    if st.button("📬 Connect Gmail", help="Authenticate with Gmail and fetch supplier emails"):
        try:
            from src.gmail_monitor import authenticate_gmail, get_supplier_emails, download_email
            from datetime import datetime, timedelta
            
            with st.spinner("Authenticating with Gmail..."):
                service = authenticate_gmail()
            
            st.session_state.gmail_connected = True
            st.success("✅ Gmail authenticated!")
            
            with st.spinner("Fetching supplier emails..."):
                after_date = datetime.now() - timedelta(days=7)
                messages = get_supplier_emails(service, after_date=after_date)
            
            if messages:
                downloaded = 0
                for msg in messages[:5]:  # Limit to 5 emails
                    filepath = download_email(service, msg['id'])
                    if filepath:
                        downloaded += 1
                
                if downloaded > 0:
                    st.success(f"📥 Downloaded {downloaded} email(s) to data/emails/")
                    st.session_state.last_email_count = 0  # Reset to trigger notification
                    st.rerun()
                else:
                    st.info("No new emails to download")
            else:
                st.info("No supplier emails found in last 7 days")
                
        except Exception as e:
            st.error(f"Gmail error: {str(e)[:100]}")

# Check for new email notifications
if 'last_email_count' not in st.session_state:
    st.session_state.last_email_count = 0

current_email_count = len([f for f in os.listdir(EMAIL_DIR) if f.endswith('.eml')]) if EMAIL_DIR.exists() else 0
if current_email_count > st.session_state.last_email_count:
    new_emails = current_email_count - st.session_state.last_email_count
    st.toast(f"📧 {new_emails} new email(s) received!", icon="📬")
    st.session_state.last_email_count = current_email_count


# ============== MAIN CONTENT ==============

# Header
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown('<p class="main-header">🤖 Hugo AI Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Voltway Procurement Intelligence</p>', unsafe_allow_html=True)

with col3:
    st.markdown(f"**{datetime.now().strftime('%B %d, %Y')}**")


# ============== DASHBOARD PAGE ==============

if page == "🏠 Dashboard":
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        issues_df = get_open_issues()
        emails_df = get_recent_emails()
        stock_df = get_low_stock()
        stock_summary = get_stock_summary()
        
        with col1:
            st.metric(
                label="🎫 Open Issues",
                value=len(issues_df),
                delta="Needs attention" if len(issues_df) > 0 else None
            )
        
        with col2:
            critical = len(issues_df[issues_df['severity'] == 'CRITICAL']) if not issues_df.empty else 0
            st.metric(
                label="🔴 Critical Issues",
                value=critical,
                delta=f"{critical} urgent" if critical > 0 else None,
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                label="📧 Emails Processed", 
                value=len(emails_df),
                delta="Today"
            )
        
        with col4:
            st.metric(
                label="📦 Low Stock Alerts",
                value=len(stock_df),
                delta="Below threshold" if len(stock_df) > 0 else None
            )
        
        st.markdown("---")
        
        # Two columns: Issues and Emails
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎫 Active Issues")
            if not issues_df.empty:
                for _, row in issues_df.head(5).iterrows():
                    severity = row['severity']
                    icon = "🔴" if severity == "CRITICAL" else ("🟠" if severity == "HIGH" else "🟡")
                    
                    with st.container():
                        st.markdown(f"""
                        <div class="{severity.lower()}-issue">
                            <strong>{icon} {row['issue_id']}</strong> [{severity}]<br>
                            {row['title'][:50]}...<br>
                            <small>Part: {row['part_id'] or 'N/A'} | Order: {row['order_id'] or 'N/A'}</small>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.success("✅ No open issues!")
        
        with col2:
            st.markdown("### 📧 Recent Emails")
            if not emails_df.empty:
                for _, row in emails_df.head(5).iterrows():
                    risk = row['risk_score']
                    icon = "🔴" if risk >= 4 else ("🟡" if risk >= 2 else "🟢")
                    
                    with st.container():
                        st.markdown(f"""
                        **{icon} {row['intent']}** (Risk: {risk}/5)  
                        {row['subject'][:40] if row['subject'] else row['filename'][:40]}...  
                        <small>Part: {row['part_id'] or 'N/A'}</small>
                        """, unsafe_allow_html=True)
                        st.markdown("---")
            else:
                st.info("No emails processed yet.")
        
        st.markdown("---")
        
        # Stock Alerts Table
        st.markdown("### 📦 Stock Alerts (Below 50 units)")
        if not stock_df.empty:
            # Add visual indicators
            stock_df['Status'] = stock_df['quantity_available'].apply(
                lambda x: "🔴 Critical" if x < 25 else "🟡 Low"
            )
            st.dataframe(
                stock_df[['part_id', 'part_name', 'quantity_available', 'location', 'Status']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ All stock levels healthy!")
            
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")


# ============== ISSUES PAGE ==============

elif page == "🎫 Issues":
    st.markdown("## 🎫 Issue Tracker")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        severity_filter = st.multiselect(
            "Filter by Severity",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH", "MEDIUM"]
        )
    with col2:
        status_filter = st.multiselect(
            "Filter by Status",
            ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"],
            default=["OPEN", "IN_PROGRESS"]
        )
    
    try:
        # Get filtered issues
        all_issues = query_df("""
            SELECT issue_id, title, severity, status, part_id, order_id, 
                   source_email, created_at, resolution_notes
            FROM issues
            ORDER BY created_at DESC
        """)
        
        if not all_issues.empty:
            filtered = all_issues[
                (all_issues['severity'].isin(severity_filter)) &
                (all_issues['status'].isin(status_filter))
            ]
            
            st.markdown(f"**Showing {len(filtered)} of {len(all_issues)} issues**")
            
            for _, row in filtered.iterrows():
                severity = row['severity']
                status = row['status']
                icon = "🔴" if severity == "CRITICAL" else ("🟠" if severity == "HIGH" else "🟡")
                status_icon = "✅" if status == "RESOLVED" else "🔓"
                
                with st.expander(f"{icon} {row['issue_id']} - {row['title'][:60]}...", expanded=(severity=="CRITICAL")):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Severity:** {severity}")
                        st.markdown(f"**Status:** {status_icon} {status}")
                        st.markdown(f"**Part ID:** {row['part_id'] or 'N/A'}")
                    with col2:
                        st.markdown(f"**Order ID:** {row['order_id'] or 'N/A'}")
                        st.markdown(f"**Created:** {row['created_at'][:16] if row['created_at'] else 'N/A'}")
                        st.markdown(f"**Source:** {row['source_email'] or 'Manual'}")
                    
                    if status == "OPEN":
                        if st.button(f"✅ Resolve Issue", key=f"resolve_{row['issue_id']}"):
                            execute_query("""
                                UPDATE issues SET status = 'RESOLVED', 
                                resolved_at = ? WHERE issue_id = ?
                            """, (datetime.now().isoformat(), row['issue_id']))
                            st.success(f"Issue {row['issue_id']} resolved!")
                            st.rerun()
        else:
            st.info("No issues found.")
            
    except Exception as e:
        st.error(f"Error: {e}")


# ============== EMAILS PAGE ==============

elif page == "📧 Emails":
    st.markdown("## 📧 Processed Emails")
    
    try:
        emails_df = get_recent_emails(50)
        
        if not emails_df.empty:
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Processed", len(emails_df))
            with col2:
                high_risk = len(emails_df[emails_df['risk_score'] >= 4])
                st.metric("High Risk", high_risk)
            with col3:
                intents = emails_df['intent'].nunique()
                st.metric("Intent Types", intents)
            
            st.markdown("---")
            
            # Table with colors
            def color_risk(val):
                if val >= 4:
                    return 'background-color: #ffcdd2; color: black'
                elif val >= 2:
                    return 'background-color: #fff9c4; color: black'
                return 'background-color: #c8e6c9; color: black'
            
            display_df = emails_df[['filename', 'intent', 'risk_score', 'part_id', 'order_id', 'processed_at']]
            st.dataframe(
                display_df.style.applymap(color_risk, subset=['risk_score']),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No emails processed yet.")
            
    except Exception as e:
        st.error(f"Error: {e}")


# ============== STOCK PAGE ==============

elif page == "📦 Stock":
    st.markdown("## 📦 Inventory Status")
    
    try:
        # Summary
        summary = get_stock_summary()
        if not summary.empty:
            row = summary.iloc[0]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total SKUs", int(row['total_parts']) if row['total_parts'] else 0)
            with col2:
                st.metric("Total Units", f"{int(row['total_units']):,}" if row['total_units'] else 0)
            with col3:
                st.metric("Low Stock", int(row['low_stock']) if row['low_stock'] else 0)
            with col4:
                st.metric("Critical", int(row['critical_stock']) if row['critical_stock'] else 0)
        
        st.markdown("---")
        
        # Threshold slider
        threshold = st.slider("Stock Alert Threshold", 10, 100, 50)
        
        stock_df = get_low_stock(threshold)
        
        if not stock_df.empty:
            st.warning(f"⚠️ {len(stock_df)} parts below {threshold} units")
            
            def color_stock(val):
                if val < 25:
                    return 'background-color: #ffcdd2; color: black'
                elif val < 50:
                    return 'background-color: #fff9c4; color: black'
                return 'color: black'
            
            st.dataframe(
                stock_df.style.applymap(color_stock, subset=['quantity_available']),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success(f"✅ All parts above {threshold} units!")
        
        # Full stock table
        with st.expander("View All Stock"):
            all_stock = query_df("SELECT * FROM stock_levels ORDER BY quantity_available")
            st.dataframe(all_stock, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"Error: {e}")


# ============== CHAT PAGE ==============

elif page == "💬 Chat":
    st.markdown("## 💬 Chat with Hugo")
    st.markdown("*Ask about stock, issues, emails, or any procurement question*")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "👋 Hi! I'm Hugo, your procurement AI. Ask me about stock levels, supplier emails, issues, or anything else!"}
        ]
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask Hugo..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get Hugo's response - NOW WITH CONVERSATION HISTORY
        with st.chat_message("assistant"):
            with st.spinner("Hugo is thinking..."):
                # Pass conversation history for context
                response = chat_with_hugo(prompt, st.session_state.messages[:-1])
            st.markdown(response)
        
        # Add assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})


# ============== FOOTER ==============

st.markdown("---")
st.markdown(
    "<center><small>🤖 Hugo AI - Voltway Procurement Intelligence System | Built with Streamlit</small></center>",
    unsafe_allow_html=True
)
