import logging
import aiohttp
from discord.ext import commands

from src.services.faceit_api import FaceitAPI
from src.services.storage import StorageService
from src.utils.embeds import create_match_embed, create_group_match_embed
from src.utils.image import create_scoreboard_image
import discord

logger = logging.getLogger('faceit_bot')

class MatchHistory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storage = StorageService()

    @commands.command(name='recent')
    async def recent_matches(self, ctx, nickname: str, count: int = 3):
        """Show recent matches for a tracked player"""
        if count > 10:
            count = 10  # Limit to 10 matches
        
        async with aiohttp.ClientSession() as session:
            faceit_api = FaceitAPI(session)
            player_data = await faceit_api.fetch_player(nickname)
            
            if not player_data:
                await ctx.send(f"Could not find player with name {nickname}")
                return
                
            player_id = player_data.get('player_id')
            history_data = await faceit_api.fetch_player_history(player_id, limit=count)
            
            if not history_data or 'items' not in history_data:
                await ctx.send(f"Could not fetch match history for player {nickname}")
                return
                
            matches = history_data['items']
            
            if not matches:
                await ctx.send(f"No recent matches found for player {nickname}")
                return
                
            for match in matches:
                match_id = match.get('match_id')
                match_details = await faceit_api.fetch_match_details(match_id)
                
                if match_details:
                    embed = await create_match_embed(match_details, nickname, session)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"Could not fetch details for match {match_id}")

    @commands.command(name='grouphistory')
    async def group_history(self, ctx, count: int = 5):
        """Show recent matches where 3+ tracked players played together"""
        if count > 10:
            count = 10
            await ctx.send("Maximum number of matches is 10. Showing 10 most recent matches.")
        
        guild_id = str(ctx.guild.id)
        guild_data = self.storage.get_guild_data(guild_id)
        
        if not guild_data["players"]:
            await ctx.send("No players are being tracked in this server.")
            return

        await ctx.send("🔍 Searching for group matches... This might take a moment.")

        try:
            async with aiohttp.ClientSession() as session:
                faceit_api = FaceitAPI(session)
                all_matches = {}
                
                # Get matches for each tracked player
                for nickname, player_id in guild_data["players"].items():
                    history_data = await faceit_api.fetch_player_history(player_id, limit=20)
                    
                    if not history_data or 'items' not in history_data:
                        continue
                    
                    for match in history_data['items']:
                        match_id = match.get('match_id')
                        match_timestamp = match.get('finished_at', 0)
                        
                        if match_id not in all_matches:
                            all_matches[match_id] = {
                                'players': [],
                                'timestamp': match_timestamp,
                                'match_data': match
                            }
                        
                        all_matches[match_id]['players'].append((nickname, player_id))

                # Filter and sort matches
                group_matches = {
                    match_id: data 
                    for match_id, data in all_matches.items() 
                    if len(data['players']) >= 3
                }
                
                sorted_matches = sorted(
                    group_matches.items(),
                    key=lambda x: x[1]['timestamp'],
                    reverse=True
                )[:count]

                if not sorted_matches:
                    await ctx.send("No group matches found with 3 or more tracked players.")
                    return

                # Process each match
                for match_id, match_info in sorted_matches:
                    match_details = await faceit_api.fetch_match_details(match_id)
                    if match_details:
                        await self.send_group_match_message(ctx, match_details, match_info)

        except Exception as e:
            logger.error(f"Error in group history: {str(e)}")
            await ctx.send("❌ An error occurred while fetching group match history.")

    async def send_group_match_message(self, ctx, match_details, match_info):
        """Send a group match message with both embed and scoreboard image"""
        try:
            async with aiohttp.ClientSession() as session:
                result = await create_group_match_embed(
                    match_details,
                    match_info['players'],
                    session
                )
                
                if result:
                    match_time = FaceitAPI.format_time(match_info['timestamp'])
                    
                    # Create scoreboard image
                    image_bytes = create_scoreboard_image(result['react_data'])
                    discord_file = discord.File(
                        fp=image_bytes,
                        filename='scoreboard.png'
                    )
                    
                    await ctx.send(
                        f"📅 **Team Game on {match_time}** "
                        f"with {len(match_info['players'])} players:",
                        file=discord_file,
                        embed=result['embed']
                    )
                    
        except Exception as e:
            logger.error(f"Error sending group match message: {str(e)}")
            await ctx.send("❌ An error occurred while creating the match visualization.")

async def setup(bot):
    await bot.add_cog(MatchHistory(bot))