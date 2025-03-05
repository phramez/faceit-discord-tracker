import discord
from typing import Dict, Any, List, Tuple, Optional
import logging

from src.services.faceit_api import FaceitAPI
from src.services.storage import StorageService

logger = logging.getLogger('faceit_bot')

async def create_match_embed(match_data: Dict[str, Any], player_nickname: str, session) -> discord.Embed:
    """Create a Discord embed for a match"""
    faceit_api = FaceitAPI(session)
    storage = StorageService()
    
    match_id = match_data.get('match_id')
    game = match_data.get('game', 'Unknown Game')
    results = match_data.get('results', {})
    winning_team = results.get('winner', '').replace('faction', 'team')
    
    embed = discord.Embed(
        title="Match Result",
        url=match_data.get('faceit_url', '').replace('{lang}', 'de'),
        color=discord.Color.blue()
    )
    
    # Add match times
    finished_at = faceit_api.format_time(match_data.get('finished_at'))
    embed.add_field(
        name="Finished", 
        value=finished_at if match_data.get('finished_at') else "In Progress", 
        inline=True
    )
    
    # Get match stats
    stats_data = await faceit_api.fetch_match_stats(match_id)
    player_team = None
    player_id = None
    
    if stats_data and 'rounds' in stats_data:
        for round_data in stats_data['rounds']:
            # Process round score
            if 'round_stats' in round_data and 'Score' in round_data['round_stats']:
                round_score = round_data['round_stats']['Score']
                
                # Find player's team
                for team_idx, team in enumerate(round_data.get('teams', [])):
                    for player in team.get('players', []):
                        if player.get('nickname', '').lower() == player_nickname.lower():
                            player_team = f"team{team_idx + 1}"
                            player_id = player.get('player_id')
                            break
                    if player_team:
                        break
                
                # Add win/loss indicator to round score
                win_indicator = "✅" if (winning_team == player_team) else "❌"
                embed.add_field(
                    name="Rounds",
                    value=f"{round_score} {win_indicator}",
                    inline=True
                )
                break
        
        # Find player stats
        for round_data in stats_data['rounds']:
            for team in round_data.get('teams', []):
                for player_stats in team.get('players', []):
                    if player_stats.get('nickname', '').lower() == player_nickname.lower():
                        stats = player_stats.get('player_stats', {})
                        
                        # Calculate stats
                        kills = stats.get('Kills', 'N/A')
                        deaths = stats.get('Deaths', 'N/A')
                        
                        try:
                            kd_ratio = float(kills) / float(deaths) if float(deaths) > 0 else float(kills)
                            kd_ratio = round(kd_ratio, 2)
                        except (ValueError, TypeError):
                            kd_ratio = 'N/A'
                        
                        # Add player performance section
                        embed.add_field(
                            name=f"Player: {player_nickname}",
                            value=(
                                f"Kills: {kills}\n"
                                f"Deaths: {deaths}\n"
                                f"K/D: {kd_ratio}"
                            ),
                            inline=False
                        )
    
    # Set embed color based on win/loss
    if player_team and winning_team:
        if winning_team == player_team:
            win_status = "✅ Victory"
            embed.color = discord.Color.green()
        else:
            win_status = "❌ Defeat"
            embed.color = discord.Color.red()
        embed.add_field(name="Result", value=win_status, inline=True)
    
    # Add ELO information
    if player_id:
        current_elo = storage.player_elo_history.get(player_id, {}).get('current')
        elo_history = storage.player_elo_history.get(player_id, {}).get('history', [])
        
        if current_elo:
            elo_change_text = ""
            if elo_history:
                last_change = elo_history[-1]
                change = last_change.get('change', 0)
                
                # Ensure ELO change matches win/loss status
                if winning_team == player_team:
                    change = abs(change)
                else:
                    change = -abs(change)
                
                elo_change_text = f" ({'+' if change > 0 else ''}{change})"
            
            embed.add_field(
                name="ELO",
                value=f"{current_elo}{elo_change_text}",
                inline=True
            )
    
    return embed

