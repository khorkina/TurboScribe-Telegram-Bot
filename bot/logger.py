"""
Enhanced logging configuration
"""
import logging
import sys
from datetime import datetime

def setup_logger():
    """Setup enhanced logging configuration"""
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from some modules
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncpg').setLevel(logging.WARNING)
    
    return root_logger

def log_user_action(user_id: int, username: str, action: str, extra_info: str = ""):
    """Log user actions"""
    logging.info(f"USER_ACTION - {user_id} (@{username}): {action} {extra_info}")

def log_processing_time(user_id: int, operation: str, duration: float):
    """Log processing times"""
    logging.info(f"PERFORMANCE - {user_id}: {operation} took {duration:.2f}s")

def log_error(error_type: str, error_msg: str, user_id: int = None):
    """Log errors with context"""
    context = f" - User {user_id}" if user_id else ""
    logging.error(f"ERROR - {error_type}{context}: {error_msg}")