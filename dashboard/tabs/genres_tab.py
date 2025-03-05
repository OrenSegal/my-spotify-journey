from dashboard.tabs.shared_imports import *

def render_genres_tab(context: Dict[str, Any]):
    """Render the Genres tab content."""
    st.header("Genre Analysis")
    
    sql_filter = context.get("sql_filter", "")
    
    # First check if genres table exists using proper DuckDB syntax
    genre_check_query = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_name = 'genres'
    """
    
    genre_check = load_data(genre_check_query)
    
    if len(genre_check) > 0 and genre_check[0, 'count'] > 0:
        genres_query = """
            SELECT 
                g.name as genre,
                SUM(h.ms_played) as total_ms,
                COUNT(*) as play_count,
                COUNT(DISTINCT gt.track_uri) as unique_tracks
            FROM streaming_history h
            JOIN genre_track gt ON h.spotify_track_uri = gt.track_uri
            JOIN genres g ON gt.genre_id = g.genre_id
            WHERE h.ms_played > 0
        """
        
        if sql_filter and sql_filter.startswith('WHERE'):
            genres_query += f" AND {sql_filter[6:]}"
        elif sql_filter:
            genres_query += f" {sql_filter}"
            
        genres_query += " GROUP BY 1 ORDER BY 2 DESC LIMIT 50"
        
        genres_data = load_data(genres_query)
        
        if len(genres_data) > 0:
            st.subheader("Top Genres")
            
            genres_with_tooltip = genres_data.with_columns([
                pl.struct(['genre', 'total_ms', 'play_count']).map_elements(
                    lambda x: format_item_tooltip(x['genre'], x['total_ms'], x['play_count']),
                    return_dtype=pl.Utf8
                ).alias('item_tooltip')
            ])
            
            plot_genres_stacked(genres_with_tooltip)
            
            # Genre metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Genres", f"{len(genres_data):,}")
            
            with col2:
                total_ms = genres_data['total_ms'].sum()
                st.metric("Total Listening Time", format_duration_tooltip(total_ms))
            
            with col3:
                total_tracks = genres_data['unique_tracks'].sum()
                st.metric("Unique Tracks with Genre", f"{total_tracks:,}")
            
            # Genre evolution over time
            st.subheader("Genre Evolution")
            
            # Select appropriate timeframe based on data range
            date_range_query = """
                SELECT 
                    MIN(ts) as min_date,
                    MAX(ts) as max_date,
                    (MAX(ts) - MIN(ts)) as date_diff
                FROM streaming_history
            """
            
            if sql_filter:
                date_range_query += f" {sql_filter}"
                
            date_range = load_data(date_range_query)
            
            # Default timeframe in case the date range query fails
            timeframe = 'month'  # Default to monthly if no data
            
            if len(date_range) > 0:
                # Choose timeframe based on date range
                date_diff_days = date_range[0, 'date_diff'].days if hasattr(date_range[0, 'date_diff'], 'days') else 365
                timeframe = 'day' if date_diff_days < 60 else 'week' if date_diff_days < 365 else 'month'
                
                # Genre evolution query
                genre_evolution_query = f"""
                    WITH genre_periods AS (
                        SELECT 
                            DATE_TRUNC('{timeframe}', h.ts) as period,
                            g.name as genre,
                            COUNT(*) as plays,
                            SUM(h.ms_played) as total_ms
                        FROM streaming_history h
                        JOIN genre_track gt ON h.spotify_track_uri = gt.track_uri
                        JOIN genres g ON gt.genre_id = g.genre_id
                        WHERE h.ms_played > 0
                """
                
                if sql_filter and sql_filter.startswith('WHERE'):
                    genre_evolution_query += f" AND {sql_filter[6:]}"
                elif sql_filter:
                    genre_evolution_query += f" {sql_filter}"
                
                genre_evolution_query += """
                        GROUP BY 1, 2
                    ),
                    top_genres AS (
                        SELECT genre, SUM(total_ms) as total_time
                        FROM genre_periods
                        GROUP BY genre
                        ORDER BY total_time DESC
                        LIMIT 10
                    )
                    SELECT
                        gp.period,
                        COALESCE(tg.genre, 'Other') as genre,
                        SUM(gp.plays) as plays,
                        SUM(gp.total_ms) as total_ms,
                        SUM(gp.plays)::FLOAT / SUM(SUM(gp.plays)) OVER (PARTITION BY gp.period) as proportion
                    FROM genre_periods gp
                    LEFT JOIN top_genres tg ON gp.genre = tg.genre
                    GROUP BY 1, 2
                    ORDER BY 1, 3 DESC
                """
                
                genre_evolution = load_data(genre_evolution_query)
                
                if len(genre_evolution) > 0:
                    plot_genres_evolution(genre_evolution)
                else:
                    st.info("No genre evolution data available for the selected filters.")
            else:
                st.info("No date range data available for the selected filters.")

            # Genre diversity over time - Now timeframe is defined regardless of whether date_range has data
            st.subheader("Genre Diversity")
            st.write("Shows how your genre diversity changes over time")
            
            genre_diversity_query = f"""
                SELECT 
                    DATE_TRUNC('{timeframe}', h.ts) as period,
                    COUNT(DISTINCT g.genre_id) as genre_count
                FROM streaming_history h
                JOIN genre_track gt ON h.spotify_track_uri = gt.track_uri
                JOIN genres g ON gt.genre_id = g.genre_id
                WHERE h.ms_played > 0
            """
            
            if sql_filter and sql_filter.startswith('WHERE'):
                genre_diversity_query += f" AND {sql_filter[6:]}"
            elif sql_filter:
                genre_diversity_query += f" {sql_filter}"
            
            genre_diversity_query += " GROUP BY 1 ORDER BY 1"
            
            genre_diversity = load_data(genre_diversity_query)
            
            if len(genre_diversity) > 0:
                plot_genre_diversity(genre_diversity)
            else:
                st.info("No genre diversity data available for the selected filters.")
                
            # Genres by hour
            st.subheader("Genre Distribution by Hour")
            
            genre_hour_query = """
                SELECT 
                    EXTRACT(HOUR FROM h.ts) as hour,
                    g.name as genre,
                    COUNT(*) as count
                FROM streaming_history h
                JOIN genre_track gt ON h.spotify_track_uri = gt.track_uri
                JOIN genres g ON gt.genre_id = g.genre_id
                WHERE h.ms_played > 0
            """
            
            if sql_filter and sql_filter.startswith('WHERE'):
                genre_hour_query += f" AND {sql_filter[6:]}"
            elif sql_filter:
                genre_hour_query += f" {sql_filter}"
            
            # Filter to top 8 genres for visualization
            genre_hour_query += """
                AND g.name IN (
                    SELECT g.name
                    FROM streaming_history h
                    JOIN genre_track gt ON h.spotify_track_uri = gt.track_uri
                    JOIN genres g ON gt.genre_id = g.genre_id
                    GROUP BY g.name
                    ORDER BY SUM(h.ms_played) DESC
                    LIMIT 8
                )
                GROUP BY 1, 2
                ORDER BY 1, 3 DESC
            """
            
            genre_hour_data = load_data(genre_hour_query)
            
            if len(genre_hour_data) > 0:
                plot_genres_by_hour(genre_hour_data)
            else:
                st.info("No genre by hour data available for the selected filters.")
                
        else:
            st.info("No genre data available for the selected filters.")
    else:
        st.warning("No genre data available. Make sure you've loaded genre data using the load_data.py script.")