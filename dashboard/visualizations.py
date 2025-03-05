"""
Spotify Dashboard Visualizations Module

This module contains all visualization functions used throughout the dashboard.
Each function focuses on one specific visualization type (Single Responsibility Principle).
"""

import streamlit as st
import altair as alt
import polars as pl
from dashboard.components import create_chart

# Color schemes for consistent visualization
SPOTIFY_COLORS = {
    'green': '#1DB954',
    'black': '#191414',
    'red': '#FF6B6B',
    'blue': '#4A76FF',
    'yellow': '#FFD93D'
}

SEQUENTIAL_COLORS = alt.Scale(scheme='viridis')
CATEGORICAL_COLORS = alt.Scale(scheme='category20')


def format_duration_tooltip(ms: float) -> str:
    """Format milliseconds into hours and minutes for tooltip."""
    hours = ms / (1000 * 60 * 60)
    whole_hours = int(hours)
    minutes = int((hours - whole_hours) * 60)
    
    if whole_hours > 0:
        return f"Listened to {whole_hours} hours, {minutes} minutes"
    return f"Listened to {minutes} minutes"


def create_generic_chart(data: pl.DataFrame, chart_config: dict) -> alt.Chart:
    """Create a chart using the provided configuration."""
    if len(data) == 0:
        return None
        
    base = alt.Chart(data)
    
    # Apply mark configuration
    if isinstance(chart_config["mark"], dict):
        base = base.mark_bar(**chart_config["mark"])
    else:
        base = base.mark_bar()
    
    # Apply encoding configuration
    if "encoding" in chart_config:
        base = base.encode(**chart_config["encoding"])
    
    # Apply size configuration
    if "width" in chart_config:
        base = base.properties(width=chart_config["width"])
    if "height" in chart_config:
        base = base.properties(height=chart_config["height"])
    
    return base.interactive()


def ensure_tooltip(df, tooltip_col='duration_tooltip'):
    """Ensure DataFrame has a tooltip column for duration (DRY principle)."""
    if tooltip_col not in df.columns and 'total_ms' in df.columns:
        return df.with_columns([
            pl.col('total_ms').map_elements(
                format_duration_tooltip,
                return_dtype=pl.Utf8
            ).alias(tooltip_col)
        ])
    return df


def clean_genre(genre: str) -> str:
    """Clean genre strings by removing brackets, quotes, and special characters."""
    if not genre:
        return ""
    # Remove brackets, quotes, and special characters
    cleaned = genre.strip('[]"\'')
    # Remove any remaining special characters
    cleaned = ''.join(char for char in cleaned if char.isalnum() or char.isspace() or char == '-')
    return cleaned.strip()

def preprocess_genres(df: pl.DataFrame) -> pl.DataFrame:
    """Preprocess genre data to ensure clean formatting."""
    if 'genre' in df.columns:
        return df.with_columns([
            pl.col('genre').map_elements(clean_genre).alias('genre')
        ])
    return df


# ===== Bar Charts =====

def plot_most_listened_tracks(df):
    """Bar chart for most listened tracks with labels."""
    df = preprocess_genres(df)
    df = ensure_tooltip(df)
    chart = create_chart(df, "top_tracks")
    if chart:
        st.altair_chart(chart, use_container_width=True)


def plot_top_artists(df):
    """Bar chart for top artists with labels."""
    df = preprocess_genres(df)
    df = ensure_tooltip(df)
    chart = create_chart(df, "top_artists")
    if chart:
        st.altair_chart(chart, use_container_width=True)


