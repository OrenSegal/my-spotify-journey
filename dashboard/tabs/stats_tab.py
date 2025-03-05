from dashboard.tabs.shared_imports import *

def render_stats_tab(context: Dict[str, Any]):
    """Render the Stats tab content."""
    st.header("Listening Stats")
    
    sql_filter = context.get("sql_filter", "")
    
    # Artist repetitiveness
    st.subheader("Artist Repetitiveness")
    st.write("Shows how often you listen to the same artists in a single day (higher % = more repetition)")
    
    repetitiveness_query = """
        WITH daily_stats AS (
            SELECT 
                DATE_TRUNC('day', h.ts) as date,
                COUNT(*) as total_plays,
                COUNT(DISTINCT h.artist) as unique_artists
            FROM streaming_history h
            WHERE h.artist IS NOT NULL
    """
    
    if sql_filter and sql_filter.startswith('WHERE'):
        repetitiveness_query += f" AND {sql_filter[6:]}"
    elif sql_filter:
        repetitiveness_query += f" {sql_filter}"
            
    repetitiveness_query += """
            GROUP BY 1
        )
        SELECT 
            date as ts,
            total_plays,
            unique_artists,
            (1 - unique_artists::FLOAT / NULLIF(total_plays, 0)) * 100 as repetitiveness
        FROM daily_stats
        ORDER BY 1
    """
    
    repetitiveness_data = load_data(repetitiveness_query)
    
    if len(repetitiveness_data) > 0:
        plot_artist_repetitiveness(repetitiveness_data)
    else:
        st.info("No repetitiveness data available for the selected filters.")
        
    # Play counts by day
    st.subheader("Play Counts by Day")
    
    plays_by_day_query = """
        SELECT 
            DATE_TRUNC('day', ts) as day,
            COUNT(*) as play_count,
            SUM(ms_played) as total_ms,
            AVG(ms_played) as avg_ms
        FROM streaming_history
    """
    
    if sql_filter:
        plays_by_day_query += f" {sql_filter}"
        
    plays_by_day_query += " GROUP BY 1 ORDER BY 1"
    
    plays_by_day = load_data(plays_by_day_query)
    
    if len(plays_by_day) > 0:
        # Convert ms to minutes for better readability
        plays_by_day = plays_by_day.with_columns([
            (pl.col('total_ms') / 60000).alias('total_minutes'),
            (pl.col('avg_ms') / 60000).alias('avg_minutes')
        ])
        
        # Create the chart
        day_chart = alt.Chart(plays_by_day).mark_bar().encode(
            x=alt.X('day:T', title='Date'),
            y=alt.Y('total_minutes:Q', title='Listening Time (minutes)'),
            tooltip=['day:T', 'play_count:Q', 'total_minutes:Q', 'avg_minutes:Q']
        ).properties(
            height=300
        ).interactive()
        
        st.altair_chart(day_chart, use_container_width=True)
    else:
        st.info("No play count data available for the selected filters.")