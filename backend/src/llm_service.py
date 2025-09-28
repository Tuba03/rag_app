# backend/src/llm_service.py
import os
import pandas as pd
import time
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
import sqlite_utils
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Configuration
CHROMA_DB_DIR = 'data/chroma_db'
SQLITE_DB_PATH = 'data/people.sqlite'
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
MAX_RETRIES = 3
RETRY_DELAY = 1.0

class RAGService:
    def __init__(self):
        """Initialize RAG Service with comprehensive error handling."""
        print("Initializing RAG Service...")
        
        # Initialize all attributes to None first
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.llm = None
        self.db = None
        self.rag_chain = None
        self.is_initialized = False
        
        try:
            self._load_vector_store()
            self._load_sqlite_db()
            self._setup_llm_chain()
            self.is_initialized = True
            print("RAG Service initialized successfully.")
        except Exception as e:
            print(f"CRITICAL ERROR: RAG Service initialization failed: {e}")
            # Don't raise - allow graceful degradation

    def _load_vector_store(self):
        """Load ChromaDB with error handling."""
        if not os.path.exists(CHROMA_DB_DIR):
            raise FileNotFoundError(
                f"ChromaDB directory not found at {CHROMA_DB_DIR}. "
                "Please run 'python src/indexing.py' first."
            )
        
        try:
            self.embeddings = SentenceTransformerEmbeddings(
                model_name=EMBEDDING_MODEL_NAME
            )
            self.vectorstore = Chroma(
                persist_directory=CHROMA_DB_DIR,
                embedding_function=self.embeddings
            )
            
            # Test the vectorstore by checking if it has data
            collection = self.vectorstore._collection
            if collection.count() == 0:
                raise ValueError("ChromaDB index appears to be empty. Please re-run indexing.")
                
            self.retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": 5}
            )
            print(f"Vector store loaded successfully with {collection.count()} documents.")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load vector store: {e}")

    def _load_sqlite_db(self):
        """Load SQLite database with validation."""
        if not os.path.exists(SQLITE_DB_PATH):
            raise FileNotFoundError(
                f"SQLite database not found at {SQLITE_DB_PATH}. "
                "Please run data generation and indexing first."
            )
        
        try:
            self.db = sqlite_utils.Database(SQLITE_DB_PATH)
            
            # Validate database has the expected table and data
            if "people" not in self.db.table_names():
                raise ValueError("Database missing 'people' table.")
            
            row_count = self.db["people"].count
            if row_count == 0:
                raise ValueError("Database 'people' table is empty.")
                
            print(f"SQLite database loaded with {row_count} records.")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load SQLite database: {e}")

    def _setup_llm_chain(self):
        """Setup LLM and prompt chain with API key validation."""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please create a .env file with your API key."
            )

        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                temperature=0.1,
                google_api_key=gemini_api_key,
                request_timeout=30  # Add timeout
            )
            
            # Test the LLM with a simple call
            test_response = self.llm.invoke("Hello")
            if not test_response or not test_response.content:
                raise ValueError("LLM test call returned empty response")
                
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLM: {e}")

        # Setup prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", 
            "You are an expert recruitment assistant. Explain why the provided "
            "context matches the user query in 1-2 sentences. Be specific about "
            "relevant skills, experience, or interests. If there's no clear match, "
            "respond with: 'Limited match - consider broadening search criteria.'\n\n"
            "CONTEXT: {context}"
            ),
            ("human", "USER_QUERY: {query}")
        ])
        
        self.rag_chain = (
            self.prompt
            | self.llm
            | StrOutputParser()
        )

    def _safe_llm_call(self, context: str, query: str) -> str:
        """Make LLM call with retry logic and error handling."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.rag_chain.invoke({
                    "context": context,
                    "query": query
                })
                
                # Validate response
                if not response or len(response.strip()) < 10:
                    return "Match found but explanation unavailable."
                    
                return response.strip()
                
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"LLM call attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                else:
                    print(f"All LLM attempts failed: {e}")
                    return "Match found - technical details available in full profile."
        
        return "Match found but explanation service temporarily unavailable."

    def search(self, query: str) -> List[Dict]:
        """
        Search with comprehensive error handling and fallback strategies.
        """
        # Validate service is initialized
        if not self.is_initialized:
            raise Exception(
                "RAG Service not properly initialized. Check logs for setup errors."
            )
        
        # Validate query
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")
        
        query = query.strip()
        if len(query) < 2:
            raise ValueError("Query must be at least 2 characters long.")
        
        results = []
        
        try:
            # Step 1: Vector retrieval
            docs = self.retriever.invoke(query)
            
            if not docs:
                return []  # No matches found
            
            print(f"Retrieved {len(docs)} candidate matches.")
            
            # Step 2: Process each match
            for i, doc in enumerate(docs):
                try:
                    doc_id = doc.metadata.get('id')
                    if not doc_id:
                        print(f"Warning: Document {i} missing ID in metadata")
                        continue
                    
                    # Get full record from SQLite with error handling
                    try:
                        full_record = dict(self.db["people"].get(doc_id))
                    except sqlite_utils.db.NotFoundError:
                        print(f"Warning: Record {doc_id} not found in SQLite")
                        continue
                    except Exception as e:
                        print(f"Error fetching record {doc_id}: {e}")
                        continue
                    
                    # Generate explanation with fallback
                    explanation = self._safe_llm_call(doc.page_content, query)
                    
                    # Build result with defensive programming
                    result = {
                        "id": full_record.get("id", "unknown"),
                        "founder_name": full_record.get("founder_name", "Name unavailable"),
                        "role": full_record.get("role", "Role unspecified"),
                        "company": full_record.get("company", "Company unspecified"),
                        "location": full_record.get("location", "Location unspecified"),
                        "match_explanation": explanation,
                        "provenance": {
                            "matched_on_fields": doc.metadata.get('search_fields', 'multiple fields'),
                            "csv_id": doc_id,
                        },
                        "full_details": {
                            "idea": full_record.get("idea", "Not specified"),
                            "about": full_record.get("about", "Not specified"),
                            "keywords": full_record.get("keywords", "None listed"),
                            "linked_in": full_record.get("linked_in", "#"),
                            "notes": full_record.get("notes", ""),
                            "stage": full_record.get("stage", "Unspecified"),
                        }
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"Error processing document {i}: {e}")
                    continue  # Skip this document but continue with others
            
            print(f"Successfully processed {len(results)} results.")
            return results
            
        except Exception as e:
            # Log the error but provide user-friendly message
            print(f"Search error: {e}")
            raise Exception(
                "Search temporarily unavailable. Please try again or contact support."
            )

# Global service instance
rag_service = RAGService()