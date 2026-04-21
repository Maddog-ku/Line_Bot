from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    line_channel_access_token: str = ""
    line_channel_secret: str = ""
    tz: str = "Asia/Taipei"
    database_url: str = "sqlite:///./data/bot.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
