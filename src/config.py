"""
Configuration settings for FDA NDC to RxNorm Matching Agent
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Data directories
    DATA_DIR: Path = Path("data")
    NDC_DATA_DIR: Path = DATA_DIR / "ndc"
    RXNORM_DATA_DIR: Path = DATA_DIR / "rxnorm"
    OUTPUT_DIR: Path = DATA_DIR / "output"
    
    # FDA NDC URLs
    FDA_NDC_BASE_URL: str = "https://www.fda.gov/media/72380/download"
    FDA_NDC_ALTERNATIVE_URL: str = "https://download.open.fda.gov/drug/ndc.txt"
    
    # RxNorm API settings
    RXNORM_API_BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"
    RXNORM_API_TIMEOUT: int = 30
    RXNORM_API_RETRY_ATTEMPTS: int = 3
    RXNORM_API_RETRY_DELAY: int = 1
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./data/ndc_rxnorm.db"
    DATABASE_ECHO: bool = False
    
    # Processing settings
    BATCH_SIZE: int = 1000
    MAX_WORKERS: int = 4
    CHUNK_SIZE: int = 10000
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[Path] = DATA_DIR / "logs" / "agent.log"
    
    # Clinical data settings
    CLINICAL_OUTPUT_FORMAT: str = "json"  # json, csv, parquet
    INCLUDE_CLINICAL_METADATA: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        settings.DATA_DIR,
        settings.NDC_DATA_DIR,
        settings.RXNORM_DATA_DIR,
        settings.OUTPUT_DIR,
        settings.LOG_FILE.parent if settings.LOG_FILE else None
    ]
    
    for directory in directories:
        if directory:
            directory.mkdir(parents=True, exist_ok=True)


# Ensure directories exist when module is imported
ensure_directories() 