# FACEIT Discord Bot

A Discord bot for tracking FACEIT players and matches in CS2.

## Features

- Track FACEIT players and their match results
- Get notifications when tracked players finish matches
- View recent matches and stats
- Track group matches where multiple players played together
- Monitor ELO changes

## Setup

1. Make sure you have Python 3.9+ installed
2. Clone this repository
3. Create a virtual environment (optional but recommended):
   ```
   python -m venv .venv
   ```
4. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`
5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
6. Set up environment variables in a `.env` file:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   FACEIT_API_KEY=your_faceit_api_key
   ```
   
   You need to create a Discord bot at [Discord Developer Portal](https://discord.com/developers/applications) 
   and get a FACEIT API key from [FACEIT Developer Portal](https://developers.faceit.com/).

## Running the Bot

### Windows
Double-click `run_bot.bat` or run from command line:
```
.venv\Scripts\python main.py
```

### Mac/Linux
Make the script executable first:
```
chmod +x run_bot.sh
```

Then run:
```
./run_bot.sh
```

Or directly:
```
.venv/bin/python main.py
```

## Discord Commands

- `!track <nickname>` - Track a FACEIT player
- `!untrack <nickname>` - Stop tracking a player
- `!list` - List all tracked players
- `!recent <nickname> [count]` - Show recent matches for a player
- `!grouphistory [count]` - Show matches where 3+ tracked players played together
- `!addchannel [#channel]` - Add a channel for notifications
- `!removechannel [#channel]` - Remove a channel from notifications
- `!listchannels` - List all notification channels

## Project Structure

```
├── main.py                 # Main entry point
├── .env                    # Environment variables (create this)
├── tracked_players.json    # Storage for tracked players
├── player_elo_history.json # Storage for ELO history
├── src/
│   ├── bot.py              # Bot setup and initialization
│   ├── config.py           # Configuration variables
│   ├── cogs/               # Discord command modules
│   ├── services/           # Core services
│   └── utils/              # Utility modules
```

## Troubleshooting

- If the bot doesn't run, check that your `.env` file is properly set up
- Make sure the bot has the necessary permissions in your Discord server
- Check the logs for detailed error messages
