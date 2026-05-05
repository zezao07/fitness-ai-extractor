from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Fitness Data Extractor API"
    API_VERSION: str = "v1"
    # Groq API key will be loaded from the .env file
    GROQ_API_KEY: str = ""

    class Config:
        env_file = ".env"

# Single shared instance imported across the project
settings = Settings()