# streamlit_app.py 
import streamlit as st
import sys
import os

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
try:
    from backend.llm_service import rag_service, RAGService  
except ImportError:
    try:
        sys.path.append(os.path.join(current_dir, 'backend'))
        from backend.llm_service import rag_service, RAGService
    except ImportError as e:
        st.error(f"Could not find RAGService. Please ensure llm_service.py is accessible. Details: {e}")
        st.stop()
    

# --- CRITICAL FIX: Session State Initialization (MUST run before any callbacks) ---
def initialize_session_state():
    """Initializes all necessary session state variables to prevent KeyErrors."""
    # Ensure all keys used in the main app body or callbacks are present
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

initialize_session_state() # <--- CALL THE INITIALIZER IMMEDIATELY AT TOP LEVEL

# --- Streamlit Configuration and Global Styling ---
st.set_page_config(
    page_title="RAG Startup Matchmaker 🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide footer and main menu for a clean look
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}

/* Custom CSS to increase the size of the Expander header text only */
.streamlit-expanderHeader {
    font-size: 1.15rem !important; /* Increase font size */
    font-weight: 600 !important;   /* Make it semi-bold */
    color: #2563eb !important;     /* Apply blue color */
}
</style>
""", unsafe_allow_html=True)


def set_query_value_and_key(query):
    """Sets the query state and forces the text input to re-render with the new value."""
    # This callback now safely accesses st.session_state because it was initialized above.
    st.session_state['query_input_value'] = query
    st.session_state['has_searched'] = False
    
    # This line now safely increments the key
    st.session_state['search_input_key_counter'] += 1 

# --- Homepage Guide and Quick-Query Buttons ---

def render_homepage_guide():
    """Renders the main title, description, and clickable query suggestions."""
    
    st.title("RAG Startup Matchmaker 🚀")
    
    st.markdown(
        """
        Welcome! This application uses **Retrieval-Augmented Generation (RAG)**
        to help you find potential co-founders or investors based on their profile data.
        Enter a query describing the ideal match, and the Gemini LLM will summarize the results.
        """
    )
    st.divider()

    st.subheader("💡 Try a Quick Query:")
    
    # Define example queries
    example_queries = [
        "Fintech co-founder with blockchain experience in London",
        "Who is the seed stage founder in Berlin working on e-commerce?",
        "Find a healthtech engineer who uses AI/ML for optimization",
    ]
    
    # Used columns to lay out the buttons horizontally
    cols = st.columns(len(example_queries))
    
    for i, query in enumerate(example_queries):
        # Pass the query to the callback function
        cols[i].button(
            query, 
            key=f"quick_btn_{i}", 
            use_container_width=True,
            on_click=set_query_value_and_key, # Used the state update and key change callback
            args=(query,) # Pass the query as an argument
        )
    st.divider()


def render_result_card(match):
    """
    Renders a single match using ONLY native Streamlit components, 
    with maximized font sizes for better readability.
    """
    
    with st.container(border=True): 
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.header(match['founder_name'])
        with col2:
            st.subheader(f":blue[{match['role']}]") 

        st.markdown(f"##### **{match['company']}** • _{match['location']}_")
        st.divider() 
        
        st.info(f"**🎯 Match Reason:** {match['match_explanation']}")

        st.subheader("💡 Idea")
        st.markdown(f"#### {match['full_details']['idea']}") 
        
        st.markdown("---") 
        
        st.subheader("👤 About")
        st.markdown(f"#### {match['full_details']['about']}")

        with st.expander("📋 Show Full Details"):
            colA, colB = st.columns(2)
            
            with colA:
                st.markdown(f"**Keywords:** {match['full_details']['keywords']}")
                st.markdown(f"**Stage:** {match['full_details']['stage']}")
                
            with colB:
                st.markdown(f"[🔗 LinkedIn Profile]({match['full_details']['linked_in']})")
                
            if match['full_details']['notes']:
                st.success(f"**📝 Notes:** {match['full_details']['notes']}")

    st.markdown("##") 


def main_streamlit_app():
    """Main function for the Streamlit application."""

    # 1. Initialization and Guide
    render_homepage_guide()

    # The is_initialized flag is a more robust way to check for RAG service status
    # Assuming RAGService has an 'is_initialized' attribute updated in __init__
    if not rag_service.is_initialized: 
        st.error("⚠️ RAG Service initialization failed. This usually means the data (Chroma index) could not load. Please run 'python indexing.py' and check the console logs for the NumPy error.")
        return

    # 2. Search Interface
    col1, col2 = st.columns([5, 1])
    
    with col1:
        # The text input's key is dynamic, forcing it to update on callback
        query = st.text_input(
            "Search",
            # Ensure value is pulled from session state, which is now guaranteed to exist
            value=st.session_state['query_input_value'], 
            placeholder="e.g., 'seed stage founder in AI/ML based in San Francisco'",
            label_visibility="collapsed",
            # CRITICAL FIX: The key changes when the button callback runs
            key=f"search_input_{st.session_state['search_input_key_counter']}"
        )
    
    with col2:
        search_clicked = st.button("Search", use_container_width=True, type="primary")

    # --- Handle Search Logic ---
    
    # 3. Determine if a search should run
    # This logic remains robust: run if the button is clicked OR if the query value 
    # is different from the last successfully searched query.
    should_run_search = search_clicked or (st.session_state['query_input_value'] != st.session_state.get('last_query', '') and query)
    
    if should_run_search and query:
        
        # 4. Finalize the state and run the search
        st.session_state['query_input_value'] = query 
            
        with st.spinner(f"Searching for **{query}**..."):
            try:
                matches = rag_service.search(query)
                st.session_state['matches'] = matches
                st.session_state['has_searched'] = True
                st.session_state['last_query'] = query 
                st.session_state['error'] = None
            except Exception as e:
                st.session_state['error'] = str(e)
                st.session_state['matches'] = []
                st.session_state['has_searched'] = True
    
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


if __name__ == "__main__":
    # Initialization is handled above by initialize_session_state()
    main_streamlit_app()