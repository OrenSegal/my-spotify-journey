"""LangChain implementation for Spotify data analysis."""

import os
import logging
from typing import Dict, List, Any, Optional, Callable
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from backend.llm.schemas import SpotifyAnalysisResponse, VisualizationSpec
from backend.llm.openrouter_client import create_openrouter_client
import json

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langchain_integration")

# Templates for different stages of the analysis
SCHEMA_ANALYZER_TEMPLATE = """You are analyzing the user's listening history data.
Given the schema below, identify the relevant tables, columns, and altair visualization for this question.
SCHEMA:
{schema}
QUESTION: {question}
Consider:
1. Which tables and columns are needed
2. What type of analysis is required
3. What visualization would best show the results
Return ONLY a valid JSON object with the following structure:
{{
    "tables": ["table_names"],
    "columns": ["column_names"],
    "analysis_type": "aggregation/trend/comparison/etc",
    "visualization": {{
        "type": "bar/stacked bar/line/scatter/pie/heatmap/polar bar/ridgeline plot chart",
        "dimensions": {{
            "x": {{"field": "column_name", "type": "temporal/ordinal/quantitative/nominal"}},
            "y": {{"field": "column_name", "type": "quantitative"}},
            "color": {{"field": "column_name", "type": "nominal"}}
        }}
    }}
}}
Important: Your response must be a valid JSON object. Do not include any explanation or text outside of the JSON structure."""

SQL_GENERATOR_TEMPLATE = """Generate a DuckDB SQL query for this analysis.
SCHEMA:
{schema}
QUESTION: {question}
ANALYSIS:
{analysis}
CONTEXT:
{context}

Important guidelines:
1. Use only tables and columns from the schema.
2. Always include explicit column names in your SELECT clause, avoid using '*'.
3. For time-series data, use appropriate grouping (e.g., DATE_TRUNC).
4. For aggregations, use appropriate aggregation functions (SUM, COUNT, AVG, etc.).
5. Alias columns with clear, descriptive names.
6. Include appropriate WHERE clauses to filter the data if needed.
7. If using JOINs, ensure the join conditions are correct.
8. Limit results to a reasonable number if returning many rows (e.g., LIMIT 50).
9. For time calculations, convert milliseconds to more readable units when appropriate.

Return only the SQL query."""

