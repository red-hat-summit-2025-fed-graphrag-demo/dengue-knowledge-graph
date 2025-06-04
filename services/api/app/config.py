"""
Configuration settings for the Dengue Knowledge Graph API
"""
import os
import logging
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings configuration class"""
    
    # API configuration
    app_name: str = "Dengue Knowledge Graph API"
    api_prefix: str = "/api/v1"
    debug: bool = False
    
    # Neo4j database configuration
    neo4j_uri: str = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password: str = os.environ.get("NEO4J_PASSWORD", "neo4j")
    
    # Security settings
    api_key_name: str = "x-api-key"
    api_key: Optional[str] = os.environ.get("API_KEY", None)
    
    # Logging
    log_level: str = os.environ.get("LOG_LEVEL", "info")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get settings with caching for improved performance"""
    return Settings()


def configure_logging():
    """Configure application logging based on settings"""
    log_level = get_settings().log_level.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Set specific loggers to higher level to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
