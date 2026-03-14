import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    ENABLE_TTS = os.getenv("ENABLE_TTS", "false").lower() == "true"
    DB_PATH = os.getenv("DB_PATH", "data/memory.db")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "05dae85c1eeba9c43924fce31778ce9b")

    def validate(self):
        if not self.GROQ_API_KEY:
            raise ValueError("Missing GROQ_API_KEY in .env")