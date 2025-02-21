import os
import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from datetime import datetime
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('faceit_bot')

# Configuration (Load from environment variables or config file)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
FACEIT_API_KEY = os.getenv('FACEIT_API_KEY')
FACEIT_API_URL = "https://open.faceit.com/data/v4"

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store tracked players per server
tracked_players = {}
# Load tracked players from file if exists
try:
    with open('tracked_players.json', 'r') as f:
        tracked_players = json.load(f)
except FileNotFoundError:
    tracked_players = {}

# Helper function to save tracked players to file
def save_tracked_players():
    with open('tracked_players.json', 'w') as f:
        json.dump(tracked_players, f)

# Function to fetch player details from FACEIT API
async def fetch_player(session, nickname):
    headers = {
        'Authorization': f'Bearer {FACEIT_API_KEY}'
    }
    
    url = f"{FACEIT_API_URL}/players?nickname={nickname}"
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch player {nickname}: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error fetching player {nickname}: {str(e)}")
        return None

# Function to fetch player match history
async def fetch_player_history(session, player_id, game="cs2", limit=5):
    headers = {
        'Authorization': f'Bearer {FACEIT_API_KEY}'
    }
    
    url = f"{FACEIT_API_URL}/players/{player_id}/history?game={game}&limit={limit}"
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch match history for player {player_id}: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error fetching match history for player {player_id}: {str(e)}")
        return None

# Function to fetch match details
async def fetch_match_details(session, match_id):
    headers = {
        'Authorization': f'Bearer {FACEIT_API_KEY}'
    }
    
    url = f"{FACEIT_API_URL}/matches/{match_id}"
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch match details for match {match_id}: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error fetching match details for match {match_id}: {str(e)}")
        return None

# Function to fetch match stats
async def fetch_match_stats(session, match_id):
    headers = {
        'Authorization': f'Bearer {FACEIT_API_KEY}'
    }
    
    url = f"{FACEIT_API_URL}/matches/{match_id}/stats"
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch match stats for match {match_id}: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error fetching match stats for match {match_id}: {str(e)}")
        return None

# Format timestamp
def format_time(timestamp):
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    return "Unknown time"

# Create an embed for match details with stats
async def create_match_embed(match_data, player_nickname, session):
    match_id = match_data.get('match_id')
    game = match_data.get('game', 'Unknown Game')
    status = match_data.get('status', 'Unknown')
    
    # Get match teams and results
    teams = match_data.get('teams', {})
    results = match_data.get('results', {})
    
    # Create embed
    embed = discord.Embed(
        title=f"Match Result",
        url=match_data.get('faceit_url', 'https://www.faceit.com'),
        color=discord.Color.blue()
    )
    
    # Add match times
    finished_at = format_time(match_data.get('finished_at'))
    embed.add_field(name="Finished", value=finished_at if match_data.get('finished_at') else "In progress", inline=True)
    
    # Add match score
    if results and 'score' in results:
        team1_score = results['score'].get('faction1', '0')
        team2_score = results['score'].get('faction2', '0')
        embed.add_field(name="Score", value=f"{team1_score} - {team2_score}", inline=True)
    
    # Get match stats to find player performance
    stats_data = await fetch_match_stats(session, match_id)
    if stats_data and 'rounds' in stats_data:
        # Find our player and their stats
        player_found = False
        for round_data in stats_data['rounds']:
            for team in round_data.get('teams', []):
                for player_stats in team.get('players', []):
                    player_name = player_stats.get('nickname', '')
                    
                    if player_name.lower() == player_nickname.lower():
                        player_found = True
                        stats = player_stats.get('player_stats', {})
                        
                        # Add player stats to embed
                        kills = stats.get('Kills', 'N/A')
                        deaths = stats.get('Deaths', 'N/A')
                        
                        # Calculate K/D
                        try:
                            kd_ratio = float(kills) / float(deaths) if float(deaths) > 0 else float(kills)
                            kd_ratio = round(kd_ratio, 2)
                        except (ValueError, TypeError):
                            kd_ratio = 'N/A'
                        
                        # Calculate K/R (kills per round)
                        rounds_played = int(team1_score) + int(team2_score)
                        try:
                            kr_ratio = float(kills) / rounds_played if rounds_played > 0 else 0
                            kr_ratio = round(kr_ratio, 2)
                        except (ValueError, TypeError):
                            kr_ratio = 'N/A'
                            
                        # Get ADR if available
                        adr = stats.get('Average Damage per Round', 'N/A')
                        
                        # Add player performance section
                        embed.add_field(
                            name=f"Player: {player_name}",
                            value=(
                                f"Kills: {kills}\n"
                                f"Deaths: {deaths}\n"
                                f"K/D: {kd_ratio}\n"
                                f"K/R: {kr_ratio}\n"
                                f"ADR: {adr}"
                            ),
                            inline=False
                        )
                        
                        # Break out once we found our player
                        break
                if player_found:
                    break
            if player_found:
                break
    
    # Note about ELO change - FACEIT API doesn't directly provide ELO changes
    # We would need to track player ELO before and after matches to calculate this
    embed.set_footer(text="ELO changes are not directly available through the FACEIT API")
    
    return embed

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user}')
    check_match_updates.start()

