from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

env_file = Path(__file__).parent.parent.parent.parent / ".env"

class Settings(BaseSettings):
    """..."""
    sqlalchemy_database_url: str
    secret_key: str
    algorithm: str
    mail_username: str
    mail_password: str
    mail_from: str
    mail_from_name: str
    mail_port: int
    mail_server: str
    redis_host: str
    redis_port: int
    cors_origins: str
    rate_limiter_times: int
    rate_limiter_seconds: int
    blob_chunk_size: str = "10MB"  
    media_cache_size: str = "400MB"      
    media_cache_record_limit: str = "20MB"
    blob_chunk_size_bytes: int = 10*1024*1024
    media_cache_size_bytes: int = 400*1024*1024
    media_cache_record_limit_bytes: int = 20*1024*1024

    model_config = ConfigDict(extra="ignore",
                              env_file=env_file if env_file.exists() else None,
                              env_file_encoding = "utf-8")

    @property
    def rate_limiter_description(self) -> str: 
        f"No more than {self.rate_limiter_times} requests per {self.rate_limiter_seconds} seconds"

settings = Settings()