async def create_group_match_embed(
    match_data: Dict[str, Any],
    tracked_players_info: List[Tuple[str, str]],
    session
) -> Optional[Dict[str, Any]]:
    """Create embed data for matches with 3+ tracked players"""
    faceit_api = FaceitAPI(session)
    storage = StorageService()
    
    match_id = match_data.get('match_id')
    stats_data = await faceit_api.fetch_match_stats(match_id)
    
    if not stats_data or 'rounds' not in stats_data:
        return None

    # Process match data
    round_data = stats_data['rounds'][0]
    map_name_raw = round_data['round_stats'].get('Map', 'Unknown Map')
    
    # Format map name (de_inferno -> Inferno)
    map_name = map_name_raw
    if map_name_raw.startswith('de_'):
        map_name = map_name_raw[3:].capitalize()
    
    score = round_data['round_stats'].get('Score', '0 / 0')
    winning_team = match_data.get('results', {}).get('winner', '').replace('faction', 'team')

    # Track player information
    player_teams = {}
    tracked_player_teams = set()
    players_by_team = {"team1": 0, "team2": 0}
    all_player_stats = []

    # Process teams and players
    for team_idx, team in enumerate(round_data.get('teams', [])):
        team_name = f"team{team_idx + 1}"
        for player in team.get('players', []):
            player_id = player.get('player_id', '')
            player_name = player.get('nickname', '')
            
            if any(p[0].lower() == player_name.lower() for p in tracked_players_info):
                player_teams[player_id] = team_name
                tracked_player_teams.add(team_name)
                players_by_team[team_name] += 1
                
                stats = player.get('player_stats', {})
                
                # Get ELO info
                current_elo = storage.player_elo_history.get(player_id, {}).get('current')
                elo_history = storage.player_elo_history.get(player_id, {}).get('history', [])
                elo_change = 0
                
                if elo_history:
                    last_change = elo_history[-1].get('change', 0)
                    if team_name == winning_team:
                        elo_change = abs(last_change)
                    else:
                        elo_change = -abs(last_change)

                # Calculate multi-kills
                multi_kills = sum(int(stats.get(kill_type, 0)) for kill_type in [
                    'Double Kills', 'Triple Kills', 'Quadro Kills', 'Penta Kills'
                ])

                # Prepare player stats
                all_player_stats.append({
                    'name': player_name,
                    'kills': int(stats.get('Kills', 0)),
                    'deaths': int(stats.get('Deaths', 0)),
                    'assists': int(stats.get('Assists', 0)),
                    'kd': float(stats.get('K/D Ratio', 0)),
                    'adr': float(stats.get('ADR', 0)),
                    'multiKills': multi_kills,
                    'utilityDmg': int(stats.get('Utility Damage', 0)),
                    'elo': current_elo,
                    'eloChange': elo_change,
                    'team': team_name
                })

    # Sort players by ADR
    all_player_stats.sort(key=lambda x: x['adr'], reverse=True)
    
    # Determine if match was won by majority of tracked players
    majority_team = "team1" if players_by_team["team1"] > players_by_team["team2"] else "team2"
    match_won = majority_team == winning_team
    win_indicator = "WIN" if match_won else "LOSS"

    # Create Discord embed - still use emoji in Discord embed since it renders fine there
    embed_indicator = "✅" if match_won else "❌"
    embed = discord.Embed(
        title=f"{embed_indicator} Group Match",
        url=match_data.get('faceit_url', '').replace('{lang}', 'de'),
        color=discord.Color.green() if match_won else discord.Color.red()
    )

    # Add match info
    finished_at = faceit_api.format_time(match_data.get('finished_at'))
    embed.add_field(name="Time", value=finished_at, inline=True)
    embed.add_field(name="Map", value=map_name, inline=True)
    embed.add_field(name="Score", value=score, inline=True)

    return {
        'embed': embed,
        'react_data': {
            'map': map_name,
            'score': score,
            'finishedAt': finished_at,
            'players': all_player_stats,
            'win_indicator': win_indicator,
            'match_won': match_won
        }
    }