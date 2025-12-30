import os
import sys
import json
from langchain_google_vertexai import VertexAIEmbeddings  # Standardize
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import tool

# --- CENTRALIZED AUTH ---
def get_credentials():
    # Robust finder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    json_name = "google_credentials.json"
    
    paths = [
        os.path.join(base_dir, json_name),
        os.path.join(root_dir, json_name),
        json_name
    ]
    
    for p in paths:
        if os.path.exists(p):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = p
            return p
            
    print(f"❌ Critical Error: {json_name} not found.")
    sys.exit(1)

get_credentials()

# --- SETUP ---
embeddings = VertexAIEmbeddings(model_name="text-embedding-004")

# Dynamic Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
PDF_DB_PATH = os.path.join(ROOT_DIR, "chroma_specs_index")
PDF_SOURCE = os.path.join(ROOT_DIR, "data", "specs", "specs_manual.pdf")

def setup_rag():
    if os.path.exists(PDF_DB_PATH) and os.listdir(PDF_DB_PATH):
        return

    print("📄 Indexing PDF Manual...")
    if not os.path.exists(PDF_SOURCE):
        print(f"⚠️ Warning: PDF not found at {PDF_SOURCE}")
        return

    loader = PyPDFLoader(PDF_SOURCE)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = splitter.split_documents(docs)
    
    Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=PDF_DB_PATH)
    print("✅ PDF Indexing Complete.")

@tool
def query_specs(query: str) -> str:
    """Searches the technical manuals for assembly steps, safety warnings, 
    torque specs, and troubleshooting guides."""
    setup_rag()
    if not os.path.exists(PDF_DB_PATH): return "Specs not found."
    
    vectorstore = Chroma(persist_directory=PDF_DB_PATH, embedding_function=embeddings)
    results = vectorstore.similarity_search(query, k=3)
    return "\n".join([doc.page_content for doc in results])