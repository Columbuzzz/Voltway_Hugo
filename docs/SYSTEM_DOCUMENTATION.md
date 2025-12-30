# Hugo AI - Complete System Documentation

## 🎯 Executive Summary

**Hugo** is an AI-powered procurement intelligence agent for Voltway, an electric scooter manufacturer. It monitors supplier communications, tracks inventory, automatically detects supply chain risks, and provides actionable insights through natural language interaction.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HUGO AI SYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   📥 INPUT SOURCES              🤖 AI PROCESSING              💾 STORAGE    │
│  ┌─────────────────┐          ┌─────────────────┐         ┌──────────────┐  │
│  │  📬 Gmail API   │─────────▶│   🐕 Watchdog   │────────▶│   SQLite     │  │
│  │  📁 .eml Files  │          │  Risk Scoring   │         │   Database   │  │
│  └─────────────────┘          └─────────────────┘         └──────────────┘  │
│                                       │                          │          │
│                                       │ risk ≥ 4                 │          │
│                                       ▼                          ▼          │
│                               ┌───────────────┐          ┌──────────────┐   │
│                               │ 🎫 Auto-Create │          │  ChromaDB    │   │
│                               │    Issues     │          │  (Schema)    │   │
│                               └───────────────┘          └──────────────┘   │
│                                                                  │          │
│   💬 CHAT INTERFACE                                              │          │
│  ┌─────────────────┐          ┌─────────────────┐               │          │
│  │   User Query    │─────────▶│   🔧 SQL Agent  │◀──────────────┘          │
│  │                 │          │   17 Tools      │                           │
│  └─────────────────┘          └────────┬────────┘                           │
│                                        │                                    │
│                                        ▼                                    │
│                               ┌─────────────────┐                           │
│                               │  📝 Response    │                           │
│                               └─────────────────┘                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🖥️ STREAMLIT DASHBOARD                               │
│         ┌────────────┬────────────┬────────────┬────────────┐               │
│         │ 🎫 Issues  │ 📧 Emails  │ 📦 Stock   │ 💬 Chat    │               │
│         └────────────┴────────────┴────────────┴────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### Email Processing Flow
```
📧 Email Received
       │
       ▼
┌─────────────────┐
│  🐕 Watchdog    │
│  - Classify     │
│  - Score (1-5)  │
│  - Extract IDs  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
Risk ≥ 4   Risk < 4
    │         │
    ▼         ▼
🎫 Create   📝 Log
  Issue      Only
    │         │
    └────┬────┘
         ▼
   💾 Store in DB
         │
         ▼
   📊 Dashboard
```

### Chat Flow
```
👤 User Query ──▶ 💬 chat_with_hugo() ──▶ 🔧 SQL Agent ──▶ 🛠️ Tools ──▶ 💾 DB ──▶ 📝 Response
```

---

## 📁 Project Structure

```
Voltway_Hugo/
├── streamlit_app.py           # Main dashboard (ENTRY POINT)
├── voltway.db                 # SQLite database
├── google_credentials.json    # GCP service account
├── gmail_api_credentials.json # Gmail OAuth credentials
│
├── src/
│   ├── agents.py              # LLM agents, chat_with_hugo()
│   ├── tools.py               # check_fulfillment, safety_stock
│   ├── stock_tools.py         # 5 inventory tools
│   ├── email_tools.py         # 4 email tools
│   ├── issue_tools.py         # 6 issue tracking tools
│   ├── gmail_monitor.py       # Gmail OAuth2
│   ├── rag_schema.py          # Schema embeddings
│   ├── ingest_specs.py        # BOM extraction
│   └── setup_db.py            # DB initialization
│
├── data/
│   ├── emails/                # .eml files
│   ├── specs/                 # PDF manuals
│   └── *.csv                  # Data files
│
└── docs/
    └── SYSTEM_DOCUMENTATION.md
```

---

## 🧩 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| LLM | Gemini 2.5 Flash | AI backbone |
| Framework | LangChain | SQL agent |
| Database | SQLite | Primary storage |
| Embeddings | VertexAI | Schema search |
| Vector Store | ChromaDB | RAG scaling |
| Frontend | Streamlit | Dashboard |
| Email | Gmail API | Inbox monitoring |

---

## 🛠️ Agent Tools (17 Total)

### 📦 Stock (5 tools)
| Tool | Purpose |
|------|---------|
| `get_stock_status(part_id)` | Stock for specific part |
| `get_low_stock_alerts(threshold)` | Parts below threshold |
| `get_stock_summary()` | Inventory overview |
| `get_stock_by_model(model)` | BOM stock check |
| `check_part_usage(part_id)` | BOM usage + demand |

### 📧 Email (4 tools)
| Tool | Purpose |
|------|---------|
| `get_email_history(limit)` | Recent emails |
| `search_emails(keyword, intent)` | Search emails |
| `get_email_summary(filename)` | Email details |
| `get_emails_by_risk(min_risk)` | High-risk filter |

### 🎫 Issues (6 tools)
| Tool | Purpose |
|------|---------|
| `get_open_issues()` | Active issues |
| `get_issue_details(issue_id)` | Issue info |
| `resolve_issue(id, notes)` | Close issue |
| `create_issue(title, desc, severity)` | New issue |
| `update_issue_status(id, status)` | Update status |
| `get_issue_summary()` | Statistics |

### 🔧 Operations (2 tools)
| Tool | Purpose |
|------|---------|
| `check_fulfillment(date, model, qty)` | Build feasibility |
| `calculate_lean_safety_stock(lead, demand)` | Safety stock |

---

## 🎫 Issue Lifecycle

```
NEW EMAIL (risk ≥ 4)
       │
       ▼
    ┌──────┐
    │ OPEN │ ◀─── Awaiting action
    └──┬───┘
       ▼
┌───────────┐
│IN_PROGRESS│ ◀─── Being addressed
└─────┬─────┘
      ▼
 ┌──────────┐
 │ RESOLVED │ ◀─── Fixed
 └──────────┘
```

### Severity Levels
| Score | Severity | Triggers |
|-------|----------|----------|
| 5 | 🔴 CRITICAL | Quality recall, production stop |
| 4 | 🟠 HIGH | Cancellation, discontinuation |
| 3 | 🟡 MEDIUM | Delay, partial shipment |
| 1-2 | 🟢 LOW | Price quotes, proposals |

---

## 📧 Email Intent Categories

| Intent | Auto-Actions |
|--------|--------------|
| DELAY | Check buffer stock, find alternates |
| QUALITY_ALERT | Set stock to HOLD, create issue |
| DISCONTINUATION | Recommend last-time-buy |
| PRICE_CHANGE | Calculate cost impact |
| PROPOSAL | Log for review |

---

## 🚀 Quick Start

```bash
# Setup database
python -c "from src.setup_db import create_sql_db; create_sql_db()"

# (Optional) Extract BOMs
python -m src.ingest_specs

# Run dashboard
streamlit run streamlit_app.py
```

---

## ⚙️ Configuration

```python
# src/tools.py - Simulated date for testing
SIMULATED_TODAY = datetime.date(2025, 4, 10)  # Testing
SIMULATED_TODAY = None  # Production

# src/agents.py - Rate limiting
MAX_RETRIES = 3
RETRY_DELAY = 10
```

---

## 📈 Anti-Hallucination

```
CRITICAL RULES:
- NEVER make up numbers
- ALWAYS use check_part_usage() before claiming demand
- If part not in BOM, say so clearly
```

---

*Last Updated: December 2024*
