"""Shared imports for all dashboard tab modules."""
import streamlit as st
import polars as pl
import altair as alt
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from dashboard.data_transformations import (
    format_item_tooltip, 
    safe_metric_value, 
    format_duration_tooltip, 
    format_listening_time
)
from dashboard.db_utils import load_data
from dashboard.components import (
    create_chart, 
    format_metrics_section, 
    create_error_message,
    create_info_message,
    create_header,
    create_container_with_title,
    create_dataframe_display,
    create_download_button
)
from dashboard.visualizations import (
    plot_most_listened_tracks,
    plot_genre_diversity,
    plot_artist_repetitiveness,
    plot_weekday_hour_heatmap,
    plot_hour_polar,
    plot_genres_stacked,
    plot_genres_by_hour,
    plot_genres_evolution,
    plot_release_ridgeline,
    plot_same_year_violin,
    plot_remix_pie,
    plot_skip_pie,
    plot_listening_trends
)