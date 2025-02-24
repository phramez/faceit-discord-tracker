import logging
from discord.ext import commands
import discord

from src.services.storage import StorageService

logger = logging.getLogger('faceit_bot')

class ChannelManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storage = StorageService()

    @commands.command(name='addchannel')
    async def add_notification_channel(self, ctx, channel: discord.TextChannel = None):
        """Add a channel to receive match notifications
        Usage: !addchannel [#channel]
        If no channel is specified, uses the current channel"""
        guild_id = str(ctx.guild.id)
        channel = channel or ctx.channel
        
        guild_data = self.storage.get_guild_data(guild_id)
        
        # Check if channel is already registered
        if str(channel.id) in guild_data.get("notification_channels", []):
            await ctx.send(f"{channel.mention} is already receiving match notifications!")
            return
        
        # Add the channel
        if "notification_channels" not in guild_data:
            guild_data["notification_channels"] = []
        guild_data["notification_channels"].append(str(channel.id))
        self.storage.save_tracked_players()
        
        await ctx.send(f"✅ {channel.mention} will now receive match notifications!")

    @commands.command(name='removechannel')
    async def remove_notification_channel(self, ctx, channel: discord.TextChannel = None):
        """Remove a channel from receiving match notifications
        Usage: !removechannel [#channel]
        If no channel is specified, uses the current channel"""
        guild_id = str(ctx.guild.id)
        channel = channel or ctx.channel
        
        guild_data = self.storage.get_guild_data(guild_id)
        
        if (str(channel.id) not in guild_data.get("notification_channels", [])):
            await ctx.send(f"{channel.mention} is not receiving match notifications!")
            return
        
        # Remove the channel
        guild_data["notification_channels"].remove(str(channel.id))
        self.storage.save_tracked_players()
        
        await ctx.send(f"❌ {channel.mention} will no longer receive match notifications!")

    @commands.command(name='listchannels')
    async def list_notification_channels(self, ctx):
        """List all channels that receive match notifications"""
        guild_id = str(ctx.guild.id)
        guild_data = self.storage.get_guild_data(guild_id)
        
        if not guild_data.get("notification_channels", []):
            await ctx.send("No channels are currently receiving match notifications!")
            return
        
        channels = []
        for channel_id in guild_data["notification_channels"]:
            channel = ctx.guild.get_channel(int(channel_id))
            if channel:
                channels.append(channel.mention)
        
        if channels:
            await ctx.send("**Channels receiving match notifications:**\n" + "\n".join(channels))
        else:
            await ctx.send("No active notification channels found!")

async def setup(bot):
    await bot.add_cog(ChannelManagement(bot))