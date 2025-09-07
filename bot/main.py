"""
Main bot module
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config
from bot.handlers import router
from database.models import db

async def main():
    """Main function to run the bot"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Check if required environment variables are set
    if not Config.BOT_TOKEN:
        logging.error("BOT_TOKEN is not set!")
        return
    
    if not Config.OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not set!")
        return
    
    if not Config.DATABASE_URL:
        logging.error("DATABASE_URL is not set!")
        return
    
    # Initialize database
    await db.connect()
    logging.info("Database connected successfully")
    
    # Initialize bot and dispatcher
    bot = Bot(token=Config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register handlers
    dp.include_router(router)
    
    # Log startup
    bot_info = await bot.get_me()
    logging.info(f"Bot @{bot_info.username} started successfully!")
    
    try:
        # Start polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot error: {e}")
    finally:
        # Cleanup
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())