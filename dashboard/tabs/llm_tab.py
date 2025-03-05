from dashboard.tabs.shared_imports import *
from dashboard.llm_insights import render_llm_insights_tab

def render_llm_tab(context: Dict[str, Any] = None):
    """Render the LLM (Ask the LLM) tab content."""
    render_llm_insights_tab()