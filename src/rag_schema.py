import os
import json
# FIX 1: Use the new langchain-chroma library
from langchain_chroma import Chroma
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.documents import Document
from src.tools import db

# Load Credentials
json_path = "google_credentials.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
with open(json_path, "r") as f:
    creds = json.load(f)
    my_project_id = creds.get("project_id")

# --- SETUP EMBEDDINGS ---
embeddings = VertexAIEmbeddings(
    model_name="text-embedding-004", 
    project=my_project_id,
    location="global" 
)

DB_PATH = "./chroma_schema_index"

def build_schema_index():
    print("📊 Indexing Database Schema...")
    
    table_names = db.get_table_names()
    documents = []
    
    for table in table_names:
        raw_schema = db.get_table_info([table])
        doc = Document(
            page_content=raw_schema,
            metadata={"table_name": table}
        )
        documents.append(doc)
    
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    print(f"✅ Schema Indexing Complete. {len(documents)} tables indexed.")

def get_relevant_tables(query: str, k=4):
    if not os.path.exists(DB_PATH):
        build_schema_index()
        
    vectorstore = Chroma(
        persist_directory=DB_PATH, 
        embedding_function=embeddings
    )
    
    results = vectorstore.similarity_search(query, k=k)
    relevant_schema_text = "\n\n".join([doc.page_content for doc in results])
    return relevant_schema_text

if __name__ == "__main__":
    build_schema_index()