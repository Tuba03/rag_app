# # backend/src/llm_service.py
# import os
# import time
# import json
# from dotenv import load_dotenv
# from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import SentenceTransformerEmbeddings
# from langchain_google_genai import ChatGoogleGenerativeAI 
# from langchain.prompts import ChatPromptTemplate
# from langchain.schema.output_parser import StrOutputParser
# import sqlite_utils # Import the utility library here
# from typing import List, Dict, Optional
# from langchain.schema.document import Document # Needed for type hints

# # Load environment variables from .env (for non-Streamlit/local runs)
# load_dotenv()

# # Configuration
# CHROMA_DB_DIR = 'data/chroma_db'
# SQLITE_DB_PATH = 'data/people.sqlite'
# EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
# LLM_MODEL = "gemini-2.5-flash"
# K_RETRIEVAL = 5 # Number of documents to retrieve

# class RAGService:
#     def __init__(self):
#         """Initialize RAG Service with comprehensive error handling."""
#         print("Initializing RAG Service...")
        
#         # Initialize all attributes to None first
#         self.embeddings = None
#         self.vectorstore = None
#         self.llm = None
#         self.db_path = None # Store the path, not the connection object
#         self.rag_chain = None
#         self.is_initialized = False
        
#         try:
#             # Note: _get_api_key is called inside _setup_llm_chain
#             self._load_vector_store()
#             self._load_sqlite_db_path() # Renamed to reflect storing path only
#             self._setup_llm_chain()
#             self.is_initialized = True
#             print("RAG Service initialized successfully.")
#         except Exception as e:
#             # CRITICAL: This log is essential for debugging
#             print(f"CRITICAL ERROR: RAG Service initialization failed: {e}")
#             self.is_initialized = False

#     def _get_api_key(self) -> str:
#         """Dynamically fetch the Gemini API Key from secrets.toml (Streamlit) or environment (.env/os)."""
        
#         # 1. Check Streamlit secrets (only works if 'streamlit' package is available)
#         try:
#             import streamlit as st
#             if "GEMINI_API_KEY" in st.secrets:
#                 print("API Key found in Streamlit secrets.")
#                 return st.secrets["GEMINI_API_KEY"]
#         except ImportError:
#             pass # Not running in Streamlit environment

#         # 2. Check environment variables (for FastAPI/local runs using .env)
#         api_key = os.getenv("GEMINI_API_KEY")
#         if api_key:
#             print("API Key found in environment variables.")
#             return api_key

#         # If neither is found, raise a clear error
#         raise ValueError(
#             "GEMINI_API_KEY not found. Please set it in your environment or in the .streamlit/secrets.toml file."
#         )


#     def _load_vector_store(self):
#         """Load the SentenceTransformerEmbeddings and Chroma vector store."""
#         # Check for directory first
#         if not os.path.exists(CHROMA_DB_DIR):
#             raise FileNotFoundError(f"Chroma DB not found at {CHROMA_DB_DIR}. Run 'python indexing.py' first.")

#         # LangChainDeprecationWarning: SentenceTransformerEmbeddings is deprecated
#         self.embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        
#         # LangChainDeprecationWarning: Chroma is deprecated
#         self.vectorstore = Chroma(
#             persist_directory=CHROMA_DB_DIR, 
#             embedding_function=self.embeddings
#         )
#         print(f"Vector store loaded successfully with {self.vectorstore._collection.count()} documents.")

#     def _load_sqlite_db_path(self):
#         """Store the SQLite database path and verify existence."""
#         if not os.path.exists(SQLITE_DB_PATH):
#             raise FileNotFoundError(f"SQLite DB not found at {SQLITE_DB_PATH}. Run 'python indexing.py' first.")
            
#         self.db_path = SQLITE_DB_PATH # Store the path for later use

#         # Verify record count using a temporary connection (safe)
#         temp_db = sqlite_utils.Database(SQLITE_DB_PATH)
#         count = temp_db["people"].count
#         print(f"SQLite database path stored with verified count of {count} records. (Connection postponed due to threading issues)")


#     def _setup_llm_chain(self):
#         """Set up the LLM and the RAG Prompt chain."""
#         api_key = self._get_api_key()
        
#         # Initialize LLM
#         self.llm = ChatGoogleGenerativeAI(
#             model=LLM_MODEL, 
#             api_key=api_key
#         )
        
