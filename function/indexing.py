# function/indexing.py
import pandas as pd
import sqlite_utils
import os
# from langchain.text_splitter import CharacterTextSplitter # Not used, can be commented out
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain.schema.document import Document
import shutil # Used for deleting old directory

# 1. Configuration
CSV_PATH = 'data/people.csv'
SQLITE_DB_PATH = 'data/people.sqlite'
CHROMA_DB_DIR = 'data/chroma_db'
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# 2. Text Preparation
# function/indexing.py (The corrected part)

def create_documents(df):
    """Combines relevant columns into a single 'document' text for embedding and adds CRITICAL metadata."""
    documents = []
    for _, row in df.iterrows():
        # ... content concatenation remains the same ...
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
                # ... (other keys)
                "location": row['location'],
                "stage": row['stage'], # <--- THIS KEY IS ESSENTIAL FOR FILTERING
                "search_fields": f"idea, about, keywords, role, company, location, stage", 
            }
        )
        documents.append(doc)
    return documents

# 3. Indexing Function
def index_data():
    print("--- Starting Data Indexing ---")
    
    # Check if CSV exists
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: CSV file not found at {CSV_PATH}. Please run 'python src/data_generator.py' first.")
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

    # Use the local Sentence Transformer model for embeddings (free!)
    embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    print(f"Loaded embedding model: {EMBEDDING_MODEL_NAME}")
    
    # Create the Chroma index
    vectorstore = Chroma.from_documents(
        documents=documents, 
        embedding=embeddings, 
        persist_directory=CHROMA_DB_DIR
    )
    vectorstore.persist()
    print(f"ChromaDB index created and saved to {CHROMA_DB_DIR}")
    print("--- Data Indexing Complete ---")

if __name__ == "__main__":
    index_data()