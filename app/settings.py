import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv(override=True)

@dataclass
class Settings:
  
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "stub")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")

settings = Settings()
