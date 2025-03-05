import altair as alt
import polars as pl
import streamlit as st
from typing import Dict, Any, Optional, List
from dashboard.chart_config import CHART_CONFIGS
from dashboard.data_transformations import format_listening_time, safe_metric_value #import format functions

# Constants
CATEGORY_COLORS = alt.Scale(scheme='category20')
SEQUENTIAL_COLORS = alt.Scale(scheme='viridis')
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def create_chart(df: pl.DataFrame, chart_type: str, params: dict = None) -> Optional[alt.Chart]:
    """Create an Altair chart based on type and parameters."""
    if params is None:
        params = {}

    if df.is_empty():
        return alt.Chart(pl.DataFrame()).mark_text().encode(
            text=alt.value("No data available for this chart.")
        )

    chart_creation_func = {
        "top_tracks": _create_top_tracks_chart,
        "artist_popularity": _create_artist_popularity_chart,
        "punch_card": _create_punch_card_chart,
        "genre_evolution": _create_genre_evolution_chart,
        "polar_hour": _create_polar_hour_chart,
        "ridgeline_year": _create_ridgeline_year_chart,
        "remix_pie": _create_remix_pie_chart,
        "skip_pie": _create_skip_pie_chart,
        "listening_trends_scatter":_create_listening_trends_scatter,
        "top_artists": _create_top_artists_chart,
        "top_albums": _create_top_albums_chart,
        "top_genres": _create_top_genres_chart

    }.get(chart_type)

    if chart_creation_func:
        try:
            return chart_creation_func(df)
        except Exception as e:
            print(f"Error creating chart: {e}")  # Debugging
            return alt.Chart(pl.DataFrame()).mark_text().encode(
                text=alt.value(f"Error creating chart: {str(e)}")
            )
    else:
        return alt.Chart(df).mark_bar().encode(
            x=':T', y=':Q'  # Generic chart as fallback
        )

def _create_top_tracks_chart(df: pl.DataFrame) -> alt.Chart:
    """Create top tracks chart."""
    df = df.with_columns([
        (pl.col('artist') + ' - ' + pl.col('track')).alias('track_label')
    ])
    return alt.Chart(df).mark_bar().encode(
        x=alt.X("total_ms:Q", title="Total Listening Time (ms)"),
        y=alt.Y("track_label:N", sort="-x", title="Track"),
        color=alt.Color("artist:N", scale=CATEGORY_COLORS),
        tooltip=["track_label:N", "artist:N", "total_ms:Q", "play_count:Q"]
    ).properties(title="Top Tracks", width=600, height=400).interactive()

def _create_top_artists_chart(df: pl.DataFrame) -> alt.Chart:
    """Create top artists chart."""
    return alt.Chart(df).mark_bar().encode(
        x=alt.X("total_ms:Q", title="Total Listening Time (ms)"),
        y=alt.Y("artist:N", sort="-x", title="Artist"),
        tooltip=["artist:N", "total_ms:Q", "play_count:Q", "unique_tracks:Q"]
    ).properties(title="Top Artists", width=600, height=400).interactive()

def _create_top_albums_chart(df: pl.DataFrame) -> alt.Chart:
    """Create top albums chart."""
    return alt.Chart(df).mark_bar().encode(
        x=alt.X("total_ms:Q", title="Total Listening Time (ms)"),
        y=alt.Y("album:N", sort="-x", title="Album"),
        color=alt.Color("artist:N", scale=CATEGORY_COLORS),
        tooltip=["album:N", "artist:N", "total_ms:Q", "play_count:Q", "unique_tracks:Q"]
    ).properties(title="Top Albums", width=600, height=400).interactive()
def _create_top_genres_chart(df: pl.DataFrame) -> alt.Chart:
    return alt.Chart(df).mark_bar().encode(
        x=alt.X("total_ms:Q", title="Total Listening Time (ms)"),
        y=alt.Y("genre:N", sort="-x", title="Genre"),
        tooltip=["genre:N", "total_ms:Q", "play_count:Q", "unique_tracks:Q"]
    ).properties(title="Top Genres", width=600, height=400).interactive()
