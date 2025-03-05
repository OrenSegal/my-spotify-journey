from dashboard.tabs.shared_imports import *

def render_release_tab(context: Dict[str, Any]):
    """Render the Release Analysis tab content."""
    st.header("Release Analysis")
    
    sql_filter = context.get("sql_filter", "")
    
    # Check if metadata exists
    metadata_query = """
        SELECT COUNT(*) as count
        FROM track_metadata
        WHERE album_release_date IS NOT NULL
    """
    
    metadata_check = load_data(metadata_query)
    
    if len(metadata_check) > 0 and metadata_check[0, 'count'] > 0:
        # Overview of release years
        st.subheader("Release Year Distribution")
        
        # Get overall release year distribution
        release_overview_query = """
            SELECT 
                EXTRACT(YEAR FROM album_release_date) as release_year,
                COUNT(DISTINCT h.spotify_track_uri) as unique_tracks,
                SUM(h.ms_played) as total_ms,
                COUNT(*) as play_count
            FROM streaming_history h
            JOIN track_metadata m ON h.spotify_track_uri = m.spotify_track_uri
            WHERE album_release_date IS NOT NULL 
            AND EXTRACT(YEAR FROM album_release_date) > 1900 
            AND EXTRACT(YEAR FROM album_release_date) <= EXTRACT(YEAR FROM CURRENT_DATE)
        """
        
        if sql_filter:
            # Add AND instead of overriding the WHERE clause
            if sql_filter.strip().startswith("WHERE"):
                release_overview_query += f" AND {sql_filter[6:]}"
            else:
                release_overview_query += f" AND {sql_filter}"
            
        release_overview_query += " GROUP BY 1 ORDER BY 1"
        
        release_overview = load_data(release_overview_query)
        
        if len(release_overview) > 0:
            # Create decade column for grouping
            release_overview = release_overview.with_columns([
                ((pl.col('release_year') / 10).floor() * 10).alias('decade')
            ])
            
            # Create area chart for release years
            years_chart = alt.Chart(release_overview).mark_area(
                opacity=0.7,
                interpolate='monotone'
            ).encode(
                x=alt.X('release_year:Q', title='Release Year', 
                       scale=alt.Scale(zero=False), axis=alt.Axis(format='d')),
                y=alt.Y('total_ms:Q', title='Listening Time'),
                tooltip=['release_year:Q', 'unique_tracks:Q', 'play_count:Q', 'total_ms:Q']
            ).properties(
                height=300
            ).interactive()
            
            st.altair_chart(years_chart, use_container_width=True)
            
            # Group by decade for a bar chart view
            decade_data = release_overview.group_by('decade').agg([
                pl.sum('total_ms').alias('total_ms'),
                pl.sum('play_count').alias('play_count'),
                pl.sum('unique_tracks').alias('unique_tracks')
            ]).sort('decade')
            
            # Create bar chart for decades
            decade_chart = alt.Chart(decade_data).mark_bar().encode(
                x=alt.X('decade:O', title='Decade', axis=alt.Axis(format='d')),
                y=alt.Y('total_ms:Q', title='Listening Time'),
                tooltip=['decade:O', 'unique_tracks:Q', 'play_count:Q', 'total_ms:Q']
            ).properties(
                height=300
            ).interactive()
            
            st.subheader("Listening by Decade")
            st.altair_chart(decade_chart, use_container_width=True)
            
            # Music release years by listening period
            st.subheader("Music Release Years by Listening Period")
            st.write("Shows how your music taste evolves in terms of release years over your listening history")
            
            # Release year distribution query
            release_year_query = """
                SELECT 
                    DATE_TRUNC('month', h.ts) as period,
                    EXTRACT(YEAR FROM m.album_release_date) as release_year,
                    COUNT(*) as count,
                    SUM(h.ms_played) as total_ms
                FROM streaming_history h
                JOIN track_metadata m ON h.spotify_track_uri = m.spotify_track_uri
                WHERE m.album_release_date IS NOT NULL 
                AND EXTRACT(YEAR FROM m.album_release_date) > 1900 
                AND EXTRACT(YEAR FROM m.album_release_date) <= EXTRACT(YEAR FROM CURRENT_DATE)
            """
            
            if sql_filter:
                # Add AND instead of overriding the WHERE clause
                if sql_filter.strip().startswith("WHERE"):
                    release_year_query += f" AND {sql_filter[6:]}"
                else:
                    release_year_query += f" AND {sql_filter}"
                
            release_year_query += " GROUP BY 1, 2 ORDER BY 1, 2"
            
            release_data = load_data(release_year_query)
            
            if len(release_data) > 0:
                plot_release_ridgeline(release_data)
                
                # Add average release year trend
                avg_release_year_query = """
                    SELECT 
                        DATE_TRUNC('month', h.ts) as period,
                        AVG(EXTRACT(YEAR FROM m.album_release_date)) as avg_release_year,
                        MIN(EXTRACT(YEAR FROM m.album_release_date)) as min_release_year,
                        MAX(EXTRACT(YEAR FROM m.album_release_date)) as max_release_year
                    FROM streaming_history h
                    JOIN track_metadata m ON h.spotify_track_uri = m.spotify_track_uri
                    WHERE m.album_release_date IS NOT NULL 
                    AND EXTRACT(YEAR FROM m.album_release_date) > 1900 
                    AND EXTRACT(YEAR FROM m.album_release_date) <= EXTRACT(YEAR FROM CURRENT_DATE)
                """
                
                if sql_filter:
                    # Add AND instead of overriding the WHERE clause
                    if sql_filter.strip().startswith("WHERE"):
                        avg_release_year_query += f" AND {sql_filter[6:]}"
                    else:
                        avg_release_year_query += f" AND {sql_filter}"
                    
                avg_release_year_query += " GROUP BY 1 ORDER BY 1"
                
                avg_release_year = load_data(avg_release_year_query)
                
                if len(avg_release_year) > 0:
                    st.subheader("Average Release Year Trend")
                    st.write("Shows how the average release year of your music changes over time")
                    
                    avg_chart = alt.Chart(avg_release_year).mark_line(point=True).encode(
                        x=alt.X('period:T', title='Listening Period'),
                        y=alt.Y('avg_release_year:Q', title='Avg Release Year', 
                               scale=alt.Scale(zero=False), axis=alt.Axis(format='d')),
                        tooltip=['period:T', 'avg_release_year:Q', 'min_release_year:Q', 'max_release_year:Q']
                    ).properties(
                        height=300
                    ).interactive()
                    
                    st.altair_chart(avg_chart, use_container_width=True)
                
                # Same year analysis
                st.subheader("Contemporary Music Analysis")
                st.write("Shows how often you listen to music released in the same year you were listening")
                
                same_year_query = """
                    WITH yearly_stats AS (
                        SELECT 
                            EXTRACT(YEAR FROM h.ts) as listening_year,
                            COUNT(*) as total_plays,
                            SUM(CASE WHEN EXTRACT(YEAR FROM h.ts) = EXTRACT(YEAR FROM m.album_release_date) THEN 1 ELSE 0 END) as same_year_plays
                        FROM streaming_history h
                        JOIN track_metadata m ON h.spotify_track_uri = m.spotify_track_uri
                        WHERE m.album_release_date IS NOT NULL
                """
                
                if sql_filter:
                    # Add AND instead of overriding the WHERE clause
                    if sql_filter.strip().startswith("WHERE"):
                        same_year_query += f" AND {sql_filter[6:]}"
                    else:
                        same_year_query += f" AND {sql_filter}"
                    
                same_year_query += """
                        GROUP BY 1
                    )
                    SELECT 
                        listening_year as year,
                        total_plays,
                        same_year_plays,
                        (same_year_plays::FLOAT / NULLIF(total_plays, 0) * 100) as percentage
                    FROM yearly_stats
                    ORDER BY 1
                """
                
                same_year_data = load_data(same_year_query)
                
                if len(same_year_data) > 0:
                    plot_same_year_violin(same_year_data)
                    
                    # Add bar chart showing percentage by year
                    same_year_bar = alt.Chart(same_year_data).mark_bar().encode(
                        x=alt.X('year:O', title='Listening Year'),
                        y=alt.Y('percentage:Q', title='Same-year Music Percentage'),
                        tooltip=['year:O', 'total_plays:Q', 'same_year_plays:Q', 'percentage:Q']
                    ).properties(
                        height=300
                    ).interactive()
                    
                    st.altair_chart(same_year_bar, use_container_width=True)
                else:
                    st.info("No same-year analysis data available for the selected filters.")
            else:
                st.info("No release year data available for the selected filters.")
        else:
            st.info("No release year data available for the selected filters.")
    else:
        st.warning("No track metadata with release dates available. Please load metadata using the load_data.py script.")