def plot_genres_stacked(df):
    """Bar chart for genre distribution."""
    df = preprocess_genres(df)
    df = ensure_tooltip(df)

    # Create bar chart with Spotify styling
    chart = alt.Chart(df).mark_bar(
        color=SPOTIFY_COLORS['green']
    ).encode(
        x=alt.X("total_ms:Q", title="Total Listening Time (ms)"),
        y=alt.Y("genre:N", 
                sort="-x", 
                title="Genre",
                axis=alt.Axis(minExtent=200)),  # Ensure enough space for labels
        tooltip=["genre:N", "total_ms:Q", "play_count:Q", "unique_tracks:Q"]
    ).properties(
        title="Top Genres",
        width=600,
        height={"step": 25}  # Ensure each bar has enough height
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


# ===== Line and Area Charts =====

def plot_genre_diversity(df):
    """Line chart for genre diversity over time."""
    df = preprocess_genres(df)
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("period:T", title="Time Period"),
        y=alt.Y("genre_count:Q", title="Unique Genres"),
        color=alt.value(SPOTIFY_COLORS['blue']),
        tooltip=["period:T", "genre_count:Q"]
    ).properties(
        width=600,
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


def plot_genres_evolution(df):
    """
    Violin plot showing genre proportion distribution over time.
    """
    df = preprocess_genres(df)
    if len(df) == 0:
        return

    # Create the violin plot
    chart = alt.Chart(df).transform_density(
        'proportion',
        as_=['proportion', 'density'],
        extent=[0, 1],
        groupby=['genre']
    ).mark_area(
        orient='horizontal',
        opacity=0.7
    ).encode(
        y=alt.Y(
            'genre:N',
            title='Genre',
            sort=alt.EncodingSortField(field='proportion', op='mean', order='descending')
        ),
        x=alt.X(
            'proportion:Q',
            title='Proportion of Plays',
            axis=alt.Axis(format='%')
        ),
        color=alt.Color(
            'genre:N',
            scale=CATEGORICAL_COLORS,  # Fixed from CATEGORY_COLORS to CATEGORICAL_COLORS
            legend=alt.Legend(title='Genre')
        ),
        tooltip=[
            alt.Tooltip('genre:N', title='Genre'),
            alt.Tooltip('proportion:Q', title='Proportion', format='.1%'),
            alt.Tooltip('plays:Q', title='Plays')
        ]
    ).properties(
        width=700,
        height=400
    ).interactive()

    st.altair_chart(chart, use_container_width=True)


def plot_artist_repetitiveness(df):
    """Line chart for showing artist repetitiveness over time."""
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X('ts:T', title='Date'),
        y=alt.Y('repetitiveness:Q', 
                title='Artist Repetitiveness (%)',
                scale=alt.Scale(domain=[0, 100])),
        color=alt.value(SPOTIFY_COLORS['green']),
        tooltip=[
            alt.Tooltip('ts:T', title='Date'),
            alt.Tooltip('repetitiveness:Q', title='Repetitiveness', format='.1f'),
            alt.Tooltip('total_plays:Q', title='Total Plays'),
            alt.Tooltip('unique_artists:Q', title='Unique Artists')
        ]
    ).properties(
        width=600,
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


# ===== Heatmaps and Time Analysis =====

def plot_weekday_hour_heatmap(df):
    """GitHub-style punch card plot for listening patterns."""
    if len(df) == 0:
        return
        
    # Convert weekday numbers to names for better readability
    weekday_names = {
        0: "Sunday", 1: "Monday", 2: "Tuesday", 
        3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday"
    }
    df = df.with_columns([
        pl.col('weekday').map_elements(
            lambda x: weekday_names.get(x, str(x)),
            return_dtype=pl.Utf8
        ).alias('weekday')
    ])
    
    # Create the bubble plot
    base = alt.Chart(df).encode(
        x=alt.X('hour:O', title='Hour of Day', 
                axis=alt.Axis(labelAngle=0, format='%H')),
        y=alt.Y('weekday:O', title='Day of Week',
                sort=list(weekday_names.values())),
        tooltip=['weekday:N', 'hour:O', 'count:Q', 'avg_duration_min:Q']
    )
    
    # Background heatmap
    heatmap = base.mark_rect().encode(
        color=alt.Color('count:Q', 
                       title='Number of Plays',
                       scale=SEQUENTIAL_COLORS)
    )
    
    # Overlay circles
    circles = base.mark_circle().encode(
        size=alt.Size('count:Q', 
                     title='Number of Plays',
                     scale=alt.Scale(range=[0, 1000]))
    )
    
    # Combine layers
    chart = (heatmap + circles).properties(
        width=600,
        height=300
    ).resolve_scale(
        color='independent',
        size='independent'
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


def plot_hour_polar(df):
    """Polar bar chart for hourly listening distribution."""
    if len(df) == 0:
        return
        
    # Convert hour to radians for polar coordinates
    df = df.with_columns([
        (pl.col('hour') * (2 * 3.14159 / 24)).alias('angle'),
        pl.col('count').alias('radius')
    ])
    
    # Create the polar chart
    chart = alt.Chart(df).mark_arc(innerRadius=20).encode(
        theta=alt.Theta('angle:Q', 
                       scale=alt.Scale(domain=[0, 2 * 3.14159])),
        radius=alt.Radius('radius:Q', 
                         scale=alt.Scale(type='sqrt')),
        color=alt.Color('count:Q', 
                       scale=SEQUENTIAL_COLORS),
        tooltip=['hour:O', 'count:Q']
    ).properties(
        width=400,
        height=400
    ).configure_view(
        strokeWidth=0
    )
    
    st.altair_chart(chart, use_container_width=True)


def plot_genres_by_hour(df):
    """Strip plot with jitter for genre distribution by hour."""
    df = preprocess_genres(df)
    if len(df) == 0:
        return
        
    base = alt.Chart(df).encode(
        x=alt.X('hour:O', title='Hour of Day', 
                axis=alt.Axis(values=list(range(24)))),
        y=alt.Y('genre:N', title='Genre'),
        tooltip=['genre:N', 'hour:O', 'count:Q']
    )
    
    # Background heatmap
    heatmap = base.mark_rect().encode(
        color=alt.Color('count:Q', scale=alt.Scale(scheme='viridis'))
    )
    
    # Points layer
    points = base.mark_circle(size=60).encode(
        opacity=alt.value(0.6)
    ).transform_calculate(
        # Add jitter to hour positions
        hour_jittered='datum.hour + (random() - 0.5) * 0.5'
    )
    
    chart = (heatmap + points).properties(
        width=600,
        height=400
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


# ===== Release Year Analysis =====

def plot_release_ridgeline(df):
    """Ridgeline plot for album release distribution."""
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).transform_density(
        'release_year',
        as_=['release_year', 'density'],
        groupby=['period']
    ).mark_area(
        opacity=0.5,
        interpolate='monotone'
    ).encode(
        alt.X('release_year:Q', title='Release Year'),
        alt.Y('period:O',
              sort=alt.SortField(field='period', order='descending')),
        alt.Y2('density:Q'),
        color='period:O'
    ).properties(
        width=600,
        height=400
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


def plot_release_year_area(df):
    """Area chart for release year distribution."""
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).mark_area(
        opacity=0.7,
        interpolate='monotone'
    ).encode(
        x=alt.X('release_year:Q', title='Release Year', 
                scale=alt.Scale(zero=False), 
                axis=alt.Axis(format='d')),
        y=alt.Y('total_ms:Q', title='Listening Time'),
        tooltip=['release_year:Q', 'unique_tracks:Q', 'play_count:Q', 'total_ms:Q']
    ).properties(
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


def plot_release_year_bar(df):
    """Bar chart for release year by decade."""
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('decade:O', title='Decade', axis=alt.Axis(format='d')),
        y=alt.Y('total_ms:Q', title='Listening Time'),
        tooltip=['decade:O', 'unique_tracks:Q', 'play_count:Q', 'total_ms:Q']
    ).properties(
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


def plot_avg_release_year(df):
    """Line chart for average release year over time."""
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X('period:T', title='Listening Period'),
        y=alt.Y('avg_release_year:Q', title='Avg Release Year', 
                scale=alt.Scale(zero=False), 
                axis=alt.Axis(format='d')),
        tooltip=['period:T', 'avg_release_year:Q', 'min_release_year:Q', 'max_release_year:Q']
    ).properties(
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


def plot_same_year_violin(df):
    """Violin plot for same-year release percentage."""
    if len(df) == 0:
        return
        
    violin_chart = alt.Chart(df).mark_area().encode(
        x=alt.X(
            'density:Q',
            stack='center',
            axis=None
        ),
        y=alt.Y('percentage:Q', 
                title='Same-year Music Percentage', 
                scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('year:N')
    ).transform_density(
        'percentage',
        as_=['percentage', 'density'],
        groupby=['year']
    ).properties(
        width=400,
        height=300
    ).interactive()
    
    st.altair_chart(violin_chart, use_container_width=True)


def plot_same_year_bar(df):
    """Bar chart for same-year release percentage."""
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('year:O', title='Listening Year'),
        y=alt.Y('percentage:Q', title='Same-year Music Percentage'),
        tooltip=['year:O', 'total_plays:Q', 'same_year_plays:Q', 'percentage:Q']
    ).properties(
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


# ===== Pie Charts =====

def plot_remix_pie(df):
    """Pie chart for remix vs original tracks."""
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).mark_arc().encode(
        theta=alt.Theta('count:Q'),
        color=alt.Color('is_remix:N', 
                        scale=alt.Scale(
                            domain=['Original', 'Remix'], 
                            range=['#1db954', '#ff6b6b']
                        )),
        tooltip=[
            alt.Tooltip('is_remix:N'),
            alt.Tooltip('count:Q'),
            alt.Tooltip('percentage:Q', format='.1%')
        ]
    ).properties(
        width=300,
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


def plot_skip_pie(df):
    """Pie chart for skipped vs completed tracks."""
    if len(df) == 0:
        return
        
    chart = alt.Chart(df).mark_arc().encode(
        theta=alt.Theta('count:Q'),
        color=alt.Color('skipped:N', 
                        scale=alt.Scale(
                            domain=['Completed', 'Skipped'], 
                            range=['#1db954', '#ff6b6b']
                        )),
        tooltip=[
            alt.Tooltip('skipped:N'),
            alt.Tooltip('count:Q'),
            alt.Tooltip('percentage:Q', format='.1%')
        ]
    ).properties(
        width=300,
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


# ===== Complex Multi-Chart Visualizations =====

def plot_listening_trends(df):
    """Scatterplot for personal listening trends."""
    if len(df) == 0:
        return
        
    # Create a selection for time window
    brush = alt.selection_interval(encodings=['x'])
    
    # Base chart
    base = alt.Chart(df).encode(
        x=alt.X('ts:T', title='Date'),
        tooltip=[
            alt.Tooltip('ts:T'),
            alt.Tooltip('ms_played:Q', title='Minutes'),
            alt.Tooltip('hour:O'),
            alt.Tooltip('skip_rate:Q', format='.1%')
        ]
    )
    
    # Points
    points = base.mark_circle().encode(
        y=alt.Y('ms_played:Q', title='Minutes Played'),
        color=alt.Color('hour:O', scale=alt.Scale(scheme='viridis')),
        size=alt.Size('skip_rate:Q', scale=alt.Scale(domain=[0, 1]))
    ).add_selection(brush)
    
    # Overview with line
    overview = base.mark_line().encode(
        y=alt.Y('average(ms_played):Q', title='Avg. Minutes')
    ).properties(
        height=60
    ).add_selection(brush)
    
    # Combine charts
    chart = alt.vconcat(
        points.properties(width=600, height=300),
        overview.properties(width=600)
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)


def plot_genre_decade_heatmap(df):
    """Heatmap for genres by decade."""
    if len(df) == 0:
        return
        
    heatmap = alt.Chart(df).mark_rect().encode(
        x=alt.X('decade:O', title='Release Decade', axis=alt.Axis(format='d')),
        y=alt.Y('genre:N', title='Genre'),
        color=alt.Color('total_ms:Q', title='Listening Time', scale=alt.Scale(scheme='viridis')),
        tooltip=['genre:N', 'decade:O', 'total_ms:Q', 'play_count:Q']
    ).properties(
        height=400
    ).interactive()
    
    st.altair_chart(heatmap, use_container_width=True)


def plot_plays_by_day(df):
    """Bar chart for plays by day."""
    if len(df) == 0:
        return
        
    # Convert ms to minutes for better readability
    df = df.with_columns([
        (pl.col('total_ms') / 60000).alias('total_minutes'),
        (pl.col('avg_ms') / 60000).alias('avg_minutes')
    ])
    
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('day:T', title='Date'),
        y=alt.Y('total_minutes:Q', title='Listening Time (minutes)'),
        tooltip=['day:T', 'play_count:Q', 'total_minutes:Q', 'avg_minutes:Q']
    ).properties(
        height=300
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)