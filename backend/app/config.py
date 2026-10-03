from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://taylor:taylor@localhost:5432/taylor"
    data_dir: str = "../data"

    jwt_secret: str = "taylor-music-rating-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    http_host: str = "0.0.0.0"
    http_port: int = 8000
    https_port: int = 8443

    cert_dir: str = "/certs"
    cert_cn: str = "localhost"


@lru_cache
def get_settings() -> Settings:
    return Settings()