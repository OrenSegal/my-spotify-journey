"""OpenRouter client implementation for LangChain."""
import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_openrouter_client(temperature=0):
    """Create a ChatOpenAI client configured for OpenRouter.
    
    Args:
        temperature: Temperature for generation
        
    Returns:
        ChatOpenAI: A configured LangChain ChatOpenAI client
    """
    # Get API key from environment
    LLM_MODEL = os.getenv("LLM_MODEL")
    LLM_API_KEY = os.environ.get("LLM_API_KEY")
    # Default to OpenRouter's API URL if not specified
    LLM_API_URL = os.environ.get("LLM_API_URL", "https://openrouter.ai/api/v1")
    
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY environment variable not set!")
        raise ValueError("No API key found. Please set the LLM_API_KEY environment variable.")
    
    logger.info(f"Creating OpenRouter client with model: {LLM_MODEL}, API URL: {LLM_API_URL}")
    
    # Define additional parameters for OpenRouter
    default_kwargs = {
        "model": LLM_MODEL,
        "openai_api_key": LLM_API_KEY,
        "openai_api_base": LLM_API_URL,
        "temperature": temperature
    }
    
    # Set HTTP referrer through environment variable for OpenRouter
    # This is required by OpenRouter
    os.environ["HTTP_REFERER"] = os.environ.get("HTTP_REFERER", "https://github.com/OrenSegal/spotify-streaming-journey")
    
    # Create client with minimal configuration
    client = ChatOpenAI(**default_kwargs)
    
    return client