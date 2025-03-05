import os
import discord
from discord.ext import commands
import logging
import asyncio
from dotenv import load_dotenv

# Local imports
from src.config import LOGGING_FORMAT, LOGGING_LEVEL

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=LOGGING_LEVEL,
    format=LOGGING_FORMAT
)
logger = logging.getLogger('faceit_bot')

# Get the absolute path to the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COGS_DIR = os.path.join(PROJECT_ROOT, 'src', 'cogs')

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user}')
    await load_cogs()  # Load cogs when bot is ready

async def load_cogs():
    """Load all cogs from the cogs directory"""
    if not os.path.exists(COGS_DIR):
        logger.error(f"Cogs directory not found at {COGS_DIR}")
        return

    for filename in os.listdir(COGS_DIR):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'src.cogs.{filename[:-3]}')
                logger.info(f'Loaded cog: {filename[:-3]}')
            except Exception as e:
                logger.error(f'Failed to load cog {filename}: {str(e)}')

async def main():
    """Main bot execution function"""
    # Environment variables should already be validated by the initialization process
    discord_token = os.getenv('DISCORD_TOKEN')
    
    # Start the bot, setup match tracker, and run until closed
    try:
        # Initialize the match tracker service
        from src.services import start_match_tracker
        tracker = await start_match_tracker(bot)
        
        # Start the bot
        logger.info("Starting Discord bot...")
        async with bot:
            await bot.start(discord_token)
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        raise

if __name__ == "__main__":
    # If running directly (not imported), first initialize project
    from src.utils.setup import initialize_project
    if initialize_project():
        asyncio.run(main())
    else:
        logger.error("Failed to initialize project. Please check the logs for details.")
        import sys
        sys.exit(1)