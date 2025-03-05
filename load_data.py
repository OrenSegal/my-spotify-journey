import os
import sys
import json
import traceback
from pathlib import Path
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import from the centralized database module
from backend.db.duckdb_helper import (
    get_db_path,
    get_db_connection, 
    create_tables_if_needed, 
    table_exists, 
    load_metadata_from_parquet,
    populate_genre_tables
)

def check_file_exists(file_path, file_type="File"):
    """Check if a file exists and print appropriate message."""
    if Path(file_path).exists():
        print(f"✅ {file_type} found: {file_path}")
        return True
    else:
        print(f"❌ {file_type} not found: {file_path}")
        return False

def filter_json_streaming_data(json_file_path):
    """Parse and filter streaming history JSON file."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
            
            # Check if the file ends properly
            file_content = file_content.strip()
            if not file_content.endswith(']'):
                print(f"Warning: JSON file {json_file_path} appears malformed. Attempting to fix...")
                # Try to find the last valid JSON object and close the array
                if file_content.rfind('}') > file_content.rfind(']'):
                    file_content = file_content[:file_content.rfind('}')+1] + ']'
                    print("Fixed: Truncated and closed JSON array")
            
            # Parse the JSON content
            data = json.loads(file_content)
            
            # Check if data is None or empty
            if not data:
                print(f"Warning: Empty or null data in {json_file_path}")
                return [], 0
                
            # Filter out podcasts and other non-music content
            music_items = []
            skipped_count = 0
            
            for item in data:
                if not item:
                    continue
                    
                # Get spotify_track_uri safely
                track_uri = item.get("spotify_track_uri", "")
                
                # Skip podcasts or empty entries
                if track_uri and "spotify:track:" in track_uri:
                    # Add skipped status if available
                    if "reason_end" in item:
                        item["skipped"] = item["reason_end"] == "forward" or item["reason_end"] == "back"
                    else:
                        item["skipped"] = None
                    music_items.append(item)
                else:
                    skipped_count += 1
                    
            return music_items, skipped_count
            
    except json.JSONDecodeError as je:
        error_line = je.lineno
        error_col = je.colno
        error_pos = je.pos
        print(f"JSON parsing error in {json_file_path} at line {error_line}, column {error_col}, position {error_pos}")
        print(f"Error details: {je}")
        
        # Attempt to recover part of the file
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Try parsing up to the last complete object
                last_obj_end = content.rfind('},')
                if last_obj_end > 0:
                    partial_content = content[:last_obj_end+1] + ']'
                    print(f"Attempting to parse {len(partial_content)} characters up to the last complete object...")
                    partial_data = json.loads(partial_content)
                    print(f"Recovered {len(partial_data)} items from the file")
                    
                    # Process the partial data
                    music_items = []
                    skipped_count = 0
                    
                    for item in partial_data:
                        if not item:
                            continue
                        track_uri = item.get("spotify_track_uri", "")
                        if track_uri and "spotify:track:" in track_uri:
                            if "reason_end" in item:
                                item["skipped"] = item["reason_end"] == "forward" or item["reason_end"] == "back"
                            else:
                                item["skipped"] = None
                            music_items.append(item)
                        else:
                            skipped_count += 1
                    
                    print(f"Successfully recovered {len(music_items)} music items from damaged file")
                    return music_items, skipped_count
        except Exception as recovery_error:
            print(f"Recovery attempt failed: {recovery_error}")
        
        return [], 0
    except Exception as e:
        print(f"Error parsing JSON file {json_file_path}: {e}")
        traceback.print_exc()
        return [], 0

def setup_database():
    """Set up database tables."""
    print("Setting up database tables...")
    return create_tables_if_needed()

def load_streaming_history(history_files):
    """Load streaming history from JSON files."""
    success_count = 0
    skipped_count = 0
    error_files = []
    
    with get_db_connection(read_only=False) as conn:
        if not conn:
            print("Database connection failed")
            return 0, 0
            
        # Prepare insert statement
        sql_insert = """
        INSERT INTO streaming_history 
        (ts, platform, ms_played, track, artist, album, 
        spotify_track_uri, reason_start, reason_end, skipped, conn_country)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Process each file
        for file_path in history_files:
            print(f"Processing {file_path.name}...")
            filtered_items, file_skipped = filter_json_streaming_data(file_path)
            
            if not filtered_items:
                error_files.append(file_path.name)
                continue
                
            skipped_count += file_skipped
            
            # Process filtered items
            items_inserted = 0
            for item in filtered_items:
                try:
                    conn.execute(sql_insert, (
                        item.get("ts"),
                        item.get("platform"),
                        item.get("ms_played"),
                        item.get("master_metadata_track_name"),
                        item.get("master_metadata_album_artist_name"),
                        item.get("master_metadata_album_album_name"),
                        item.get("spotify_track_uri"),
                        item.get("reason_start"),
                        item.get("reason_end"),
                        item.get("skipped"),
                        item.get("conn_country")
                    ))
                    items_inserted += 1
                    success_count += 1
                except Exception as e:
                    print(f"Error inserting record: {e}")
            
            print(f"Inserted {items_inserted} records from {file_path.name}")
    
    if error_files:
        print(f"\nWarning: Failed to process {len(error_files)} files: {', '.join(error_files)}")
                    
    return success_count, skipped_count

