import datetime
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from src.config import TRACKED_PLAYERS_FILE, PLAYER_ELO_HISTORY_FILE

logger = logging.getLogger('faceit_bot')

class StorageService:
    def __init__(self):
        """
        Initialize storage service with tracked players and ELO history
        Loads existing data or creates new storage files if they don't exist
        """
        self.tracked_players = self._load_json(TRACKED_PLAYERS_FILE, {})
        self.player_elo_history = self._load_json(PLAYER_ELO_HISTORY_FILE, {})

    @staticmethod
    def _load_json(filename: str, default: Any) -> Any:
        """
        Load data from a JSON file
        
        Args:
            filename (str): Path to the JSON file
            default (Any): Default value if file cannot be loaded
        
        Returns:
            Loaded JSON data or default value
        """
        try:
            # Ensure the directory exists
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            
            # Try to open and read the file
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create the file with default content
            try:
                with open(filename, 'w') as f:
                    json.dump(default, f)
                logger.info(f"Created new storage file: {filename}")
                return default
            except Exception as e:
                logger.error(f"Error creating {filename}: {str(e)}")
                return default
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding {filename}: {str(e)}")
            
            # Backup corrupted file
            try:
                backup_name = f"{filename}.backup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                Path(filename).rename(backup_name)
                logger.warning(f"Backed up corrupted file to {backup_name}")
                
                # Create a new file with default content
                with open(filename, 'w') as f:
                    json.dump(default, f)
                logger.info(f"Created new storage file: {filename}")
                
                return default
            except Exception as backup_error:
                logger.error(f"Error backing up corrupted file: {str(backup_error)}")
                return default

    def save_tracked_players(self) -> None:
        """
        Save tracked players data to file
        Handles potential file writing errors
        """
        try:
            with open(TRACKED_PLAYERS_FILE, 'w') as f:
                json.dump(self.tracked_players, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tracked players: {str(e)}")

    def save_player_elo_history(self) -> None:
        """
        Save player ELO history to file
        Handles potential file writing errors
        """
        try:
            with open(PLAYER_ELO_HISTORY_FILE, 'w') as f:
                json.dump(self.player_elo_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving player ELO history: {str(e)}")

    def get_guild_data(self, guild_id: str) -> Dict[str, Any]:
        """
        Retrieve or initialize data for a specific guild
        
        Args:
            guild_id (str): Discord guild ID
        
        Returns:
            Dict containing guild-specific data
        """
        if guild_id not in self.tracked_players:
            self.tracked_players[guild_id] = {
                "notification_channels": [],
                "players": {},
                "last_matches": {}
            }
            # Automatically save when new guild is added
            self.save_tracked_players()
        return self.tracked_players[guild_id]

    def add_player(self, guild_id: str, nickname: str, player_id: str) -> None:
        """
        Add a player to tracked players for a specific guild
        
        Args:
            guild_id (str): Discord guild ID
            nickname (str): Player's nickname
            player_id (str): Player's FACEIT ID
        """
        guild_data = self.get_guild_data(guild_id)
        guild_data["players"][nickname] = player_id
        
        # Initialize last matches for this player
        if player_id not in guild_data["last_matches"]:
            guild_data["last_matches"][player_id] = []
        
        self.save_tracked_players()

    def remove_player(self, guild_id: str, nickname: str) -> bool:
        """
        Remove a player from tracked players
        
        Args:
            guild_id (str): Discord guild ID
            nickname (str): Player's nickname
        
        Returns:
            bool: True if player was removed, False if not found
        """
        guild_data = self.get_guild_data(guild_id)
        
        if nickname in guild_data["players"]:
            player_id = guild_data["players"][nickname]
            
            # Remove player from tracked players
            del guild_data["players"][nickname]
            
            # Remove player's last matches
            if player_id in guild_data["last_matches"]:
                del guild_data["last_matches"][player_id]
            
            self.save_tracked_players()
            return True
        
        return False

    def update_player_elo(self, player_id: str, current_elo: int) -> None:
        """
        Update a player's ELO history
        
        Args:
            player_id (str): Player's FACEIT ID
            current_elo (int): Current ELO value
        """
        # If player not in ELO history, initialize
        if player_id not in self.player_elo_history:
            self.player_elo_history[player_id] = {
                "current": current_elo,
                "history": []
            }
        
        # Check if ELO has changed
        current_stored_elo = self.player_elo_history[player_id].get("current")
        if current_stored_elo != current_elo:
            # Calculate ELO change
            elo_change = current_elo - current_stored_elo if current_stored_elo is not None else 0
            
            # Add to ELO history
            self.player_elo_history[player_id]["history"].append({
                "previous": current_stored_elo,
                "current": current_elo,
                "change": elo_change,
                "timestamp": datetime.datetime.now().timestamp()
            })
            
            # Update current ELO
            self.player_elo_history[player_id]["current"] = current_elo
            
            # Save updated ELO history
            self.save_player_elo_history()