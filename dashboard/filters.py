import streamlit as st
from typing import List, Tuple, Dict, Any
from datetime import datetime, date
from dashboard.db_utils import get_date_range
from backend.db.duckdb_helper import get_connection

WEEKDAYS = ["All Days", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_ABBR = ["All", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TIMES_OF_DAY = ["All Day", "12AM-6AM", "6AM-12PM", "12PM-6PM", "6PM-12AM"]
TIME_PERIODS = ["All Time", "Year", "Month", "Week", "Day"]
DEFAULT_TIMEFRAME = "All Time"

# Mapping for SQL queries
WEEKDAY_MAP = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 0, 
               "Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 0}
TIME_RANGES = {"12AM-6AM": (0, 6), "6AM-12PM": (6, 12), "12PM-6PM": (12, 18), "6PM-12AM": (18, 24)}

class FilterState:
    """Manages filter state using Streamlit's session state."""
    
    @staticmethod
    def init_filters(min_date: date, max_date: date) -> None:
        """Initialize filter defaults in session state."""
        if "filters" not in st.session_state:
            st.session_state["filters"] = {
                "timeframe": DEFAULT_TIMEFRAME,
                "time_buckets": [],  # Use multi-select, so default is empty list
                "days": [],  # Use multi-select, so default is empty list
                "date_range": (min_date, max_date)  # Store as datetime objects
            }
    
    @staticmethod
    def get() -> Dict[str, Any]:
        """Get the current filter state."""
        return st.session_state.get("filters", {})
    
    @staticmethod
    def update(key: str, value: Any) -> None:
        """Update a specific filter value."""
        if "filters" not in st.session_state:
            st.session_state["filters"] = {}
        st.session_state["filters"][key] = value
    
    @staticmethod
    def reset(min_date: date, max_date: date) -> None:
        """Reset filters to their default values"""
        st.session_state["filters"] = {
            "timeframe": DEFAULT_TIMEFRAME,
            "time_buckets": [],
            "days": [],
            "date_range": (min_date, max_date)
        }

def on_timeframe_change(section: str) -> None:
    """Handle timeframe changes."""
    FilterState.update("timeframe", st.session_state[f"time_period_select_{section}"])

def on_buckets_change(section: str) -> None:
    """Handle time bucket changes."""
    FilterState.update("time_buckets", st.session_state.get(f"buckets_select_{section}", []))

def on_days_change(section: str) -> None:
    """Handle day changes."""
    FilterState.update("days", st.session_state.get(f"days_select_{section}", []))

def on_date_range_change(section: str) -> None:
    """Handle the date range changes"""
    FilterState.update("date_range", st.session_state.get(f"date_range_select_{section}"))

def shared_filters(section: str = "global") -> Dict[str, Any]:
    """Shared filter component for Streamlit, supporting date range."""
    # Get database connection
    conn = get_connection()
    if not conn:
        st.error("Could not connect to database")
        return {"timeframe": DEFAULT_TIMEFRAME, "time_buckets": [], "days": []}
        
    # Call get_date_range without passing the connection parameter
    min_date, max_date = get_date_range()
    
    FilterState.init_filters(min_date, max_date)
    filters = FilterState.get()
    
    with st.sidebar:
        st.selectbox(
            "Time Period",
            TIME_PERIODS,
            key=f"time_period_select_{section}",
            index=TIME_PERIODS.index(filters["timeframe"]),
            on_change=on_timeframe_change,
            args=(section,)
        )
        
        if filters["timeframe"] == "All Time":
            with st.expander("Custom Date Range"):
                selected_range = st.date_input(
                    "Select Date Range:",
                    value=filters["date_range"],
                    min_value=min_date,
                    max_value=max_date,
                    key=f"date_range_select_{section}",
                    on_change=on_date_range_change,
                    args=(section,)
                )
                
                if isinstance(selected_range, tuple) and len(selected_range) == 2:
                    FilterState.update("date_range", selected_range)
        
        st.multiselect(
            "Time of Day",
            TIMES_OF_DAY[1:],  # Exclude "All Day"
            default=filters["time_buckets"],
            key=f"buckets_select_{section}",
            on_change=on_buckets_change,
            args=(section,)
        )
        
        st.multiselect(
            "Days",
            WEEKDAYS[1:],  # Exclude "All Days"
            default=filters["days"],
            key=f"days_select_{section}",
            on_change=on_days_change,
            args=(section,)
        )
        
        if st.button("Reset Filters"):
            FilterState.reset(min_date, max_date)
            st.experimental_rerun()
    
    return filters

def build_sql_filter(filters: Dict[str, Any], table_prefix: str = "", append_mode: bool = False) -> str:
    """Build SQL WHERE clause from filter settings."""
    conditions = []
    prefix = f"{table_prefix}." if table_prefix else ""
    
    # Date range filter (if using custom date range)
    if filters.get("timeframe") == "All Time" and "date_range" in filters:
        start_date, end_date = filters["date_range"]
        if start_date and end_date:
            conditions.append(f"CAST({prefix}ts AS DATE) BETWEEN '{start_date}' AND '{end_date}'")
            
    # Timeframe filter (simpler alternative to date range)
    elif filters.get("timeframe") != "All Time":
        interval_map = {
            "Year": "1 year", 
            "Month": "1 month",
            "Week": "1 week", 
            "Day": "1 day"
        }
        interval = interval_map.get(filters["timeframe"])
        if interval:
            conditions.append(f"{prefix}ts >= CURRENT_TIMESTAMP - INTERVAL '{interval}'")
    
    # Multi-select days filter
    if filters.get("days"):
        day_nums = [str(WEEKDAY_MAP[day]) for day in filters["days"]]
        conditions.append(f"EXTRACT(DOW FROM {prefix}ts) IN ({','.join(day_nums)})")
    
    # Multi-select time buckets filter
    if filters.get("time_buckets"):
        time_conditions = []
        for bucket in filters["time_buckets"]:
            if bucket in TIME_RANGES:
                start_hour, end_hour = TIME_RANGES[bucket]
                time_conditions.append(f"(EXTRACT(HOUR FROM {prefix}ts) BETWEEN {start_hour} AND {end_hour})")
        if time_conditions:
            conditions.append(f"({' OR '.join(time_conditions)})")
    
    if not conditions:
        return ""
        
    join_word = "AND" if append_mode else "WHERE"
    return f"{join_word} " + " AND ".join(conditions)

def get_filter_description(filters: Dict[str, Any]) -> str:
    """Generate a human-readable description of the current filters."""
    descriptions = []
    
    if filters.get("timeframe") != "All Time":
        descriptions.append(f"Time Period: {filters['timeframe']}")
    elif "date_range" in filters:
        start_date, end_date = filters["date_range"]
        descriptions.append(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    if filters.get("days"):
        descriptions.append(f"Days: {', '.join(filters['days'])}")
        
    if filters.get("time_buckets"):
        descriptions.append(f"Times: {', '.join(filters['time_buckets'])}")
        
    if not descriptions:
        return "No filters applied"
        
    return " • ".join(descriptions)