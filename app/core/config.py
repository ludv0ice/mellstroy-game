from pydantic import BaseModel


class Settings(BaseModel):
    database_path: str = "telecom.db"
    api_prefix: str = "/api/v1"


settings = Settings()
