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
# Dictionary to store player ELO history
player_elo_history = {}
# Load tracked players from file if exists
try:
    with open('tracked_players.json', 'r') as f:
        tracked_players = json.load(f)
except FileNotFoundError:
    tracked_players = {}
    
# Load player ELO history from file if exists
try:
    with open('player_elo_history.json', 'r') as f:
        player_elo_history = json.load(f)
except FileNotFoundError:
    player_elo_history = {}

# Helper function to save tracked players to file
def save_tracked_players():
    with open('tracked_players.json', 'w') as f:
        json.dump(tracked_players, f)
        
# Helper function to save player ELO history to file
def save_player_elo_history():
    with open('player_elo_history.json', 'w') as f:
        json.dump(player_elo_history, f)
        
# Helper function to update player ELO
async def update_player_elo(session, player_id, game="cs2"):
    player_data = await fetch_player(session, player_id)
    
    if player_data and 'games' in player_data and game in player_data['games']:
        current_elo = player_data['games'][game].get('faceit_elo', 0)
        
        if player_id not in player_elo_history:
            player_elo_history[player_id] = {"current": current_elo, "history": []}
        else:
            # If ELO changed, add to history
            if player_elo_history[player_id]["current"] != current_elo:
                previous_elo = player_elo_history[player_id]["current"]
                elo_change = current_elo - previous_elo
                
                player_elo_history[player_id]["history"].append({
                    "previous": previous_elo,
                    "current": current_elo,
                    "change": elo_change,
                    "timestamp": datetime.now().timestamp()
                })
                
                player_elo_history[player_id]["current"] = current_elo
                
        save_player_elo_history()
        return current_elo, player_elo_history[player_id]["history"]
    
    return None, []

# Function to fetch player details from FACEIT API
async def fetch_player(session, nickname_or_id):
    """Fetch player details from FACEIT API by nickname or ID"""
    headers = {
        'Authorization': f'Bearer {FACEIT_API_KEY}'
    }
    
    # Check if this is likely an ID (length and format check)
    if len(nickname_or_id) >= 32 and '-' in nickname_or_id:
        # This is likely an ID, use the player ID endpoint
        url = f"{FACEIT_API_URL}/players/{nickname_or_id}"
    else:
        # This is likely a nickname, use the player lookup endpoint
        url = f"{FACEIT_API_URL}/players?nickname={nickname_or_id}"
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch player {nickname_or_id}: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error fetching player {nickname_or_id}: {str(e)}")
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
        return dt.strftime("%d.%m, %H:%M Uhr")
    return "Unbekannte Zeit"

