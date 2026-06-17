from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Provider selection: "groq" | "openai" | "ollama"
    ai_provider: str = "groq"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Ollama (local fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    # Database (not used in Phase 1A, ready for 1B)
    database_url: str = "postgresql+asyncpg://chatbot:chatbot_dev_pass@localhost:5432/ai_chatbot"

    # Qdrant (not used in Phase 1A, ready for Phase 3)
    qdrant_url: str = "http://localhost:6333"

    # Security
    jwt_secret: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"

    # Server
    backend_port: int = 8001

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:8081"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def active_model(self) -> str:
        """Model name for the currently selected provider — no client instantiation."""
        return {
            "groq": self.groq_model,
            "openai": self.openai_model,
            "ollama": self.ollama_model,
        }.get(self.ai_provider.lower(), "unknown")

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
