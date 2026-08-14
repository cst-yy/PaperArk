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
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

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
