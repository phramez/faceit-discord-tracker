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
    if not os.getenv('DISCORD_TOKEN'):
        logger.error("DISCORD_TOKEN environment variable not set")
        return
    if not os.getenv('FACEIT_API_KEY'):
        logger.error("FACEIT_API_KEY environment variable not set")
        return
    
    try:
        async with bot:
            await bot.start(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())