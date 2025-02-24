import os
import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from datetime import datetime
import json
import logging
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io
from typing import List, Dict

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

async def create_match_embed(match_data, player_nickname, session):
    match_id = match_data.get('match_id')
    game = match_data.get('game', 'Unknown Game')
    status = match_data.get('status', 'Unknown')
    
    # Get match teams and results
    teams = match_data.get('teams', {})
    results = match_data.get('results', {})
    winning_team = results.get('winner', '')
    
    # Create embed and handle winning team conversion
    winning_team = results.get('winner', '')
    if winning_team.startswith('faction'):
        winning_team = winning_team.replace('faction', 'team')
        
    embed = discord.Embed(
        title=f"Match Ergebnis",
        url=match_data.get('faceit_url', '').replace('{lang}', 'de'),
        color=discord.Color.blue()
    )
    
    # Add match times
    finished_at = format_time(match_data.get('finished_at'))
    embed.add_field(
        name="Beendet", 
        value=finished_at if match_data.get('finished_at') else "Läuft noch", 
        inline=True
    )
    
    # Get match stats
    stats_data = await fetch_match_stats(session, match_id)
    player_team = None
    
    if stats_data and 'rounds' in stats_data:
        for round_data in stats_data['rounds']:
            if 'round_stats' in round_data and 'Score' in round_data['round_stats']:
                round_score = round_data['round_stats']['Score']
                
                # Find player's team
                for team_idx, team in enumerate(round_data.get('teams', [])):
                    for player in team.get('players', []):
                        if player.get('nickname', '').lower() == player_nickname.lower():
                            player_team = f"team{team_idx + 1}"
                            break
                    if player_team:
                        break
                
                # Add win/loss indicator to round score
                win_indicator = "✅" if (winning_team == player_team) else "❌"
                embed.add_field(
                    name="Runden",
                    value=f"{round_score} {win_indicator}",
                    inline=True
                )
                break
                

        
        # Find our player and their stats
        player_found = False
        for round_data in stats_data['rounds']:
            for team in round_data.get('teams', []):
                for player_stats in team.get('players', []):
                    player_name = player_stats.get('nickname', '')
                    
                    if player_name.lower() == player_nickname.lower():
                        player_found = True
                        player_id = player_stats.get('player_id')
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
                        break
                if player_found:
                    break
            if player_found:
                break
    
    # Set embed color based on win/loss
    if player_team and winning_team:
        if winning_team == player_team:
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
            # Find the most recent ELO change
            elo_change_text = ""
            if elo_history and len(elo_history) > 0:
                last_change = elo_history[-1]
                change = last_change.get('change', 0)
                # Ensure ELO change matches win/loss status
                if winning_team == player_team:
                    change = abs(change)
                else:
                    change = -abs(change)
                
                if change > 0:
                    elo_change_text = f" (+{change})"
                else:
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

