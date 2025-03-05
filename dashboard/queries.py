from typing import Dict, List, Any, Optional
import streamlit as st
import polars as pl
from dashboard.filters import QueryBuilder  # Import the QueryBuilder

# Optimized query templates.  Placeholders for {filters} and {timeframe}
QUERIES = {
    "overview_stats": """
        WITH filtered_data AS (
            SELECT * FROM streaming_history h
            {filters}
        )
        SELECT
            COUNT(DISTINCT track) as unique_tracks,
            COUNT(DISTINCT artist) as unique_artists,
            SUM(ms_played)/3600000.0 as total_hours,
            SUM(CASE WHEN skipped THEN 1 ELSE 0 END)::FLOAT/COUNT(*) as skip_rate
        FROM filtered_data
    """,

    "top_tracks": """
        SELECT
            track,
            artist,
            SUM(ms_played) as total_ms,
            COUNT(*) as play_count
        FROM streaming_history h
        {filters}
        GROUP BY 1, 2
        ORDER BY total_ms DESC
        LIMIT 100
    """,

     "artist_popularity": """
        SELECT
            h.artist,
            AVG(m.artist_popularity) as artist_popularity,
            COUNT(*) as play_count
        FROM streaming_history h
        JOIN track_metadata m ON h.spotify_track_uri = m.track_uri
        {filters}
        GROUP BY 1
        ORDER BY play_count DESC
        LIMIT 50
    """,
    "daily_patterns": """
        SELECT
            EXTRACT(DOW FROM ts) as weekday,
            EXTRACT(HOUR FROM ts) as hour,
            COUNT(*) as count,
            AVG(ms_played)/60000.0 as avg_duration_min
        FROM streaming_history h
        {filters}
        GROUP BY 1, 2
        ORDER BY 1, 2
    """,

    "hours_filter": """
        SELECT EXTRACT(HOUR FROM ts) as hour,
               COUNT(*) as count
        FROM streaming_history h
        {filters}
        GROUP BY 1
        ORDER BY 1
    """,

    "skip_patterns": """
        SELECT
            CASE WHEN skipped THEN 'Skipped' ELSE 'Completed' END as skipped,
            COUNT(*) as count,
            COUNT(*)::FLOAT / SUM(COUNT(*)) OVER () as percentage
        FROM streaming_history h
        {filters}
        GROUP BY 1
    """,

    "genre_evolution": """
        WITH filtered_data AS (
            SELECT
                DATE_TRUNC('{timeframe}', h.ts) as period,
                m.artist_genres as genre,
                COUNT(*) as plays
            FROM streaming_history h
            JOIN track_metadata m
                ON h.spotify_track_uri = m.track_uri
            {filters}
            GROUP BY 1, 2
        ),
        top_genres AS (
            SELECT genre, SUM(plays) as total
            FROM filtered_data
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 10
        )
        SELECT
            f.period,
            COALESCE(t.genre, 'Other') as genre,
            SUM(f.plays) as plays,
            SUM(f.plays)::FLOAT / SUM(SUM(f.plays)) OVER (PARTITION BY f.period) as proportion
        FROM filtered_data f
        LEFT JOIN top_genres t USING (genre)
        GROUP BY 1, 2
        ORDER BY 1, plays DESC
    """,
    "remix_analysis": """
            SELECT
                CASE WHEN LOWER(track) LIKE '%remix%' THEN 'Remix' ELSE 'Original' END as is_remix,
                COUNT(*) as count,
                COUNT(*)::FLOAT / SUM(COUNT(*)) OVER () as percentage
            FROM streaming_history h
            {filters}
            GROUP BY 1
        """,
        "top_artists": """
        SELECT
            artist,
            SUM(ms_played) as total_ms,
            COUNT(*) as play_count,
            COUNT(DISTINCT track) as unique_tracks
        FROM streaming_history h
        {filters}
        GROUP BY 1
        ORDER BY total_ms DESC
        LIMIT 100
    """,

    "top_albums": """
        SELECT
            album,
            artist,
            SUM(ms_played) as total_ms,
            COUNT(*) as play_count,
            COUNT(DISTINCT track) as unique_tracks
        FROM streaming_history h
        {filters}
        GROUP BY 1, 2
        ORDER BY total_ms DESC
        LIMIT 100
    """,

    "top_genres": """
        SELECT
            m.artist_genres as genre,
            SUM(h.ms_played) as total_ms,
            COUNT(*) as play_count,
            COUNT(DISTINCT h.track) as unique_tracks
        FROM streaming_history h
        JOIN track_metadata m ON h.spotify_track_uri = m.track_uri
        {filters}
        GROUP BY 1
        ORDER BY total_ms DESC
        LIMIT 100
    """,
 "table_counts": """
        SELECT
            (SELECT COUNT(*) FROM streaming_history) as history_count,
            (SELECT COUNT(*) FROM track_metadata) as metadata_count
    """,

}
@st.cache_data(ttl=3600)
def execute_query(conn, query_name: str, params: Optional[Dict[str, Any]] = None) -> pl.DataFrame:
    """Execute query with caching."""
    if params is None:
        params = {}

    query_template = QUERIES.get(query_name)
    if not query_template:
        return pl.DataFrame()

    filters = params.get('filters', '')
    timeframe = params.get('timeframe', 'month').lower()

    final_query = query_template.format(filters=filters, timeframe=timeframe)

    try:
        return conn.execute(final_query).pl()
    except Exception as e:
        print(f"Error executing query: {e}")
        return pl.DataFrame()