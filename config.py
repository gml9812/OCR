import os
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.0-flash-001")
CONFIG_FILE = "country_config.json"

# Global variable to hold loaded config
COUNTRY_CONFIG: Dict[str, Any] = {}

def load_config() -> Dict[str, Any]:
    """Load and validate country configuration from JSON file."""
    global COUNTRY_CONFIG
    # Initialize COUNTRY_CONFIG fresh each time load_config is called
    # This is important if load_config could be called multiple times, 
    # though in our FastAPI startup, it's typically once.
    current_loaded_config: Dict[str, Any] = {}
    try:
        logger.info(f"Attempting to load configuration from {CONFIG_FILE}...")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            raw_config_data = json.load(f)
        
        if not isinstance(raw_config_data, dict):
            raise TypeError("Configuration file root must be a JSON object (dictionary).")

        for country_code, config_data in raw_config_data.items():
            if not isinstance(country_code, str):
                logger.warning(f"Skipping non-string country key in config: {country_code}")
                continue
            if not isinstance(config_data, dict):
                logger.warning(f"Skipping non-dictionary config data for country '{country_code}'")
                continue
            
            current_loaded_config[country_code.lower()] = config_data

        if not current_loaded_config:
            logger.warning(f"Configuration file {CONFIG_FILE} loaded but resulted in empty configuration.")
        else:
            logger.info(f"Successfully loaded country configuration from {CONFIG_FILE}")
            logger.info(f"Supported countries from config.py: {list(current_loaded_config.keys())}")
            logger.info(f"ID of current_loaded_config in config.py load_config: {id(current_loaded_config)}")
        
        # Optionally, still update the global COUNTRY_CONFIG in this module if other parts of 
        # config.py might need it directly, though it's cleaner to rely on the return value.
        COUNTRY_CONFIG = current_loaded_config
        return current_loaded_config # Return the loaded config

    except FileNotFoundError:
        logger.error(f"CRITICAL: Configuration file {CONFIG_FILE} not found.")
    except json.JSONDecodeError as e:
        logger.error(f"CRITICAL: Error decoding JSON from {CONFIG_FILE}: {e}")
    except Exception as e:
        logger.error(f"CRITICAL: An unexpected error occurred during config loading: {e}")
    return {} # Return empty if error 