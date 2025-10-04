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

load_dotenv()

# Configuration
CHROMA_DB_DIR = 'data/chroma_db'
SQLITE_DB_PATH = 'data/people.sqlite'
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K_DOCUMENTS = 20  # Increased to get more candidates before filtering

class RAGService:
    AVAILABLE_LOCATIONS = [
        "San Francisco, USA", "New York, USA", "London, UK", "Berlin, Germany",
        "Bangalore, India", "Singapore, Singapore", "Toronto, Canada", "Paris, France"
    ]
    
    LOCATION_MAPPING = {
        "ny": "New York, USA",
        "new york": "New York, USA",
        "sf": "San Francisco, USA",
        "san francisco": "San Francisco, USA",
        "london": "London, UK",
        "bangalore": "Bangalore, India",
        "blr": "Bangalore, India",
        "sg": "Singapore, Singapore",
        "singapore": "Singapore, Singapore",
        "toronto": "Toronto, Canada",
        "paris": "Paris, France",
        "berlin": "Berlin, Germany",
    }
    
    # NEW: Define available stages for extraction
    STAGE_MAPPING = {
        "seed stage": "seed",
        "seed": "seed",
        "pre-seed": "pre-seed",
        "series a": "series A",
        "series a stage": "series A",
        "growth stage": "growth",
        "growth": "growth",
        "a": "series A", 
    }

    def __init__(self):
        print("Initializing RAG Service...")
        
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.llm = None
        self.db_path = None
        self.rag_chain = None
        self.is_initialized = False
        
        try:
            self._load_vector_store()
            self._load_sqlite_db_path()
            self._setup_llm_chain()
            self.is_initialized = True
            print("RAG Service initialized successfully.")
        except Exception as e:
            print(f"CRITICAL ERROR: RAG Service initialization failed: {e}")
            self.is_initialized = False

    def _get_api_key(self) -> str:
        """Fetch API Key from Streamlit secrets or environment."""
        try:
            import streamlit as st
            if "GEMINI_API_KEY" in st.secrets:
                print("API Key found in Streamlit secrets.")
                return st.secrets["GEMINI_API_KEY"]
        except ImportError:
            pass

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            print("API Key found in environment variables.")
            return api_key

        raise ValueError(
            "GEMINI_API_KEY not found. Set it in environment or .streamlit/secrets.toml"
        )

    def _load_vector_store(self):
        if not os.path.exists(CHROMA_DB_DIR):
            raise FileNotFoundError(f"Chroma DB not found at {CHROMA_DB_DIR}")

        self.embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        self.vectorstore = Chroma(
            persist_directory=CHROMA_DB_DIR, 
            embedding_function=self.embeddings
        )
        print(f"Vector store loaded with {self.vectorstore._collection.count()} documents.")

    def _load_sqlite_db_path(self):
        if not os.path.exists(SQLITE_DB_PATH):
            raise FileNotFoundError(f"SQLite DB not found at {SQLITE_DB_PATH}")
            
        self.db_path = SQLITE_DB_PATH
        temp_db = sqlite_utils.Database(SQLITE_DB_PATH)
        count = temp_db["people"].count
        print(f"SQLite database verified with {count} records.")

    def _setup_llm_chain(self):
        api_key = self._get_api_key()
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            api_key=api_key,
            temperature=0.0
        )
        
        template = """You are an expert matchmaking assistant analyzing founder profiles.

    
User Query: {query}

Retrieved Profiles (JSON):
{context}

Instructions:
1. Identify the TOP 5 best matches based on the query.
2. The provided profiles have ALREADY been filtered by any strict criteria (like stage or location) present in the User Query. Do NOT filter them again.
3. Your final output must be from the provided profiles.
4. Generate a clear 1-2 sentence explanation for each match.

Output Format (JSON array only, no markdown):
[
  {{
    "csv_id": "exact-id-from-profile",
    "founder_name": "name",
    "match_explanation": "Concise explanation mentioning why they match"
  }}
]

If no good matches exist, return: []
"""
        
        prompt = ChatPromptTemplate.from_template(template)
        self.rag_chain = prompt | self.llm | StrOutputParser()
        
    # NEW METHOD: Extracts the stage filter
    def _extract_stage_filter(self, query: str) -> Optional[str]:
        """Extracts the stage filter from the query based on predefined keywords."""
        lower_query = query.lower()

        for keyword, stage_value in self.STAGE_MAPPING.items():
            # Use regex to match whole words (e.g., prevent "series a" matching "area")
            if re.search(r'\b' + re.escape(keyword) + r'\b', lower_query):
                return stage_value
        
        return None

    def _parse_location(self, query: str) -> Optional[str]:
        """Extract and normalize location from query."""
        lower_query = query.lower()
        
        # Check exact locations first
        for location in self.AVAILABLE_LOCATIONS:
            if location.lower() in lower_query:
                return location
        
        # Check aliases
        for alias, canonical in self.LOCATION_MAPPING.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', lower_query):
                return canonical
                
        return None

    def _get_full_record(self, doc_id: str) -> Optional[Dict]:
        """Retrieve full record from SQLite (thread-safe)."""
        try:
            db_conn = sqlite_utils.Database(self.db_path)
            record = db_conn["people"].get(doc_id)
            return record 
        except Exception as e:
            print(f"Error retrieving record {doc_id}: {e}")
            return None

    def search(self, query: str) -> List[Dict]:
        """Perform RAG search with hard metadata filtering (Stage and Location)."""
        if not self.is_initialized:
            raise Exception("RAG Service not initialized. Check logs.")
            
        try:
            # 1. FILTER EXTRACTION
            stage_filter = self._extract_stage_filter(query)
            location_filter = self._parse_location(query)
            
            # 2. BUILD CHROMA WHERE CLAUSE
            chroma_where_filter = {}
            if stage_filter:
                chroma_where_filter["stage"] = stage_filter
            if location_filter:
                chroma_where_filter["location"] = location_filter
                
            print(f"ChromaDB WHERE clause: {chroma_where_filter}")
            
            # Use 'filter' key if the where clause is not empty, otherwise None
            chroma_filter_arg = chroma_where_filter if chroma_where_filter else None
            
            # 3. RETRIEVAL (Hybrid Search with Filter)
            # This applies the filter (e.g., stage='seed') BEFORE the similarity search.
            retrieved_docs_and_scores = self.vectorstore.similarity_search_with_score(
                query, 
                k=TOP_K_DOCUMENTS,
                filter=chroma_filter_arg 
            )
            
            print(f"Retrieved {len(retrieved_docs_and_scores)} documents after strict filtering.")

            if not retrieved_docs_and_scores:
                return []
            
            # Take only the document objects
            retrieved_docs = [doc for doc, score in retrieved_docs_and_scores]

            # 4. Format context for LLM (top 10 subset)
            context_json = json.dumps([
                {
                    "id": doc.metadata.get('id'),
                    "stage": doc.metadata.get('stage'), 
                    "location": doc.metadata.get('location'),
                    "content": doc.page_content
                }
                for doc in retrieved_docs[:10] # Pass a smaller, highly relevant set to LLM
            ], indent=2)
            
            # 5. Get LLM rankings (Generation)
            llm_output = self.rag_chain.invoke({
                "query": query,
                "context": context_json
            })
            
            # 6. Parse LLM output
            llm_output = llm_output.strip()
            if llm_output.startswith('```json'):
                llm_output = llm_output[7:]
            if llm_output.endswith('```'):
                llm_output = llm_output[:-3]
            llm_output = llm_output.strip()
            
            try:
                llm_matches = json.loads(llm_output)
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                print(f"Raw output: {llm_output}")
                return []
            
            if not isinstance(llm_matches, list):
                llm_matches = [llm_matches] if isinstance(llm_matches, dict) else []
            
            # 7. Compile final results
            results = []
            for match in llm_matches[:5]:
                doc_id = match.get('csv_id')
                if not doc_id:
                    continue
                
                full_record = self._get_full_record(doc_id)
                if not full_record:
                    continue
                
                # FINAL VALIDATION: Ensure the returned record still matches the stage filter (sanity check)
                if stage_filter and full_record.get('stage') != stage_filter:
                    continue 

                result = {
                    "id": doc_id,
                    "founder_name": full_record.get("founder_name", "N/A"),
                    "role": full_record.get("role", "N/A"),
                    "company": full_record.get("company", "N/A"),
                    "location": full_record.get("location", "N/A"),
                    "match_explanation": match.get("match_explanation", "Match found based on profile."),
                    "provenance": {
                        "matched_on_fields": "idea, about, keywords, location",
                        "csv_id": doc_id,
                    },
                    "full_details": {
                        "idea": full_record.get("idea", ""),
                        "about": full_record.get("about", ""),
                        "keywords": full_record.get("keywords", ""),
                        "linked_in": full_record.get("linked_in", "#"),
                        "notes": full_record.get("notes", ""),
                        "stage": full_record.get("stage", ""),
                    }
                }
                results.append(result)
            
            print(f"Returning {len(results)} final results")
            return results
            
        except Exception as e:
            print(f"Search error: {e}")
            raise Exception(f"RAG search failed: {e}")

# Global service instance
rag_service = RAGService()