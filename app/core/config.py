from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_username: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password123")

    # OpenAI
    openai_api_key: str = Field(...)
    llm_model: str = Field(default="gpt-4o-mini")

    # Embedding
    embedding_model: str = Field(default="snunlp/KR-SBERT-V40K-klueNLI-augSTS")
    embedding_dimension: int = Field(default=768)

    # App
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Pipeline
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
