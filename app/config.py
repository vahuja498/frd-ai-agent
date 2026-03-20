"""
app/config.py — Centralised configuration via environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────────────────────
    model_provider: str = Field(default="ollama")

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="")
    openai_model: str   = Field(default="gpt-4o")

    # ── Grok ──────────────────────────────────────────────────────────────────
    grok_api_key: str   = Field(default="")
    grok_base_url: str  = Field(default="https://api.x.ai/v1")
    grok_model: str     = Field(default="grok-3-fast")

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_model: str    = Field(default="llama3.2")
    ollama_base_url: str = Field(default="http://localhost:11434/api/generate")

    # ── Azure DevOps ──────────────────────────────────────────────────────────
    azure_devops_org: str           = Field(default="")
    azure_devops_project: str       = Field(default="")
    azure_devops_pat: str           = Field(default="")
    azure_devops_trigger_tag: str   = Field(default="generate-frd")
    azure_devops_done_tag: str      = Field(default="frd-generated")
    azure_devops_poll_interval: int = Field(default=60)

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_model: str = Field(default="all-MiniLM-L6-v2")

    # ── Vector Store ──────────────────────────────────────────────────────────
    vectorstore_path: str = Field(default="./vectorstore")
    top_k_results: int    = Field(default=3)

    # ── App ───────────────────────────────────────────────────────────────────
    app_host: str  = Field(default="0.0.0.0")
    app_port: int  = Field(default=8000)
    debug: bool    = Field(default=True)

    @property
    def active_api_key(self) -> str:
        if self.model_provider == "grok":
            return self.grok_api_key
        if self.model_provider == "openai":
            return self.openai_api_key
        return "ollama-no-key-needed"

    @property
    def active_model(self) -> str:
        if self.model_provider == "grok":
            return self.grok_model
        if self.model_provider == "ollama":
            return self.ollama_model
        return self.openai_model

    @property
    def active_base_url(self) -> str | None:
        if self.model_provider == "grok":
            return self.grok_base_url
        return None


settings = Settings()