#         # Define RAG Prompt
#         template = """
#         You are a smart matching engine. Your task is to analyze a user query 
#         and the context provided below (details of potential founders).
        
#         1. Evaluate how well each founder's profile aligns with the user's query.
#         2. Generate a concise, single-paragraph 'match_explanation' for each founder, 
#            explaning *why* they are a good match, citing specifics from their profile.
#         3. Do not include any introductory or concluding text, only the final JSON object.
        
#         User Query: {query}
        
#         Context (Founder Profiles to Evaluate):
#         ---
#         {context}
#         ---

#         Output a JSON array of objects, where each object has the following keys:
#         - founder_name (string)
#         - match_explanation (string, the explanation generated by you)
#         - csv_id (string, the original ID from the context)
#         """
        
#         prompt = ChatPromptTemplate.from_template(template)
        
#         # Setup the RAG Chain components
#         self.rag_chain = (
#             prompt 
#             | self.llm 
#             | StrOutputParser()
#         )

#     def _format_context(self, docs: List[Document]):
#         """Formats the retrieved LangChain documents into a single string for the LLM."""
#         context = []
#         for i, doc in enumerate(docs):
#             context.append(f"--- Document {i+1} (ID: {doc.metadata.get('id', 'N/A')}) ---\n{doc.page_content}")
#         return "\n\n".join(context)

#     def _get_full_record(self, doc_id: str) -> Optional[Dict]:
#         """
#         Retrieves the full record from the SQLite database.
        
#         CRITICAL FIX: A new connection is opened for every lookup to ensure 
#         it happens in the current thread, resolving the SQLite threading error.
#         """
#         try:
#             # Open a new connection using the stored path
#             db_conn = sqlite_utils.Database(self.db_path)
            
#             # Assumes 'id' is the primary key in the 'people' table
#             record = db_conn["people"].get(doc_id)
            
#             return record 
#         except Exception as e:
#             # We must print the error here to catch failed lookups
#             print(f"Error retrieving full record for ID {doc_id}: {e}")
#             return None

#     def search(self, query: str) -> List[Dict]:
#         """Performs RAG retrieval and generation."""
#         if not self.is_initialized:
#             raise Exception("RAG Service failed to initialize. Check logs for critical errors (e.g., missing API Key or data files).")
            
#         try:
#             # 1. Retrieval: Get relevant documents with scores
#             retrieved_docs_and_scores = self.vectorstore.similarity_search_with_score(query, k=K_RETRIEVAL)
            
            
#             # --- DEBUG BLOCK START (Check your terminal for this output!) ---
#             print(f"\n--- DEBUG: Retrieved Documents ({len(retrieved_docs_and_scores)}) for Query: '{query[:50]}...' ---")
            
#             if not retrieved_docs_and_scores:
#                 print("RETRIEVER RETURNED ZERO DOCUMENTS. Index is not the issue, but no semantic match was found.")
#                 return [] 
            
#             retrieved_docs = []
#             for doc, score in retrieved_docs_and_scores:
#                 # Log score and snippet for debugging
#                 print(f"SCORE: {score:.4f} | ID: {doc.metadata.get('id', 'N/A')} | Content Snippet: {doc.page_content[:50]}...")
#                 retrieved_docs.append(doc)
            
#             print("---------------------------------------------------\n")
#             # --- DEBUG BLOCK END ---
            
#             context = self._format_context(retrieved_docs)
            
#             # 2. Generation: Ask LLM to explain matches
#             llm_output_text = self.rag_chain.invoke({"query": query, "context": context})
            
#             # --- Robust JSON Parsing ---
#             llm_output_text = llm_output_text.strip()
#             if llm_output_text.startswith('```json'):
#                 llm_output_text = llm_output_text[7:].strip()
#             if llm_output_text.endswith('```'):
#                 llm_output_text = llm_output_text[:-3].strip()

#             llm_output = json.loads(llm_output_text)
#             if not isinstance(llm_output, list):
#                 # If the LLM returns an object instead of an array (sometimes happens)
#                 if isinstance(llm_output, dict):
#                      llm_output = [llm_output]
#                 else:
#                     raise ValueError("LLM returned valid JSON but it was not an array of matches.")


#             # 3. Final Result Compilation
#             results = []
            
#             for match_explanation in llm_output:
#                 doc_id = match_explanation.get('csv_id')
#                 explanation = match_explanation.get('match_explanation', 'No explanation provided.')
                
