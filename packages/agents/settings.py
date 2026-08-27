"""Agent environment settings (non-LLM). LLM uses packages.agents.llm.config."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    identify_max_docs: int = Field(default=3, alias="IDENTIFY_MAX_DOCS")


def get_agent_settings() -> AgentSettings:
    return AgentSettings()
