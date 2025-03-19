import logging
import aiohttp
from discord.ext import commands, tasks
from typing import Dict, Any, List, Optional

from src.services.faceit_api import FaceitAPI
from src.services.storage import StorageService

logger = logging.getLogger('faceit_bot')

class EloTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storage = StorageService()
        self.update_all_elo.start()

    def cog_unload(self):
        self.update_all_elo.cancel()
    
    @tasks.loop(hours=6)  # Update ELO every 6 hours
    async def update_all_elo(self):
        """Periodically update ELO for all tracked players"""
        logger.info("Starting scheduled ELO update for all tracked players")
        await self.fetch_and_update_all_elo()
    
    @update_all_elo.before_loop
    async def before_update_elo(self):
        """Wait for bot to be ready before starting the update loop"""
        await self.bot.wait_until_ready()
    
    @commands.command(name='updateelo')
    async def update_elo_command(self, ctx):
        """Manually trigger an update of ELO for all tracked players"""
        await ctx.send("🔄 Updating ELO for all tracked players... This might take a moment.")
        
        updated = await self.fetch_and_update_all_elo()
        
        if updated:
            await ctx.send(f"✅ Successfully updated ELO for {updated} players!")
        else:
            await ctx.send("❌ No players found to update or there was an error.")
    
    @commands.command(name='elo')
    async def show_player_elo(self, ctx, nickname: str = None):
        """Show ELO for a player or all tracked players"""
        guild_id = str(ctx.guild.id)
        guild_data = self.storage.get_guild_data(guild_id)
        
        if not guild_data["players"]:
            await ctx.send("No players are being tracked in this server.")
            return
        
        if nickname:
            # Show ELO for specific player
            player_id = self.storage.get_player_id_by_nickname(guild_id, nickname)
            
            if not player_id:
                await ctx.send(f"Player {nickname} is not being tracked.")
                return
            
            elo_data = self.storage.player_elo_history.get(player_id, {})
            current_elo = elo_data.get('current')
            
            if current_elo is None:
                await ctx.send(f"No ELO data available for {nickname}. Try running `!updateelo` first.")
                return
            
            # Get ELO history
            history = elo_data.get('history', [])
            if history:
                last_change = history[-1].get('change', 0)
                change_indicator = f" (+{last_change})" if last_change > 0 else f" ({last_change})"
            else:
                change_indicator = ""
            
            await ctx.send(f"**{nickname}** current ELO: **{current_elo}**{change_indicator}")
        else:
            # Show ELO for all tracked players
            all_players_data = []
            
            for player_nickname, player_id in guild_data["players"].items():
                elo_data = self.storage.player_elo_history.get(player_id, {})
                current_elo = elo_data.get('current')
                
                if current_elo is not None:
                    # Get ELO history
                    history = elo_data.get('history', [])
                    if history:
                        last_change = history[-1].get('change', 0)
                        change_indicator = f" (+{last_change})" if last_change > 0 else f" ({last_change})"
                    else:
                        change_indicator = ""
                    
                    all_players_data.append((player_nickname, current_elo, change_indicator))
            
            if not all_players_data:
                await ctx.send("No ELO data available for any tracked players. Try running `!updateelo` first.")
                return
            
            # Sort by ELO (highest first)
            all_players_data.sort(key=lambda x: x[1], reverse=True)
            
            # Create message
            players_list = "\n".join([f"**{nickname}**: {elo}{change}" for nickname, elo, change in all_players_data])
            
            await ctx.send(f"**Current ELO for Tracked Players:**\n{players_list}")
    
    async def fetch_and_update_all_elo(self) -> int:
        """
        Fetch and update current ELO for all tracked players across all guilds
        
        Returns:
            int: Number of players updated
        """
        updated_count = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                faceit_api = FaceitAPI(session)
                
                # Go through all guilds and players
                for guild_id, guild_data in self.storage.tracked_players.items():
                    for nickname, player_id in guild_data["players"].items():
                        try:
                            # Fetch player data from FACEIT
                            player_data = await faceit_api.fetch_player(player_id)
                            
                            if player_data and 'games' in player_data:
                                # CS2 is the primary game for ELO tracking (previously CS:GO)
                                # Check both CS2 and CS:GO for ELO
                                cs2_data = player_data['games'].get('cs2', {})
                                csgo_data = player_data['games'].get('csgo', {})
                                
                                # Use CS2 ELO if available, otherwise try CS:GO
                                if 'faceit_elo' in cs2_data:
                                    current_elo = cs2_data['faceit_elo']
                                elif 'faceit_elo' in csgo_data:
                                    current_elo = csgo_data['faceit_elo']
                                else:
                                    logger.warning(f"No ELO data found for {nickname}")
                                    continue
                                
                                # Update player ELO
                                self.storage.update_player_elo(player_id, current_elo)
                                updated_count += 1
                                logger.info(f"Updated ELO for {nickname}: {current_elo}")
                        
                        except Exception as e:
                            logger.error(f"Error updating ELO for {nickname}: {str(e)}")
                
                # Save all changes
                self.storage.save_player_elo_history()
                
                return updated_count
        
        except Exception as e:
            logger.error(f"Error in fetch_and_update_all_elo: {str(e)}")
            return 0
                
async def setup(bot):
    await bot.add_cog(EloTracker(bot))