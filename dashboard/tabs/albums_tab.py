from dashboard.tabs.shared_imports import *

def render_albums_tab(context: Dict[str, Any]):
    """Render the Albums tab content."""
    st.header("Top Albums")
    
    sql_filter = context.get("sql_filter", "")
    
    album_query = """
        SELECT 
            album,
            artist,
            SUM(ms_played) as total_ms,
            COUNT(*) as play_count,
            COUNT(DISTINCT track) as unique_tracks
        FROM streaming_history
        WHERE album IS NOT NULL AND album != ''
    """
    
    if sql_filter:
        # Add AND instead of overriding the WHERE clause
        if sql_filter.strip().startswith("WHERE"):
            album_query += f" AND {sql_filter[6:]}"  # Remove the "WHERE" part and add AND
        else:
            album_query += f" AND {sql_filter}"
        
    album_query += " GROUP BY 1, 2 ORDER BY total_ms DESC LIMIT 50"
    
    album_data = load_data(album_query)
    
    if len(album_data) > 0:
        # Create album_label column for display
        album_data = album_data.with_columns([
            (pl.col('album') + ' - ' + pl.col('artist')).alias('album_label')
        ])
        
        # Ensure numeric columns are properly typed
        album_data = album_data.with_columns([
            pl.col('unique_tracks').cast(pl.Int64),
            pl.col('play_count').cast(pl.Int64),
            pl.col('total_ms').cast(pl.Int64)
        ])
        
        album_with_tooltip = album_data.with_columns([
            pl.struct(['album_label', 'total_ms', 'play_count']).map_elements(
                lambda x: format_item_tooltip(x['album_label'], x['total_ms'], x['play_count']),
                return_dtype=pl.Utf8
            ).alias('item_tooltip')
        ])
        
        chart = create_chart(album_with_tooltip, "top_albums")
        if chart:
            st.altair_chart(chart, use_container_width=True)
            
        # Album track distribution
        st.subheader("Album Completion")
        st.write("Shows how completely you listen to albums based on unique tracks vs play count")
        
        # Calculate album completion ratio with proper type casting
        album_completion = album_data.select([
            pl.col('album_label'),
            pl.col('unique_tracks'),
            pl.col('play_count'),
            (pl.col('unique_tracks').cast(pl.Float64) / pl.col('play_count').cast(pl.Float64)).alias('completion_ratio')
        ]).sort('completion_ratio', descending=False).head(20)
        
        # Create bar chart for album completion
        completion_chart = alt.Chart(album_completion).mark_bar().encode(
            x=alt.X('completion_ratio:Q', title='Completion Ratio (lower is more complete album plays)'),
            y=alt.Y('album_label:N', title=None, sort=None),
            tooltip=['album_label', 'unique_tracks', 'play_count', 'completion_ratio']
        ).properties(
            height=min(24 * len(album_completion), 500)
        ).interactive()
        
        st.altair_chart(completion_chart, use_container_width=True)
    else:
        st.info("No album data available for the selected filters.")