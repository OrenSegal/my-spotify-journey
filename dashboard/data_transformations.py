import polars as pl
from datetime import timedelta
import math
from typing import Any, Optional, Dict, Union
import logging

logger = logging.getLogger(__name__)

def format_count(value: Union[int, float]) -> str:
    """Format a number with thousand separators."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "0"
    return f"{int(value):,}"

def format_duration(ms: int) -> str:
    """Format milliseconds to days, hours, minutes."""
    seconds = ms / 1000
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{days}d {hours}h {minutes}m"

def format_item_tooltip(item: str, ms_played: int, count: int) -> str:
    """Format tooltip text for items (tracks, artists, albums)."""
    duration = format_duration_tooltip(ms_played)
    return f"{item}\n{duration}\nPlayed {count:,} times"

def format_duration_tooltip(ms: float) -> str:
    """Format milliseconds into hours and minutes for tooltip."""
    hours = ms / (1000 * 60 * 60)
    whole_hours = int(hours)
    minutes = int((hours - whole_hours) * 60)
    
    if whole_hours > 0:
        return f"Listened to {whole_hours} hours, {minutes} minutes"
    return f"Listened to {minutes} minutes"

def safe_metric_value(df_or_dict: Union[pl.DataFrame, Dict[str, Any]], column: str, default: Any = 0.0) -> Any:
    """Safely extract metric value from DataFrame or dictionary, handling None and empty DataFrames."""
    try:
        # Handle dictionary
        if isinstance(df_or_dict, dict):
            return df_or_dict.get(column, default)
        # Handle polars DataFrame
        elif isinstance(df_or_dict, pl.DataFrame):
            if df_or_dict.is_empty() or column not in df_or_dict.columns:
                return default
            value = df_or_dict[column][0]
            return value if value is not None else default
        # Handle unexpected type
        else:
            logger.warning(f"Unexpected type {type(df_or_dict)} passed to safe_metric_value")
            return default
    except (KeyError, IndexError) as e:
        logger.error(f"Error extracting metric {column}: {e}")
        return default

def format_hours(hours: Optional[float]) -> str:
    """Format hours with fallback, handling None gracefully."""
    if hours is None or (isinstance(hours, float) and math.isnan(hours)):
        return "N/A"
    return f"{hours:.1f} hours"

def format_listening_time(ms):
    """Format milliseconds into a detailed human-readable duration string."""
    if ms is None:
        return "0m"
    
    try:
        # Convert to more readable format
        ms = float(ms)
        seconds = ms / 1000
        minutes = seconds / 60
        hours = minutes / 60
        days = hours / 24
        months = days / 30.44  # Average month length
        
        parts = []
        
        if months >= 1:
            whole_months = int(months)
            days = days % 30.44
            parts.append(f"{whole_months}mo")
        
        if days >= 1:
            whole_days = int(days)
            hours = hours % 24
            parts.append(f"{whole_days}d")
        
        if hours >= 1:
            whole_hours = int(hours)
            minutes = minutes % 60
            parts.append(f"{whole_hours}h")
        
        if minutes >= 1 or not parts:  # Include minutes if it's the only unit or there are remaining minutes
            whole_minutes = int(minutes)
            parts.append(f"{whole_minutes}m")
        
        return " ".join(parts)
    except Exception as e:
        logger.error(f"Error formatting time {ms}: {e}")
        return "0m"