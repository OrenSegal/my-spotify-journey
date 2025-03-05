from dashboard.tabs.shared_imports import *
from typing import Optional
import os
from backend.llm.openrouter_client import create_openrouter_client

def generate_visualization_code(question: str, df: pl.DataFrame) -> Optional[str]:
    """Generate Altair visualization code using OpenRouter."""
    try:
        # Create OpenRouter client
        client = create_openrouter_client(temperature=0)
        
        # Get the data types in a more descriptive format
        dtype_map = {
            pl.Int64: "integer",
            pl.Float64: "float",
            pl.Utf8: "string",
            pl.Boolean: "boolean",
            pl.Datetime: "datetime",
            pl.Duration: "duration"
        }
        
        schema_info = "\n".join([
            f"- {col}: {dtype_map.get(dtype, str(dtype))}" 
            for col, dtype in zip(df.columns, df.dtypes)
        ])
        
        prompt = f"""Given a polars DataFrame with the following schema:
{schema_info}

Generate Altair code to visualize the answer to this question: {question}

The code should:
1. Use the provided DataFrame 'df'
2. Create an Altair chart using 'alt.Chart(df)'
3. Include appropriate encoding and transformations
4. Only use the available columns and appropriate data types
5. Be complete and executable
6. Return only the code, no explanations
7. Use simple data types (Q for numbers, N for categories, T for dates)

Example format:
alt.Chart(df).mark_bar().encode(
    x='column:Q',
    y='value:Q'
).properties(title='Chart Title')"""

        # Use LangChain's OpenRouter client to make the request
        response = client.invoke(
            [{"role": "user", "content": prompt}]
        )
        
        return response.content
    except Exception as e:
        st.error(f"Error generating visualization: {str(e)}")
        return None

def ensure_compatible_types(df: pl.DataFrame) -> pl.DataFrame:
    """Convert problematic data types to compatible ones."""
    for col in df.columns:
        # Convert any problematic numeric types to float64
        if df[col].dtype in [pl.Int8, pl.Int16, pl.Int32, pl.UInt8, pl.UInt16, pl.UInt32]:
            df = df.with_columns(pl.col(col).cast(pl.Float64))
        # Handle any other specific type conversions here
    return df

def render_polars_ai_tab(context: Dict[str, Any]):
    """Render the PolarsAI tab content."""
    st.title("🤖 PolarsAI Insights")
    st.write("Ask questions about your Spotify data and get AI-generated visualizations using Polars and Altair.")

    sql_filter = context.get("sql_filter", "")
    
    # Initialize session state for question input
    if "polars_ai_question" not in st.session_state:
        st.session_state.polars_ai_question = ""

    # Input for user question with session state persistence
    question = st.text_input(
        "What would you like to visualize?",
        value=st.session_state.polars_ai_question,
        placeholder="Example: Show my top 10 artists by listening time",
        key="polars_ai_question_input"
    )
    # Capture question
    st.session_state.polars_ai_question = question

    # Example questions as buttons
    st.write("Or try one of these examples:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Top artists by play count"):
            st.session_state.polars_ai_question = "Show my top 10 artists by number of plays"
            st.rerun()
    with col2:
        if st.button("Listening by hour of day"):
            st.session_state.polars_ai_question = "Show my listening patterns by hour of the day"
            st.rerun()
    with col3:
        if st.button("Genre distribution"):
            st.session_state.polars_ai_question = "Visualize the distribution of music genres I listen to"
            st.rerun()

    if st.button("Generate Visualization", use_container_width=True):
        if not question:
            st.warning("Please enter a question.")
            return

        # Get the data based on the question
        base_query = """
            SELECT 
                h.*,
                DATE_TRUNC('month', h.ts) as month,
                EXTRACT(YEAR FROM h.ts) as year,
                EXTRACT(DOW FROM h.ts) as weekday,
                EXTRACT(HOUR FROM h.ts) as hour,
                m.album_release_date,
                m.track_popularity,
                m.explicit,
                m.album_type,
                m.total_tracks,
                m.genres,
                m.artist_popularity,
                m.artist_followers
            FROM streaming_history h
            LEFT JOIN track_metadata m ON h.spotify_track_uri = m.spotify_track_uri
        """
        
        if sql_filter:
            if sql_filter.strip().startswith("WHERE"):
                base_query += f" {sql_filter}"
            else:
                base_query += f" WHERE {sql_filter}"

        with st.spinner("Loading data..."):
            # Get data as Polars DataFrame
            df = load_data(base_query)
            
            if len(df) == 0:
                st.warning("No data available for the selected filters.")
                return
            
            # Convert problematic data types
            df = ensure_compatible_types(df)
            
            # Clean up genre data
            if 'genres' in df.columns:
                df = df.with_columns(
                    pl.col('genres').str.replace_all(r'[\[\]\"]', '').alias('genres')
                )
            
            # Check if LLM API key is set
            llm_api_key = os.getenv("LLM_API_KEY")
            if not llm_api_key:
                st.error("LLM API key not found. Please set the LLM_API_KEY environment variable.")
                return

            with st.spinner("Generating visualization..."):
                viz_code = generate_visualization_code(question, df)
                
                if viz_code:
                    try:
                        # Execute the generated code
                        chart = eval(viz_code)
                        
                        # Display the chart
                        st.subheader("Visualization")
                        st.altair_chart(chart, use_container_width=True)
                        
                        # Show the generated code in an expander
                        with st.expander("Show generated code"):
                            st.code(viz_code, language="python")
                            
                        # Show the data in an expander
                        with st.expander("Show data"):
                            st.dataframe(df.head(100))
                    except Exception as e:
                        st.error(f"Error executing visualization code: {str(e)}")
                        st.code(viz_code, language="python")