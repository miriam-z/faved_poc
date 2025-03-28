# backend/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env only once from this file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
BRIEF_PROMPT_PATH = DATA_DIR / "brief_prompt_questions.json"


# API keys and environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = "influencer-submission"  # Using our standardized index name


def print_config_status():
    """Print configuration status to console."""
    print("\n=== Configuration Status ===")
    print(f"OpenAI API Key: {'✓ Loaded' if OPENAI_API_KEY else '✗ Missing'}")
    print(f"Pinecone API Key: {'✓ Loaded' if PINECONE_API_KEY else '✗ Missing'}")
    print(f"Pinecone Environment: {PINECONE_ENVIRONMENT or '✗ Missing'}")
    print(f"Pinecone Index: {PINECONE_INDEX_NAME}")
    print(f"Data Directory: {DATA_DIR}")
    print("========================\n")


# Optionally add more shared constants or paths
