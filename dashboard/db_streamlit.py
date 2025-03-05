import streamlit as st
import duckdb
import logging
from dashboard.db_utils import get_db_path, create_tables_if_needed  # Import from db_utils

logger = logging.getLogger('db_streamlit')

@st.cache_resource(ttl=None)  # Cache the connection, never expiring
def get_streamlit_connection(read_only=True):
    """Get a database connection specifically for Streamlit caching."""
    db_path = str(get_db_path())  # Ensure it's a string
    logger.info(f"Getting {'read-only' if read_only else 'writable'} connection to {db_path}")

    try:
        conn = duckdb.connect(db_path, read_only=read_only)
        # Quick test to make sure the connection works and tables are there.
        conn.execute("SELECT 1").fetchone()
        logger.info("Database connection successful")

        #Ensure tables exist
        if not read_only:
          create_tables_if_needed(conn)
        return conn

    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        return None # Don't raise, return None for Streamlit to handle