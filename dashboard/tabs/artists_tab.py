from dashboard.tabs.shared_imports import *

def render_artists_tab(context: Dict[str, Any]):
    """Render the Artists tab content."""
    st.header("Top Artists")
    
    sql_filter = context.get("sql_filter", "")
    
    # Query for top artists
    artist_query = """
        SELECT 
            artist,
            SUM(ms_played) as total_ms,
            COUNT(*) as play_count
        FROM streaming_history
        WHERE artist IS NOT NULL
    """
    
    if sql_filter:
        # Add AND instead of overriding the WHERE clause
        if sql_filter.strip().startswith("WHERE"):
            artist_query += f" AND {sql_filter[6:]}"
        else:
            artist_query += f" AND {sql_filter}"
        
    artist_query += " GROUP BY 1 ORDER BY total_ms DESC LIMIT 50"
    
    artist_data = load_data(artist_query)
    
    if len(artist_data) > 0:
        artist_with_tooltip = artist_data.with_columns([
            pl.struct(['artist', 'total_ms', 'play_count']).map_elements(
                lambda x: format_item_tooltip(x['artist'], x['total_ms'], x['play_count']),
                return_dtype=pl.Utf8
            ).alias('item_tooltip')
        ])
        
        chart = create_chart(artist_with_tooltip, "top_artists")
        if chart:
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No artist data available for the selected filters.")
        
    # Artist listening trends over time
    st.subheader("Artist Listening Trends")
    
    artist_trends_query = """
        SELECT 
            DATE_TRUNC('month', ts) as month,
            artist,
            COUNT(*) as plays,
            SUM(ms_played) as total_ms
        FROM streaming_history
        WHERE artist IS NOT NULL
    """
    
    if sql_filter:
        # Add AND instead of overriding the WHERE clause
        if sql_filter.strip().startswith("WHERE"):
            artist_trends_query += f" AND {sql_filter[6:]}"
        else:
            artist_trends_query += f" AND {sql_filter}"
        
    artist_trends_query += """
        GROUP BY 1, 2
        ORDER BY 1, 4 DESC
    """
    
    artist_trends_data = load_data(artist_trends_query)
    
    if len(artist_trends_data) > 0:
        # Get top 10 artists by total listening time
        top_artists_query = """
            SELECT 
                artist,
                SUM(ms_played) as total_ms
            FROM streaming_history
            WHERE artist IS NOT NULL
        """
        
        if sql_filter:
            # Add AND instead of overriding the WHERE clause
            if sql_filter.strip().startswith("WHERE"):
                top_artists_query += f" AND {sql_filter[6:]}"
            else:
                top_artists_query += f" AND {sql_filter}"
            
        top_artists_query += " GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
        
        top_artists = load_data(top_artists_query)
        
        if len(top_artists) > 0:
            # Filter trends data to only include top artists
            artist_list = top_artists['artist'].to_list()
            filtered_trends = artist_trends_data.filter(pl.col('artist').is_in(artist_list))
            
            # Create the chart
            artist_chart = alt.Chart(filtered_trends).mark_line(point=True).encode(
                x=alt.X('month:T', title='Month'),
                y=alt.Y('total_ms:Q', title='Listening Time'),
                color=alt.Color('artist:N', title='Artist'),
                tooltip=['month:T', 'artist:N', 'plays:Q', 'total_ms:Q']
            ).properties(
                height=400
            ).interactive()
            
            st.altair_chart(artist_chart, use_container_width=True)
        else:
            st.info("No artist trend data available for the selected filters.")
    else:
        st.info("No artist trend data available for the selected filters.")