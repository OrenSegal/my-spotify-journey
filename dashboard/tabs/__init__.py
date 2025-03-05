"""Tab modules for the Spotify Streaming Journey dashboard."""

from .overview_tab import render_overview_tab
from .llm_tab import render_llm_tab
from .artists_tab import render_artists_tab
from .albums_tab import render_albums_tab
from .tracks_tab import render_tracks_tab
from .time_tab import render_time_tab
from .genres_tab import render_genres_tab
from .release_tab import render_release_tab
from .stats_tab import render_stats_tab
from .polars_ai_tab import render_polars_ai_tab

__all__ = [
    'render_overview_tab',
    'render_llm_tab',
    'render_artists_tab',
    'render_albums_tab',
    'render_tracks_tab',
    'render_time_tab',
    'render_genres_tab',
    'render_release_tab',
    'render_stats_tab',
    'render_polars_ai_tab'
]