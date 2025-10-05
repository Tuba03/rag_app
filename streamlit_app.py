# streamlit_app.py 
import streamlit as st
import sys
import os
import subprocess
import time # Import time for a small pause after setup

# --- PATH SETUP (Ensures module imports and subprocess calls are robust) ---
# Set project root to the directory containing this file
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')

# Add the project root to sys.path for module imports (e.g., from backend.llm_service)
if APP_ROOT not in sys.path:
    sys.path.append(APP_ROOT)
    
# --- Data Generation/Indexing Helper ---
def ensure_data_exists():
    """Checks for the ChromaDB index and runs the generation/indexing scripts if missing."""
    chroma_db_path = os.path.join(DATA_DIR, 'chroma_db')
    
    if not os.path.exists(chroma_db_path):
        st.info("🔎 **First-time setup:** Generating data and building vector index. This may take a minute.")
        
        try:
            st.text("1/2 Running data_generator.py...")
            
            # USE ABSOLUTE PATHS and cwd=APP_ROOT for robustness
            data_generator_path = os.path.join(APP_ROOT, 'data_generator.py')
            subprocess.run([sys.executable, data_generator_path], check=True, cwd=APP_ROOT, capture_output=True, text=True)

            st.text("2/2 Running indexing.py to build ChromaDB...")
            indexing_path = os.path.join(APP_ROOT, 'indexing.py')
            subprocess.run([sys.executable, indexing_path], check=True, cwd=APP_ROOT, capture_output=True, text=True)

            st.success("✅ Data and Vector Index are ready!")
            time.sleep(1) # Wait briefly before rerunning
            st.rerun() # Rerun the script to load the newly created index
            
        except subprocess.CalledProcessError as e:
            st.error(f"❌ **Data Setup Failed!** Check console logs for errors in `data_generator.py` or `indexing.py`.")
            st.exception(e.stdout + e.stderr)
            st.stop()
        except FileNotFoundError:
            st.error("❌ **Data Setup Failed!** Make sure `data_generator.py` and `indexing.py` are in the project root.")
            st.stop()

# Check and set up data pipeline before importing the service
ensure_data_exists()

# --- Import RAG Service (It will auto-load the index now) ---
from backend.llm_service import rag_service, RAGService 
    
# --- CRITICAL FIX: Session State Initialization (MUST run before any callbacks) ---
def initialize_session_state():
    """Initializes all necessary session state variables to prevent KeyErrors."""
    if 'query_input_value' not in st.session_state:
        st.session_state['query_input_value'] = ""
    if 'search_input_key_counter' not in st.session_state:
        st.session_state['search_input_key_counter'] = 0 
    if 'has_searched' not in st.session_state:
        st.session_state['has_searched'] = False
    if 'last_query' not in st.session_state:
        st.session_state['last_query'] = ""
    if 'matches' not in st.session_state:
        st.session_state['matches'] = []
    if 'error' not in st.session_state:
        st.session_state['error'] = None

initialize_session_state()

# --- UI Components ---
def render_result_card(match: dict):
    """Renders a single matched founder profile."""
    col1, col2 = st.columns([1, 4])
    
    with col1:
        # Simple placeholder/initials image
        initials = "".join([n[0] for n in match['founder_name'].split()]).upper()
        st.markdown(f"<div style='border-radius: 50%; width: 60px; height: 60px; background-color: #f0f2f6; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold;'>{initials}</div>", unsafe_allow_html=True)
        st.markdown(f"[LinkedIn]({match['full_details']['linked_in']})")
    
    with col2:
        st.markdown(f"#### **{match['founder_name']}** ({match['role']})")
        st.markdown(f"**{match['company']}** | *{match['location']}* | Stage: {match['full_details']['stage'].title()}")
        st.markdown(f"**Match Rationale:** *{match['match_explanation']}*")
        
        with st.expander("Full Profile Details"):
            st.markdown(f"**Idea:** {match['full_details']['idea']}")
            st.markdown(f"**About:** {match['full_details']['about']}")
            st.markdown(f"**Keywords:** {match['full_details']['keywords']}")
            if match['full_details']['notes']:
                 st.markdown(f"**Notes:** {match['full_details']['notes']}")
        
    st.divider()

# --- Main App Logic ---
st.set_page_config(layout="wide", page_title="RAG Founder Matchmaker")
st.title("💡 RAG Founder Matchmaker (Gemini + ChromaDB)")
st.caption("Enter a detailed search query to find founders based on their profile, idea, and location/stage filters.")


def perform_search_on_click(query: str):
    """Callback function for quick queries."""
    st.session_state['query_input_value'] = query
    st.session_state['search_input_key_counter'] += 1 # Force rerun of the main search widget
    st.session_state['has_searched'] = False # Reset search state to trigger search in main body

# Quick Query buttons
st.markdown("##### Quick Queries:")
col = st.columns(3)
col[0].button("AI founder in San Francisco, seed stage", on_click=perform_search_on_click, args=("I need a seed-stage AI founder in San Francisco.",), use_container_width=True)
col[1].button("Healthtech founder in London", on_click=perform_search_on_click, args=("Looking for a healthtech co-founder in London.",), use_container_width=True)
col[2].button("Fintech co-founder with blockchain experience", on_click=perform_search_on_click, args=("Fintech co-founder with deep blockchain experience.",), use_container_width=True)

# Main Search Input
query = st.text_input(
    "Enter your search query:",
    value=st.session_state['query_input_value'],
    key=f"search_input_{st.session_state['search_input_key_counter']}",
    on_change=lambda: st.session_state.update(has_searched=False, query_input_value=st.session_state[f"search_input_{st.session_state['search_input_key_counter']}"]),
    placeholder="e.g., A founder with a background in devtools and SaaS, located in Berlin."
)

if st.button("Search Founders", use_container_width=True) or st.session_state.get('has_searched') is False and query and st.session_state.get('last_query') != query:
    if query:
        with st.spinner(f"Searching for **{query}**..."):
            try:
                # The search service is ready because ensure_rag_data_is_ready ran successfully
                matches = rag_service.search(query)
                st.session_state['matches'] = matches
                st.session_state['has_searched'] = True
                st.session_state['last_query'] = query 
                st.session_state['error'] = None
            except Exception as e:
                st.session_state['error'] = str(e)
                st.session_state['matches'] = []
                st.session_state['has_searched'] = True
    else:
        st.warning("Please enter a query.")

# --- Display Results ---
if st.session_state.get('error'):
    st.error(f"❌ **Error:** {st.session_state['error']}")

elif st.session_state.get('has_searched'):
    matches = st.session_state.get('matches', [])
    query_text = st.session_state.get('last_query', '')
    
    if matches:
        st.success(f"✅ **Found {len(matches)} match{'es' if len(matches) != 1 else ''} for \"{query_text}\"**")
        
        st.subheader(f"Top {len(matches)} Match{'es' if len(matches) != 1 else ''}")
        st.divider()
        
        for match in matches:
            render_result_card(match)
    else:
        st.warning(f"⚠️ No matches found for \"{query_text}\"")
else:
    st.info("💡 Enter your detailed search query above or click a quick query to find founder matches.")