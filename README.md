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
python -c "from src.setup_db import create_sql_db; create_sql_db()"
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
│   └── gmail_monitor.py       # Gmail OAuth2
│
├── data/
│   ├── emails/                # .eml files
│   ├── stock_levels.csv       # Inventory
│   ├── material_orders.csv    # Purchase orders
│   └── suppliers.csv          # Supplier database
│
└── docs/
    └── SYSTEM_DOCUMENTATION.md
```

---

## 💬 Chat Examples

Ask Hugo:
- *"Which stocks are running low?"*
- *"Show me open issues"*
- *"Can we build 100 S2_V2 scooters by May 2025?"*
- *"Which suppliers provide P302?"*
- *"How will the delay on O5007 impact us?"*

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
