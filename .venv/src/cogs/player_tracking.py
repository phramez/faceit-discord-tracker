import logging
import aiohttp
from discord.ext import commands

from src.services.faceit_api import FaceitAPI
from src.services.storage import StorageService

logger = logging.getLogger('faceit_bot')

class PlayerTracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storage = StorageService()

    @commands.command(name='track')
    async def track_player(self, ctx, nickname: str):
        """Track a FACEIT player"""
        guild_id = str(ctx.guild.id)
        guild_data = self.storage.get_guild_data(guild_id)
        
        # Check if player already tracked
        if nickname.lower() in [p.lower() for p in guild_data["players"]]:
            await ctx.send(f"Player {nickname} is already being tracked!")
            return
        
        async with aiohttp.ClientSession() as session:
            faceit_api = FaceitAPI(session)
            player_data = await faceit_api.fetch_player(nickname)
            
            if player_data:
                player_id = player_data.get('player_id')
                self.storage.add_player(guild_id, nickname, player_id)
                
                # Initialize ELO tracking
                if 'games' in player_data:
                    for game_id, game_data in player_data['games'].items():
                        if 'faceit_elo' in game_data:
                            self.storage.update_player_elo(player_id, game_data['faceit_elo'])
                
                await ctx.send(f"Now tracking FACEIT player: {nickname} (ID: {player_id})")
            else:
                await ctx.send(f"Could not find player with name {nickname}")

    @commands.command(name='untrack')
    async def untrack_player(self, ctx, nickname: str):
        """Stop tracking a FACEIT player"""
        guild_id = str(ctx.guild.id)
        
        if self.storage.remove_player(guild_id, nickname):
            await ctx.send(f"Stopped tracking player {nickname}.")
        else:
            await ctx.send(f"Player {nickname} is not being tracked.")

    @commands.command(name='list')
    async def list_tracked_players(self, ctx):
        """List all tracked FACEIT players"""
        guild_id = str(ctx.guild.id)
        guild_data = self.storage.get_guild_data(guild_id)
        
        if not guild_data["players"]:
            await ctx.send("No players are being tracked in this server.")
            return
        
        players_list = "\n".join(guild_data["players"].keys())
        await ctx.send(f"**Tracked FACEIT Players:**\n{players_list}")

async def setup(bot):
    await bot.add_cog(PlayerTracking(bot))