class SpotifyLangChain:
    """LangChain implementation for Spotify data analysis."""
    
    def __init__(self, api_key: str, model_name: str = None):
        """Initialize the LangChain implementation.
        
        Args:
            api_key: OpenRouter API key
            model_name: Model to use (defaults to value from LLM_MODEL env var)
        """
        # We need to set the API key in the environment for the client function to use
        os.environ["LLM_API_KEY"] = api_key
        
        # Use model from params or env var
        model = model_name or os.environ.get("LLM_MODEL")
        
        # Initialize LLM using our simplified function
        self.llm = create_openrouter_client(temperature=0)
        self.setup_chains()

    def setup_chains(self):
        """Initialize the analysis chains."""
        # Schema analysis chain
        self.schema_analyzer = PromptTemplate(
            template=SCHEMA_ANALYZER_TEMPLATE,
            input_variables=["schema", "question"]
        ) | self.llm | StrOutputParser()

        # SQL generation chain
        self.sql_generator = PromptTemplate(
            template=SQL_GENERATOR_TEMPLATE,
            input_variables=["schema", "question", "analysis", "context"]
        ) | self.llm | StrOutputParser()

    async def analyze_query(
        self,
        question: str,
        schema: str,
        context: Optional[Dict[str, Any]] = None,
        executor: Optional[Callable[[str], Dict]] = None
    ) -> SpotifyAnalysisResponse:
        """Process a natural language query through the analysis chain."""
        try:
            # Step 1: Analyze schema and determine approach
            logger.info(f"Analyzing question: {question}")
            schema_analysis = await self.schema_analyzer.ainvoke({
                "schema": schema,
                "question": question
            })
            
            logger.info(f"Raw schema analysis result: {schema_analysis}")

            # Parse analysis results with improved error handling
            try:
                # Try to extract JSON if it's embedded in other text
                analysis_text = schema_analysis.strip()
                
                # Find the first { and last } to extract JSON
                start_idx = analysis_text.find('{')
                end_idx = analysis_text.rfind('}') + 1
                
                if (start_idx >= 0 and end_idx > 0):
                    json_text = analysis_text[start_idx:end_idx]
                    logger.info(f"Extracted JSON: {json_text}")
                    analysis = json.loads(json_text)
                else:
                    # Try parsing the full text as JSON
                    analysis = json.loads(analysis_text)
                
                # Validate required fields
                required_fields = ["tables", "columns", "analysis_type", "visualization"]
                missing_fields = [field for field in required_fields if field not in analysis]
                
                if missing_fields:
                    return SpotifyAnalysisResponse(
                        type="error",
                        content=f"Invalid schema analysis: missing required fields {missing_fields}"
                    )
                    
                # Validate visualization structure
                if not isinstance(analysis["visualization"], dict) or "type" not in analysis["visualization"] or "dimensions" not in analysis["visualization"]:
                    return SpotifyAnalysisResponse(
                        type="error",
                        content="Invalid visualization specification in schema analysis"
                    )
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return SpotifyAnalysisResponse(
                    type="error",
                    content=f"Failed to parse schema analysis: {e}. Raw response: {schema_analysis[:100]}..."
                )
            except Exception as e:
                logger.error(f"Error parsing schema analysis: {e}")
                return SpotifyAnalysisResponse(
                    type="error",
                    content=f"Error parsing schema analysis: {str(e)}"
                )

            # Step 2: Generate SQL
            logger.info("Generating SQL query")
            sql_query = await self.sql_generator.ainvoke({
                "schema": schema,
                "question": question,
                "analysis": json.dumps(analysis, indent=2),
                "context": json.dumps(context) if context else "{}"
            })
            
            # Clean up the SQL query - remove quotes and extra whitespace
            sql_query = sql_query.strip()
            sql_query = sql_query.strip('`').strip("'").strip('"')
            
            logger.info(f"Generated SQL: {sql_query}")

            # If we have an executor, run the query
            if executor and sql_query:
                logger.info("Executing query")
                
                try:
                    # Execute the query through the provided executor
                    result = executor(sql_query)
                    
                    logger.info(f"Query execution result: success={result['success']}, data rows={len(result.get('data', []))}")
                    
                    if not result["success"]:
                        logger.error(f"Query execution failed: {result['error']}")
                        return SpotifyAnalysisResponse(
                            type="error",
                            content=f"Query execution failed: {result['error']}",
                            sql=sql_query
                        )
                    
                    # Check if we have data
                    data = result.get("data", [])
                    if not data:
                        # Try to fix the query if there's no data
                        logger.warning("Query returned no data, trying to fix")
                        
                        # Generate a simpler query
                        simplified_query = await self.generate_simplified_query(
                            schema, question, analysis
                        )
                        
                        if simplified_query and simplified_query != sql_query:
                            logger.info(f"Trying simplified query: {simplified_query}")
                            result = executor(simplified_query)
                            
                            if result["success"] and result.get("data"):
                                logger.info("Simplified query returned data!")
                                sql_query = simplified_query
                                data = result["data"]
                            else:
                                logger.warning("Simplified query also failed, using original response")
                    
                    # Create visualization spec
                    viz_spec = VisualizationSpec(
                        type=analysis["visualization"]["type"],
                        title=question,
                        dimensions=analysis["visualization"]["dimensions"]
                    )

                    logger.info("Analysis complete, returning visualization response")
                    return SpotifyAnalysisResponse(
                        type="visualization",
                        content=f"Analysis of {analysis['analysis_type']}",
                        sql=sql_query,
                        data=result["data"],
                        visualization=viz_spec
                    )
                except Exception as e:
                    logger.error(f"Error during query execution: {e}", exc_info=True)
                    return SpotifyAnalysisResponse(
                        type="error",
                        content=f"Error executing SQL query: {str(e)}",
                        sql=sql_query
                    )
            
            # No executor, just return the SQL
            logger.info("No executor provided, returning SQL response")
            return SpotifyAnalysisResponse(
                type="sql",
                content=sql_query
            )

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return SpotifyAnalysisResponse(
                type="error",
                content=f"Analysis failed: {str(e)}"
            )
    
    async def generate_simplified_query(
        self, 
        schema: str, 
        question: str, 
        analysis: Dict[str, Any]
    ) -> str:
        """Generate a simplified query when the original one returns no data."""
        # Create a simplified prompt for the SQL generator
        simplified_template = """
        The previous query returned no data. Generate a simpler SQL query that is more likely to return results.
        SCHEMA:
        {schema}
        QUESTION: {question}
        ANALYSIS:
        {analysis}
        
        Guidelines:
        1. Remove complex joins or conditions that might be filtering out all data
        2. Use simpler aggregations
        3. Remove or broaden WHERE clauses
        4. Ensure table and column names are correct
        5. Focus on the core tables needed for the question
        6. Consider adding LIMIT to check if any data exists at all
        
        Return ONLY the SQL query.
        """
        
        try:
            prompt = PromptTemplate(
                template=simplified_template,
                input_variables=["schema", "question", "analysis"]
            )
            
            chain = prompt | self.llm | StrOutputParser()
            
            simplified_query = await chain.ainvoke({
                "schema": schema,
                "question": question,
                "analysis": json.dumps(analysis, indent=2)
            })
            
            # Clean up the SQL query
            simplified_query = simplified_query.strip()
            simplified_query = simplified_query.strip('`').strip("'").strip('"')
            
            return simplified_query
        except Exception as e:
            logger.error(f"Failed to generate simplified query: {e}")
            return None
