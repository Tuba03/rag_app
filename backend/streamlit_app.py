# streamlit_app.py
import streamlit as st
import pandas as pd
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
# Add the current directory (which contains llm_service.py) to the Python path
if current_dir not in sys.path:
    sys.path.append(current_dir)
    print(f"Added {current_dir} to sys.path for import.")
    
# Attempt the import with the modified path
try:
    # This assumes llm_service.py is in the same directory as streamlit_app.py
    from llm_service import rag_service, RAGService  
except ImportError as e:
    # If it still fails, check a common subdirectory structure
    try:
        sys.path.append(os.path.join(current_dir, 'src'))
        from backend.llm_service import rag_service, RAGService
    except ImportError:
        st.error(f"Could not find RAGService. Please ensure llm_service.py is accessible. Details: {e}")
        st.stop()
    
# --- Streamlit UI Components ---

def render_result_card(match):
    """Renders a single match using Streamlit columns and containers."""
    
    st.markdown(
        f"""
        <div style="background-color: #ffffff; padding: 20px; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-left: 5px solid #3b82f6;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="color: #1e3a8a; margin: 0; font-size: 1.5rem; font-weight: 800;">
                    {match['founder_name']}
                </h3>
                <span style="background-color: #8b5cf6; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    {match['role']}
                </span>
            </div>
            
            <p style="color: #4b5563; margin-top: 5px; font-size: 1rem;">
                <strong>{match['company']}</strong> in {match['location']}
            </p>
            
            <div style="background-color: #f0f9ff; padding: 12px; border-radius: 8px; margin: 15px 0;">
                <strong style="color: #1d4ed8;">💡 Match Explanation:</strong> 
                <span style="font-style: italic; color: #374151;">{match['match_explanation']}</span>
            </div>
            
            <details>
                <summary style="font-weight: bold; color: #1e3a8a; cursor: pointer; margin-top: 10px; padding: 5px 0;">
                    View Full Profile Details
                </summary>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #e5e7eb; font-size: 0.9rem;">
                    <p><strong>Stage:</strong> <span style="color:#059669; font-weight:600;">{match['full_details']['stage']}</span></p>
                    <p><strong>Idea:</strong> {match['full_details']['idea']}</p>
                    <p><strong>Bio:</strong> {match['full_details']['about']}</p>
                    <p><strong>Keywords:</strong> {match['full_details']['keywords']}</p>
                    <p><strong>LinkedIn:</strong> <a href="{match['full_details']['linked_in']}" target="_blank" style="color: #3b82f6;">View Profile</a></p>
                    {match['full_details']['notes'] and f"<p style='color: #ef4444; font-style: italic;'><strong>Notes:</strong> {match['full_details']['notes']}</p>"}
                </div>
            </details>
            
            <p style="text-align: right; color: #9ca3af; font-size: 0.75rem; margin-top: 10px;">
                Matched on: {match['provenance']['matched_on_fields']} | ID: {match['id'][:8]}...
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


def main_streamlit_app():
    """Main function for the Streamlit application."""
    st.set_page_config(
        page_title="RAG Founder Matchmaker 🚀",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.title("RAG Founder Matchmaker 🚀")
    st.markdown("Find the perfect founder match using **natural language search** in a database powered by **RAG** (Retrieval-Augmented Generation).")
    st.markdown("---")

    # Check for initialization status
    if not rag_service.is_initialized:
        st.error(
            f"**RAG Service Initialization Failed!** Please check the following:\n\n"
            f"1. **GEMINI_API_KEY** is set in `.streamlit/secrets.toml`.\n"
            f"2. Data files (`data/people.sqlite`, `data/chroma_db`) exist. Run your setup script.\n"
            f"3. Dependency conflicts in `requirements.txt` are resolved."
        )
        return

    # User Query Input
    query = st.text_input(
        "Enter your search criteria:",
        placeholder="E.g., Find me a seed-stage founder with expertise in cleantech and robotics.",
        key="founder_query"
    )

    search_button = st.button("Find Matches", type="primary")

    if search_button and query:
        with st.spinner(f"Searching for matches for: **{query}**..."):
            try:
                # Call the RAG service search method
                matches = rag_service.search(query)
                st.session_state['matches'] = matches
                st.session_state['has_searched'] = True
                st.session_state['last_query'] = query
                
            except Exception as e:
                st.error(f"Search Error: {e}")
                st.session_state['matches'] = []
                st.session_state['has_searched'] = True
    
    # Display Results
    if st.session_state.get('has_searched'):
        matches = st.session_state.get('matches', [])
        last_query = st.session_state.get('last_query', "")
        
        if matches:
            st.success(f"**Found {len(matches)} match(es) for '{last_query}'!**")
            
            # Use a container for the results
            results_container = st.container()
            with results_container:
                for match in matches:
                    render_result_card(match)
        else:
            st.warning(f"No matches found for **'{last_query}'**. Please try a different query.")
    
    elif not st.session_state.get('has_searched'):
        st.info("Type your query above and click 'Find Matches' to start searching.")

if __name__ == "__main__":
    # Ensure RAGService is initialized
    if rag_service:
        main_streamlit_app()
    else:
        st.error("Failed to initialize RAG Service globally.")