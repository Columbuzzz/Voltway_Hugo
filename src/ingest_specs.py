import os
import sys
import json
import sqlite3
import re
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- CONFIG ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SPECS_DIR = os.path.join(PROJECT_ROOT, "data", "specs")
DB_PATH = os.path.join(PROJECT_ROOT, "voltway.db")

# --- AUTH ---
def get_project_id():
    filename = "google_credentials.json"
    possible_paths = [
        os.path.join(CURRENT_DIR, filename),
        os.path.join(PROJECT_ROOT, filename),
        filename,
    ]
    for path in possible_paths:
        if os.path.exists(path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
            with open(path, "r") as f:
                return json.load(f).get("project_id")
    sys.exit("❌ Google credentials not found.")

PROJECT_ID = get_project_id()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    project=PROJECT_ID,
    temperature=0
)

# --- HELPERS ---

def extract_model_from_filename(filename):
    """
    scanned_S1_V1_specs.pdf → S1_V1
    """
    match = re.search(r"(S\d+_V\d+)", filename, re.IGNORECASE)
    return match.group(1) if match else "UNKNOWN_MODEL"


def ocr_pdf_to_text(pdf_path):
    """
    Convert scanned PDF pages to OCR text
    """
    print("   🔍 Running OCR...")
    pages = convert_from_path(pdf_path, dpi=300)
    full_text = []

    for i, page in enumerate(pages):
        text = pytesseract.image_to_string(page, config="--psm 6")
        full_text.append(text)

    return "\n".join(full_text)


def parse_bom_with_llm(raw_text, model_name):
    """
    Extract structured BOM rows from noisy OCR text
    """
    print(f"   🧠 Structuring BOM for {model_name}...")

    prompt = f"""
You are extracting a Bill of Materials table from OCR text.

MODEL: {model_name}

RULES:
- Extract ONLY BOM table rows
- Ignore headers like "Overview", "Assembly Requirements"
- Each row MUST include:
    - part_id (Pxxx)
    - part_name
    - quantity (integer)
- If quantity missing, infer from context (default = 1)
- Ignore Notes column
- Do NOT hallucinate parts

OCR TEXT:
{raw_text[:6000]}

RETURN STRICT JSON ONLY:
[
  {{
    "part_id": "P300",
    "part_name": "S1 V1 500W Brushless Motor",
    "quantity": 1
  }}
]
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("   ❌ LLM parse failed:", e)
        return []


# --- MAIN INGESTION ---

def ingest_boms():
    if not os.path.exists(SPECS_DIR):
        print("❌ Specs directory not found.")
        return

    print("🏭 Starting OCR-based BOM Ingestion...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    pdf_files = [f for f in os.listdir(SPECS_DIR) if f.endswith(".pdf")]

    for filename in pdf_files:
        pdf_path = os.path.join(SPECS_DIR, filename)
        model = extract_model_from_filename(filename)
        table_name = f"BOM_{model}"

        print(f"\n📄 Processing {filename} → {table_name}")

        try:
            raw_text = ocr_pdf_to_text(pdf_path)
            parts = parse_bom_with_llm(raw_text, model)

            if not parts:
                print(f"   ⚠️ No BOM rows detected.")
                continue

            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            cursor.execute(
                f"""
                CREATE TABLE {table_name} (
                    part_id TEXT,
                    part_name TEXT,
                    quantity_needed INTEGER
                )
                """
            )

            for item in parts:
                cursor.execute(
                    f"INSERT INTO {table_name} VALUES (?,?,?)",
                    (
                        item["part_id"],
                        item["part_name"],
                        item["quantity"]
                    )
                )

            print(f"   ✅ {table_name} created ({len(parts)} rows)")

        except Exception as e:
            print(f"   ❌ Error processing {filename}: {e}")

    conn.commit()
    conn.close()
    print("\n🎉 BOM ingestion complete.")
