"""Database helper functions for DuckDB integration."""
import os
import logging
import traceback
import duckdb
import polars as pl
import platform
import subprocess
import time
import random
from pathlib import Path
from typing import Dict, Callable, Union, Optional, List, Any, Tuple
from contextlib import contextmanager
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db')

# Load environment variables
load_dotenv()

# Constants for connection management
MAX_RETRIES = 5
BASE_RETRY_DELAY = 1.0
LOCK_TIMEOUT = 60  # seconds

def get_db_path() -> str:
    """Get the path to the DuckDB database file."""
    # Get project root directory - works regardless of where it's called from
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Use the DB_PATH from environment variable, or fallback to default
    db_path = os.getenv("DB_PATH", "data/spotify_streaming.duckdb")
    
    # Resolve the full path
    full_path = project_root / db_path
    
    # Ensure parent directory exists
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Database path resolved to: {full_path}")
    return str(full_path)

def detect_db_locks() -> List[Dict[str, str]]:
    """Detect processes locking the database."""
    db_path = get_db_path()
    locked_by = []
    try:
        if platform.system() in ("Darwin", "Linux"):
            cmd = f"lsof -t {db_path}" if platform.system() == "Darwin" else f"fuser {db_path} 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n' if platform.system() == "Darwin" else ' ')
                
                for pid in pids:
                    if pid:
                        try:
                            proc_result = subprocess.run(f"ps -p {pid} -o comm=", shell=True, 
                                                       capture_output=True, text=True)
                            process_name = proc_result.stdout.strip()
                            locked_by.append({"pid": pid, "process": process_name})
                        except:
                            locked_by.append({"pid": pid, "process": "unknown"})
        return locked_by
    except Exception as e:
        logger.error(f"Error detecting locks: {e}")
        return []

def handle_lock_file() -> bool:
    """Handle database lock file, removing if stale."""
    db_path = get_db_path()
    lock_file = Path(f"{db_path}.lock")
    
    if lock_file.exists() and time.time() - lock_file.stat().st_mtime > LOCK_TIMEOUT:
        logger.info("Removing stale lock file")
        try:
            lock_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Error removing lock file: {e}")
            return False
    return True

def get_connection_with_retry(read_only: bool = True, retry_count: int = 0) -> Optional[duckdb.DuckDBPyConnection]:
    """Get a database connection with retry logic."""
    db_path = get_db_path()
    
    # Handle lock file
    if not handle_lock_file():
        return None
    
    try:
        conn = duckdb.connect(db_path, read_only=read_only)
        # Test connection
        conn.execute("SELECT 1")
        return conn
    except duckdb.Error as e:
        if retry_count < MAX_RETRIES and "different configuration" in str(e):
            # Exponential backoff with jitter
            delay = BASE_RETRY_DELAY * (2 ** retry_count) + random.uniform(0, 0.5)
            logger.info(f"Connection conflict, retrying in {delay:.2f}s ({retry_count+1}/{MAX_RETRIES})")
            time.sleep(delay)
            return get_connection_with_retry(read_only, retry_count + 1)
        else:
            logger.error(f"Database connection error: {e}")
            return None

@contextmanager
def get_db_connection(read_only=True):
    """Context manager for database connections to ensure proper closure."""
    conn = None
    try:
        conn = get_connection_with_retry(read_only)
        if conn is None:
            logger.error("Failed to establish database connection")
            raise Exception("Could not connect to database")
        yield conn
    except Exception as e:
        logger.error(f"Error with database connection: {e}")
        logger.error(traceback.format_exc())
        if conn:
            try:
                conn.close()
                logger.info("Closed database connection after error")
            except:
                pass
        raise
    finally:
        if conn:
            try:
                conn.close()
                logger.info("Closed database connection")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

@st.cache_resource
def get_connection(read_only=True):
    """Get a cached database connection for Streamlit."""
    conn = get_connection_with_retry(read_only)
    if conn and not read_only:
        create_tables_if_needed(conn)
    return conn

