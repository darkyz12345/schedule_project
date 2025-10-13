from pydantic_settings import BaseSettings

class DBSettings(BaseSettings):
    HOST: str
    PORT: str
    USER_NAME: str
    PASSWORD: str
    DB_NAME: str
    ECHO: str

    class Config:
        env_file = ".env"