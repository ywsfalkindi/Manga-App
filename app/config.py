from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    POCKETBASE_URL: str
    
    class Config:
        env_file = ".env"

settings = Settings()