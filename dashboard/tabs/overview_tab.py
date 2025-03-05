from dashboard.tabs.shared_imports import *
from dashboard.data_transformations import format_duration, format_count

def render_overview_tab(context: Dict[str, Any]):
    """Render the Overview tab content."""
    st.header("Overview")
    
    sql_filter = context.get("sql_filter", "")
    
    # Get overview stats with improved query
    overview_stats_query = """
        WITH base_stats AS (
            SELECT 
                SUM(ms_played) as total_ms,
                COUNT(DISTINCT artist) as unique_artists,
                COUNT(DISTINCT track) as unique_tracks,
                COUNT(DISTINCT album) as unique_albums,
                CAST(SUM(CASE WHEN skipped THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) as skip_rate
            FROM streaming_history
            WHERE ms_played > 0
        ),
        genre_stats AS (
            SELECT COUNT(DISTINCT g.name) as unique_genres
            FROM streaming_history h
            JOIN genre_track gt ON h.track = gt.track AND h.artist = gt.artist
            JOIN genres g ON gt.genre_id = g.id
            WHERE ms_played > 0
        )
        SELECT 
            base_stats.*,
            CAST(total_ms AS FLOAT) / (1000 * 60 * 60) as total_hours,
            genre_stats.unique_genres
        FROM base_stats
        CROSS JOIN genre_stats
    """
    
    if sql_filter and sql_filter.startswith('WHERE'):
        overview_stats_query = overview_stats_query.replace(
            "WHERE ms_played > 0", 
            f"WHERE ms_played > 0 AND {sql_filter[6:]}"
        )
    
    overview_stats = load_data(overview_stats_query)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_ms = safe_metric_value(overview_stats, 'total_ms', 0)
        st.metric("Total Listening Time", format_duration(total_ms))
        
        unique_tracks = safe_metric_value(overview_stats, 'unique_tracks', 0)
        st.metric("Unique Tracks", format_count(unique_tracks))

    with col2:
        unique_artists = safe_metric_value(overview_stats, 'unique_artists', 0)
        st.metric("Unique Artists", format_count(unique_artists))
        
        unique_albums = safe_metric_value(overview_stats, 'unique_albums', 0)
        st.metric("Unique Albums", format_count(unique_albums))

    with col3:
        unique_genres = safe_metric_value(overview_stats, 'unique_genres', 0)
        st.metric("Unique Genres", format_count(unique_genres))
        
        skip_rate = safe_metric_value(overview_stats, 'skip_rate', 0)
        st.metric("Skip Rate", f"{skip_rate:.1%}")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Remix vs Original (by Listening Time)")
        remix_query = """
            SELECT 
                CASE WHEN LOWER(track) LIKE '%remix%' THEN 'Remix' ELSE 'Original' END as is_remix,
                COUNT(*) as count,
                SUM(ms_played) as total_ms,
                SUM(ms_played)::FLOAT / SUM(SUM(ms_played)) OVER () as percentage
            FROM streaming_history
        """
        
        if sql_filter:
            remix_query += f" {sql_filter}"
            
        remix_query += " GROUP BY 1"
        
        remix_data = load_data(remix_query)
        if len(remix_data) > 0:
            plot_remix_pie(remix_data)
        else:
            st.info("No data available for this chart.")
    
    with col2:
        st.subheader("Completed vs Skipped (by Listening Time)")
        skip_query = """
            SELECT
                CASE WHEN skipped THEN 'Skipped' ELSE 'Completed' END as skipped,
                COUNT(*) as count,
                SUM(ms_played) as total_ms,
                SUM(ms_played)::FLOAT / SUM(SUM(ms_played)) OVER () as percentage
            FROM streaming_history
            WHERE skipped IS NOT NULL
        """
        
        if sql_filter:
            skip_query += f" AND {sql_filter[6:]}" if sql_filter.startswith('WHERE') else f" {sql_filter}"
            
        skip_query += " GROUP BY 1"
        
        skip_data = load_data(skip_query)
        if len(skip_data) > 0:
            plot_skip_pie(skip_data)
        else:
            st.info("No data available for this chart.")