from dotenv import load_dotenv
import os

load_dotenv()


GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
project_id = os.environ.get("PROJECT_ID")
redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
