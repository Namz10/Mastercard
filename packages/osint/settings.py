"""OSINT environment settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OsintSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    identify_live_search: bool = Field(default=False, alias="IDENTIFY_LIVE_SEARCH")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    greynoise_api_key: str = Field(default="", alias="GREYNOISE_API_KEY")
    osint_extractor: str = Field(default="tavily", alias="OSINT_EXTRACTOR")
    firecrawl_api_key: str = Field(default="", alias="FIRECRAWL_API_KEY")


def get_osint_settings() -> OsintSettings:
    return OsintSettings()
