from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "SWHC Enterprise v2"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "production"
    APP_DEBUG: bool = False
    
    # Server Settings
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    
    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/swch.db"
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security Settings
    SECRET_KEY: str = "change-me-in-production"
    ENCRYPTION_KEY: str = "change-me-encryption-key-32-bytes"
    
    # Switch Credentials
    SWITCH_USERNAME: str = "networks"
    SWITCH_PASSWORD: str = "w00Lw0rTh$"
    SWITCH_ENABLE_SECRET: str = "w00Lw0rTh$"
    
    # Monitoring Settings
    CHECK_INTERVAL_SECONDS: int = 30
    CONNECTION_TIMEOUT: int = 15
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
