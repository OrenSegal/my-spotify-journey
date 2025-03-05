from pydantic import BaseModel
from typing import Optional, List, Dict, Union, Any

class VisualizationSpec(BaseModel):
    """Specification for a visualization"""
    type: str  # bar, line, scatter, etc.
    title: str
    dimensions: Dict[str, Any]  # x, y, color, etc.
    config: Optional[Dict[str, Any]] = None  # Additional config

class SpotifyAnalysisResponse(BaseModel):
    type: str  # "visualization", "text", "sql", or "error"
    content: Union[str, Dict[str, Any]]  # Text content, error message, or structured data
    sql: Optional[str] = None  # SQL query if applicable
    data: Optional[List[Dict[str, Any]]] = None  # Result data
    visualization: Optional[VisualizationSpec] = None  # Visualization spec