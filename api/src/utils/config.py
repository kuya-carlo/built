# api/src/utils/config.py
import json
import os
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Load from root .env file - add explicit loading
env_path = os.path.join(os.path.dirname(__file__), "../../../.env")
if os.path.exists(env_path):
    from dotenv import load_dotenv

    load_dotenv(env_path)
else:
    raise FileNotFoundError(f"ENV file {env_path} not found. Exiting.")


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./app.db"

    # JWT
    secret_key: str = "default-secret-key-change-in-production"
    refresh_key: str = "default-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API
    api_v1_str: str = "/api/v1"
    project_title: str = "Built"
    project_name: str = "Built | Cost Management API"
    project_description: str = "A cost management system for construction companies"
    version: str = "0.1.2"
    debug: bool = False

    # CORS - Pydantic will automatically parse JSON
    backend_cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="List of allowed CORS origins",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If JSON parsing fails, try comma-separated
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,  # Allows case-insensitive env vars
        "extra": "ignore",  # Ignore extra environment variables
    }


settings = Settings()

# Quick test to verify everything loads
if __name__ == "__main__":
    print("=== Settings Load Test ===")
    print(f"Database: {settings.database_url}")
    print(f"CORS Origins: {settings.backend_cors_origins}")
    print(f"Project: {settings.project_name}")
    print(f"Debug: {settings.debug}")
