from dotenv import load_dotenv
from pathlib import Path
import os

#Explicit path
env_path = Path(__file__).resolve().parent.parent / '.env'

load_dotenv(dotenv_path=env_path)