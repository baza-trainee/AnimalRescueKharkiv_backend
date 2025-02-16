from pathlib import Path

from humanfriendly import parse_size
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

local_env_file = Path(__file__).parent.parent.parent.parent / "local.env"
env_file = (local_env_file
            if local_env_file.exists()
            else Path(__file__).parent.parent.parent.parent / ".env")


class Settings(BaseSettings):
    """..."""
    logging_level: str = "INFO"
    api_prefix: str = ""
    media_prefix: str = "/media"
    media_assets_prefix: str = "/assets"
    permissions_prefix: str = "/permissions"
    roles_prefix: str = "/roles"
    auth_prefix: str = "/auth"
    users_prefix: str = "/users"
    stats_prefix: str = "/stats"
    crm_prefix: str = "/crm"
    animals_prefix: str = "/animals"
    password_regex: str = r"^(?=.*[a-zA-Z])(?=.*\d)(?=.*[\W_])(?!.*\s).{8,14}$"
    password_incorrect_message: str = ("The password length should be between 8 and 14 characters, "
        "the password must include at least 1 number, 1 letter and 1 special character")
    media_short_url_id: bool = True
    default_cache_ttl: int = 15 * 60 # 15 minutes
    sqlalchemy_database_url: str
    secret_key: str
    algorithm: str
    mail_username: str
    mail_password: str
    mail_from: str
    mail_from_name: str
    mail_port: int
    mail_server: str
    url_register: str = "http://localhost:3000/register"
    url_reset_pwd: str = "http://localhost:3000/resetPassword"
    url_login: str = "http://localhost:3000/login"
    redis_host: str
    redis_port: int
    cors_origins: str
    rate_limiter_times: int
    rate_limiter_seconds: int
    blob_chunk_size: str = "10MB"
    media_cache_size: str = "400MB"
    media_cache_record_limit: str = "20MB"
    super_user_password: str = "1234qwe!"
    super_user_mail: str = "admin@ark.ua"
    super_user_role: str = "admin"
    super_user_domain: str = "system"
    super_user_permission: str = "system:admin"
    scheduler_frequency: int = 4 * 60 * 60 # 4 hours
    access_token_expire_mins: int = 45 # 45 minutes
    invitation_token_expire_days: int = 10 # 10 days
    refresh_token_expire_days: int = 7 # 7 days
    reset_password_expire_mins: int = 15 # 15 minutes
    crm_editing_lock_expire_minutes: int = 15 # 15 minutes

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
