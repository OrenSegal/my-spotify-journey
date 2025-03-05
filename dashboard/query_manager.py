import streamlit as st
import polars as pl
import duckdb
from typing import Dict, Any, Optional, List
from functools import lru_cache

class QueryManager:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.queries = QUERIES  # Use the QUERIES dict

    @st.cache_data(ttl=3600)
    def execute_query(_self, query_name: str, params: Dict[str, Any]) -> pl.DataFrame:
        """Execute cached query with parameters."""
        try:
            query_template = _self.queries[query_name]
            where_clause = _self._build_where_clause(params)
            # Remove timeframe from params if it exists, as it's handled by _get_timeframe
            params_copy = params.copy()  # Create a copy to avoid modifying the original
            timeframe = params_copy.pop('timeframe', None)  # Remove 'timeframe', if present

            final_query = query_template.format(
                where_clause=where_clause,
                timeframe=_self._get_timeframe(timeframe), # Use the result of get_timeframe
                **params_copy  # Use the modified params (without timeframe)
            )

            return _self.conn.execute(final_query).pl()
        except KeyError:
            st.error(f"Query '{query_name}' not found.")
            return pl.DataFrame()
        except Exception as e:
            st.error(f"Query execution failed: {str(e)}")
            return pl.DataFrame()

    @staticmethod
    def _build_where_clause(params: Dict[str, Any]) -> str:
        """Build optimized WHERE clause."""
        conditions = []

        if timeframe := params.get('timeframe'):
            if timeframe != "All Time":
                conditions.append(
                    f"h.ts >= DATE_TRUNC('{timeframe.lower()}', CURRENT_TIMESTAMP) - INTERVAL '1 year'"
                )

        if time_buckets := params.get('time_buckets'):
            hour_conditions = []
            for bucket in time_buckets:
                start, end = TIME_RANGES[bucket]
                hour_conditions.append(
                    f"EXTRACT(HOUR FROM h.ts) BETWEEN {start} AND {end-1}"
                )
            if hour_conditions:
                conditions.append(f"({' OR '.join(hour_conditions)})")

        if days := params.get('days'):
            day_nums = [str(DAY_MAP[d]) for d in days]
            conditions.append(f"EXTRACT(DOW FROM h.ts) IN ({','.join(day_nums)})")

        return f"WHERE {' AND '.join(conditions)}" if conditions else ""

    @staticmethod
    @lru_cache(maxsize=32)
    def _get_timeframe(timeframe: Optional[str]) -> str:
        """Get SQL timeframe with caching."""
        return {
            "All Time": "month",
            "Year": "year",
            "Month": "month",
            "Week": "week",
            "Day": "day"
        }.get(timeframe, "month")

# Constants
TIME_RANGES = {
    "12AM-6AM": (0, 6),
    "6AM-12PM": (6, 12),
    "12PM-6PM": (12, 18),
    "6PM-12AM": (18, 24)
}

DAY_MAP = {
    "Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4,
    "Fri": 5, "Sat": 6, "Sun": 0
}
# Optimized query templates
QUERIES = {
 "overview_stats": """
        WITH filtered_data AS (
            SELECT * FROM streaming_history h
            {where_clause}
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
        {where_clause}
        GROUP BY 1, 2
        ORDER BY total_ms DESC 
        LIMIT 100
    """,

    "top_artists": """
        SELECT
            artist,
            SUM(ms_played) as total_ms,
            COUNT(*) as play_count,
            COUNT(DISTINCT track) as unique_tracks
        FROM streaming_history h
        {where_clause}
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
        {where_clause}
        GROUP BY 1, 2
        ORDER BY total_ms DESC
        LIMIT 100
    """,

    "top_genres": """
        SELECT 
            m.genre as genre,
            SUM(h.ms_played) as total_ms,
            COUNT(*) as play_count,
            COUNT(DISTINCT h.track) as unique_tracks
        FROM streaming_history h
        JOIN track_metadata m ON h.spotify_track_uri = m.track_uri
        {where_clause}
        GROUP BY 1
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
        {where_clause}
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
        {where_clause}
        GROUP BY 1, 2
        ORDER BY 1, 2
    """,

    "hours_filter": """
        SELECT EXTRACT(HOUR FROM ts) as hour,
               COUNT(*) as count
        FROM streaming_history h
        {where_clause}
        GROUP BY 1
        ORDER BY 1
    """,

    "skip_patterns": """
        SELECT
            CASE WHEN skipped THEN 'Skipped' ELSE 'Completed' END as skipped,
            COUNT(*) as count,
            COUNT(*)::FLOAT / SUM(COUNT(*)) OVER () as percentage
        FROM streaming_history h
        {where_clause}
        GROUP BY 1
    """,

    "genre_evolution": """
        WITH filtered_data AS (
            SELECT
                DATE_TRUNC('{timeframe}', h.ts) as period,
                m.genres as genre,
                COUNT(*) as plays
            FROM streaming_history h
            JOIN track_metadata m
                ON h.spotify_track_uri = m.track_uri
            {where_clause}
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
            {where_clause}
            GROUP BY 1
        """,

}