from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "金融数据分类分级打标平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./data_assets.db"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DASHSCOPE_API_KEY: str = ""
    ENCRYPTION_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
