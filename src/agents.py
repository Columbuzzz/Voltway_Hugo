# src/agents.py
import os, json, datetime, time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_community.agent_toolkits import create_sql_agent

from src.schemas import EmailExtraction
from src.tools import db, check_fulfillment, calculate_lean_safety_stock
from src.rag import query_specs
from src.rag_schema import get_relevant_tables
from src.stock_tools import (
    get_stock_status, 
    get_low_stock_alerts, 
    get_stock_summary,
    get_stock_by_model,
    check_part_usage
)
from src.email_tools import (
    get_email_history,
    search_emails,
    get_email_summary,
    get_emails_by_risk
)
from src.issue_tools import (
    get_open_issues,
    get_issue_details,
    resolve_issue,
    create_issue,
    update_issue_status,
    get_issue_summary
)

# ---------------- RATE LIMIT HANDLER ----------------
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds

def with_retry(func):
    """Decorator to retry on rate limit errors (429)."""
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        print(f"⏳ Rate limit hit. Waiting {RETRY_DELAY}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(RETRY_DELAY)
                    else:
                        return "⚠️ API rate limit reached. Please wait a moment and try again."
                else:
                    raise e
    return wrapper

# ---------------- MEMORY ----------------
ACTION_HISTORY = []

def log_action(intent, score, details):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    ACTION_HISTORY.append(f"[{ts}] {intent} ({score}/5) → {details}")
    ACTION_HISTORY[:] = ACTION_HISTORY[-20:]


@tool
def check_action_history(query: str) -> str:
    """
    Returns a chronological log of recent actions taken by Hugo,
    including detected risks, intents, and automated decisions.
    Useful for audit trails and operational transparency.
    """
    if not ACTION_HISTORY:
        return "No recent actions processed."
    return "\n".join(ACTION_HISTORY)


# ---------------- AUTH ----------------
with open("google_credentials.json") as f:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
    PROJECT_ID = json.load(f)["project_id"]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    project=PROJECT_ID,
    temperature=0
)

# ---------------- WATCHDOG ----------------
def run_watchdog(email_text: str) -> EmailExtraction:
    structured = llm.with_structured_output(EmailExtraction)
    prompt = """
    You are a procurement risk classifier.
    Identify intent and risk score (1–5).
    Extract part_id, order_id, old_value, new_value.
    """
    return structured.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=email_text[:3000])
    ])

# ---------------- ANALYST ----------------
sql_agent = create_sql_agent(
    llm=llm,
    db=db,
    extra_tools=[
        # Core tools
        query_specs,
        check_fulfillment,
        calculate_lean_safety_stock,
        check_action_history,
        # Stock awareness tools
        get_stock_status,
        get_low_stock_alerts,
        get_stock_summary,
        get_stock_by_model,
        check_part_usage,
        # Email awareness tools
        get_email_history,
        search_emails,
        get_email_summary,
        get_emails_by_risk,
        # Issue tracking tools
        get_open_issues,
        get_issue_details,
        resolve_issue,
        create_issue,
        update_issue_status,
        get_issue_summary
    ],
    agent_type="tool-calling",
    verbose=False
)

def run_analyst(data: EmailExtraction):
    
    schema = get_relevant_tables(
        f"{data.intent} inventory orders suppliers", k=5
    )

    sop = f"""
    ROLE: Voltway Procurement Commander
    INTENT: {data.intent}
    DATA: {data.dict()}

    SCHEMA:
    {schema}

    Execute correct SOP using SQL or tools.
    """

    result = sql_agent.invoke(sop)
    output = result.get("output", "No action taken.")
    log_action(data.intent, data.risk_score, output)
    return output

# ---------------- RESPONSE CLEANER ----------------
def clean_response(output):
    """
    Cleans the LLM response to extract readable text.
    Handles cases where output contains structured data with signatures.
    """
    if output is None:
        return "Unable to answer."
    
    # If it's a simple string, return as-is
    if isinstance(output, str):
        # Check if it looks like a stringified list of dicts
        if output.startswith("[{") and "'type': 'text'" in output:
            try:
                import ast
                parsed = ast.literal_eval(output)
                return clean_response(parsed)
            except:
                pass
        return output
    
    # If it's a list, extract text from each item
    if isinstance(output, list):
        text_parts = []
        for item in output:
            if isinstance(item, dict):
                if 'text' in item:
                    text_parts.append(item['text'])
                elif 'content' in item:
                    text_parts.append(item['content'])
            elif isinstance(item, str):
                text_parts.append(item)
        return ''.join(text_parts) if text_parts else str(output)
    
    # If it's a dict with text key
    if isinstance(output, dict):
        if 'text' in output:
            return output['text']
        if 'content' in output:
            return output['content']
        if 'output' in output:
            return clean_response(output['output'])
    
    return str(output)


# ---------------- CHATBOT ----------------
@with_retry
def chat_with_hugo(user_input: str, conversation_history: list = None):
    """
    Chat with Hugo with rate limit handling.
    Optimized for token usage.
    """
    
    # Build minimal conversation context (last 4 messages only)
    history_context = ""
    if conversation_history:
        recent = conversation_history[-4:]  # Only last 4 messages to save tokens
        for msg in recent:
            role = "U" if msg["role"] == "user" else "H"
            # Truncate each message to 200 chars
            content = msg['content'][:200]
            history_context += f"{role}: {content}\n"
    
    # SHORTENED prompt to reduce tokens
    prompt = """You are Hugo, Voltway's procurement AI. Use these tools:
📦 Stock: get_stock_status, get_low_stock_alerts, get_stock_summary, check_part_usage
📧 Email: get_email_history, search_emails, get_emails_by_risk
🎫 Issues: get_open_issues, get_issue_details, resolve_issue
🔧 Ops: check_fulfillment, query_specs
💾 SQL: sales_orders, material_orders, suppliers, stock_levels

CRITICAL RULES:
- NEVER make up numbers. If data is unavailable, say "I don't have that data."
- ALWAYS use check_part_usage(part_id) BEFORE claiming demand/outbound quantities for a part.
- If a part isn't in any BOM, say so clearly - don't invent demand figures.

Be concise. Use emojis. Give actionable recommendations."""
    
    if history_context:
        prompt += f"\n\nRecent chat:\n{history_context}"
    
    # Truncate user input to avoid huge prompts
    user_input = user_input[:1000]
    prompt += f"\n\nUser: {user_input}"
    
    res = sql_agent.invoke(prompt)
    raw_output = res.get("output", "Unable to answer.")
    return clean_response(raw_output)