@bot.command(name='track')
async def track_player(ctx, nickname):
    """Track a FACEIT player's matches"""
    guild_id = str(ctx.guild.id)
    
    # Initialize server entry if not exists
    if guild_id not in tracked_players:
        tracked_players[guild_id] = {
            "channel_id": str(ctx.channel.id),
            "players": {},
            "last_matches": {}
        }
    
    # Check if player already tracked
    if nickname.lower() in [p.lower() for p in tracked_players[guild_id]["players"]]:
        await ctx.send(f"Player {nickname} is already being tracked!")
        return
    
    async with aiohttp.ClientSession() as session:
        player_data = await fetch_player(session, nickname)
        
        if player_data:
            player_id = player_data.get('player_id')
            tracked_players[guild_id]["players"][nickname] = player_id
            tracked_players[guild_id]["last_matches"][player_id] = []
            
            save_tracked_players()
            await ctx.send(f"Now tracking FACEIT player: {nickname} (ID: {player_id})")
        else:
            await ctx.send(f"Could not find player with nickname: {nickname}")

@bot.command(name='untrack')
async def untrack_player(ctx, nickname):
    """Stop tracking a FACEIT player's matches"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in tracked_players:
        await ctx.send("No players are being tracked in this server.")
        return
    
    player_found = False
    for player_name, player_id in list(tracked_players[guild_id]["players"].items()):
        if player_name.lower() == nickname.lower():
            del tracked_players[guild_id]["players"][player_name]
            if player_id in tracked_players[guild_id]["last_matches"]:
                del tracked_players[guild_id]["last_matches"][player_id]
            player_found = True
            break
    
    if player_found:
        save_tracked_players()
        await ctx.send(f"Stopped tracking player: {nickname}")
    else:
        await ctx.send(f"Player {nickname} is not being tracked.")

@bot.command(name='list')
async def list_tracked_players(ctx):
    """List all tracked FACEIT players"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in tracked_players or not tracked_players[guild_id]["players"]:
        await ctx.send("No players are being tracked in this server.")
        return
    
    players_list = "\n".join(tracked_players[guild_id]["players"].keys())
    await ctx.send(f"**Tracked FACEIT players:**\n{players_list}")

@bot.command(name='recent')
async def recent_matches(ctx, nickname, count: int = 3):
    """Show recent matches for a tracked player"""
    if count > 10:
        count = 10  # Limit to 10 matches to avoid spamming
    
    async with aiohttp.ClientSession() as session:
        player_data = await fetch_player(session, nickname)
        
        if not player_data:
            await ctx.send(f"Could not find player with nickname: {nickname}")
            return
            
        player_id = player_data.get('player_id')
        history_data = await fetch_player_history(session, player_id, limit=count)
        
        if not history_data or 'items' not in history_data:
            await ctx.send(f"Could not fetch match history for player: {nickname}")
            return
            
        matches = history_data['items']
        
        if not matches:
            await ctx.send(f"No recent matches found for player: {nickname}")
            return
            
        for match in matches:
            match_id = match.get('match_id')
            match_details = await fetch_match_details(session, match_id)
            
            if match_details:
                embed = await create_match_embed(match_details, nickname, session)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Could not fetch details for match: {match_id}")

@tasks.loop(minutes=10)
async def check_match_updates():
    """Check for match updates for all tracked players"""
    try:
        logger.info("Checking for match updates...")
        
        async with aiohttp.ClientSession() as session:
            for guild_id, guild_data in tracked_players.items():
                channel_id = guild_data.get("channel_id")
                channel = bot.get_channel(int(channel_id)) if channel_id else None
                
                if not channel:
                    logger.warning(f"Could not find channel for guild {guild_id}")
                    continue
                
                for nickname, player_id in guild_data["players"].items():
                    # Get match history
                    history_data = await fetch_player_history(session, player_id, limit=3)
                    
                    if not history_data or 'items' not in history_data:
                        logger.warning(f"Could not fetch match history for player: {nickname}")
                        continue
                    
                    matches = history_data['items']
                    
                    # Check if there are new matches
                    known_match_ids = tracked_players[guild_id]["last_matches"].get(player_id, [])
                    new_match_ids = []
                    
                    for match in matches:
                        match_id = match.get('match_id')
                        new_match_ids.append(match_id)
                        
                        # If this is a new match
                        if match_id not in known_match_ids:
                            match_details = await fetch_match_details(session, match_id)
                            
                            if match_details and match_details.get('status') == 'FINISHED':
                                embed = await create_match_embed(match_details, nickname, session)
                                await channel.send(f"New match result for {nickname}:", embed=embed)
                    
                    # Update the known matches
                    tracked_players[guild_id]["last_matches"][player_id] = new_match_ids
            
            save_tracked_players()
    except Exception as e:
        logger.error(f"Error in check_match_updates task: {str(e)}")

@check_match_updates.before_loop
async def before_check_match_updates():
    await bot.wait_until_ready()

# Run the bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set")
        exit(1)
    if not FACEIT_API_KEY:
        logger.error("FACEIT_API_KEY environment variable not set")
        exit(1)
    
    logger.info("Starting bot...")
    bot.run(DISCORD_TOKEN)