# Create an embed for match details with stats
async def create_match_embed(match_data, player_nickname, session):
    match_id = match_data.get('match_id')
    game = match_data.get('game', 'Unknown Game')
    status = match_data.get('status', 'Unknown')
    
    # Get match teams and results
    teams = match_data.get('teams', {})
    results = match_data.get('results', {})
    
    # Fix the match URL
    faceit_url = match_data.get('faceit_url', '')
    if faceit_url:
        # Replace the {lang} placeholder with 'de'
        faceit_url = faceit_url.replace('{lang}', 'de')
        # Add /scoreboard if it doesn't already have it and if it contains 'room/'
        if 'room/' in faceit_url and not faceit_url.endswith('/scoreboard'):
            faceit_url = faceit_url + '/scoreboard'
    else:
        faceit_url = 'https://www.faceit.com'
    
    # Create embed
    embed = discord.Embed(
        title=f"Match Ergebnis",
        url=faceit_url,
        color=discord.Color.blue()
    )
    
    # Add match times
    finished_at = format_time(match_data.get('finished_at'))
    embed.add_field(name="Beendet", value=finished_at if match_data.get('finished_at') else "Läuft noch", inline=True)
    
    # Get match stats to find player performance and detailed round score
    stats_data = await fetch_match_stats(session, match_id)
    detailed_round_score = None
    player_id = None
    player_team = None
    rounds_played = 0
    win_status = "❓"  # Default unknown status
    
    if stats_data and 'rounds' in stats_data:
        # Get detailed round score
        for round_data in stats_data['rounds']:
            if 'round_stats' in round_data and 'Score' in round_data['round_stats']:
                detailed_round_score = round_data['round_stats']['Score']
                embed.add_field(name="Runden", value=detailed_round_score, inline=True)
                
                # Parse the round score safely to get the total rounds played
                try:
                    # Handle different score formats (e.g., "13:10" or "13 / 10")
                    if ':' in detailed_round_score:
                        score_parts = detailed_round_score.split(':')
                    elif '/' in detailed_round_score:
                        score_parts = detailed_round_score.split('/')
                    else:
                        score_parts = detailed_round_score.split()  # Split by whitespace
                    
                    # Extract numerical values
                    score_values = []
                    for part in score_parts:
                        # Extract digits only
                        digits = ''.join(filter(str.isdigit, part))
                        if digits:
                            score_values.append(int(digits))
                    
                    if len(score_values) >= 2:
                        rounds_played = sum(score_values[:2])  # Take the first two scores
                except Exception as e:
                    logger.error(f"Error parsing round score: {e}")
                    rounds_played = 0  # Default if parsing fails
                
                break
                
        # Find our player and their stats
        player_found = False
        for round_data in stats_data['rounds']:
            for team_index, team in enumerate(round_data.get('teams', [])):
                for player_stats in team.get('players', []):
                    player_name = player_stats.get('nickname', '')
                    
                    if player_name.lower() == player_nickname.lower():
                        player_found = True
                        player_id = player_stats.get('player_id')
                        player_team = f"team{team_index + 1}"  # team1 or team2
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
                        try:
                            kr_ratio = float(kills) / rounds_played if rounds_played > 0 else 0
                            kr_ratio = round(kr_ratio, 2)
                        except (ValueError, TypeError):
                            kr_ratio = 'N/A'
                        
                        # Add player performance section
                        embed.add_field(
                            name=f"Spieler: {player_name}",
                            value=(
                                f"Kills: {kills}\n"
                                f"Tode: {deaths}\n"
                                f"K/D: {kd_ratio}\n"
                                f"K/R: {kr_ratio}"
                            ),
                            inline=False
                        )
                        
                        # Break out once we found our player
                        break
                if player_found:
                    break
            if player_found:
                break
    
    # Determine if player won or lost
    if player_team and results and 'winner' in results:
        winner = results.get('winner')
        if winner == player_team or winner == player_team.replace('team', 'faction'):
            win_status = "✅ Easy Win"
            embed.color = discord.Color.green()
        else:
            win_status = "❌ Verkackt"
            embed.color = discord.Color.red()
    
    # Add win/loss status
    embed.add_field(name="Ergebnis", value=win_status, inline=True)
    
    # Update and fetch ELO information if we found the player ID
    if player_id:
        current_elo, elo_history = await update_player_elo(session, player_id, game)
        
        if current_elo:
            # Find the most recent ELO change if any
            elo_change_text = ""
            if elo_history and len(elo_history) > 0:
                last_change = elo_history[-1]
                change = last_change.get('change', 0)
                if change > 0:
                    elo_change_text = f" (+{change})"
                elif change < 0:
                    elo_change_text = f" ({change})"
            
            embed.add_field(
                name="ELO",
                value=f"{current_elo}{elo_change_text}",
                inline=True
            )
    
    return embed

@bot.event
async def on_ready():
    logger.info(f'Bot angemeldet als {bot.user}')
    check_match_updates.start()

@bot.command(name='track')
async def track_player(ctx, nickname):
    """Verfolge einen FACEIT-Spieler"""
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
        await ctx.send(f"Spieler {nickname} wird bereits verfolgt!")
        return
    
    async with aiohttp.ClientSession() as session:
        player_data = await fetch_player(session, nickname)
        
        if player_data:
            player_id = player_data.get('player_id')
            tracked_players[guild_id]["players"][nickname] = player_id
            tracked_players[guild_id]["last_matches"][player_id] = []
            
            # Initialize player ELO tracking
            if 'games' in player_data:
                for game_id, game_data in player_data['games'].items():
                    if 'faceit_elo' in game_data:
                        current_elo = game_data['faceit_elo']
                        if player_id not in player_elo_history:
                            player_elo_history[player_id] = {"current": current_elo, "history": []}
                        else:
                            player_elo_history[player_id]["current"] = current_elo
            
            save_tracked_players()
            save_player_elo_history()
            await ctx.send(f"FACEIT-Spieler wird jetzt verfolgt: {nickname} (ID: {player_id})")
        else:
            await ctx.send(f"Konnte Spieler mit Namen {nickname} nicht finden")

@bot.command(name='untrack')
async def untrack_player(ctx, nickname):
    """Höre auf, einen FACEIT-Spieler zu verfolgen"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in tracked_players:
        await ctx.send("Es werden keine Spieler in diesem Server verfolgt.")
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
        await ctx.send(f"Verfolgung von Spieler {nickname} beendet.")
    else:
        await ctx.send(f"Spieler {nickname} wird nicht verfolgt.")

@bot.command(name='list')
async def list_tracked_players(ctx):
    """Liste alle verfolgten FACEIT-Spieler auf"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in tracked_players or not tracked_players[guild_id]["players"]:
        await ctx.send("Es werden keine Spieler in diesem Server verfolgt.")
        return
    
    players_list = "\n".join(tracked_players[guild_id]["players"].keys())
    await ctx.send(f"**Verfolgte FACEIT-Spieler:**\n{players_list}")

