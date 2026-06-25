"""Lightweight configuration for the standalone RAG pipeline.

Reads optional settings from environment variables so the pipeline can run
on its own (no dependency on the main `app` package). All values have safe
defaults, and every external service (Qdrant, Neo4j, OpenAI) falls back to an
in-memory / rule-based mode when not configured.
"""

import os


class Settings:
    """Environment-driven settings with sensible defaults."""

    # Vector database (Qdrant) - falls back to in-memory if unreachable
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

    # Knowledge graph (Neo4j) - falls back to rule-based skill graph if unset
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

    # LLM provider - falls back to rule-based generation if no API key
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")


settings = Settings()
