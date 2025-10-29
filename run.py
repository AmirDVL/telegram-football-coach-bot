#!/usr/bin/env python3
"""
Football Coach Bot - Main Entry Point

This is the main entry point for running the Telegram bot.
It imports and runs the bot from the organized src/ structure.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the bot
from bot.main import main

if __name__ == "__main__":
    main()
