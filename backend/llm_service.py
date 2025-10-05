# backend/llm_service.py
import os
import time
import json
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
import sqlite_utils
from typing import List, Dict, Optional
from langchain.schema.document import Document
import re

# --- Robust Environment Loading ---
# Determine the absolute path to the project root (.. from backend/)
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# Force load .env from the project root for local development
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, '.env'))


# --- Configuration ---
CHROMA_DB_DIR = os.path.join(PROJECT_ROOT, 'data', 'chroma_db')
SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'people.sqlite')
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K_DOCUMENTS = 20  
RESULTS_LIMIT = 5

class RAGService:
    # ... (LOCATION_MAPPING and other constants are the same) ...

    def __init__(self):
        self.retriever = None
        self.db = None
        
        # Initialize DB client 
        if os.path.exists(SQLITE_DB_PATH):
            self.db = sqlite_utils.Database(SQLITE_DB_PATH)
        else:
            print(f"⚠️  SQLite DB not found at {SQLITE_DB_PATH}. Will initialize without provenance lookup.")
            
        # Initialize LLM
        # FIX: Explicitly pass the API key from environment variables
        # Note: Streamlit Cloud makes secrets available via os.environ automatically.
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not gemini_api_key:
            # Raise a clear error if the key is missing
            raise ValueError("GEMINI_API_KEY environment variable is not set. Cannot initialize RAGService. Please check your .env or Streamlit secrets.")
            
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.0, 
            google_api_key=gemini_api_key, 
            client=None, 
        )
        self.embedding_model = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        
        # Initialize ChromaDB vector store
        if os.path.exists(CHROMA_DB_DIR):
            try:
                vectorstore = Chroma(
                    persist_directory=CHROMA_DB_DIR, 
                    embedding_function=self.embedding_model
                )
                self.retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K_DOCUMENTS})
                print(f"✅ RAGService initialized. ChromaDB loaded from {CHROMA_DB_DIR}")
            except Exception as e:
                print(f"❌ Error loading ChromaDB: {e}. Index might be corrupted or missing.")
        else:
            print(f"❌ ChromaDB directory not found at {CHROMA_DB_DIR}. Run indexing.py first.")
    
    # ... (rest of the file remains the same: _parse_query_for_filters, _get_full_record_from_db, search methods) ...

rag_service = RAGService()