import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.config import FACEIT_API_KEY, FACEIT_API_URL

logger = logging.getLogger('faceit_bot')

class FaceitAPI:
    def __init__(self, session):
        self.session = session
        self.headers = {'Authorization': f'Bearer {FACEIT_API_KEY}'}

    async def fetch_player(self, nickname_or_id: str) -> Optional[Dict[str, Any]]:
        """Fetch player details from FACEIT API by nickname or ID"""
        # Determine if input is likely an ID or nickname
        if len(nickname_or_id) >= 32 and '-' in nickname_or_id:
            url = f"{FACEIT_API_URL}/players/{nickname_or_id}"
        else:
            url = f"{FACEIT_API_URL}/players?nickname={nickname_or_id}"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to fetch player {nickname_or_id}: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching player {nickname_or_id}: {str(e)}")
            return None

    async def fetch_player_history(
        self, 
        player_id: str, 
        game: str = "cs2", 
        limit: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Fetch player match history"""
        url = f"{FACEIT_API_URL}/players/{player_id}/history?game={game}&limit={limit}"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to fetch match history: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching match history: {str(e)}")
            return None

    async def fetch_match_details(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch match details"""
        url = f"{FACEIT_API_URL}/matches/{match_id}"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to fetch match details: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching match details: {str(e)}")
            return None

    async def fetch_match_stats(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch match statistics"""
        url = f"{FACEIT_API_URL}/matches/{match_id}/stats"
        
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to fetch match stats: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching match stats: {str(e)}")
            return None

    @staticmethod
    def format_time(timestamp: Optional[int]) -> str:
        """Format timestamp to readable string"""
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%d.%m, %H:%M Uhr")
        return "Unknown Time"