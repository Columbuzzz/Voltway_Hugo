# 🤖 Hugo AI - Procurement Intelligence Agent

An AI-powered procurement assistant for Voltway electric scooters that monitors supplier emails, tracks inventory, detects supply chain risks, and provides actionable insights through natural language.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1+-green.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-purple.svg)

## ✨ Features

- **📧 Email Monitoring** - Analyzes supplier emails for delays, quality alerts, price changes
- **🎫 Issue Tracking** - Auto-creates issues for high-risk emails (risk ≥ 4)
- **💬 Chat Interface** - Natural language queries about stock, orders, suppliers
- **📦 Inventory Awareness** - Real-time stock levels, low-stock alerts, BOM analysis
- **📊 Dashboard** - Streamlit web UI with all panels
- **📬 Gmail Integration** - OAuth2 integration to fetch real emails

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/Voltway_Hugo.git
cd Voltway_Hugo
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Google Cloud Credentials

**Required:** A Google Cloud project with:
- Vertex AI API enabled
- Gemini API access

Create `google_credentials.json` in root folder:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  ...
}
```

### 5. Initialize Database

```bash
# Create the SQLite database with all tables
python -c "from src.setup_db import create_sql_db; create_sql_db()"

# (Optional) Extract BOMs from scanned PDFs
python -m src.ingest_specs

# (Optional) Align data for test scenarios
cd data && python augment_data.py && cd ..

# (Optional) Build schema index for RAG
python -c "from src.rag_schema import build_schema_index; build_schema_index()"
```

### 6. Run the Dashboard
```bash
streamlit run streamlit_app.py
```

Open http://localhost:8501

---

## 📁 Project Structure

```
Voltway_Hugo/
├── streamlit_app.py           # Main dashboard
├── voltway.db                 # SQLite database
├── requirements.txt           # Dependencies
│
├── src/
│   ├── agents.py              # LLM agents & chat
│   ├── tools.py               # Core operations
│   ├── stock_tools.py         # Inventory tools
│   ├── email_tools.py         # Email awareness
│   ├── issue_tools.py         # Issue tracking
│   ├── gmail_monitor.py       # Gmail OAuth2
│   ├── rag_schema.py          # Schema embeddings (for scaling)
│   ├── ingest_specs.py        # OCR-based BOM extraction
│   └── setup_db.py            # Database initialization
│
├── data/
│   ├── emails/                # .eml files
│   ├── specs/                 # Scanned PDF manuals
│   ├── stock_levels.csv       # Inventory
│   ├── material_orders.csv    # Purchase orders
│   └── suppliers.csv          # Supplier database
│
└── docs/
    └── SYSTEM_DOCUMENTATION.md
```

---

## 🛠️ Agent Tools & Capabilities

Hugo has access to **17 specialized tools**:

### 📦 Stock & Inventory
| Tool | Description |
|------|-------------|
| `get_stock_status(part_id)` | Get stock levels for a specific part |
| `get_low_stock_alerts(threshold)` | Find parts below threshold |
| `get_stock_summary()` | Executive inventory overview |
| `get_stock_by_model(model)` | Stock for all BOM components |
| `check_part_usage(part_id)` | Which BOMs use this part + demand |

### 📧 Email Awareness
| Tool | Description |
|------|-------------|
| `get_email_history(limit)` | Recent processed emails |
| `search_emails(keyword, intent)` | Search by keyword or intent |
| `get_email_summary(filename)` | Full email details |
| `get_emails_by_risk(min_risk)` | High-risk email filter |

### 🎫 Issue Tracking
| Tool | Description |
|------|-------------|
| `get_open_issues()` | All active issues |
| `get_issue_details(issue_id)` | Full issue info |
| `resolve_issue(id, notes)` | Close an issue |
| `create_issue(title, desc, severity)` | Manual issue creation |
| `get_issue_summary()` | Dashboard statistics |

### 🔧 Operations
| Tool | Description |
|------|-------------|
| `check_fulfillment(date, model, qty)` | Build feasibility check |
| `calculate_lean_safety_stock(lead, demand)` | Statistical safety stock |

---

## 💬 Chat Examples

### Stock Queries
- *"Which stocks are running low?"*
- *"What's the stock status for P302?"*
- *"Give me a stock summary"*
- *"How is P305 used across our products?"*

### Build Feasibility
- *"Can we build 100 S2_V2 scooters by May 2025?"*
- *"Is it feasible to produce 50 S1_V1 by April 15?"*

### Email & Suppliers
- *"Show me recent supplier emails"*
- *"Find emails about delays"*
- *"Show high-risk emails"*
- *"Which suppliers provide P302?"*

### Issue Management
- *"What open issues need attention?"*
- *"Show me issue ISS-20251229-001"*
- *"Give me an issue summary"*

---

## 📧 Gmail Integration (Optional)

1. Create OAuth credentials in Google Cloud Console
2. Download and save as `gmail_api_credentials.json`
3. Click **"📬 Connect Gmail"** in sidebar
4. Complete OAuth flow in browser
5. Emails download to `data/emails/`

---

## 🔧 Configuration

### Testing Mode (Sample Data)
Sample data is set in March-April 2025. To use simulated date:

```python
# src/tools.py
SIMULATED_TODAY = datetime.date(2025, 4, 10)  # For testing
```

### Production Mode
```python
SIMULATED_TODAY = None  # Uses real date
```

---

## 📊 Sample Data

Included sample data simulates:
- 40+ inventory parts across 3 warehouses
- 6 scooter models with full BOMs
- 10 supplier relationships
- Sample supplier emails (delays, quality alerts, price changes)

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | Gemini 2.5 Flash |
| Framework | LangChain + LangGraph |
| Database | SQLite |
| Frontend | Streamlit |
| Embeddings | VertexAI |
| Vector Store | ChromaDB |

---

## 📝 License

MIT License - feel free to use and modify.

---

## 🙏 Acknowledgments

Built with [LangChain](https://langchain.com), [Streamlit](https://streamlit.io), and [Google Gemini](https://ai.google.dev).
