from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://paper:paper123@localhost:5432/paper_workspace"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Workspace storage
    WORKSPACE_DIR: str = "./workspace"
    BACKUP_DIR: str = "./backups"
    STORAGE_DIR: str = "./storage"  # legacy override; defaults to workspace/storage in Docker
    MAX_UPLOAD_SIZE_MB: int = 100

    # Security
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # AI / Embedding
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o-mini"
    AI_MAX_OUTPUT_TOKENS: int = 1200
    AI_TEMPERATURE: float = 0.1
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32
    SEMANTIC_CANDIDATE_K: int = 50
    SEMANTIC_MIN_SIMILARITY: float = 0.30
    HYBRID_RRF_K: int = 60
    HYBRID_CANDIDATE_ENTITIES: int = 50
    HYBRID_MAX_CANDIDATE_ENTITIES: int = 200
    RAG_CANDIDATE_K: int = 40
    RAG_DEFAULT_MAX_SOURCES: int = 8
    RAG_DEFAULT_TOKEN_BUDGET: int = 6000
    RAG_MAX_TOKEN_BUDGET: int = 12000
    RAG_MAX_CHUNK_SOURCE_TOKENS: int = 1200
    RAG_MAX_NOTE_SOURCE_TOKENS: int = 1000
    RAG_MAX_NOTE_SOURCES: int = 2
    RAG_MAX_PAPER_SOURCES_PER_PAPER: int = 4
    DEEP_READING_CONTEXT_BUDGET: int = 12000
    DEEP_READING_MAX_SOURCES: int = 20
    DEEP_READING_SECTION_SOURCE_CAP: int = 4
    DEEP_READING_MAX_OUTPUT_TOKENS: int = 4000

    # PDF Processing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20

    @property
    def workspace_path(self) -> Path:
        path = Path(self.WORKSPACE_DIR).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def backup_path(self) -> Path:
        path = Path(self.BACKUP_DIR).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def storage_path(self) -> Path:
        path = Path(self.STORAGE_DIR).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        for directory in ("pdfs", "covers", "thumbnails", "clips"):
            (path / directory).mkdir(exist_ok=True)
        return path

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
