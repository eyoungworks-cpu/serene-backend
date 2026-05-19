from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ASYLUM_API_BASE: str
    ENV: str = "dev"
    PROJECT_NAME: str = "Serene Exec Panel"

    class Config:
        env_file = ".env"

settings = Settings()