import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Document Assistant (RAG)"
    API_V1_STR: str = "/api"
    VECTOR_STORE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "vector_store"))
    COLLECTION_NAME: str = "fastapi_docs"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:1.5b"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501", "*"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