def main():
    """Main function to load streaming history and metadata."""
    parser = argparse.ArgumentParser(description="Load Spotify streaming data into database")
    parser.add_argument("--force-reload", action="store_true", 
                        help="Force reload data even if tables already have data")
    parser.add_argument("--clear", action="store_true", 
                        help="Clear existing data before loading")
    args = parser.parse_args()
    
    # Get file paths
    data_dir = Path(os.getenv('DATA_DIR', 'data'))
    metadata_parquet_path = Path(os.getenv('METADATA_PARQUET_PATH', 'data/metadata/metadata.parquet'))
    streaming_history_dir = data_dir / "Streaming_History"
    
    # Ensure directories exist
    data_dir.mkdir(parents=True, exist_ok=True)
    streaming_history_dir.mkdir(parents=True, exist_ok=True)
    metadata_parquet_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n--- CHECKING FILES ---")
    # Check for streaming history files
    history_files = list(streaming_history_dir.glob("Streaming_History_Audio_*.json"))
    history_files_exist = len(history_files) > 0
    
    if history_files_exist:
        print(f"✅ Found {len(history_files)} streaming history JSON files")
    else:
        print("❌ No streaming history JSON files found")
    
    # Check for metadata file
    metadata_exists = check_file_exists(metadata_parquet_path, "Track metadata Parquet")
    
    # Connect to database
    print("\n--- CONNECTING TO DATABASE ---")
    db_path = get_db_path()
    print(f"Database path: {db_path}")
    
    try:
        # Setup database
        if not setup_database():
            print("❌ Database setup failed")
            return 1
            
        print("✅ Database setup successful")
        
        # Get current record counts
        with get_db_connection(read_only=True) as conn:
            if not conn:
                print("❌ Database connection failed")
                return 1
                
            history_count = conn.execute("SELECT COUNT(*) FROM streaming_history").fetchone()[0]
            
            # Safely get metadata count
            try:
                metadata_count = conn.execute("SELECT COUNT(*) FROM track_metadata").fetchone()[0]
            except:
                metadata_count = 0
                
            print(f"Initial record counts: streaming_history={history_count:,}, track_metadata={metadata_count:,}")
        
        # Clear data if requested
        if args.clear:
            print("\n--- CLEARING EXISTING DATA ---")
            with get_db_connection(read_only=False) as conn:
                if conn:
                    conn.execute("DELETE FROM streaming_history")
                    conn.execute("DELETE FROM track_metadata")
                    print("Data cleared")
                    history_count = 0
                    metadata_count = 0
        
        # Determine what needs loading
        streaming_needed = history_count == 0 or args.force_reload
        metadata_needed = metadata_count == 0 or args.force_reload
        
        if not streaming_needed and not metadata_needed:
            print("\n⚠️ Database already contains data. Use --force-reload or --clear to reload.")
            return 0
        
        # Load streaming history
        if streaming_needed and history_files_exist:
            print("\n--- LOADING STREAMING HISTORY ---")
            loaded, skipped = load_streaming_history(history_files)
            print(f"✅ Loaded {loaded:,} streaming records (skipped {skipped:,} podcasts)")
        else:
            print("\nSkipping streaming history loading")
        
        # Load metadata
        if metadata_needed and metadata_exists:
            print("\n--- LOADING TRACK METADATA ---")
            if not load_metadata_from_parquet(metadata_parquet_path):
                print("❌ Failed to load track metadata")
        else:
            print("\nSkipping track metadata loading")
        
        # Populate genre tables
        print("\n--- SETTING UP GENRE TABLES ---")
        if populate_genre_tables():
            print("✅ Genre tables populated successfully")
        else:
            print("❌ Failed to populate genre tables")
        
        # Show final counts
        with get_db_connection(read_only=True) as conn:
            if conn:
                history_count = conn.execute("SELECT COUNT(*) FROM streaming_history").fetchone()[0]
                try:
                    metadata_count = conn.execute("SELECT COUNT(*) FROM track_metadata").fetchone()[0]
                except:
                    metadata_count = 0
                genre_count = conn.execute("SELECT COUNT(*) FROM genres").fetchone()[0]
                genre_track_count = conn.execute("SELECT COUNT(*) FROM genre_track").fetchone()[0]
                print(f"\nFinal record counts: streaming_history={history_count:,}, track_metadata={metadata_count:,}")
                print(f"Genre system: {genre_count:,} unique genres, {genre_track_count:,} genre-track associations")
    
    except Exception as e:
        print(f"Error during database operations: {e}")
        traceback.print_exc()
        return 1
    
    print("\nData loading complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())