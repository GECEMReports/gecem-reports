from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gecem_reports"
    DATABASE_SSL: bool = False
    CHECKPOINT_DATABASE_URL: str = ""
    CHECKPOINT_SSL: bool = False
    DEEPSEEK_API_KEY: str = ""
    JWT_SECRET: str = "change-this-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    model_config = {"env_file": ".env"}


settings = Settings()
