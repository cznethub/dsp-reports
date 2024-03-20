from functools import lru_cache

from pydantic import BaseSettings

class Settings(BaseSettings):
    mongo_username: str
    mongo_password: str
    mongo_host: str
    mongo_database: str
    mongo_protocol: str

    @property
    def mongo_url(self):
        return f"{self.mongo_protocol}://{self.mongo_username}:{self.mongo_password}@{self.mongo_host}/?retryWrites=true&w=majority"


@lru_cache()
def get_settings():
    return Settings()
