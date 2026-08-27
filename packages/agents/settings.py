"""Identify environment settings (non-LLM). LLM uses packages.agents.llm.config."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IdentifySettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    identify_live_search: bool = Field(default=False, alias="IDENTIFY_LIVE_SEARCH")
    identify_max_candidates: int = Field(default=0, alias="IDENTIFY_MAX_CANDIDATES")
    identify_max_queries: int = Field(default=0, alias="IDENTIFY_MAX_QUERIES")
    identify_tavily_max_results: int = Field(default=0, alias="IDENTIFY_TAVILY_MAX_RESULTS")
    identify_tavily_max_calls_per_run: int = Field(default=12, alias="IDENTIFY_TAVILY_MAX_CALLS_PER_RUN")
    identify_rss_max_with_topic: int = Field(default=0, alias="IDENTIFY_RSS_MAX_WITH_TOPIC")
    identify_rss_max_no_topic: int = Field(default=0, alias="IDENTIFY_RSS_MAX_NO_TOPIC")
    identify_rss_feed_entries: int = Field(default=0, alias="IDENTIFY_RSS_FEED_ENTRIES")
    identify_max_docs: int = Field(default=0, alias="IDENTIFY_MAX_DOCS")
    identify_max_hitl: int = Field(default=0, alias="IDENTIFY_MAX_HITL")
    identify_max_extract_chars: int = Field(default=8000, alias="IDENTIFY_MAX_EXTRACT_CHARS")
    identify_llm_article_chars: int = Field(default=6000, alias="IDENTIFY_LLM_ARTICLE_CHARS")
    identify_curator_enabled: bool = Field(default=True, alias="IDENTIFY_CURATOR_ENABLED")
    identify_curator_batch_size: int = Field(default=20, alias="IDENTIFY_CURATOR_BATCH_SIZE")
    identify_curator_min_score: int = Field(default=0, alias="IDENTIFY_CURATOR_MIN_SCORE")
    identify_curator_snippet_chars: int = Field(default=400, alias="IDENTIFY_CURATOR_SNIPPET_CHARS")
    identify_tavily_enabled: bool = Field(default=True, alias="IDENTIFY_TAVILY_ENABLED")
    identify_rss_enabled: bool = Field(default=True, alias="IDENTIFY_RSS_ENABLED")
    identify_arxiv_api_enabled: bool = Field(default=True, alias="IDENTIFY_ARXIV_API_ENABLED")
    identify_gnews_enabled: bool = Field(default=True, alias="IDENTIFY_GNEWS_ENABLED")
    identify_search_pack_enabled: bool = Field(default=True, alias="IDENTIFY_SEARCH_PACK_ENABLED")
    identify_catalog_queries_enabled: bool = Field(default=False, alias="IDENTIFY_CATALOG_QUERIES_ENABLED")
    identify_tavily_advanced_on_topic: bool = Field(default=True, alias="IDENTIFY_TAVILY_ADVANCED_ON_TOPIC")


def get_identify_settings() -> IdentifySettings:
    return IdentifySettings()


# Back-compat alias
def get_agent_settings() -> IdentifySettings:
    return get_identify_settings()