def create_tables_if_needed(conn: Optional[duckdb.DuckDBPyConnection] = None) -> bool:
    """Create the required database tables if they don't exist."""
    logger.info("Checking/creating database tables")
    
    # Use provided connection or create a new one
    close_conn = False
    if conn is None:
        conn = get_connection_with_retry(read_only=False)
        close_conn = True
        if not conn:
            return False
    
    try:
        # Create streaming_history table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS streaming_history (
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
            )
        """)
        
        # Create track_metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS track_metadata (
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
            )
        """)
        
        # Create indices for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_track_uri ON streaming_history(spotify_track_uri)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON streaming_history(ts)")
        
        logger.info("Tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if close_conn and conn:
            try:
                conn.close()
            except:
                pass

def adjust_timezone(ts: datetime, conn_country: str) -> datetime:
    """Adjust timezone based on connection country."""
    adjustments = {
        "US": -7,
        "NO": -1, "ES": -1, "DE": -1, "FR": -1, "IT": -1,
    }
    hours_offset = adjustments.get(conn_country, 0)
    return ts + timedelta(hours=hours_offset)

def get_table_schema(table_name: str) -> Dict[str, str]:
    """Get the schema of a table."""
    with get_db_connection() as conn:
        try:
            result = conn.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """).fetchall()
            
            return {col[0]: col[1] for col in result}
        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {e}")
            return {}

def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        with get_db_connection() as conn:
            if not conn:
                return False
            result = conn.execute(f"""
                SELECT count(*) 
                FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            """).fetchone()[0]
            return result > 0
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {e}")
        return False

def get_table_counts() -> Dict[str, int]:
    """Get counts of records in main tables."""
    try:
        with get_db_connection() as conn:
            if not conn:
                return {}
            
            # Query for track metadata with genres (non-null)
            result = conn.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM streaming_history) as history_count,
                    (SELECT COUNT(*) FROM track_metadata) as metadata_count,
                    (SELECT COUNT(*) FROM track_metadata WHERE genres IS NOT NULL AND genres != '') as genre_track_count
            """).fetchone()
            
            return {
                "history_count": result[0],
                "metadata_count": result[1],
                "genre_track_count": result[2]
            }
    except Exception as e:
        logger.error(f"Error getting table counts: {e}")
        return {}

def execute_query(sql: str, params: Optional[Dict[str, Any]] = None) -> pl.DataFrame:
    """Execute a SQL query and return results as a Polars DataFrame."""
    logger.info(f"Executing query: {sql[:100]}...")  # Log first 100 chars
    try:
        with get_db_connection() as conn:
            if params:
                result = conn.execute(sql, params)
            else:
                result = conn.execute(sql)
            return result.pl()
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        logger.error(f"Query: {sql}")
        if params:
            logger.error(f"Params: {params}")
        return pl.DataFrame()

def execute_visualization_query(conn: duckdb.DuckDBPyConnection, sql: str) -> pl.DataFrame:
    """Execute a SQL query specifically for visualization purposes.
    
    Args:
        conn: DuckDB connection
        sql: SQL query to execute
        
    Returns:
        Polars DataFrame with query results
    """
    try:
        logger.info(f"Executing visualization query: {sql[:100]}...")  # Log first 100 chars
        result = conn.execute(sql)
        return result.pl()
    except Exception as e:
        logger.error(f"Error executing visualization query: {e}")
        logger.error(f"Query: {sql}")
        return pl.DataFrame()

def execute_write_query(sql: str, params: Optional[Dict[str, Any]] = None) -> bool:
    """Execute a SQL write query that doesn't return results."""
    try:
        with get_db_connection(read_only=False) as conn:
            if not conn:
                return False
            
            if params:
                conn.execute(sql, params)
            else:
                conn.execute(sql)
            return True
    except Exception as e:
        logger.error(f"Error executing write query: {e}")
        logger.error(f"Query: {sql}")
        if params:
            logger.error(f"Params: {params}")
        return False

def close_connections():
    """Close all database connections."""
    try:
        # Clean up any stale lock files
        handle_lock_file()
        logger.info("Database connections closed and lock files cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Register close_connections to run at exit
import atexit
atexit.register(close_connections)
