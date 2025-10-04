# streamlit_app.py - Final Streamlit-Native Version with Maximized Readability
import streamlit as st
import sys
import os

# --- PATH SETUP (Keep as is) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
try:
    from llm_service import rag_service, RAGService  
except ImportError:
    try:
        sys.path.append(os.path.join(current_dir, 'backend'))
        from llm_service import rag_service, RAGService
    except ImportError as e:
        st.error(f"Could not find RAGService. Please ensure llm_service.py is accessible. Details: {e}")
        st.stop()
    
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
/* This is a stable Streamlit workaround */
.streamlit-expanderHeader {
    font-size: 1.15rem !important; /* Increase font size */
    font-weight: 600 !important;   /* Make it semi-bold */
    color: #2563eb !important;     /* Apply blue color */
}
</style>
""", unsafe_allow_html=True)


def render_result_card(match):
    """
    Renders a single match using ONLY native Streamlit components, 
    with maximized font sizes for better readability.
    """
    
    # Use st.container(border=True) for the card structure.
    with st.container(border=True): 
        
        # --- Header Section ---
        col1, col2 = st.columns([3, 1])
        with col1:
            st.header(match['founder_name'])
        with col2:
            # Use st.subheader for Role to ensure a large font
            st.subheader(f":blue[{match['role']}]") 

        # Company and Location - Use H5 equivalent (Markdown) for better size
        st.markdown(f"##### **{match['company']}** • _{match['location']}_")
        st.divider() 
        
        # --- Match Reason (Highlighted) ---
        # st.info is used for clean visual highlighting
        st.info(f"**🎯 Match Reason:** {match['match_explanation']}")

        # --- Idea & About ---
        
        # IDEA Label: Use st.subheader for a prominent label size
        st.subheader("💡 Idea")
        # IDEA Content: Use H4 equivalent for descriptive text size
        st.markdown(f"#### {match['full_details']['idea']}") 
        
        st.markdown("---") 
        
        # ABOUT Label: Use st.subheader for a prominent label size
        st.subheader("👤 About")
        # ABOUT Content: Use H4 equivalent for descriptive text size
        st.markdown(f"#### {match['full_details']['about']}")

        # --- Expandable Full Details (Native Expander with custom styling via CSS) ---
        # The CSS above ensures this header is large and prominent
        with st.expander("📋 Show Full Details"):
            colA, colB = st.columns(2)
            
            # Metadata uses standard markdown (default size)
            with colA:
                st.markdown(f"**Keywords:** {match['full_details']['keywords']}")
                st.markdown(f"**Stage:** {match['full_details']['stage']}")
                
            with colB:
                st.markdown(f"[🔗 LinkedIn Profile]({match['full_details']['linked_in']})")
                
            if match['full_details']['notes']:
                st.success(f"**📝 Notes:** {match['full_details']['notes']}")

    # Add a small gap between cards
    st.markdown("##") # Use a small heading for a clean vertical spacing


def main_streamlit_app():
    """Main function for the Streamlit application."""

    # Header
    st.title("RAG Startup Matchmaker 🚀")
    st.markdown("Find the perfect founder match using natural language search.")
    st.divider()

    # Check for initialization
    if not rag_service.is_initialized:
        st.error("⚠️ RAG Service initialization failed. Please check your configuration.")
        return

    # Search interface
    col1, col2 = st.columns([5, 1])
    
    with col1:
        query = st.text_input(
            "Search",
            placeholder="e.g., 'seed stage founder in AI/ML based in San Francisco'",
            label_visibility="collapsed",
            key="search_input"
        )
    
    with col2:
        search_clicked = st.button("Search", use_container_width=True, type="primary")

    # Handle search
    if search_clicked and query:
        with st.spinner("Searching..."):
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

    # Display results
    st.markdown("<br>") 
    
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
        st.info("💡 Enter a search query above to find founder matches")


if __name__ == "__main__":
    if 'has_searched' not in st.session_state:
        st.session_state['has_searched'] = False
    
    if rag_service:
        main_streamlit_app()
    else:
        st.error("Failed to initialize RAG Service")