def _create_artist_popularity_chart(df: pl.DataFrame) -> alt.Chart:
    """Create artist popularity chart."""
    return alt.Chart(df).mark_circle(opacity=0.6).encode(
        x=alt.X("artist_popularity:Q", title="Artist Popularity", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("play_count:Q", title="Number of Plays"),
        size=alt.Size("play_count:Q", scale=alt.Scale(range=[100, 1000])),
        color=alt.Color("artist_popularity:Q", scale=SEQUENTIAL_COLORS),
        tooltip=["artist:N", "artist_popularity:Q", "play_count:Q"]
    ).properties(title="Artist Popularity vs. Play Count", width=500, height=300).interactive()

def _create_punch_card_chart(df: pl.DataFrame) -> alt.Chart:
    """Create punch card chart."""
    return alt.Chart(df).mark_circle().encode(
        x=alt.X("hour:O", title="Hour of Day"),
        y=alt.Y("weekday:O", title="Day of Week", sort=WEEKDAYS),
        size=alt.Size("count:Q", scale=alt.Scale(range=[50, 500])),
        color=alt.Color("avg_duration_min:Q", scale=SEQUENTIAL_COLORS),
        tooltip=["weekday:O", "hour:O", "count:Q", "avg_duration_min:Q"]
    ).properties(title="Listening Patterns by Hour and Day", width=700, height=300).interactive()

def _create_genre_evolution_chart(df: pl.DataFrame) -> alt.Chart:
    """Create genre evolution chart."""
    return alt.Chart(df).mark_area().encode(
        x=alt.X("period:T", title="Time"),
        y=alt.Y("plays:Q", stack="normalize", title="Proportion of Plays"),
        color=alt.Color("genre:N", scale=CATEGORY_COLORS),
        tooltip=["period:T", "genre:N", "plays:Q", "proportion:Q"]
    ).properties(title="Genre Evolution Over Time", width=700, height=400).interactive()

def _create_polar_hour_chart(df: pl.DataFrame) -> alt.Chart:
    """Create polar hour chart."""
    return alt.Chart(df).mark_arc(innerRadius=20).encode(
        theta=alt.Theta("hour:O", scale=alt.Scale(domain=list(range(24)))),
        radius=alt.Radius("count:Q", scale=alt.Scale(type="sqrt")),
        color=alt.Color("count:Q", scale=SEQUENTIAL_COLORS),
        tooltip=["hour:O", "count:Q"]
    ).properties(title="Listening Distribution by Hour", width=400, height=400).configure_view(stroke=None).interactive()

def _create_ridgeline_year_chart(df: pl.DataFrame) -> alt.Chart:
    """Create ridgeline chart for album release years."""
    return alt.Chart(df).transform_density(
        'year',
        as_=['year', 'density'],
        groupby=['year'],
        steps=100,
        extent=[1950, 2024]  # Adjust as needed
    ).mark_area(
        interpolate='monotone',
        fillOpacity=0.6,
        stroke='lightgray',
        strokeWidth=0.5
    ).encode(
         x=alt.X('year:Q', title='Release Year', scale = alt.Scale(domain=[1950,2024])),
        y=alt.Y('year:N', title='Year', axis=alt.Axis(domain=False, tickSize=0), sort='descending'),
        color=alt.Color('year:N', scale=alt.Scale(scheme='viridis'), legend=None),
        size=alt.Size('count:Q', title='Number of Tracks', scale = alt.Scale(range=[0,50])),
        tooltip = ['year:Q', 'density:Q']
    ).properties(title="Release Year Distribution", width=700, height=400)

def _create_remix_pie_chart(df: pl.DataFrame) -> alt.Chart:
    """Create remix pie chart."""
    return alt.Chart(df).mark_arc(innerRadius=50).encode(
        theta=alt.Theta("count:Q"),
        color=alt.Color("is_remix:N", scale=alt.Scale(domain=['Original', 'Remix'], range=['#1db954', '#ff6b6b'])),
        tooltip=["is_remix:N", "count:Q", "percentage:Q"]
    ).properties(title="Remix vs. Original Tracks", width=300, height=300)

def _create_skip_pie_chart(df: pl.DataFrame) -> alt.Chart:
    """Create skip pie chart."""
    return alt.Chart(df).mark_arc(innerRadius=50).encode(
        theta=alt.Theta("count:Q"),
        color=alt.Color("skipped:N", scale=alt.Scale(domain=['Completed', 'Skipped'], range=['#1db954', '#ff6b6b'])),
        tooltip=["skipped:N", "count:Q", "percentage:Q"]
    ).properties(title="Completed vs. Skipped Tracks", width=300, height=300)

def _create_listening_trends_scatter(df: pl.DataFrame) -> alt.Chart:
    return alt.Chart(df).mark_circle(opacity=0.6).encode(
        x=alt.X('hour:Q', title='Hour of Day'),
        y=alt.Y('weekday:O', title='Day of Week'),
        size=alt.Size('count:Q', legend=alt.Legend(title='Plays')),
        color=alt.Color('avg_duration_min:Q',
                       scale=alt.Scale(scheme='viridis'),
                       legend=alt.Legend(title='Avg Duration (min)')),
        tooltip=['weekday:O', 'hour:Q', 'count:Q', 'avg_duration_min:Q']
    ).properties(title="Listening Trends by Hour and Day", width=700, height=400).interactive()

def format_metrics_section(overview_stats: pl.DataFrame) -> None:
    """Format and display overview metrics with proper spacing and styling."""
    if overview_stats.is_empty():
        st.info("No data available to display metrics.")
        return

    # --- Apply custom styling to metrics ---
    st.markdown(
        """
        <style>
        div[data-testid="metric-container"] {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f0f2f6; /* Light gray background */
            margin-bottom: 1rem; /* Add space between metric containers */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Total Listening Time
    total_ms = safe_metric_value(overview_stats, 'total_hours')
    display_value = format_listening_time(total_ms*1000*3600) if total_ms and total_ms > 0 else "0m"
    st.metric("Total Listening Time", display_value)


    col1, col2, col3, col4 = st.columns(4)
    with col1:
      st.metric("Unique Artists", f"{int(safe_metric_value(overview_stats, 'unique_artists', 0)):,}")
    with col2:
      st.metric("Unique Tracks", f"{int(safe_metric_value(overview_stats, 'unique_tracks',0)):,}")
    with col3:
        st.metric("Unique Albums", f"{int(safe_metric_value(overview_stats, 'unique_albums',0)):,}")
    with col4:
        st.metric("Unique Genres", f"{int(safe_metric_value(overview_stats, 'unique_genres',0)):,}")

def create_error_message(message: str) -> None:
    """Display an error message."""
    st.error(f"⚠️ {message}")

def create_info_message(message: str) -> None:
    """Display an info message."""
    st.info(f"ℹ️ {message}")

def create_header(title: str, description: str = "", level: int = 2) -> None:
    """Create a header with optional description."""
    if level == 1:
        st.title(title)
    elif level == 2:
        st.header(title)
    elif level == 3:
        st.subheader(title)
    else:
        st.markdown(f"{'#' * level} {title}")
    if description:
        st.write(description)

def create_container_with_title(title: str, level: int = 3) -> st.delta_generator.DeltaGenerator:
    """Create a container with a title."""
    create_header(title, level=level)
    return st.container()

def create_dataframe_display(df: pl.DataFrame, title: str = "", use_expander: bool = False, expanded: bool = False, height:int = None) -> None:
    """Display a DataFrame with consistent styling and title."""
    if df.is_empty():
        create_info_message("No data available to display.")
        return
    if use_expander:
        with st.expander(title, expanded=expanded):
            st.dataframe(df, use_container_width=True, height=height)
    else:
        if title:
            st.subheader(title)
        st.dataframe(df, use_container_width=True, height=height)

def create_download_button(df: pl.DataFrame, file_name: str, label: str = "Download data", mime_type: str = "text/csv") -> None:
    """Create a download button for a DataFrame."""
    if not df.is_empty():
        st.download_button(
            label=label,
            data=df.write_csv().encode('utf-8'),
            file_name=file_name,
            mime=mime_type,
        )

def render_database_info(table_counts: Dict[str, int], sql_filter: str, filters: Dict[str, Any]) -> None:
    """Render database information section."""
    st.subheader("Database Information")
    
    # Display current table counts
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Streaming History Entries", f"{safe_metric_value(table_counts, 'history_count', 0):,}")
    with col2:
        st.metric("Track Metadata Entries", f"{safe_metric_value(table_counts, 'metadata_count', 0):,}")
    with col3:
        st.metric("Genre Mappings", f"{safe_metric_value(table_counts, 'genre_track_count', 0):,}")
    
    # Display current filters
    from dashboard.filters import get_filter_description
    st.markdown("**Active Filters:**")
    st.info(get_filter_description(filters))
    
    if sql_filter:
        with st.expander("Show SQL Filter"):
            st.code(sql_filter, language="sql")