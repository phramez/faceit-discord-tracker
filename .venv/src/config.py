import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
FACEIT_API_KEY = os.getenv('FACEIT_API_KEY')
FACEIT_API_URL = "https://open.faceit.com/data/v4"

# File paths
TRACKED_PLAYERS_FILE = 'tracked_players.json'
PLAYER_ELO_HISTORY_FILE = 'player_elo_history.json'

# Match tracking configuration
MATCH_CHECK_INTERVAL = 5  # minutes
MAX_RECENT_MATCHES = 10
MAX_GROUP_MATCHES = 10

# Logging configuration
LOGGING_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGGING_LEVEL = logging.INFO