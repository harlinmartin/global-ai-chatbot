from ai.providers.base import AIProvider
from config import settings


def get_ai_provider() -> AIProvider:
    """
    Returns the correct AI provider based on the AI_PROVIDER env var.
    Swap providers by changing one line in .env — no code changes needed.
    """
    provider = settings.ai_provider.lower()

    if provider == "groq":
        from ai.providers.groq_provider import GroqProvider
        return GroqProvider()

    if provider == "openai":
        from ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if provider == "ollama":
        from ai.providers.ollama_provider import OllamaProvider
        return OllamaProvider()

    raise ValueError(
        f"Unknown AI_PROVIDER '{provider}'. Choose: groq | openai | ollama"
    )
