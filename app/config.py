import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_PATH = PROJECT_ROOT / "afterthought.db"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "").strip() or "mock"
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
GEMMA_MODEL = "gemma-4-26b-a4b-it"
