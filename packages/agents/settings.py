"""Agent / LLM environment settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"

# Match models visible in Groq console (account-specific catalog).
DEFAULT_GROQ_MODEL = "groq/compound-mini"
DEFAULT_GROQ_API_BASE = "https://api.groq.com/openai/v1"

# Try in order when the configured model 404s (deprecated / unavailable).
GROQ_MODEL_FALLBACKS = (
    "groq/compound-mini",
    "groq/compound",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
)


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.is_file() else None,
        extra="ignore",
    )

    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default=DEFAULT_GROQ_MODEL, alias="GROQ_MODEL")
    groq_api_base: str = Field(default=DEFAULT_GROQ_API_BASE, alias="GROQ_API_BASE")


def get_agent_settings() -> AgentSettings:
    return AgentSettings()
