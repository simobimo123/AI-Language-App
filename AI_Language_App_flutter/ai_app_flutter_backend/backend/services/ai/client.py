import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured in the .env file"
    )


client = genai.Client(api_key=GEMINI_API_KEY)

AI_MODEL = os.getenv("GEMINI_MAIN_MODEL", "gemini-3.6-flash")
AI_CLASSIFIER_MODEL = os.getenv(
    "GEMINI_CLASSIFIER_MODEL",
    "gemini-3.5-flash-lite",
)


