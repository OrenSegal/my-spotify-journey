import polars as pl
from typing import Dict

def get_altair_type(column_name: str) -> str:
    """Determine the appropriate Altair data type based on column name."""
    column_name = column_name.lower()

    if column_name in ("ts", "date", "period", "month", "year"):
        return "T"  # Temporal
    elif "count" in column_name or "ms" in column_name or "duration" in column_name or "popularity" in column_name or "plays" in column_name or "total" in column_name:
        return "Q"  # Quantitative
    elif "weekday" in column_name or "hour" in column_name:
        return "O" #Ordinal
    else:
        return "N"  # Nominal (default)

# Example usage with a dictionary (you can adapt this as needed)
COLUMN_DATA_TYPES: Dict[str, str] = {
    "ts": "T",
    "track": "N",
    "artist": "N",
    "album": "N",
    "spotify_track_uri": "N",
    "track_uri": "N",
    "artist_genres": "N",
    "total_tracks": "Q",
    "ms_played": "Q",
    "explicit": "N",
    "album_type": "N",
    "duration_ms": "Q",
    "total_ms": "Q",
    "track_popularity": "Q",
    "artist_popularity": "Q",
    "artist_followers": "Q",
    "artist_uri": "N",
    "platform": "N",
    "conn_country": "N",
    "reason_start": "N",
    "reason_end": "N",
    "weekday": "O",
    "hour": "O",
    "count": "Q",
    "avg_duration_min": "Q",
    "plays": "Q",
    "proportion": "Q",
    "period": "T",
    "genre": "N",
    "is_remix": "N",
    "skipped": "N",
    "percentage": "Q",
    "density": "Q",
    "year": "Q",
    "play_count": "Q",
    "unique_tracks": "Q",
    "album_label": "N",
    "track_label": "N",
    "avg_release_year": "Q",
    "min_release_year": "Q",
    "max_release_year":"Q",
    "same_year_plays":"Q",
    "total_plays":"Q",
    "listening_year":"Q",
    "release_year": "Q",
    "decade":"O",
    "unique_artists": "Q",
    "repetitiveness":"Q"
}