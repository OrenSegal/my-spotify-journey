import streamlit as st
import asyncio
import logging
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
import altair as alt
from backend.llm.chains import SpotifyAnalysisChain  # Corrected import
from backend.db.duckdb_helper import get_db_connection
from dashboard.components import create_error_message, create_info_message

# Configure logging
logger = logging.getLogger("llm_insights")

load_dotenv()
# --- Helper Functions ---
async def process_user_query(question: str, chain: SpotifyAnalysisChain) -> Optional[Dict[str, Any]]:
    """Process a user query using the LLM chain."""
    try:
        # Define database schema for the LLM
        schema = """
        CREATE TABLE streaming_history (
            ts TIMESTAMP,
            platform VARCHAR,
            ms_played INTEGER,
            track VARCHAR,
            artist VARCHAR,
            album VARCHAR,
            spotify_track_uri VARCHAR,
            reason_start VARCHAR,
            reason_end VARCHAR,
            skipped BOOLEAN,
            conn_country VARCHAR
        );
        
        CREATE TABLE track_metadata (
            spotify_track_uri VARCHAR PRIMARY KEY,
            track VARCHAR,
            artist VARCHAR,
            track_popularity INTEGER,
            album_release_date DATE,
            album VARCHAR,
            duration_ms INTEGER,
            explicit BOOLEAN,
            album_type VARCHAR,
            total_tracks INTEGER,
            genres VARCHAR,
            artist_popularity INTEGER,
            artist_uri VARCHAR,
            artist_followers INTEGER
        );
        """
        
        # Call analyze with the required schema parameter
        response = await chain.analyze(question, schema=schema)
        return response.model_dump()  # Convert Pydantic model to dict
    except Exception as e:
        logger.error(f"Error processing user query: {e}")
        return None

# --- Main Rendering Function ---

def render_llm_insights_tab():
    """Render the LLM Insights tab in Streamlit."""
    st.title("💡 AI Insights")
    st.write("Ask questions about your Spotify listening history and get AI-powered insights, including visualizations.")

    # Initialize session state for question input
    if "llm_question" not in st.session_state:
        st.session_state.llm_question = ""

    # Input for user question with session state persistence
    question = st.text_input(
        "Ask a question about your Spotify data",
        value=st.session_state.llm_question,
        placeholder="Example: What are my top 5 artists in the last month?",
        key="llm_question_input"  # Unique key for the input
    )
    #capture question
    st.session_state.llm_question = question
    # --- LLM Chain Initialization (cached) ---
    conn = get_db_connection()
    if not conn:
        create_error_message("Could not connect to the database.")
        st.stop()

    @st.cache_resource(show_spinner=False)
    def get_llm_chain():
        logger.info("Initializing SpotifyAnalysisChain...")
        api_key = os.getenv("LLM_API_KEY")
        model_name = os.getenv("LLM_MODEL")
        
        if not api_key:
            raise ValueError("LLM_API_KEY environment variable not set.")
            
        return SpotifyAnalysisChain(api_key=api_key, model_name=model_name)

    chain = get_llm_chain()

    col1, col2 = st.columns([1,5])
    with col1:
      generate_button = st.button("Generate Insights", use_container_width=True)
    with col2:
      # Example questions as buttons
      # Example questions as buttons (using st.columns for layout)
      ex_col1, ex_col2, ex_col3 = st.columns(3)
      with ex_col1:
          if st.button("Top 5 artists?"):
              st.session_state.llm_question = "What are my top 5 artists of all time?"
              st.rerun()
      with ex_col2:
        if st.button("Listening patterns?"):
          st.session_state.llm_question = "What time of the day I listen to music the most"
          st.rerun()
      with ex_col3:
          if st.button("Genre diversity?"):
            st.session_state.llm_question = "Show my listening patterns by genre"
            st.rerun()
    if generate_button:
        if not question:
            st.warning("Please enter a question.")
            return

        with st.spinner("Analyzing your question and generating insights..."):
            # Use asyncio.run to call the async function
            response = asyncio.run(process_user_query(question, chain))

            if response:
                if response["type"] == "error":
                    create_error_message(f"LLM Error: {response['content']}")
                elif response["type"] == "text":
                    st.markdown(f"**Answer:**\n\n{response['content']}")
                elif response["type"] == "visualization":
                    if response["data"]:

                        st.subheader("Visualization")
                        try:
                            chart = alt.Chart.from_dict(response["content"])
                            st.altair_chart(chart, use_container_width=True)

                            #Raw data
                            with st.expander("Show Raw Data"):
                              st.dataframe(response["data"])

                        except Exception as e:
                            st.error("Error rendering the generated chart")

                    else:
                        create_info_message("The LLM could not generate a visualization for your query.")
                with st.expander("SQL Query"):
                  st.code(response["sql"], language="sql") #Show SQL

            else:
                create_error_message("An unexpected error occurred.")