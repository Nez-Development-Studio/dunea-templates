from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "dunea_app"

    class Config:
        env_file = ".env"
        # The platform writes additional vars (DUNEA_SITE_ID, DUNEA_CAPTURE_URL)
        # to .env at runtime — ignore unknown keys instead of crashing on startup.
        extra = "ignore"


settings = Settings()
