"""OSINT environment settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


class OsintSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.is_file() else None,
        extra="ignore",
    )

    identify_live_search: bool = Field(default=False, alias="IDENTIFY_LIVE_SEARCH")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    greynoise_api_key: str = Field(default="", alias="GREYNOISE_API_KEY")
    osint_extractor: str = Field(default="tavily", alias="OSINT_EXTRACTOR")
    firecrawl_api_key: str = Field(default="", alias="FIRECRAWL_API_KEY")


def get_osint_settings() -> OsintSettings:
    return OsintSettings()
