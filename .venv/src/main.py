#!/usr/bin/env python
import os
import sys
import logging
import asyncio

# Set up the path to find modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Setup basic logging until config is loaded
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('faceit_bot')

async def startup():
    """Initialize the project and start the bot"""
    try:
        # Import setup utility
        from src.utils.setup import initialize_project
        
        # Initialize project structure and config
        if not initialize_project():
            logger.error("Project initialization failed. Check the logs for details.")
            return False
        
        # Import and start the bot
        from src.bot import main as bot_main
        await bot_main()
        
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
        return False
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        # Run the bot
        asyncio.run(startup())
    except KeyboardInterrupt:
        logger.info("Bot shutdown by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        sys.exit(1)