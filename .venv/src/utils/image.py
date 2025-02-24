from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, Any

def create_scoreboard_image(match_data: Dict[str, Any]) -> io.BytesIO:
    """Creates a scoreboard image from match data
    Returns a BytesIO object containing the PNG image"""
    
    # Constants for image creation
    PADDING = 20
    HEADER_HEIGHT = 60
    ROW_HEIGHT = 40
    COLUMN_WIDTHS = {
        'player': 200,
        'stats': 60,   # Width for K/D/A/KD/MK columns
        'adr': 70,     # Slightly wider for ADR
        'util': 70,    # Width for UTIL
        'elo': 80      # Width for ELO and change
    }
    
    # Calculate total dimensions
    total_width = (
        PADDING * 2 +
        COLUMN_WIDTHS['player'] +
        (COLUMN_WIDTHS['stats'] * 4) +
        COLUMN_WIDTHS['adr'] +
        COLUMN_WIDTHS['util'] +
        COLUMN_WIDTHS['elo']
    )
    total_height = (
        PADDING * 2 +
        HEADER_HEIGHT +
        (ROW_HEIGHT * len(match_data['players'])) +
        40  # Extra space for legend
    )
    
    try:
        # Create image with dark background
        image = Image.new('RGB', (total_width, total_height), '#2C2F33')
        draw = ImageDraw.Draw(image)
        
        # Load fonts (using default if custom font fails)
        try:
            header_font = ImageFont.truetype("arial.ttf", 24)
            regular_font = ImageFont.truetype("arial.ttf", 20)
            small_font = ImageFont.truetype("arial.ttf", 16)
        except:
            header_font = ImageFont.load_default()
            regular_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Draw header background
        header_bg = Image.new('RGB', (total_width, HEADER_HEIGHT), '#23272A')
        image.paste(header_bg, (0, 0))
        
        # Draw header information
        draw.text(
            (PADDING, PADDING),
            match_data['map'],
            font=header_font,
            fill='#FFFFFF'
        )
        draw.text(
            (PADDING + 200, PADDING),
            match_data['score'],
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
        header_widths = (
            [COLUMN_WIDTHS['player']] +
            [COLUMN_WIDTHS['stats']] * 4 +
            [COLUMN_WIDTHS['adr']] +
            [COLUMN_WIDTHS['stats']] +
            [COLUMN_WIDTHS['util']] +
            [COLUMN_WIDTHS['elo']] * 2
        )

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
            draw.text(
                (x, y + 8),
                player['name'],
                font=regular_font,
                fill='#FFFFFF'
            )
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
                draw.text(
                    (x, y + 8),
                    stat,
                    font=regular_font,
                    fill='#FFFFFF',
                    align='center'
                )
                x += COLUMN_WIDTHS['stats']

            # Draw ELO change with color
            elo_change = player['eloChange']
            if elo_change:
                color = '#43B581' if elo_change > 0 else '#F04747'
                text = f"+{elo_change}" if elo_change > 0 else str(elo_change)
            else:
                color = '#99AAB5'
                text = '-'
            
            draw.text(
                (x, y + 8),
                text,
                font=regular_font,
                fill=color,
                align='center'
            )

        # Draw legend at bottom
        legend_y = total_height - 30
        draw.text(
            (PADDING, legend_y),
            "MKs = Multi Kills | UTIL = Utility Damage | ADR = Average Damage per Round",
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
        error_draw.text(
            (20, 40),
            f"Error creating scoreboard: {str(e)}",
            fill='#FFFFFF'
        )
        error_bytes = io.BytesIO()
        error_image.save(error_bytes, format='PNG')
        error_bytes.seek(0)
        return error_bytes