async def create_group_match_embed(match_data, tracked_players_info, session):
    """
    Create an embed and React component data for matches with 3+ tracked players
    tracked_players_info is a list of tuples (nickname, player_id)
    Returns a dict with 'embed' and 'react_data' keys
    """
    match_id = match_data.get('match_id')
    
    # Get match stats
    stats_data = await fetch_match_stats(session, match_id)
    if not stats_data or 'rounds' not in stats_data:
        return None

    # Process match data
    round_data = stats_data['rounds'][0]  # Get first round data
    map_name = round_data['round_stats'].get('Map', 'Unknown Map')
    score = round_data['round_stats'].get('Score', '0 / 0')
    winning_team = match_data.get('results', {}).get('winner', '')
    
    # Handle both team and faction naming
    if winning_team.startswith('faction'):
        winning_team = winning_team.replace('faction', 'team')

    # Initialize tracking variables
    player_teams = {}
    tracked_player_teams = set()
    all_player_stats = []

    # Process teams and players
    for team_idx, team in enumerate(round_data.get('teams', [])):
        team_name = f"team{team_idx + 1}"
        for player in team.get('players', []):
            player_id = player.get('player_id', '')
            player_name = player.get('nickname', '')
            
            # Check if this is a tracked player
            if any(p[0].lower() == player_name.lower() for p in tracked_players_info):
                player_teams[player_id] = team_name
                tracked_player_teams.add(team_name)
                
                stats = player.get('player_stats', {})
                
                # Get ELO info
                current_elo, elo_history = await update_player_elo(session, player_id)
                elo_change = 0
                if elo_history and len(elo_history) > 0:
                    if team_name == winning_team:
                        elo_change = abs(elo_history[-1].get('change', 0))
                    else:
                        elo_change = -abs(elo_history[-1].get('change', 0))

                # Calculate multi-kills
                multi_kills = (
                    int(stats.get('Double Kills', 0)) +
                    int(stats.get('Triple Kills', 0)) +
                    int(stats.get('Quadro Kills', 0)) +
                    int(stats.get('Penta Kills', 0))
                )

                # Prepare player stats
                player_data = {
                    'name': player_name,
                    'kills': int(stats.get('Kills', 0)),
                    'deaths': int(stats.get('Deaths', 0)),
                    'assists': int(stats.get('Assists', 0)),
                    'kd': float(stats.get('K/D Ratio', 0)),
                    'adr': float(stats.get('ADR', 0)),
                    'multiKills': multi_kills,
                    'utilityDmg': int(stats.get('Utility Damage', 0)),
                    'elo': current_elo,
                    'eloChange': elo_change
                }
                all_player_stats.append(player_data)

    # Sort players by ADR
    all_player_stats.sort(key=lambda x: x['adr'], reverse=True)

    # Create Discord embed
    embed = discord.Embed(
        title="🎮 Group Match Detected!",
        url=match_data.get('faceit_url', '').replace('{lang}', 'de'),
        color=discord.Color.gold()
    )

    # Add match info to embed
    finished_at = format_time(match_data.get('finished_at'))
    embed.add_field(
        name="Time", 
        value=finished_at if match_data.get('finished_at') else "In Progress", 
        inline=True
    )
    embed.add_field(name="Map", value=map_name, inline=True)
    embed.add_field(name="Score", value=score, inline=True)

    # Prepare React component data
    react_data = {
        'map': map_name,
        'score': score,
        'finishedAt': finished_at,
        'players': all_player_stats
    }

    return {
        'embed': embed,
        'react_data': react_data
    }


async def send_group_match_message(ctx, match_details, match_info, session):
    """
    Sends a group match message with both embed and scoreboard image
    """
    try:
        result = await create_group_match_embed(
            match_details,
            match_info['players'],
            session
        )
        
        if result:
            match_time = format_time(match_info['timestamp'])
            
            # Create the scoreboard image
            image_bytes = create_scoreboard_image(result['react_data'])
            
            # Create the file object for Discord
            discord_file = discord.File(
                fp=image_bytes,
                filename='scoreboard.png'
            )
            
            # Send the message with embed and image
            await ctx.send(
                f"📅 **Team Game on {match_time}** "
                f"with {len(match_info['players'])} players:",
                file=discord_file,
                embed=result['embed']
            )
            
    except Exception as e:
        logger.error(f"Error sending group match message: {str(e)}")
        await ctx.send("❌ An error occurred while creating the match visualization.")

@bot.command(name='grouphistory')
async def group_history(ctx, count: int = 5):
    """Show recent matches where 3+ tracked players played together"""
    if count > 10:
        count = 10
        await ctx.send("Maximum number of matches is 10. Showing 10 most recent matches.")
    
    guild_id = str(ctx.guild.id)
    if guild_id not in tracked_players or not tracked_players[guild_id]["players"]:
        await ctx.send("No players are being tracked in this server.")
        return

    await ctx.send("🔍 Searching for group matches... This might take a moment.")

    try:
        async with aiohttp.ClientSession() as session:
            # Collect all matches
            all_matches = {}
            
            # Get matches for each tracked player
            for nickname, player_id in tracked_players[guild_id]["players"].items():
                history_data = await fetch_player_history(session, player_id, limit=20)
                
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
                match_details = await fetch_match_details(session, match_id)
                if match_details:
                    await send_group_match_message(ctx, match_details, match_info, session)

    except Exception as e:
        logger.error(f"Error in group history: {str(e)}")
        await ctx.send("❌ An error occurred while fetching group match history.")


