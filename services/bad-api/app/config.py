from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Neo4j Connection Details (read from environment variables)
    NEO4J_URI: str = Field(default="bolt://localhost:7687", validation_alias="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(default="neo4j", validation_alias="NEO4J_PASSWORD")
    NEO4J_AUTH: str = Field(default="basic", validation_alias="NEO4J_AUTH")

    # Logging Level
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # Optional: Add other API settings if needed
    API_TITLE: str = "Dengue Knowledge Graph API"
    API_VERSION: str = "0.1.0"

    class Config:
        # Load environment variables from a .env file if present (optional)
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra env vars not defined in the model

# Instantiate the settings
settings = Settings()
