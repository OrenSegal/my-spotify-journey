from dashboard.tabs.shared_imports import *

def render_tracks_tab(context: Dict[str, Any]):
    """Render the Tracks tab content."""
    st.header("Tracks")
    
    sql_filter = context.get("sql_filter", "")
    
    # Get top tracks with duration tooltip
    tracks_query = """
        SELECT 
            track,
            artist,
            album,
            SUM(ms_played) as total_ms,
            COUNT(*) as play_count,
            FORMAT_DURATION(SUM(ms_played)) as duration_display
        FROM streaming_history h
        WHERE ms_played > 0
    """
    
    if sql_filter and sql_filter.startswith('WHERE'):
        tracks_query += f" AND {sql_filter[6:]}"
    
    tracks_query += """
        GROUP BY track, artist, album
        ORDER BY total_ms DESC
        LIMIT 25
    """
    
    top_tracks = load_data(tracks_query)
    
    if not top_tracks.is_empty():
        # Add track_label column for display
        top_tracks = top_tracks.with_columns([
            (pl.col('artist') + ' - ' + pl.col('track')).alias('track_label')
        ])
        plot_most_listened_tracks(top_tracks)
    else:
        st.info("No track data available to display.")
    
    # Add more track-related visualizations...