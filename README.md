# spotify-streaming-journey
=======
# 🎵 Spotify Streaming Journey

A versatile, LLM-powered dashboard for analyzing and visualizing my Spotify listening history with AI-powered insights.

## Features

- 📊 **Comprehensive Data Analysis**: Analyze your Spotify streaming history across multiple dimensions:
  - Artist preferences and listening patterns
  - Album and track statistics
  - Genre distribution and evolution
  - Time-based listening patterns
  - Release year analysis
  - Skip rates and completion statistics

- 🤖 **AI-Powered Insights**:
  - Natural language queries using LangChain-based LLM integration
  - PolarsAI visualization generation
  - Automated data analysis and pattern detection

- 📈 **Interactive Visualizations**:
  - Rich, interactive charts using Altair
  - Customizable filters and time ranges
  - Real-time data exploration

- 🔍 **Advanced Filtering**:
  - Time-based filtering
  - Artist/track/album filtering
  - Genre-based filtering
  - Custom SQL query support

## Tech Stack

- **Backend**:
  - Python
  - DuckDB for high-performance analytics
  - OpenAI integration for AI features
  - LangChain for LLM orchestration

- **Frontend**:
  - Streamlit for interactive dashboard
  - Altair for data visualization
  - Polars for efficient data manipulation

## Project Structure

```
spotify-streaming-journey/
├── backend/               # Backend logic and data processing
│   ├── db/               # Database operations
│   └── llm/              # AI/LLM integration
├── dashboard/            # Streamlit dashboard
│   ├── components/       # Reusable UI components
│   ├── tabs/            # Dashboard tab modules
│   └── visualizations.py # Visualization functions
├── data/                # Data storage
│   ├── metadata/        # Track metadata
│   └── Streaming_History/ # Spotify streaming history
└── tests/              # Test suite
```

## Getting Started

1. **Prerequisites**:
   - Python 3.12 or higher
   - Spotify streaming history data
   - OpenAI API key for AI features

2. **Installation**:
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/spotify-streaming-journey.git
   cd spotify-streaming-journey

   # Install dependencies
   pip install -e .
   ```

3. **Configuration**:
   - Create a `.env` file with your OpenAI API key:
     ```
     LLM_API_KEY=your_api_key_here
     LLM_MODEL=your_model_name_here
     ```
   - Place your Spotify data in the `data/` directory

4. **Running the Dashboard**:
   ```bash
   python -m streamlit run dashboard/streamlit_app.py
   ```

## Dashboard Tabs

1. **Overview**: General statistics and key metrics
2. **Ask the LLM**: Natural language queries about your listening history
3. **PolarsAI**: AI-generated visualizations using Polars and Altair
4. **Artists**: Deep dive into artist listening patterns
5. **Albums**: Album-based analysis
6. **Tracks**: Track-level statistics
7. **Time Analysis**: Temporal listening patterns
8. **Genres**: Genre distribution and evolution
9. **Release Analysis**: Music release year patterns
10. **Stats**: Advanced statistics and metrics

## Contributing

Contributions are welcome! Please read our contributing guidelines and code of conduct before submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with Streamlit, Polars, Altair and LangChain
- AI features powered by Google's Gemini
- Data storage and querying powered by DuckDB
>>>>>>> Stashed changes