def create_scoreboard_image(match_data: Dict) -> io.BytesIO:
    """
    Creates a scoreboard image from match data
    Returns a BytesIO object containing the PNG image
    """
    # Constants for image creation
    PADDING = 20
    HEADER_HEIGHT = 60
    ROW_HEIGHT = 40
    COLUMN_WIDTHS = {
        'player': 200,
        'stats': 60,  # Width for K/D/A/KD/MK columns
        'adr': 70,    # Slightly wider for ADR
        'util': 70,   # Width for UTIL
        'elo': 80     # Width for ELO and change
    }
    
    # Calculate total width and height
    total_width = PADDING * 2 + COLUMN_WIDTHS['player'] + (COLUMN_WIDTHS['stats'] * 4) + \
                 COLUMN_WIDTHS['adr'] + COLUMN_WIDTHS['util'] + COLUMN_WIDTHS['elo']
    total_height = PADDING * 2 + HEADER_HEIGHT + (ROW_HEIGHT * len(match_data['players'])) + 40  # Extra 40px for legend
    
    # Create image with dark background
    image = Image.new('RGB', (total_width, total_height), '#2C2F33')
    draw = ImageDraw.Draw(image)
    
    try:
        # Load fonts (using default if custom font fails)
        try:
            header_font = ImageFont.truetype("arial.ttf", 24)
            regular_font = ImageFont.truetype("arial.ttf", 20)
            small_font = ImageFont.truetype("arial.ttf", 16)
        except:
            header_font = ImageFont.load_default()
            regular_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Draw header
        header_bg = Image.new('RGB', (total_width, HEADER_HEIGHT), '#23272A')
        image.paste(header_bg, (0, 0))
        
        # Draw map and score
        draw.text(
            (PADDING, PADDING),
            f"{match_data['map']}",
            font=header_font,
            fill='#FFFFFF'
        )
        draw.text(
            (PADDING + 200, PADDING),
            f"{match_data['score']}",
            font=header_font,
            fill='#FFFFFF'
        )
        draw.text(
            (total_width - 200, PADDING),
            match_data['finishedAt'],
            font=small_font,
            fill='#99AAB5'
        )

        # Draw column headers
        y = HEADER_HEIGHT + 10
        x = PADDING
        headers = ['Player', 'K', 'D', 'A', 'K/D', 'ADR', 'MKs', 'UTIL', 'ELO', 'Δ']
        header_widths = [COLUMN_WIDTHS['player']] + [COLUMN_WIDTHS['stats']] * 4 + \
                       [COLUMN_WIDTHS['adr']] + [COLUMN_WIDTHS['stats']] + \
                       [COLUMN_WIDTHS['util']] + [COLUMN_WIDTHS['elo']] * 2

        for header, width in zip(headers, header_widths):
            draw.text((x, y), header, font=regular_font, fill='#99AAB5')
            x += width

        # Draw player rows
        for idx, player in enumerate(match_data['players']):
            y = HEADER_HEIGHT + ROW_HEIGHT + (ROW_HEIGHT * idx)
            x = PADDING
            
            # Alternate row backgrounds
            if idx % 2 == 0:
                row_bg = Image.new('RGB', (total_width, ROW_HEIGHT), '#2F3136')
                image.paste(row_bg, (0, y))

            # Draw player name
            draw.text((x, y + 8), player['name'], font=regular_font, fill='#FFFFFF')
            x += COLUMN_WIDTHS['player']

            # Draw stats
            stats = [
                str(player['kills']),
                str(player['deaths']),
                str(player['assists']),
                f"{player['kd']:.2f}",
                f"{player['adr']:.1f}",
                str(player['multiKills']),
                str(player['utilityDmg']),
                str(player['elo'] or '-'),
            ]
            
            # Draw each stat
            for stat in stats[:-1]:  # All except ELO change
                draw.text((x, y + 8), stat, font=regular_font, fill='#FFFFFF', align='center')
                x += COLUMN_WIDTHS['stats']

            # Draw ELO change with color
            elo_change = player['eloChange']
            if elo_change:
                color = '#43B581' if elo_change > 0 else '#F04747'
                text = f"+{elo_change}" if elo_change > 0 else str(elo_change)
            else:
                color = '#99AAB5'
                text = '-'
            draw.text((x, y + 8), text, font=regular_font, fill=color, align='center')

        # Draw legend
        legend_y = total_height - 30
        draw.text(
            (PADDING, legend_y),
            "MKs = Multi Kills (Double + Triple + Quadro + Penta)  |  UTIL = Utility Damage",
            font=small_font,
            fill='#99AAB5'
        )

        # Convert to bytes
        byte_array = io.BytesIO()
        image.save(byte_array, format='PNG')
        byte_array.seek(0)
        return byte_array

    except Exception as e:
        # If there's an error, create a simple error image
        error_image = Image.new('RGB', (400, 100), '#2C2F33')
        error_draw = ImageDraw.Draw(error_image)
        error_draw.text((20, 40), f"Error creating scoreboard: {str(e)}", fill='#FFFFFF')
        error_bytes = io.BytesIO()
        error_image.save(error_bytes, format='PNG')
        error_bytes.seek(0)
        return error_bytes

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
                
                if not valid_channels:
                    continue

                # Track matches that have multiple tracked players
                group_matches = {}  # match_id -> list of (nickname, player_id)
                
                # First pass: collect all matches and their players
                for nickname, player_id in guild_data["players"].items():
                    history_data = await fetch_player_history(session, player_id, limit=3)
                    
                    if not history_data or 'items' not in history_data:
                        continue
                    
                    for match in history_data['items']:
                        match_id = match.get('match_id')
                        if match_id not in group_matches:
                            group_matches[match_id] = []
                        group_matches[match_id].append((nickname, player_id))

                # Second pass: process matches
                for match_id, players in group_matches.items():
                    # Skip if we've already processed this match
                    if any(match_id in tracked_players[guild_id]["last_matches"].get(pid, [])
                         for _, pid in players):
                        continue

                    match_details = await fetch_match_details(session, match_id)
                    if not match_details or match_details.get('status') != 'FINISHED':
                        continue

                    # For matches with 3+ tracked players, create special group embed
                    if len(players) >= 3:
                        group_embed = await create_group_match_embed(
                            match_details, 
                            players,
                            session
                        )
                        if group_embed:
                            for channel in valid_channels:
                                try:
                                    await channel.send(
                                        f"🎮 **Gruppenspiel gefunden mit {len(players)} Spielern!**",
                                        embed=group_embed
                                    )
                                except Exception as e:
                                    logger.error(f"Error sending to channel {channel.id}: {str(e)}")
                    else:
                        # Regular match processing for matches with 1-2 players
                        for nickname, player_id in players:
                            embed = await create_match_embed(match_details, nickname, session)
                            for channel in valid_channels:
                                try:
                                    await channel.send(f"Neues Match-Ergebnis für {nickname}:", embed=embed)
                                except Exception as e:
                                    logger.error(f"Error sending to channel {channel.id}: {str(e)}")

                    # Update last matches for all players in this match
                    for _, player_id in players:
                        if player_id not in tracked_players[guild_id]["last_matches"]:
                            tracked_players[guild_id]["last_matches"][player_id] = []
                        tracked_players[guild_id]["last_matches"][player_id].append(match_id)

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