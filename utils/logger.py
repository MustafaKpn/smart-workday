"""
Centralized logging configuration
"""
import logging
import sys
from pathlib import Path


def setup_logging(level=logging.INFO):
    """
    Setup logging for the entire application.
    
    Args:
        level: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR
    """
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            # Write to file
            logging.FileHandler('logs/app.log'),
            # Also print to console
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("Logging initialized")