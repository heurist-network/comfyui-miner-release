import os
import sys
import toml
from web3 import Web3
from pathlib import Path
from loguru import logger

def setup_logging(log_level="INFO"):
    """Configure loguru logger with custom format and multiple sinks"""
    # Remove default logger
    logger.remove()
    
    # Format for console output
    console_format: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Add console handler with sys.stdout
    logger.add(
        sink=sys.stdout,
        format=console_format,
        level=log_level,
        colorize=True,
        enqueue=True
    )
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Add daily rotating file handler
    logger.add(
        sink="logs/miner_{time:YYYY-MM-DD}.log",  # Date in filename
        rotation="00:00",  # Rotate at midnight
        retention="10 days",  # Keep logs for 10 days
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level=log_level,
        enqueue=True
    )

def load_config(filename='config.toml'):
    """Load configuration from TOML file"""
    base_dir = Path(__file__).resolve().parents[1]
    config_path = os.path.join(base_dir, filename)
    
    try:
        config = toml.load(config_path)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file {filename} not found in {base_dir}")
        raise FileNotFoundError(f"Configuration file {filename} not found in {base_dir}")
    except toml.TomlDecodeError:
        logger.error(f"Error decoding the TOML configuration file {filename}")
        raise ValueError(f"Error decoding the TOML configuration file {filename}")

def validate_erc20_address(address: str) -> bool:
    """Validate ERC20 address format"""
    if not Web3.is_address(address):
        logger.error(f"Invalid ERC20 address: {address}")
        raise ValueError("Invalid ERC20 address format")
    return True