@bot.command(name='recent')
async def recent_matches(ctx, nickname, count: int = 3):
    """Zeige aktuelle Matches für einen verfolgten Spieler"""
    if count > 10:
        count = 10  # Limit to 10 matches to avoid spamming
    
    async with aiohttp.ClientSession() as session:
        player_data = await fetch_player(session, nickname)
        
        if not player_data:
            await ctx.send(f"Konnte Spieler mit Namen {nickname} nicht finden")
            return
            
        player_id = player_data.get('player_id')
        history_data = await fetch_player_history(session, player_id, limit=count)
        
        if not history_data or 'items' not in history_data:
            await ctx.send(f"Konnte Match-Verlauf für Spieler {nickname} nicht abrufen")
            return
            
        matches = history_data['items']
        
        if not matches:
            await ctx.send(f"Keine aktuellen Matches für Spieler {nickname} gefunden")
            return
            
        for match in matches:
            match_id = match.get('match_id')
            match_details = await fetch_match_details(session, match_id)
            
            if match_details:
                embed = await create_match_embed(match_details, nickname, session)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Konnte Details für Match {match_id} nicht abrufen")

@bot.command(name='addchannel')
async def add_notification_channel(ctx, channel: discord.TextChannel = None):
    """Add a channel to receive match notifications
    Usage: !addchannel [#channel]
    If no channel is specified, uses the current channel"""
    guild_id = str(ctx.guild.id)
    channel = channel or ctx.channel
    
    # Initialize server entry if not exists
    if guild_id not in tracked_players:
        tracked_players[guild_id] = {
            "notification_channels": [],
            "players": {},
            "last_matches": {}
        }
    elif "notification_channels" not in tracked_players[guild_id]:
        tracked_players[guild_id]["notification_channels"] = []
    
    # Check if channel is already registered
    if str(channel.id) in tracked_players[guild_id]["notification_channels"]:
        await ctx.send(f"{channel.mention} is already receiving match notifications!")
        return
    
    # Add the channel
    tracked_players[guild_id]["notification_channels"].append(str(channel.id))
    save_tracked_players()
    await ctx.send(f"✅ {channel.mention} will now receive match notifications!")

@bot.command(name='removechannel')
async def remove_notification_channel(ctx, channel: discord.TextChannel = None):
    """Remove a channel from receiving match notifications
    Usage: !removechannel [#channel]
    If no channel is specified, uses the current channel"""
    guild_id = str(ctx.guild.id)
    channel = channel or ctx.channel
    
    if (guild_id not in tracked_players or 
        "notification_channels" not in tracked_players[guild_id] or
        str(channel.id) not in tracked_players[guild_id]["notification_channels"]):
        await ctx.send(f"{channel.mention} is not receiving match notifications!")
        return
    
    # Remove the channel
    tracked_players[guild_id]["notification_channels"].remove(str(channel.id))
    save_tracked_players()
    await ctx.send(f"❌ {channel.mention} will no longer receive match notifications!")

@bot.command(name='listchannels')
async def list_notification_channels(ctx):
    """List all channels that receive match notifications"""
    guild_id = str(ctx.guild.id)
    
    if (guild_id not in tracked_players or 
        "notification_channels" not in tracked_players[guild_id] or
        not tracked_players[guild_id]["notification_channels"]):
        await ctx.send("No channels are currently receiving match notifications!")
        return
    
    channels = []
    for channel_id in tracked_players[guild_id]["notification_channels"]:
        channel = ctx.guild.get_channel(int(channel_id))
        if channel:
            channels.append(channel.mention)
    
    if channels:
        await ctx.send("**Channels receiving match notifications:**\n" + "\n".join(channels))
    else:
        await ctx.send("No active notification channels found!")

@tasks.loop(minutes=5)
async def check_match_updates():
    """Check for match updates for all tracked players"""
    try:
        logger.info("Checking for match updates...")
        
        async with aiohttp.ClientSession() as session:
            for guild_id, guild_data in tracked_players.items():
                # Skip if no notification channels are set up
                if ("notification_channels" not in guild_data or 
                    not guild_data["notification_channels"]):
                    continue
                
                guild = bot.get_guild(int(guild_id))
                if not guild:
                    logger.warning(f"Could not find guild {guild_id}")
                    continue
                
                # Get all valid notification channels
                valid_channels = []
                for channel_id in guild_data["notification_channels"]:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        valid_channels.append(channel)
                    else:
                        logger.warning(f"Could not find channel {channel_id} in guild {guild_id}")
                
                if not valid_channels:
                    continue
                
                # Check each player's matches
                for nickname, player_id in guild_data["players"].items():
                    history_data = await fetch_player_history(session, player_id, limit=3)
                    
                    if not history_data or 'items' not in history_data:
                        logger.warning(f"Could not fetch match history for player {nickname}")
                        continue
                    
                    matches = history_data['items']
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
                                
                                # Send to all notification channels
                                for channel in valid_channels:
                                    try:
                                        await channel.send(f"New match result for {nickname}:", embed=embed)
                                    except Exception as e:
                                        logger.error(f"Error sending to channel {channel.id}: {str(e)}")
                    
                    # Update the known matches
                    tracked_players[guild_id]["last_matches"][player_id] = new_match_ids
            
            save_tracked_players()
    except Exception as e:
        logger.error(f"Error in match update check: {str(e)}")

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