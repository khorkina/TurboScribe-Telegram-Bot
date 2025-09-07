#!/usr/bin/env python3
"""
Telegram Bot for Audio/Video Transcription and Translation
"""

import asyncio
import logging
from bot.main import main

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())