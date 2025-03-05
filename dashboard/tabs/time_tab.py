from dashboard.tabs.shared_imports import *

def render_time_tab(context: Dict[str, Any]):
    """Render the Time Analysis tab content."""
    st.header("Time Analysis")
    
    sql_filter = context.get("sql_filter", "")
    
    # Daily patterns query
    daily_patterns_query = """
        SELECT
            EXTRACT(DOW FROM ts) as weekday,
            EXTRACT(HOUR FROM ts) as hour,
            COUNT(*) as count,
            AVG(ms_played)/60000.0 as avg_duration_min
        FROM streaming_history
    """
    
    if sql_filter:
        daily_patterns_query += f" {sql_filter}"
        
    daily_patterns_query += " GROUP BY 1, 2 ORDER BY 1, 2"
    
    daily_patterns = load_data(daily_patterns_query)
    
    if len(daily_patterns) > 0:
        st.subheader("Listening Patterns by Hour and Day")
        plot_weekday_hour_heatmap(daily_patterns)
        
        st.subheader("Listening by Hour (Polar View)")
        # Aggregate by hour for polar chart
        hour_data = daily_patterns.group_by('hour').agg([
            pl.sum('count').alias('count'),
            pl.mean('avg_duration_min').alias('avg_duration_min')
        ]).sort('hour')
        
        plot_hour_polar(hour_data)
    else:
        st.info("No time pattern data available for the selected filters.")
    
    # Listening trends over time
    st.subheader("Listening Trends Over Time")
    
    trends_query = """
        SELECT 
            DATE_TRUNC('day', ts) as ts,
            SUM(ms_played)/60000.0 as ms_played,
            EXTRACT(HOUR FROM ts) as hour,
            SUM(CASE WHEN skipped THEN 1 ELSE 0 END)::FLOAT / NULLIF(COUNT(*), 0) as skip_rate
        FROM streaming_history
    """
    
    if sql_filter:
        trends_query += f" {sql_filter}"
        
    trends_query += " GROUP BY 1, 3 ORDER BY 1"
    
    trends_data = load_data(trends_query)
    
    if len(trends_data) > 0:
        plot_listening_trends(trends_data)
    else:
        st.info("No trend data available for the selected filters.")