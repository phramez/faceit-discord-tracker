import logging
import aiohttp
from discord.ext import tasks
import discord

from src.services.storage import StorageService
from src.utils.embeds import create_match_embed, create_group_match_embed
from src.services.faceit_api import FaceitAPI
from src.utils.image import create_scoreboard_image
from src.config import MATCH_CHECK_INTERVAL

logger = logging.getLogger('faceit_bot')

class MatchTracker:
    def __init__(self, bot):
        self.bot = bot
        self.storage = StorageService()
        self.check_match_updates.start()

    def cog_unload(self):
        self.check_match_updates.cancel()

    @tasks.loop(minutes=MATCH_CHECK_INTERVAL)
    async def check_match_updates(self):
        """Check for match updates for all tracked players"""
        try:
            logger.info("Checking for match updates...")
            
            async with aiohttp.ClientSession() as session:
                faceit_api = FaceitAPI(session)
                
                for guild_id, guild_data in self.storage.tracked_players.items():
                    # Skip if no notification channels
                    if not guild_data.get("notification_channels", []):
                        continue
                    
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        logger.warning(f"Could not find guild {guild_id}")
                        continue
                    
                    # Get valid notification channels
                    valid_channels = []
                    for channel_id in guild_data["notification_channels"]:
                        channel = guild.get_channel(int(channel_id))
                        if channel:
                            valid_channels.append(channel)
                    
                    if not valid_channels:
                        continue

                    # Track group matches
                    group_matches = {}  # match_id -> list of (nickname, player_id)
                    
                    # Collect all matches and their players
                    for nickname, player_id in guild_data["players"].items():
                        history_data = await faceit_api.fetch_player_history(player_id, limit=3)
                        
                        if not history_data or 'items' not in history_data:
                            continue
                        
                        for match in history_data['items']:
                            match_id = match.get('match_id')
                            if match_id not in group_matches:
                                group_matches[match_id] = []
                            group_matches[match_id].append((nickname, player_id))

                    # Process matches
                    for match_id, players in group_matches.items():
                        # Skip if already processed
                        if any(
                            match_id in self.storage.tracked_players[guild_id]["last_matches"].get(pid, [])
                            for _, pid in players
                        ):
                            continue

                        match_details = await faceit_api.fetch_match_details(match_id)
                        if not match_details or match_details.get('status') != 'FINISHED':
                            continue

                        # Special handling for group matches
                        if len(players) >= 3:
                            await self._process_group_match(
                                match_details,
                                players,
                                valid_channels,
                                session
                            )
                        else:
                            # Process individual matches
                            for nickname, _ in players:
                                await self._process_individual_match(
                                    match_details,
                                    nickname,
                                    valid_channels,
                                    session
                                )

                        # Update last matches for all players
                        for _, player_id in players:
                            if player_id not in guild_data["last_matches"]:
                                guild_data["last_matches"][player_id] = []
                            guild_data["last_matches"][player_id].append(match_id)

                    self.storage.save_tracked_players()
                    
        except Exception as e:
            logger.error(f"Error in match update check: {str(e)}")

    async def _process_group_match(self, match_details, players, channels, session):
        """Process and send notifications for group matches"""
        try:
            # Import inside function to avoid circular imports
            from src.utils.embeds import create_group_match_embed
            
            result = await create_group_match_embed(match_details, players, session)
            if result:
                image_bytes = create_scoreboard_image(result['react_data'])
                discord_file = discord.File(fp=image_bytes, filename='scoreboard.png')
                
                for channel in channels:
                    try:
                        await channel.send(
                            f"🎮 **Group Match Found with {len(players)} Players!**",
                            file=discord_file,
                            embed=result['embed']
                        )
                    except Exception as e:
                        logger.error(f"Error sending to channel {channel.id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error processing group match: {str(e)}")

    async def _process_individual_match(self, match_details, nickname, channels, session):
        """Process and send notifications for individual matches"""
        try:
            # Import inside function to avoid circular imports
            from src.utils.embeds import create_match_embed
            
            embed = await create_match_embed(match_details, nickname, session)
            for channel in channels:
                try:
                    await channel.send(
                        f"New Match Result for {nickname}:",
                        embed=embed
                    )
                except Exception as e:
                    logger.error(f"Error sending to channel {channel.id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error processing individual match: {str(e)}")

    async def _process_individual_match(self, match_details, nickname, channels, session):
        """Process and send notifications for individual matches"""
        try:
            embed = await create_match_embed(match_details, nickname, session)
            for channel in channels:
                try:
                    await channel.send(
                        f"New Match Result for {nickname}:",
                        embed=embed
                    )
                except Exception as e:
                    logger.error(f"Error sending to channel {channel.id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error processing individual match: {str(e)}")

    @check_match_updates.before_loop
    async def before_check_match_updates(self):
        """Wait for bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()

async def start_match_tracker(bot):
    """Initialize and start the match tracker"""
    tracker = MatchTracker(bot)
    return tracker