#                 if not doc_id: continue

#                 # FIX APPLIED HERE: _get_full_record is now thread-safe
#                 full_record = self._get_full_record(doc_id)
                
#                 if not full_record: continue

#                 # Compile the final result structure for the frontend
#                 result = {
#                     "id": doc_id,
#                     "founder_name": full_record.get("founder_name", "N/A"),
#                     "role": full_record.get("role", "N/A"),
#                     "company": full_record.get("company", "N/A"),
#                     "location": full_record.get("location", "N/A"),
#                     "match_explanation": explanation,
#                     "provenance": {
#                         "matched_on_fields": full_record.get("search_fields", "multiple fields"),
#                         "csv_id": doc_id,
#                     },
#                     "full_details": {
#                         "idea": full_record.get("idea", "Not specified"),
#                         "about": full_record.get("about", "Not specified"),
#                         "keywords": full_record.get("keywords", "None listed"),
#                         "linked_in": full_record.get("linked_in", "#"),
#                         "notes": full_record.get("notes", ""),
#                         "stage": full_record.get("stage", "Unspecified"),
#                     }
#                 }
#                 results.append(result)
                
#             print(f"Successfully compiled {len(results)} final results.")
#             return results
            
#         except json.JSONDecodeError as je:
#             print(f"JSON Parsing Error: Could not parse LLM output. Raw Output: {llm_output_text}. Error: {je}")
#             raise Exception("The LLM did not return the expected JSON format. Try adjusting your query slightly.")
#         except Exception as e:
#             # Log the error but provide user-friendly message
#             print(f"Search error: {e}")
#             raise Exception("RAG search failed during retrieval or compilation.")

# # Global service instance
# rag_service = RAGService()



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
1. Identify the TOP 5 best matches based on the query
2. For location queries, PRIORITIZE profiles from the requested location
3. For skill/keyword queries, match on idea, about, keywords, and role fields
4. Generate a clear 1-2 sentence explanation for each match

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

    def _parse_location(self, query: str) -> Optional[str]:
        """Extract and normalize location from query."""
        lower_query = query.lower()
        
        # Check exact locations first
        for location in self.AVAILABLE_LOCATIONS:
            if location.lower() in lower_query:
                print(f"Location match: '{location}'")
                return location
        
        # Check aliases
        for alias, canonical in self.LOCATION_MAPPING.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', lower_query):
                print(f"Location alias match: '{alias}' -> '{canonical}'")
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

    def search(self, query: str) -> List[Dict]:  # Fixed return type
        """Perform RAG search and return matches."""
        if not self.is_initialized:
            raise Exception("RAG Service not initialized. Check logs.")
            
        try:
            # Parse location from query
            location_filter = self._parse_location(query)
            
            # Perform vector search (no pre-filtering, get more candidates)
            print(f"\n--- Searching for: '{query}' ---")
            retrieved_docs = self.vectorstore.similarity_search(query, k=TOP_K_DOCUMENTS)
            
            print(f"Retrieved {len(retrieved_docs)} documents from vector store")
            
            # If location specified, filter retrieved docs
            if location_filter:
                filtered_docs = [
                    doc for doc in retrieved_docs 
                    if doc.metadata.get('location') == location_filter
                ]
                print(f"Filtered to {len(filtered_docs)} docs matching location: {location_filter}")
                
                if not filtered_docs:
                    print(f"WARNING: No documents found for location '{location_filter}'")
                    # Fall back to all docs and let LLM explain
                    filtered_docs = retrieved_docs[:10]
                    
                retrieved_docs = filtered_docs
            
            if not retrieved_docs:
                return []
            
            # Format context for LLM
            context_json = json.dumps([
                {
                    "id": doc.metadata.get('id'),
                    "location": doc.metadata.get('location'),
                    "content": doc.page_content
                }
                for doc in retrieved_docs
            ], indent=2)
            
            # Get LLM rankings
            llm_output = self.rag_chain.invoke({
                "query": query,
                "context": context_json
            })
            
            # Parse LLM output
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
            
            # Compile final results
            results = []
            for match in llm_matches[:5]:  # Top 5
                doc_id = match.get('csv_id')
                if not doc_id:
                    continue
                
                full_record = self._get_full_record(doc_id)
                if not full_record:
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