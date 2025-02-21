# FACEIT Match Tracker Discord Bot

A Discord bot that tracks FACEIT players and notifies when they complete matches.

## Features

- Track FACEIT players and get notifications when they complete matches
- View recent match history for tracked players
- List all currently tracked players
- Detailed match information including scores, teammates, and opponents

## Setup

### Prerequisites

- Python 3.8 or higher
- A Discord bot token (create one at [Discord Developer Portal](https://discord.com/developers/applications))
- A FACEIT API key (get one at [FACEIT Developer Portal](https://developers.faceit.com/))

### Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/faceit-discord-bot.git
cd faceit-discord-bot
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory of the project with the following content:
```
DISCORD_TOKEN=your_discord_token_here
FACEIT_API_KEY=your_faceit_api_key_here
```

### Running the Bot

```
python bot.py
```

## Usage

Once the bot is running and has been invited to your Discord server, you can use the following commands:

- `!track <nickname>` - Start tracking a FACEIT player
- `!untrack <nickname>` - Stop tracking a FACEIT player
- `!list` - List all tracked players
- `!recent <nickname> [count]` - Show recent matches for a player (default: 3, max: 10)

## Notes

- The bot checks for match updates every 10 minutes
- Tracked players are saved to a JSON file so they persist between bot restarts
- The bot will only notify about finished matches

## License

MIT