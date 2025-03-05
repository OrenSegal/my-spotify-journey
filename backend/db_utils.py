import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

def has_method(obj, method_name):
    """Check if object has callable method"""
    return hasattr(obj, method_name) and callable(getattr(obj, method_name, None))

def create_empty_result():
    """Return a standard empty result"""
    return {"data": None, "columns": [], "is_empty": True}

def safe_execute_query(conn, query, params=None):
    """
    Safely execute a database query and handle errors consistently.
    
    Args:
        conn: Database connection object
        query: SQL query string
        params: Optional parameters for the query
        
    Returns:
        Dict containing query results or empty result on failure
    """
    try:
        if conn is None:
            logger.error("No database connection provided")
            return create_empty_result()
            
        result = conn.execute(query, params) if params else conn.execute(query)
        
        # Check if this is a DuckDB connection with fetchall method
        if has_method(result, "fetchall"):
            data = result.fetchall()
            columns = [desc[0] for desc in result.description] if result.description else []
            return {
                "data": data,
                "columns": columns,
                "is_empty": len(data) == 0
            }
        return create_empty_result()
        
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        logger.debug(traceback.format_exc())
        return create_empty_result()

def check_table_exists(conn, table_name):
    """
    Check if a table exists in the database.
    
    Args:
        conn: Database connection object
        table_name: Name of the table to check
        
    Returns:
        True if table exists, False otherwise
    """
    try:
        if conn is None:
            return False
            
        # Use DuckDB's information schema to check table existence
        query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = ?
        """
        result = safe_execute_query(conn, query, [table_name])
        return not result["is_empty"] and result["data"][0][0] > 0
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {e}")
        return False

def get_row_count(conn, table_name):
    """
    Get the number of rows in a table.
    
    Args:
        conn: Database connection object
        table_name: Name of the table
        
    Returns:
        Row count or 0 if error/empty
    """
    try:
        if conn is None or not check_table_exists(conn, table_name):
            return 0
            
        query = f"SELECT COUNT(*) FROM {table_name}"
        result = safe_execute_query(conn, query)
        
        if not result["is_empty"] and result["data"]:
            return result["data"][0][0]
        return 0
    except Exception as e:
        logger.error(f"Error getting row count for {table_name}: {e}")
        return 0
