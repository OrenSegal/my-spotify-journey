"""LangChain implementation for Spotify analysis."""
import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable, Tuple
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
import polars as pl
from backend.llm.schemas import SpotifyAnalysisResponse
from backend.llm.openrouter_client import create_openrouter_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class SpotifyAnalysisChain:
    """Chain for analyzing Spotify data using LLMs."""
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        """Initialize the chain with API key and optional model name."""
        self.api_key = api_key
        self.model_name = model_name or os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.client = create_openrouter_client(temperature=0)
        
        # Load prompts from templates
        self.analysis_template = """
You are an analytics assistant specializing in Spotify streaming history data.
Given a user's question about their Spotify listening data, generate insights or visualizations.
Use the provided database schema and SQL to answer questions accurately.

Database Schema:
{schema}

User Question: {question}

First, think about what data to query to answer this question.
Then, write a SQL query that will extract the necessary data from the database.
Use only tables and columns specified in the schema.

The goal is to either:
1. Generate a text response with insights about the user's listening habits
2. Provide a visualization (in Altair JSON spec) that answers the user's question

Your response should be in JSON format with these fields:
- type: "text" for insights, "visualization" for charts, "error" for issues
- content: text answer, Altair spec for visualization, or error message
- sql: the SQL query you used to get the data

Examples:
- "What are my top 5 artists?" → Bar chart of top artists by play count
- "When do I listen to music most?" → Time analysis visualization
- "What's my favorite genre?" → Text insight or pie chart of genres

Be concise but informative.
"""

    async def analyze(self, question: str, schema: str) -> SpotifyAnalysisResponse:
        """Analyze a question about Spotify data.
        
        Args:
            question: The user's question
            schema: The database schema as SQL CREATE statements
            
        Returns:
            SpotifyAnalysisResponse object with analysis results
        """
        try:
            # Create messages for the LLM
            messages = [
                {"role": "system", "content": self.analysis_template.format(
                    schema=schema,
                    question=question
                )}
            ]
            
            # Log what we're doing
            logger.info(f"Analyzing question: {question}")
            
            # Get response from OpenRouter
            response = self.client.invoke(messages)
            
            # Parse the response content
            response_text = response.content
            
            # Try to parse as JSON
            try:
                # Sometimes LLMs wrap JSON in markdown code blocks, try to extract
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                result = json.loads(response_text)
                
                # Build the response object
                analysis_response = SpotifyAnalysisResponse(
                    type=result.get("type", "text"),
                    content=result.get("content", ""),
                    sql=result.get("sql", ""),
                    data=None  # We'll populate this later if needed
                )
                
                # If it's a visualization, execute the SQL to get the data
                if analysis_response.type == "visualization" and analysis_response.sql:
                    # This will be handled by the caller
                    pass
                    
                return analysis_response
                
            except json.JSONDecodeError:
                # If we can't parse JSON, return the raw text
                logger.error(f"Failed to parse JSON response: {response_text}")
                return SpotifyAnalysisResponse(
                    type="error",
                    content="Failed to parse LLM response as JSON.",
                    sql="",
                    data=None
                )
                
        except Exception as e:
            logger.error(f"Error in analyze: {e}")
            return SpotifyAnalysisResponse(
                type="error",
                content=f"An error occurred: {str(e)}",
                sql="",
                data=None
            )

    async def analyze_query(self, question: str, schema: Dict[str, str], context: Optional[Dict[str, Any]] = None, 
                      executor: Optional[Callable[[str], pl.DataFrame]] = None) -> SpotifyAnalysisResponse:
        """Analyze a query with schema dictionary and execute SQL if provided.
        
        Args:
            question: The user's question
            schema: Dictionary mapping table names to their column schemas
            context: Optional context information to include
            executor: Function to execute SQL queries
            
        Returns:
            SpotifyAnalysisResponse with analysis and optional data
        """
        # Convert schema dictionary to SQL CREATE statements
        schema_sql = ""
        for table, columns in schema.items():
            schema_sql += f"CREATE TABLE {table} (\n"
            for i, (col_name, col_type) in enumerate(columns.items()):
                schema_sql += f"    {col_name} {col_type}"
                if i < len(columns) - 1:
                    schema_sql += ","
                schema_sql += "\n"
            schema_sql += ");\n\n"
        
        # Get base analysis
        response = await self.analyze(question, schema_sql)
        
        # If we have a SQL query and executor, run it
        if response.sql and executor and response.type != "error":
            try:
                df = executor(response.sql)
                if not df.is_empty():
                    # Convert to dict for JSON serialization
                    records = []
                    for row in df.iter_rows(named=True):
                        records.append({k: v for k, v in row.items()})
                    response.data = records
            except Exception as e:
                logger.error(f"Error executing SQL: {e}")
                response.type = "error"
                response.content = f"Error executing SQL query: {str(e)}"
        
        return response