import datetime
import json
import logging
from typing import Dict, Any
from src.config import TRACKED_PLAYERS_FILE, PLAYER_ELO_HISTORY_FILE

logger = logging.getLogger('faceit_bot')

class StorageService:
    def __init__(self):
        self.tracked_players = self._load_json(TRACKED_PLAYERS_FILE, {})
        self.player_elo_history = self._load_json(PLAYER_ELO_HISTORY_FILE, {})

    @staticmethod
    def _load_json(filename: str, default: Any) -> Any:
        """Load data from JSON file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return default
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding {filename}: {str(e)}")
            return default

    def save_tracked_players(self) -> None:
        """Save tracked players to file"""
        try:
            with open(TRACKED_PLAYERS_FILE, 'w') as f:
                json.dump(self.tracked_players, f)
        except Exception as e:
            logger.error(f"Error saving tracked players: {str(e)}")

    def save_player_elo_history(self) -> None:
        """Save player ELO history to file"""
        try:
            with open(PLAYER_ELO_HISTORY_FILE, 'w') as f:
                json.dump(self.player_elo_history, f)
        except Exception as e:
            logger.error(f"Error saving player ELO history: {str(e)}")

    def get_guild_data(self, guild_id: str) -> Dict[str, Any]:
        """Get guild data, initialize if not exists"""
        if guild_id not in self.tracked_players:
            self.tracked_players[guild_id] = {
                "notification_channels": [],
                "players": {},
                "last_matches": {}
            }
        return self.tracked_players[guild_id]

    def add_player(self, guild_id: str, nickname: str, player_id: str) -> None:
        """Add player to tracked players"""
        guild_data = self.get_guild_data(guild_id)
        guild_data["players"][nickname] = player_id
        guild_data["last_matches"][player_id] = []
        self.save_tracked_players()

    def remove_player(self, guild_id: str, nickname: str) -> bool:
        """Remove player from tracked players"""
        guild_data = self.get_guild_data(guild_id)
        if nickname in guild_data["players"]:
            player_id = guild_data["players"][nickname]
            del guild_data["players"][nickname]
            if player_id in guild_data["last_matches"]:
                del guild_data["last_matches"][player_id]
            self.save_tracked_players()
            return True
        return False

    def update_player_elo(self, player_id: str, current_elo: int) -> None:
        """Update player's ELO history"""
        if player_id not in self.player_elo_history:
            self.player_elo_history[player_id] = {
                "current": current_elo,
                "history": []
            }
        elif self.player_elo_history[player_id]["current"] != current_elo:
            self.player_elo_history[player_id]["history"].append({
                "previous": self.player_elo_history[player_id]["current"],
                "current": current_elo,
                "change": current_elo - self.player_elo_history[player_id]["current"],
                "timestamp": datetime.now().timestamp()
            })
            self.player_elo_history[player_id]["current"] = current_elo
            self.save_player_elo_history()