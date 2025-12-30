# Hugo AI - Complete System Documentation

## 🎯 Executive Summary

**Hugo** is an AI-powered procurement intelligence agent for Voltway, an electric scooter manufacturer. It monitors supplier communications, tracks inventory, automatically detects supply chain risks, and provides actionable insights through natural language interaction.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HUGO AI SYSTEM                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐│
│  │   Gmail      │────▶│   Email      │────▶│   AI Classification  ││
│  │   Monitor    │     │   Parser     │     │   (Watchdog)         ││
│  └──────────────┘     └──────────────┘     └──────────────────────┘│
│         │                    │                       │              │
│         ▼                    ▼                       ▼              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐│
│  │   OAuth2     │     │   Intent +   │     │   SQL Agent          ││
│  │   Auth       │     │   Risk Score │     │   (Tools + DB)       ││
│  └──────────────┘     └──────────────┘     └──────────────────────┘│
│                              │                       │              │
│                              ▼                       ▼              │
│                       ┌──────────────────────────────────┐         │
│                       │        SQLite Database           │         │
│                       │  • stock_levels  • issues        │         │
│                       │  • material_orders • emails      │         │
│                       │  • suppliers    • sales_orders   │         │
│                       └──────────────────────────────────┘         │
│                                      │                              │
│                                      ▼                              │
│                       ┌──────────────────────────────────┐         │
│                       │     Streamlit Dashboard          │         │
│                       │  • Real-time monitoring          │         │
│                       │  • Chat interface                │         │
│                       │  • Gmail integration             │         │
│                       └──────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Voltway_Hugo/
├── streamlit_app.py           # Main web dashboard (PRIMARY ENTRY POINT)
├── voltway.db                 # SQLite database
├── google_credentials.json    # GCP service account
├── gmail_api_credentials.json # Gmail OAuth credentials
│
├── src/
│   ├── agents.py              # LLM agents, chat_with_hugo(), prompts
│   ├── workflow.py            # LangGraph state machine (optional)
│   ├── schemas.py             # Pydantic data models (EmailExtraction)
│   ├── tools.py               # Core tools: check_fulfillment, safety_stock
│   ├── stock_tools.py         # Inventory: get_stock_status, check_part_usage
│   ├── email_tools.py         # Email: search_emails, get_email_history
│   ├── issue_tools.py         # Issues: create_issue, resolve_issue
│   ├── gmail_monitor.py       # Gmail OAuth2 + email download
│   ├── rag_schema.py          # Schema embeddings for SQL queries
│   ├── ingest_specs.py        # OCR-based BOM extraction from PDFs
│   └── setup_db.py            # Database initialization
│
├── data/
│   ├── emails/                # Processed .eml files
│   ├── specs/                 # Technical PDF manuals (for BOM extraction)
│   ├── augment_data.py        # Data alignment script for test scenarios
│   ├── stock_levels.csv       # Inventory data
│   ├── material_orders.csv    # Purchase orders
│   ├── suppliers.csv          # Supplier database
│   └── sales_orders.csv       # Customer orders
│
└── docs/
    ├── EMAIL_SOP.md           # Email handling procedures
    └── SYSTEM_DOCUMENTATION.md # This file
```


---

## 🔄 Data Flow

### 1. Email Processing Flow

```
Local .eml files OR Gmail Inbox
         │
         ▼ (streamlit_app.py)
┌─────────────────────────────────┐
│  WATCHDOG (AI Classification)  │
│  • Classify intent             │
│  • Assign risk score (1-5)     │
│  • Extract part_id, order_id   │
└─────────────────────────────────┘
         │
         ▼ (Store results)
