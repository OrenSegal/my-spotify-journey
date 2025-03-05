import streamlit as st
import duckdb
import logging
from pathlib import Path
from dashboard.db_utils import get_db_path  # Correct import

logger = logging.getLogger('debug_utils')

def debug_database_connection():
    """Debug utility to check database connection and basic queries."""
    st.subheader("Database Connection Diagnostics")

    # Check DB path exists
    db_path = get_db_path()  # Use the function
    if db_path.exists():
        st.success(f"✅ Database file exists at: {db_path}")
        st.text(f"File size: {db_path.stat().st_size / (1024*1024):.2f} MB")
    else:
        st.error(f"❌ Database file not found at: {db_path}")
        return

    # Try direct connection (using context manager for safety)
    try:
        with duckdb.connect(str(db_path), read_only=True) as conn:
            st.success("✅ Database connection successful")

            # Check for tables
            tables_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
            """
            tables = conn.execute(tables_query).fetchall()

            if tables:
                st.success(f"✅ Found {len(tables)} tables:")
                table_names = [t[0] for t in tables]
                st.write(table_names)

                # Check each table has data
                for table in table_names:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    if count > 0:
                        st.success(f"✅ {table}: {count:,} rows")
                    else:
                        st.warning(f"⚠️ {table} is empty")
                        # If it's an important table, show table definition
                        if table in ["streaming_history", "track_metadata"]:
                            st.code(conn.execute(f"PRAGMA table_info({table});").fetchdf())
            else:
                st.error("❌ No tables found in database")

            # Try a simple query
            test_result = conn.execute("SELECT 1 as test").fetchone()
            if test_result and test_result[0] == 1:
                st.success("✅ Test query executed successfully")
            else:
                st.error("❌ Test query failed")

    except Exception as e:
        st.error(f"❌ Error connecting to database: {str(e)}")

    # Provide a sample dataset if empty
    if db_path.exists() and db_path.stat().st_size < 10000:  # If DB is too small
        st.warning("Database file seems too small or empty.")
        st.info("Try running the data import scripts to populate your database.")