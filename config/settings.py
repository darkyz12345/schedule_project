from pydantic_settings import BaseSettings
from pydantic import Field


class DBSettings(BaseSettings):
    HOST: str
    PORT: str
    USER_NAME: str
    PASSWORD: str
    DB_NAME: str
    ECHO: str

    class Config:
        env_file = ".env"
        extra = "ignore"  # ✅ Игнорировать посторонние ключи


class JWTSettings(BaseSettings):
    SECRET_KEY: str = Field(..., alias="JWT_SECRET_KEY")
    ALGORITHM: str = Field("HS256", alias="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    class Config:
        env_file = ".env"
        extra = "ignore"


class RedisSettings(BaseSettings):
    HOST: str = Field("localhost", alias="REDIS_HOST")
    PORT: str = Field("6379", alias="REDIS_PORT")
    DB: str = Field("0", alias="REDIS_DB")
    PASSWORD: str = Field("", alias="REDIS_PASSWORD")

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_url(self):
        if self.PASSWORD:
            return f"redis://:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"
        return f"redis://{self.HOST}:{self.PORT}/{self.DB}"


class Settings:
    db = DBSettings()
    jwt = JWTSettings()
    redis = RedisSettings()
