import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger('faceit_bot')

def initialize_project() -> bool:
    """
    Initialize project structure and validate requirements
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        # Create required directories
        create_project_structure()
        
        # Initialize storage files if they don't exist
        initialize_storage_files()
        
        # Validate environment variables
        if not validate_environment_variables():
            return False
        
        logger.info("Project initialization completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Project initialization failed: {str(e)}")
        return False

def create_project_structure():
    """Create necessary directories for the project"""
    # Get project root directory (parent of src)
    src_dir = Path(__file__).parent.parent
    project_root = src_dir.parent
    
    directories = [
        src_dir,
        src_dir / 'cogs',
        src_dir / 'services',
        src_dir / 'utils'
    ]
    
    for directory in directories:
        try:
            directory.mkdir(exist_ok=True)
            init_file = directory / '__init__.py'
            if not init_file.exists():
                init_file.touch()
        except Exception as e:
            logger.warning(f"Could not create directory {directory}: {e}")
    
    logger.info("Project directory structure created")

def initialize_storage_files():
    """Initialize storage files if they don't exist"""
    from src.config import TRACKED_PLAYERS_FILE, PLAYER_ELO_HISTORY_FILE
    
    files = {
        TRACKED_PLAYERS_FILE: {},
        PLAYER_ELO_HISTORY_FILE: {}
    }
    
    for file_path, default_content in files.items():
        try:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump(default_content, f)
                logger.info(f"Created storage file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not initialize storage file {file_path}: {e}")
    
    logger.info("Storage files initialized")

def validate_environment_variables() -> bool:
    """
    Validate that required environment variables are set
    
    Returns:
        bool: True if all required variables are set, False otherwise
    """
    # Load environment variables from .env file
    load_dotenv()
    
    required_vars = [
        'DISCORD_TOKEN',
        'FACEIT_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        for var in missing_vars:
            logger.error(f"Missing required environment variable: {var}")
        
        # Create or update .env file template if it doesn't exist or is missing variables
        env_path = '.env'
        existing_vars = {}
        
        # Read existing .env if it exists
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        existing_vars[key] = value
        
        # Add missing vars to template
        with open(env_path, 'w') as f:
            for var in required_vars:
                value = existing_vars.get(var, '')
                f.write(f"{var}={value}\n")
        
        logger.info(f"Created/updated .env template at {env_path}")
        logger.info("Please fill in the missing values and restart the bot")
        
        return False
    
    logger.info("Environment variables validated successfully")
    return True