┌─────────────────────────────────┐
│  processed_emails table        │
│  issues table (ALL emails)     │
└─────────────────────────────────┘
```

### 2. PDF/BOM Ingestion Pipeline

```
data/specs/*.pdf (scanned PDFs)
         │
         ▼ (src/ingest_specs.py)
┌─────────────────────────────────┐
│  OCR Processing (Tesseract)    │
│  + LLM Structuring (Gemini)    │
└─────────────────────────────────┘
         │
         ▼
BOM_S1_V1, BOM_S2_V2... tables
```

Run: `python -m src.ingest_specs`

### 3. Data Augmentation (Testing)

```bash
cd data
python augment_data.py
```

This script:
- Aligns part names with email test cases
- Adds missing orders referenced in emails
- Updates supplier prices for demo scenarios

### 2. Chat Flow

```
User Input (Streamlit)
         │
         ▼
chat_with_hugo()
         │
         ▼
┌─────────────────────────────────┐
│  SQL Agent + Custom Tools:     │
│    • get_stock_status          │
│    • get_open_issues           │
│    • check_fulfillment         │
│    • check_part_usage          │
└─────────────────────────────────┘
         │
         ▼
Formatted Answer with Emojis
```

---

## 🧩 Technology Stack

### Core AI Components

| Technology | Purpose |
|------------|---------|
| **Gemini 2.5 Flash** | LLM backbone with structured output |
| **LangChain** | Agent framework with SQL capabilities |
| **LangGraph** | Optional workflow orchestration |
| **Pydantic** | Type-safe structured outputs |

### Data & Storage

| Technology | Purpose |
|------------|---------|
| **SQLite** | Primary database (zero-config) |
| **ChromaDB** | Vector embeddings for RAG |
| **VertexAI Embeddings** | Semantic search for documents |

### Integration

| Technology | Purpose |
|------------|---------|
| **Gmail API** | Real email inbox monitoring |
| **OAuth2** | Secure Gmail authentication |

### Frontend

| Technology | Purpose |
|------------|---------|
| **Streamlit** | Web dashboard with chat |
| **streamlit-autorefresh** | Auto-update UI every 10s |

---

## 🔧 Available Tools

### Stock Awareness
| Tool | Purpose |
|------|---------|
| `get_stock_status(part_id)` | Query stock for a specific part |
| `get_low_stock_alerts(threshold)` | Find parts below threshold |
| `get_stock_summary()` | Executive inventory dashboard |
| `get_stock_by_model(model)` | BOM-based stock check |
| `check_part_usage(part_id)` | **NEW** - Which BOMs use a part + demand calculation |

### Email Awareness
| Tool | Purpose |
|------|---------|
| `get_email_history(limit)` | Recent processed emails |
| `search_emails(keyword)` | Search by keyword/intent |
| `get_email_summary(filename)` | Full email details |
| `get_emails_by_risk(min_risk)` | Filter high-risk emails |

### Issue Tracking
| Tool | Purpose |
|------|---------|
| `get_open_issues()` | All active issues |
| `get_issue_details(issue_id)` | Full issue info |
| `resolve_issue(id, notes)` | Close an issue |
| `create_issue(title, desc, severity)` | Manual creation |
| `get_issue_summary()` | Dashboard statistics |

### Operations
| Tool | Purpose |
|------|---------|
| `check_fulfillment(date, model, qty)` | Can we build X by date? |
| `calculate_lean_safety_stock(lead, demand)` | Statistical safety stock |

---

## 🎫 Issue Tracking System

### Auto-Creation Logic
```python
if risk_score >= 4:  # HIGH or CRITICAL
    create_issue_from_email()
```

### Issue Lifecycle
```
NEW EMAIL (risk >= 4)
       │
       ▼ (auto-created)
    ┌──────┐
    │ OPEN │ ← Awaiting action
    └──┬───┘
       ▼
 ┌───────────┐
 │IN_PROGRESS│ ← Being addressed
 └─────┬─────┘
       ▼
  ┌──────────┐
  │ RESOLVED │ ← Solution applied
  └──────────┘
```

### Severity Levels
| Score | Severity | Trigger |
|-------|----------|---------|
| 5 | 🔴 CRITICAL | Quality recall, production stop |
| 4 | 🟠 HIGH | Cancellation, discontinuation |
| 3 | 🟡 MEDIUM | Delay, partial shipment |
| 1-2 | 🟢 LOW | Price quotes, proposals |

---

## 📧 Email Intent Categories

| Intent | Auto-Actions |
|--------|--------------|
| **DELAY** | Check buffer stock, find alternates |
| **QUALITY_ALERT** | Set stock to HOLD, create critical issue |
| **DISCONTINUATION** | Recommend last-time-buy |
| **PRICE_CHANGE** | Calculate cost impact |
| **PROPOSAL** | Log for review |

---

## 🚀 Running the System

### Primary: Web Dashboard
```bash
streamlit run streamlit_app.py
```

### Gmail Integration
Click **"📬 Connect Gmail"** in sidebar to:
1. Authenticate via OAuth2 (opens browser)
2. Download supplier emails to `data/emails/`
3. Process through AI classification

### Testing Features (Sidebar)
- **🔄 Reprocess All** - Clear and re-analyze emails
- **🗑️ Clear Emails/Issues** - Reset for testing

---

## ⚙️ Configuration

### Simulated Date (Testing)
In `src/tools.py`:
```python
# For testing with sample data (March-April 2025)
SIMULATED_TODAY = datetime.date(2025, 4, 10)

# For production (real date)
SIMULATED_TODAY = None
```

### Rate Limiting
In `src/agents.py`:
```python
MAX_RETRIES = 3      # Retries on 429 error
RETRY_DELAY = 10     # Seconds between retries
```

---

## 🔐 Security

- OAuth2 for Gmail (no password storage)
- Token-based authentication
- Credentials in JSON files (gitignored)
- No sensitive data in code

---

## 📈 Anti-Hallucination Measures

Hugo's chat prompt includes:
```
CRITICAL RULES:
- NEVER make up numbers. Say "I don't have that data."
- ALWAYS use check_part_usage(part_id) BEFORE claiming demand quantities
- If a part isn't in any BOM, say so clearly
```

---

## 📊 Demo Checklist

1. ✅ Start: `streamlit run streamlit_app.py`
2. ✅ View Dashboard with issues panel
3. ✅ Chat with Hugo about stock/suppliers
4. ✅ Click "📬 Connect Gmail" to fetch real emails
5. ✅ Watch issues auto-create from critical emails
6. ✅ Resolve issues from dashboard

---

*Last Updated: December 2024*
