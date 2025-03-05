"""Main Streamlit application for Spotify Streaming Journey."""
import streamlit as st
import polars as pl
import sys
import os
import logging
import traceback
import altair as alt
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('streamlit_app')

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    logger.info(f"Added {project_root} to sys.path")

# Set page config (must be the first Streamlit command)
st.set_page_config(
    page_title="Spotify Streaming Journey",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Import modules ---
try:
    from backend.db.duckdb_helper import get_connection, get_table_counts
    from dashboard.tabs import (
        render_overview_tab,
        render_llm_tab,
        render_artists_tab,
        render_albums_tab,
        render_tracks_tab,
        render_time_tab,
        render_genres_tab,
        render_release_tab,
        render_stats_tab,
        render_polars_ai_tab
    )
    from dashboard.components import render_database_info
    from dashboard.filters import shared_filters, build_sql_filter
except Exception as e:
    st.error(f"Failed to import modules: {e}")
    st.error(traceback.format_exc())
    st.stop()

def main():
    """Main function to run the Streamlit app."""
    try:
        # Ensure database connection is established
        conn = get_connection()
        if conn is None:
            st.error("Failed to connect to database. Please check the database configuration.")
            st.stop()
        
        st.title("🎵 Spotify Streaming Journey")
        st.write("Explore your Spotify listening history.")
        
        # Initialize filters and get table counts
        filters = shared_filters()
        sql_filter = build_sql_filter(filters)
        table_counts = get_table_counts()
        
        # Add database information to sidebar
        render_database_info(table_counts, sql_filter, filters)
        
        # Define tab names
        tab_names = [
            "Overview", "Ask the LLM", "PolarsAI", "Artists", "Albums", "Tracks", 
            "Time Analysis", "Genres", "Release Analysis", "Stats"
        ]
        
        # Create tabs - Streamlit's tabs are natively interactive
        tabs = st.tabs(tab_names)
        
        # Create a context dict to pass to all tabs
        context = {
            "filters": filters,
            "sql_filter": sql_filter,
            "table_counts": table_counts,
        }
        
        # Render content for all tabs - Streamlit will only show the active one
        with tabs[0]:
            render_overview_tab(context)
        with tabs[1]:
            render_llm_tab(context)
        with tabs[2]:
            render_polars_ai_tab(context)
        with tabs[3]:
            render_artists_tab(context)
        with tabs[4]:
            render_albums_tab(context)
        with tabs[5]:
            render_tracks_tab(context)
        with tabs[6]:
            render_time_tab(context)
        with tabs[7]:
            render_genres_tab(context)
        with tabs[8]:
            render_release_tab(context)
        with tabs[9]:
            render_stats_tab(context)
        
    except Exception as e:
        st.error(f"An error occurred while running the app: {e}")
        st.error(traceback.format_exc())
        logger.error(f"Application error: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Close any open connections
        if 'conn' in locals():
            try:
                conn.close()
                logger.info("Database connection closed")
            except:
                pass

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("Made with ❤️ | [GitHub](https://github.com/OrenSegal/spotify-streaming-journey)")

# Configure Altair to use VegaFusion for better performance with large datasets
alt.data_transformers.disable_max_rows()
try:
    import vegafusion
    alt.data_transformers.enable('vegafusion')
except ImportError:
    try:
        import altair_data_server
        alt.data_transformers.enable('data_server')
    except ImportError:
        st.warning("For better performance with large datasets, install vegafusion or altair_data_server")

if __name__ == "__main__":
    main()