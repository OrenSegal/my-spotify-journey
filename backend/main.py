import os
import sys
import time
import platform
import argparse
import importlib
import subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
import json
import glob
import polars as pl
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.ingestion import router as ingestion_router
from dotenv import load_dotenv
from datetime import datetime, timedelta
from backend.llm.schemas import SpotifyAnalysisResponse
from backend.llm.langchain_integration import SpotifyLangChain
from backend.db.duckdb_helper import get_table_schema, execute_visualization_query, get_db_connection, table_exists, create_tables_if_needed

# --- Setup Project Paths ---
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"Added project root to path: {project_root}")


# --- Load Environment Variables ---
load_dotenv()

app = FastAPI(
    title="Spotify Streaming Journey API",
    description="API for analyzing Spotify streaming history data",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/")
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")

# --- Database Initialization (Simplified) ---
# We *don't* initialize the database here.  Initialization is handled:
# 1. By `load_data.py` if it's run.
# 2. By the ingestion endpoints if files are uploaded.
# 3. As a fallback, during the startup event.

# Add LLM configuration
llm_api_key = os.getenv("LLM_API_KEY")
analysis_chain = SpotifyLangChain(api_key=llm_api_key) if llm_api_key else None

class QuestionRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None

@app.post("/analyze", response_model=SpotifyAnalysisResponse)
async def analyze_question(request: QuestionRequest):
    """Analyze a natural language question about Spotify data."""
    if not analysis_chain:
        raise HTTPException(500, "LLM not configured")
        
    try:
        # Get database connection and schema
        conn = get_db_connection()
        if not conn:
            raise HTTPException(500, "Database connection failed")
            
        schema = get_table_schema(conn)
        
        # Get analysis from LangChain
        response = await analysis_chain.analyze_query(
            question=request.question,
            schema=schema,
            context=request.context,
            executor=lambda sql: execute_visualization_query(conn, sql)
        )
                
        return response
        
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")

# --- API Routes ---
# Include routers (ingestion routes)
app.include_router(ingestion_router)


@app.on_event("startup")
async def startup_event():
    """Initialize the database and check if tables exist."""
    if not table_exists("streaming_history") or not table_exists("track_metadata"):
        print("Database tables not found. Please initialize the database first.")
        print("Run: python load_data.py --force-reload")
    else:
        print("Database initialized and ready")
