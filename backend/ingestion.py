import json
import polars as pl
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict
from backend.db.duckdb_helper import (
    get_db_connection,
    adjust_timezone,
    table_exists,
    create_tables_if_needed
)
from datetime import datetime

router = APIRouter()

@router.post("/ingest/streaming-history")
async def ingest_streaming_history(file: UploadFile = File(...)) -> Dict[str, str]:
    """Ingest streaming history from JSON."""
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
        
        # Handle empty data
        if not data:
            return {"status": "success", "message": "No data to insert (empty file)."}
        
        # Convert to DataFrame
        df = pl.DataFrame(data)
        
        # --- Data Cleaning and Transformation ---
        columns_to_drop = ["shuffle", "offline", "offline_timestamp", "incognito_mode",
                           "episode_name", "episode_show_name", "spotify_episode_uri", "ip_addr"]
        df = df.drop([col for col in columns_to_drop if col in df.columns])
        
        # Skip if no valid records after dropping podcast entries
        if df.height == 0:
            return {"status": "success", "message": "No valid tracks to insert (only podcast entries)."}
        
        # Rename and transform columns with null handling
        df = df.with_columns([
            pl.col("ts").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%SZ").alias("ts"),
            pl.col("master_metadata_track_name").alias("track").fill_null(""),
            pl.col("master_metadata_album_artist_name").alias("artist").fill_null(""),
            pl.col("master_metadata_album_album_name").alias("album").fill_null(""),
            pl.col("skipped").cast(pl.Boolean).fill_null(False),
            pl.col("ms_played").cast(pl.Int64).fill_null(0),
            # Add other necessary columns with defaults if they don't exist
            pl.lit("spotify").alias("platform"),  # Default platform
            pl.col("spotify_track_uri").fill_null(""),
            pl.col("reason_start").fill_null("unknown"),
            pl.col("reason_end").fill_null("unknown"),
            pl.col("conn_country").fill_null("unknown")
        ])
        
        conn = get_db_connection(read_only=False)  # Get a *writeable* connection
        if not conn:
            raise HTTPException(status_code=500, detail="Could not connect to database")
        
        try:
            # Generate sequential IDs *within* the transaction
            with conn:
                if not table_exists(conn, "streaming_history"):
                    create_tables_if_needed(conn)
                
                # Safely get max ID with proper null handling
                max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM streaming_history").fetchone()
                start_id = max_id_result[0] + 1
                
                # Add sequential IDs and adjust timezone
                df = df.with_columns([
                    pl.struct(["ts", "conn_country"])
                    .map_elements(lambda x: adjust_timezone(x["ts"], x["conn_country"]))
                    .alias("ts"),
                    (pl.arange(0, df.height) + start_id).alias("id"),
                ])
                
                # Ensure correct column order with explicit selection
                required_columns = [
                    "id", "ts", "platform", "ms_played", "track", "artist", "album",
                    "spotify_track_uri", "reason_start", "reason_end", "skipped", "conn_country"
                ]
                
                # Make sure all required columns exist
                for col in required_columns:
                    if col not in df.columns:
                        df = df.with_columns(pl.lit(None).alias(col))
                
                df = df.select(required_columns)
                
                # Insert data in batches to handle large files
                batch_size = 5000
                total_inserted = 0
                
                for i in range(0, df.height, batch_size):
                    batch = df.slice(i, min(batch_size, df.height - i))
                    conn.register("streaming_df", batch)
                    conn.execute("INSERT INTO streaming_history SELECT * FROM streaming_df")
                    total_inserted += batch.height
                
                return {"status": "success", "message": f"Inserted {total_inserted} rows."}
        finally:
            conn.close()  # Always close the connection
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ingest/track-metadata")
async def ingest_track_metadata(file: UploadFile = File(...)) -> Dict[str, str]:
    """Ingest track metadata from CSV."""
    try:
        content = await file.read()
        
        # Parse CSV into DataFrame with error handling
        try:
            df = pl.read_csv(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
        
        # Validate required columns
        required_cols = ["track_uri"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise HTTPException(status_code=400, 
                detail=f"Missing required columns: {', '.join(missing)}")
        
        conn = get_db_connection(read_only=False)
        if not conn:
            raise HTTPException(status_code=500, detail="Could not connect to database")
        
        try:
            with conn:
                if not table_exists(conn, "track_metadata"):
                    create_tables_if_needed(conn)
                
                # Register DataFrame and insert with UPSERT logic
                conn.register("metadata_df", df)
                
                # Use a transaction for the upsert
                conn.execute("BEGIN TRANSACTION")
                
                # Perform upsert (insert or replace)
                conn.execute("""
                    INSERT OR REPLACE INTO track_metadata
                    SELECT
                        track_uri,
                        COALESCE(track, ''),
                        COALESCE(artist, ''),
                        CAST(COALESCE(track_popularity, 0) AS INTEGER),
                        CAST(NULLIF(album_release_date, '') AS DATE),
                        COALESCE(album, ''),
                        CAST(COALESCE(duration_ms, 0) AS INTEGER),
                        CAST(COALESCE(explicit, FALSE) AS BOOLEAN),
                        COALESCE(album_type, 'unknown'),
                        CAST(COALESCE(total_tracks, 0) AS INTEGER),
                        COALESCE(genres, ''),
                        CAST(COALESCE(artist_popularity, 0) AS INTEGER),
                        COALESCE(artist_uri, ''),
                        CAST(COALESCE(artist_followers, 0) AS INTEGER)
                    FROM metadata_df
                    WHERE track_uri IS NOT NULL
                """)
                
                conn.execute("COMMIT")
                
                return {"status": "success"}
                
        except Exception as e:
            if conn:
                conn.execute("ROLLBACK")
            raise HTTPException(status_code=400, detail=str(e))
            
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))