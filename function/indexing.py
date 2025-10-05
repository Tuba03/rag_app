# function/indexing.py
import pandas as pd
import sqlite_utils
import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain.schema.document import Document
import shutil 
import subprocess
import sys

# --- Configuration (Paths fixed for deployment) ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(CURRENT_DIR, 'data', 'people.csv')
SQLITE_DB_PATH = os.path.join(CURRENT_DIR, 'data', 'people.sqlite')
CHROMA_DB_DIR = os.path.join(CURRENT_DIR, 'data', 'chroma_db')
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DATA_GENERATOR_PATH = os.path.join(CURRENT_DIR, 'data_generator.py')

# 2. Text Preparation
def create_documents(df: pd.DataFrame) -> list[Document]:
    """Combines relevant columns into a single 'document' text for embedding and adds CRITICAL metadata."""
    documents = []
    for _, row in df.iterrows():
        # Combine searchable fields into the document content
        content = (
            f"Founder: {row['founder_name']}. Role: {row['role']}. "
            f"Company: {row['company']}. Location: {row['location']}. "
            f"Idea: {row['idea']}. About: {row['about']}. "
            f"Keywords: {row['keywords']}. Stage: {row['stage']}." 
        )
        
        doc = Document(
            page_content=content,
            metadata={
                "id": row['id'],
                "founder_name": row['founder_name'],
                "location": row['location'],
                "stage": row['stage'], 
                "search_fields": "idea, about, keywords, location",
            }
        )
        documents.append(doc)
    return documents

def main_indexing():
    if not os.path.exists(CSV_PATH):
        print(f"⚠️ CSV file not found at {CSV_PATH}. Attempting to run data_generator.py...")
        try:
            # Use sys.executable and explicit path
            subprocess.run([sys.executable, DATA_GENERATOR_PATH], check=True, cwd=CURRENT_DIR)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to run data_generator.py: {e}")
            return
    
    if not os.path.exists(CSV_PATH):
        print(f"❌ ERROR: CSV file still not found at {CSV_PATH} after generation attempt.")
        return
    
    # --- Part A: Load Data and Create SQLite DB for Metadata/Provenance ---
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} records from CSV.")
    
    # Store full dataset in SQLite for fast lookup later
    db = sqlite_utils.Database(SQLITE_DB_PATH)
    db["people"].insert_all(df.to_dict('records'), pk="id", replace=True)
    print(f"Full data stored in SQLite at {SQLITE_DB_PATH}")

    # --- Part B: Create LangChain Documents ---
    documents = create_documents(df)
    print(f"Created {len(documents)} LangChain Documents for indexing.")
    
    # --- Part C: Embed and Store in ChromaDB ---
    # Delete old index if it exists
    if os.path.exists(CHROMA_DB_DIR):
        shutil.rmtree(CHROMA_DB_DIR)
        print(f"Removed old ChromaDB directory: {CHROMA_DB_DIR}")

    # Used the local Sentence Transformer model for embeddings (free!)
    embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    print(f"Loaded embedding model: {EMBEDDING_MODEL_NAME}")
    
    # Create the Chroma index
    vectorstore = Chroma.from_documents(
        documents=documents, 
        embedding=embeddings, 
        persist_directory=CHROMA_DB_DIR
    )
    vectorstore.persist()
    print(f"✅ ChromaDB index created and saved to {CHROMA_DB_DIR}")

if __name__ == "__main__":
    main_indexing()