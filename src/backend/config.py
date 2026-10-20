from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    embeddings_model: str = "text-embedding-3-large"
    chat_model: str = "gpt-4o-mini"
    retrieval_k: int = 5
    frontend_origin: str = "http://localhost:3000"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    feedback_store_path: str = "src/backend/feedback.jsonl"
    contact_db_path: str = "src/backend/contacts.db"
    cloudflare_turnstile_secret_key: str = ""
    contact_rate_limit_per_minute: int = 5
    chroma_persist_directory: str = ".chroma"
    party_positions_path: str = "src/backend/party_positions.json"
    party_positioning_k: int = 12


settings = Settings()
