"""Database utilities for the Spotify Streaming Journey dashboard."""
import polars as pl
import streamlit as st
from datetime import date, datetime
from typing import Dict, Any, Tuple, Optional
import logging

from backend.db.duckdb_helper import (
    get_db_connection,
    get_table_schema as get_db_table_schema,
    table_exists as db_table_exists,
    get_table_counts as get_db_table_counts,
    execute_query as db_execute_query,
    create_tables_if_needed as db_create_tables
)

logger = logging.getLogger(__name__)

@st.cache_data(ttl=3600)
def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> pl.DataFrame:
    """Execute a DuckDB query and return results as a Polars DataFrame."""
    return db_execute_query(query, params)

def get_date_range() -> Tuple[date, date]:
    """Get the earliest and latest dates from the streaming history."""
    try:
        with get_db_connection() as conn:
            query = "SELECT MIN(CAST(ts AS DATE)) as min_date, MAX(CAST(ts AS DATE)) as max_date FROM streaming_history"
            result = db_execute_query(query)
            if not result.is_empty():
                # Safely get the date values (handle both datetime and date objects)
                min_date_value = result['min_date'][0]
                max_date_value = result['max_date'][0]
                
                # Convert to date object if it's a datetime, or use as is if it's already a date
                min_date = min_date_value.date() if hasattr(min_date_value, 'date') else min_date_value
                max_date = max_date_value.date() if hasattr(max_date_value, 'date') else max_date_value
                
                # Provide default dates if None are retrieved (e.g., empty table)
                if min_date is None or max_date is None:
                    return date(2015, 1, 1), date.today()  # Default range
                return min_date, max_date
    except Exception as e:
        logger.error(f"Error getting date range: {e}")
        return date(2015, 1, 1), date.today()  # Fallback dates

def sanitize_sql_query(query: str) -> str:
    """Fix common SQL syntax issues like multiple WHERE clauses."""
    query = query.replace("WHERE AND", "WHERE")
    query = query.replace("WHERE WHERE", "WHERE") #in case of human error
    return query

@st.cache_data(ttl=3600)
def load_data(query: str) -> pl.DataFrame:
    """Load data from the database with caching."""
    try:
        result = db_execute_query(query)
        if result.is_empty():
            st.error("No data returned from query")
        return result
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"Error loading data: {e}")
        logger.error(f"Query: {query}")
        return pl.DataFrame()

def get_table_info(table_name: str) -> Dict[str, Any]:
    """Get basic information about a table."""
    try:
        schema = get_db_table_schema(table_name)
        counts = get_db_table_counts()
        
        return {
            "row_count": counts.get(f"{table_name}_count", 0),
            "schema": schema
        }
    except Exception as e:
        logger.error(f"Error getting table info for {table_name}: {e}")
        return {"row_count": 0, "schema": None}

def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    return db_table_exists(table_name)

@st.cache_data(ttl=3600)
def get_all_tables() -> Dict[str, Dict[str, Any]]:
    """Get information about all tables in the database."""
    try:
        with get_db_connection() as conn:
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'main'
            """
            result = db_execute_query(query)
            
            tables = {}
            if not result.is_empty():
                for table_name in result['table_name']:
                    tables[table_name] = get_table_info(table_name)
                    
            return tables
    except Exception as e:
        logger.error(f"Error getting all tables: {e}")
        return {}

@st.cache_data(ttl=3600)
def get_table_counts() -> Dict[str, int]:
    """Get row counts for main tables."""
    return get_db_table_counts()

@st.cache_data(ttl=3600)
def get_column_stats(table_name: str, column_name: str) -> Dict[str, Any]:
    """Get basic statistics for a numeric column."""
    try:
        query = f"""
            SELECT 
                MIN({column_name}) as min_value,
                MAX({column_name}) as max_value,
                AVG({column_name}) as avg_value,
                COUNT(*) as count,
                COUNT(DISTINCT {column_name}) as unique_count
            FROM {table_name}
            WHERE {column_name} IS NOT NULL
        """
        result = db_execute_query(query)
        
        if not result.is_empty():
            return {
                "min": result['min_value'][0],
                "max": result['max_value'][0],
                "avg": result['avg_value'][0],
                "count": result['count'][0],
                "unique_count": result['unique_count'][0]
            }
        return {}
    except Exception as e:
        logger.error(f"Error getting column stats for {table_name}.{column_name}: {e}")
        return {}

def validate_query(query: str) -> bool:
    """Basic validation of a SQL query to prevent injection."""
    # List of dangerous SQL keywords that could indicate an injection attempt
    dangerous_keywords = [
        "DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT",
        "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC"
    ]
    
    query_upper = query.upper()
    
    # Check for dangerous keywords
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            logger.warning(f"Dangerous keyword '{keyword}' found in query")
            return False
    
    # Basic structure validation
    if not query_upper.startswith("SELECT"):
        logger.warning("Query must start with SELECT")
        return False
    
    return True

def get_query_explain_plan(query: str) -> Optional[str]:
    """Get the explain plan for a query."""
    try:
        if not validate_query(query):
            return None
            
        explain_query = f"EXPLAIN {query}"
        result = db_execute_query(explain_query)
        
        if not result.is_empty():
            return "\n".join(result[result.columns[0]].to_list())
        return None
    except Exception as e:
        logger.error(f"Error getting explain plan: {e}")
        return None