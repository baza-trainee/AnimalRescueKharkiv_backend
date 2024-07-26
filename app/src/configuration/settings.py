from pathlib import Path

from humanfriendly import parse_size
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

env_file = Path(__file__).parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    """..."""
    api_prefix: str = ""
    media_prefix: str = "/media"
    permissions_prefix: str = "/permissions"
    roles_prefix: str = "/roles"
    media_short_url_id: bool = True
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

    model_config = ConfigDict(extra="ignore",
                              env_file=env_file if env_file.exists() else None,
                              env_file_encoding = "utf-8")

    @property
    def rate_limiter_description(self) -> str:
        """Property returns pre-formatted description for rate limitter middleware injection"""
        return f"No more than {self.rate_limiter_times} requests per {self.rate_limiter_seconds} seconds"

    @property
    def blob_chunk_size_bytes(self) -> int:
        """Property returns blob_chunk_size setting value in bytes"""
        return parse_size(size=self.blob_chunk_size, binary=True)

    @property
    def media_cache_size_bytes(self) -> int:
        """Property returns media_cache_size setting value in bytes"""
        return parse_size(size=self.media_cache_size, binary=True)

    @property
    def media_cache_record_limit_bytes(self) -> int:
        """Property returns media_cache_record_limit setting value in bytes"""
        return parse_size(size=self.media_cache_record_limit, binary=True)

settings = Settings()
