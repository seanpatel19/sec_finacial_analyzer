"""
Configuration settings for SEC Financial Analyzer
Handles environment variables and default settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

def setup_logging(self):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, self.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(self.DATA_DIR / 'analyzer.log'),
            logging.StreamHandler()
        ]
    )
class Config:
    """Configuration class for SEC Financial Analyzer"""
    
    # Project directories
    BASE_DIR = Path(__file__).parent
    DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / "data"))
    RAW_FILINGS_DIR = DATA_DIR / "raw_filings"
    PROCESSED_DIR = DATA_DIR / "processed"
    OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', DATA_DIR / "summaries"))
    
    # SEC API Settings
    SEC_BASE_URL = "https://data.sec.gov"
    USER_AGENT = os.getenv('SEC_USER_AGENT', 'YourName-YourEmail@domain.com')
    REQUEST_DELAY = float(os.getenv('SEC_REQUEST_DELAY', 0.1))
    
    # Validate USER_AGENT
    if USER_AGENT == 'YourName-YourEmail@domain.com':
        raise ValueError(
            "Please set SEC_USER_AGENT in your .env file with your actual email address. "
            "This is required by the SEC API."
        )
    
    # LLM Settings
    MODEL_NAME = os.getenv('MODEL_NAME', 'llama2:13b')
    MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', 4096))
    TEMPERATURE = float(os.getenv('MODEL_TEMPERATURE', 0.3))
    
    # Processing Settings
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 2000))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 200))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    def __init__(self):
        """Initialize configuration and create necessary directories"""
        self._create_directories()
        self._validate_config()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.DATA_DIR,
            self.RAW_FILINGS_DIR,
            self.PROCESSED_DIR,
            self.OUTPUT_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _validate_config(self):
        """Validate configuration settings"""
        # Validate email format in USER_AGENT
        if '@' not in self.USER_AGENT:
            raise ValueError(
                "USER_AGENT must contain a valid email address (required by SEC API)"
            )
        
        # Validate model name
        if not self.MODEL_NAME:
            raise ValueError("MODEL_NAME cannot be empty")
        
        # Validate numeric settings
        if self.REQUEST_DELAY < 0.1:
            raise ValueError("REQUEST_DELAY must be at least 0.1 seconds (SEC requirement)")
    
    def __repr__(self):
        """String representation of configuration"""
        return f"""
SEC Financial Analyzer Configuration:
- Data Directory: {self.DATA_DIR}
- SEC User Agent: {self.USER_AGENT}
- LLM Model: {self.MODEL_NAME}
- Request Delay: {self.REQUEST_DELAY}s
- Chunk Size: {self.CHUNK_SIZE}
        """.strip()