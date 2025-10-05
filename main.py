# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.llm_service import rag_service
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. FastAPI App Initialization
app = FastAPI(title="RAG Matchmaking API", version="1.0.0")

# 2. CORS (Crucial for React Frontend Communication)
origins = [
    "*", # In development, allow all. In production, restrict to your frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Request/Response Schemas
class QueryRequest(BaseModel):
    query: str

# FIX: Ensure RAG Service is fully initialized before serving requests.
@app.on_event("startup")
def startup_event():
    # Because rag_service is imported globally, its __init__ runs on import.
    # This check ensures we see the initialization message in the logs.
    if rag_service.retriever is None:
        # Re-initialize or log error if init failed (e.g., if index wasn't built)
        # For simplicity, we rely on the error message inside RAGService.__init__
        pass

# 4. API Endpoint
@app.post("/api/v1/search")
async def search_people(request: QueryRequest):
    """
    Accepts a natural language query and returns the top 5 RAG-matched people.
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        results = rag_service.search(request.query)
        return {"query": request.query, "matches": results}
    except Exception as e:
        # Log the detailed error on the server side
        print(f"Error during RAG search: {e}") 
        # Return a generic error to the client
        raise HTTPException(status_code=500, detail=f"Internal RAG search error: {e}")

# 5. Health Check
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "RAG API"}
