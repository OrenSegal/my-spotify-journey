import polars as pl
from backend.db.duckdb_helper import get_db_connection

def get_most_listened_tracks(limit: int = 10):
    conn = get_db_connection()
    query = f"""
        SELECT master_metadata_track_name, master_metadata_album_artist_name, SUM(ms_played) as total_ms
        FROM streaming_history
        GROUP BY master_metadata_track_name, master_metadata_album_artist_name
        ORDER BY total_ms DESC
        LIMIT {limit}
    """
    df = conn.execute(query).pl()
    conn.close()
    return df.to_dicts()

def get_genre_diversity(timeframe: str = "month"):
    conn = get_db_connection()
    query = f"""
        SELECT DATE_TRUNC('{timeframe}', ts) as period, COUNT(DISTINCT genres) as genre_count
        FROM streaming_history
        JOIN track_metadata ON streaming_history.spotify_track_uri = track_metadata.track_uri
        GROUP BY period
        ORDER BY period
    """
    df = conn.execute(query).pl()
    conn.close()
    return df.to_dicts()

def get_artist_repetitiveness():
    conn = get_db_connection()
    query = """
        SELECT ts, master_metadata_album_artist_name,
               LAG(master_metadata_album_artist_name) OVER (ORDER BY ts) as prev_artist
        FROM streaming_history
    """
    df = conn.execute(query).pl()
    df = df.with_columns(
        (pl.col("master_metadata_album_artist_name") == pl.col("prev_artist")).alias("repeated")
    ).group_by(pl.col("ts").dt.truncate("1d")).agg(
        pl.col("repeated").mean().alias("repetitiveness")
    )
    conn.close()
    return df.to_dicts()

# Add more insight functions as needed