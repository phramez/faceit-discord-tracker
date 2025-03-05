"""
Core services for FACEIT API interaction, match tracking, and data storage.
"""

from .faceit_api import FaceitAPI
from .storage import StorageService

# Intentionally not importing match_tracker to avoid circular imports
# These are imported where needed

__all__ = ['FaceitAPI', 'StorageService']

# Function to avoid circular imports
async def start_match_tracker(bot):
    """Start the match tracker service"""
    from .match_tracker import MatchTracker
    tracker = MatchTracker(bot)
    return tracker