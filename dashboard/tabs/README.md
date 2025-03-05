# Dashboard Tabs

This directory contains the individual tab modules for the Spotify Streaming Journey dashboard.

## Structure

Each tab is implemented as a separate module with a main render function:

- `overview_tab.py`: Main dashboard overview
- `llm_tab.py`: AI-powered insights using LLM
- `artists_tab.py`: Artist analysis
- `albums_tab.py`: Album analysis
- `tracks_tab.py`: Track analysis
- `time_tab.py`: Time-based analysis
- `genres_tab.py`: Genre analysis
- `release_tab.py`: Release year analysis
- `stats_tab.py`: General statistics

## Common Imports

All tabs share common imports through `shared_imports.py`, which provides:
- Standard libraries (streamlit, polars, altair)
- Data transformation utilities
- Database utilities
- Visualization functions
- Component utilities

## Usage

Each tab module exports a single render function that takes a context dictionary:

```python
def render_*_tab(context: Dict[str, Any]):
    """Render the tab content."""
    # Access filtered data using context["sql_filter"]
    # Access filter settings using context["filters"]
    # Access table information using context["table_counts"]
```

The context dictionary provides:
- `sql_filter`: Current SQL WHERE clause based on user filters
- `filters`: Current filter settings (timeframe, days, etc.)
- `table_counts`: Row counts for main database tables