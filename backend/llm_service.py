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

# --- Configuration (Paths made relative for robustness) ---
# Assuming 'data' directory is at the project root level
BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
CHROMA_DB_DIR = os.path.join(BASE_DIR, 'data', 'chroma_db')
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'data', 'people.sqlite')
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K_DOCUMENTS = 20  # Increased to get more candidates before filtering
RESULTS_LIMIT = 5

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
        "germany": "Berlin, Germany"
    }

    def __init__(self):
        self.retriever = None
        self.db = None
        
        # Initialize DB client 
        if os.path.exists(SQLITE_DB_PATH):
            self.db = sqlite_utils.Database(SQLITE_DB_PATH)
        else:
            print(f"⚠️  SQLite DB not found at {SQLITE_DB_PATH}. Will initialize without provenance lookup.")
            
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.0, 
            client=None, # LangChain handles the client
            # The API key is auto-loaded from environment variables (GEMINI_API_KEY)
        )
        self.embedding_model = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        
        # Initialize ChromaDB vector store
        if os.path.exists(CHROMA_DB_DIR):
            try:
                # This must use the same embedding function as used during indexing
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
    
    def _parse_query_for_filters(self, query: str) -> tuple[str, Optional[str], Optional[str]]:
        """Extracts location and stage filters from the query using regex."""
        location_filter = None
        stage_filter = None
        
        # Simple Location Extraction
        for alias, canonical_location in self.LOCATION_MAPPING.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', query, re.IGNORECASE):
                location_filter = canonical_location
                break
        
        # Simple Stage Extraction
        for stage in ["none", "pre-seed", "seed", "series a", "growth"]:
            if re.search(r'\b' + re.escape(stage) + r'\b', query, re.IGNORECASE):
                stage_filter = stage
                break

        # Remove filters from query to clean it up for the vector search
        if location_filter:
            query = re.sub(r'\b(' + '|'.join(self.LOCATION_MAPPING.keys()) + r')\b', '', query, flags=re.IGNORECASE)
        if stage_filter:
            query = re.sub(r'\b' + re.escape(stage_filter) + r'\b', '', query, flags=re.IGNORECASE)
            
        return query.strip(), location_filter, stage_filter

    def _get_full_record_from_db(self, doc_id: str) -> Optional[Dict]:
        """Looks up the full data for a person by their ID in the SQLite DB."""
        if self.db and "people" in self.db.table_names():
            # sqlite-utils automatically caches table names, so this is fine
            return self.db["people"].get(doc_id)
        return None

    def search(self, query: str) -> List[Dict]:
        """Performs RAG search with post-retrieval filtering and LLM re-ranking."""
        if self.retriever is None:
            raise Exception("RAG service is not initialized. Index files are missing or corrupted.")

        # 1. Parse the query for filters
        cleaned_query, location_filter, stage_filter = self._parse_query_for_filters(query)
        print(f"Filters extracted: Location='{location_filter}', Stage='{stage_filter}'")
        print(f"Cleaned query for RAG: '{cleaned_query}'")

        # 2. Retrieve relevant documents (candidates)
        # Pass the original query to the retriever for vector similarity
        initial_matches: List[Document] = self.retriever.invoke(cleaned_query)
        print(f"Retrieved {len(initial_matches)} candidate documents from ChromaDB.")
        
        if not initial_matches:
            return []

        # 3. Build the prompt for the LLM re-ranking/analysis
        context = ""
        candidate_ids = []
        for i, doc in enumerate(initial_matches):
            doc_id = doc.metadata.get("id")
            # Filter candidates *before* passing to the LLM to save tokens
            if location_filter and doc.metadata.get('location') != location_filter:
                continue
            if stage_filter and doc.metadata.get('stage') != stage_filter:
                continue
                
            candidate_ids.append(doc_id)
            context += f"--- CANDIDATE {i+1} ---\nID: {doc_id}\n{doc.page_content}\n"
        
        if not candidate_ids:
            print("No candidates remained after filter application.")
            return []

        # 4. LLM Call for re-ranking and explanation
        template = """
        You are an expert matchmaking assistant. Your goal is to analyze the provided founder profiles (CONTEXT) and the user's SEARCH QUERY to identify the TOP {limit} most relevant matches.

        **CRITERIA:**
        1. Relevance to the SEARCH QUERY.
        2. Provide a short, concise **match_explanation** for why each profile is a good fit.

        **SEARCH QUERY:** {query}

        **CONTEXT (Founders):**
        {context}

        **RESPONSE FORMAT:**
        Return a JSON list of objects. DO NOT include any other text, reasoning, or markdown (e.g., ```json). The list must only contain the profiles you select.
        Example response for a query matching founder A and founder B:
        [
            {{"id": "A_ID", "match_explanation": "Brief reason for matching founder A."}},
            {{"id": "B_ID", "match_explanation": "Brief reason for matching founder B."}}
        ]
        
        Select the top {limit} matches based on the query.
        """
        
        prompt = ChatPromptTemplate.from_template(template).partial(
            context=context,
            query=cleaned_query,
            limit=RESULTS_LIMIT
        )

        chain = prompt | self.llm | StrOutputParser()
        
        try:
            # LLM generates a JSON string of the top matches
            llm_response_text = chain.invoke({})
        except Exception as e:
            raise Exception(f"LLM generation failed: {e}")

        # 5. Final Result Compilation
        results: List[Dict] = []
        try:
            # Attempt to clean and parse the LLM's JSON response
            # Remove any leading/trailing markdown code blocks
            llm_response_text = re.sub(r'```json\s*|```\s*', '', llm_response_text, flags=re.IGNORECASE).strip()
            
            llm_matches = json.loads(llm_response_text)
            
            if not isinstance(llm_matches, list):
                raise ValueError("LLM response was not a JSON list.")

            for match in llm_matches[:RESULTS_LIMIT]:
                doc_id = match.get("id")
                if not doc_id:
                    continue
                
                full_record = self._get_full_record_from_db(doc_id)
                if not full_record:
                    # Skip if the full record can't be found (DB lookup failed)
                    continue 

                # This is the final result object returned by the API
                result = {
                    "id": doc_id,
                    "founder_name": full_record.get("founder_name", "N/A"),
                    "role": full_record.get("role", "N/A"),
                    "company": full_record.get("company", "N/A"),
                    "location": full_record.get("location", "N/A"),
                    "match_explanation": match.get("match_explanation", "Match found based on LLM analysis."),
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
            
        except json.JSONDecodeError:
             print(f"LLM response was not valid JSON: {llm_response_text[:100]}...")
             raise Exception(f"RAG search failed: LLM output format error.")
        except Exception as e:
            print(f"Search error: {e}")
            raise Exception(f"RAG search failed: {e}")

rag_service = RAGService()